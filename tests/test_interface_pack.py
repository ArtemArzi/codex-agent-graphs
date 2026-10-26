"""Exercise public pack installation on synthetic homes, never actual profiles."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


api = load("interface_test_installer", "scripts/install.py")
packs = load("interface_test_packs", "scripts/business_pack.py")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InterfaceSourceTests(unittest.TestCase):
    def test_original_visual_examples_match_provenance(self):
        import struct
        directory = ROOT / "skills/interface-design/assets/visual-examples"
        records = json.loads((directory / "provenance.json").read_text())
        self.assertEqual({item["file"] for item in records},
                         {name + ".png" for name in ["poster", "field", "object", "spatial", "direct", "archive"]})
        for item in records:
            path = directory / item["file"]
            self.assertEqual(file_hash(path), item["sha256"])
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", path.read_bytes()[16:24])
            self.assertGreater(width, 200)
            self.assertGreater(height, 100)

    def test_manifest_and_pinned_library(self):
        pack = packs.load_pack(ROOT, "interface-design")
        self.assertEqual(pack["managed_skills"], ["interface-design", "interface-performance"])
        self.assertFalse(set(pack["managed_skills"]) & set(api.SKILLS))
        reference = ROOT / "skills/interface-design/references"
        lock = json.loads((reference / "sources.lock.json").read_text())
        self.assertEqual(len(lock["sources"]), 10)
        files = [item for source in lock["sources"] for item in source["files"]]
        self.assertEqual(len(files), 37)
        for source in lock["sources"]:
            self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
            license_file = next(item for item in source["files"]
                                if item["source_path"] == source["license_path"])
            self.assertIn("MIT License", (reference / license_file["stored_path"]).read_text())
            for item in source["files"]:
                path = reference / item["stored_path"]
                self.assertEqual(file_hash(path), item["sha256"])
                self.assertEqual(path.stat().st_size, item["bytes"])
                self.assertNotEqual(path.name, "SKILL.md")
        for notice in lock.get("additional_notices", []):
            path = reference / notice["stored_path"]
            self.assertEqual(file_hash(path), notice["sha256"])
            self.assertEqual(path.stat().st_size, notice["bytes"])
            self.assertIn("Apache License", path.read_text())

    def test_portable_authored_resources_and_plugin_channel(self):
        docs = list((ROOT / "products/interface-design").rglob("*.md"))
        for name in ["interface-design", "interface-performance"]:
            skill = ROOT / "skills" / name
            self.assertEqual(packs.declared_name(skill / "SKILL.md", api), name)
            docs.extend(path for path in skill.rglob("*.md") if "upstream" not in path.parts)
            self.assertIn("$" + name, (skill / "agents/openai.yaml").read_text())
        for doc in docs:
            text = doc.read_text()
            self.assertNotIn("\u2014", text, doc)
            for private in ["/home/", "/mnt/c/Users/", "host-receipt.json"]:
                self.assertNotIn(private, text, doc)
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                target = target.split("#", 1)[0]
                self.assertFalse(Path(target).is_absolute(), (doc, target))
                self.assertTrue((doc.parent / target).exists(), (doc, target))
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertIn("./skills/", plugin["skills"])
        self.assertEqual(plugin["version"], marketplace["plugins"][0]["version"])
        discovered = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertTrue({"interface-design", "interface-performance"} <= discovered)


class InterfaceInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cag-interface-test-")
        self.addCleanup(temporary.cleanup)
        self.user = Path(temporary.name)
        self.codex = self.user / ".codex"
        self.claude = self.user / ".claude"
        self.protected = []
        for home, names in [(self.codex, ["config.toml", "AGENTS.md", "auth.json"]),
                            (self.claude, ["settings.json", "CLAUDE.md", "AGENTS.md"])]:
            home.mkdir()
            for name in names:
                path = home / name
                path.write_text("synthetic-preserve-" + name)
                self.protected.append(path)
        other = self.claude / "skills/other/SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("---\nname: other\ndescription: Preserve this unrelated skill.\n---\n")
        self.protected.append(other)
        self.before = {path: file_hash(path) for path in self.protected}

    def run_pack(self, action, provider, root=None, pack_id="interface-design"):
        home = self.codex if provider == "codex" else self.claude
        return packs.run(action, [(provider, home)], root, api=api,
                         pack_id=pack_id, provider=provider)

    def assert_preserved(self):
        self.assertEqual({path: file_hash(path) for path in self.protected}, self.before)

    def cli(self, script, *arguments):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *arguments],
                              cwd=self.user, text=True, capture_output=True, timeout=45)

    def test_same_user_codex_and_claude_fresh_verify_repeat(self):
        for provider, root in [("codex", self.user / ".agents/skills"),
                               ("claude", self.claude / "skills")]:
            planned = self.run_pack("plan", provider)
            self.assertEqual(planned["resolved_root"], str(root))
            self.assertEqual(planned["provider"], provider)
            self.assertIn(provider + "_home", planned["environments"][0])
            self.assertTrue(all(item["status"] == "missing" for item in planned["items"]))
            self.run_pack("install", provider)
            before = {path: (file_hash(path), path.stat().st_mtime_ns)
                      for name in ["interface-design", "interface-performance"]
                      for path in (root / name).rglob("*") if path.is_file()}
            self.run_pack("install", provider)
            self.assertEqual(before, {path: (file_hash(path), path.stat().st_mtime_ns)
                                      for path in before})
            self.assertEqual(self.run_pack("verify", provider)["status"], "ok")
        self.assert_preserved()
        self.assertFalse((self.claude / "agent-graph-runtime").exists())
        self.assertFalse((self.claude / "agents").exists())

    def test_drift_refuses_whole_pack_for_both_hosts(self):
        for provider, root in [("codex", self.user / ".agents/skills"),
                               ("claude", self.claude / "skills")]:
            self.run_pack("install", provider)
            private = root / "interface-performance/SKILL.md"
            private.write_text(private.read_text() + "\nPrivate local method.\n")
            sibling = root / "interface-design/SKILL.md"
            prior = (file_hash(private), sibling.stat().st_mtime_ns)
            with self.assertRaisesRegex(api.InstallError, "drift"):
                self.run_pack("install", provider)
            self.assertEqual(prior, (file_hash(private), sibling.stat().st_mtime_ns))
            self.assertEqual(self.run_pack("verify", provider)["status"], "failed")
        self.assert_preserved()

    def test_real_claude_duplicate_stops_before_writes(self):
        duplicate = self.claude / "skills/other/nested/SKILL.md"
        duplicate.parent.mkdir()
        duplicate.write_text("---\nname: interface-design\ndescription: Private duplicate.\n---\n")
        for action in ["plan", "install"]:
            with self.assertRaisesRegex(api.InstallError, "occurs outside"):
                self.run_pack(action, "claude")
        self.assertFalse((self.claude / "skills/interface-design").exists())
        self.assertTrue(duplicate.is_file())
        self.assert_preserved()

    def test_cli_channels_and_invalid_mixed_selection(self):
        for script, flags in [("install.py", ["--skills-only", "--wsl", "--wsl-home", str(self.codex)]),
                              ("install_claude.py", ["--claude-home", str(self.claude)])]:
            for action in ["plan", "install", "verify"]:
                result = self.cli(script, action, "--pack", "interface-design", *flags)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "ok")
        for flags in [["--skill", "interface-clarity"], ["--adopt", "interface-design"],
                      ["--skill-creator", str(self.user / "creator")]]:
            result = self.cli("install_claude.py", "install", "--pack", "interface-design",
                              "--claude-home", str(self.claude), *flags)
            self.assertEqual(result.returncode, 2)
        result = self.cli("install_claude.py", "plan", "--skill-root", str(self.user / "elsewhere"))
        self.assertEqual(result.returncode, 2)
        with self.assertRaisesRegex(api.InstallError, "supports interface-design only"):
            self.run_pack("install", "claude", pack_id="marketing-cycle")
        self.assert_preserved()

    def test_native_engineering_install_and_receipt_survive_pack(self):
        flags = ["--claude-home", str(self.claude), "--skill", "interface-clarity"]
        installed = self.cli("install_claude.py", "install", *flags)
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        paths = [path for base in [self.claude / "agent-graph-runtime", self.claude / "agents",
                                  self.claude / "skills/interface-clarity"]
                 for path in base.rglob("*") if path.is_file()]
        protected = {path: file_hash(path) for path in paths}
        self.run_pack("install", "claude")
        self.assertEqual(protected, {path: file_hash(path) for path in paths})
        receipt = json.loads((self.claude / "agent-graph-runtime/claude-native.json").read_text())
        self.assertFalse(any("interface-design" in name or "interface-performance" in name
                             for name in receipt["owned"]))
        verified = self.cli("install_claude.py", "verify", *flags)
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assert_preserved()


if __name__ == "__main__":
    unittest.main()
