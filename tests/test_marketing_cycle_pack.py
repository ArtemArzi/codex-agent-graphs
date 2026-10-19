"""Marketing pack on disposable homes; no actual accounts or client data."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


installer = module("marketing_test_installer", "scripts/install.py")
packs = module("marketing_test_packs", "scripts/business_pack.py")


class MarketingSourceTests(unittest.TestCase):
    def test_portable_references_and_native_metadata(self):
        pack = packs.load_pack(ROOT, "marketing-cycle")
        docs = list((ROOT / "products/marketing-cycle").rglob("*.md"))
        for name in pack["managed_skills"]:
            skill = ROOT / "skills" / name
            self.assertEqual(packs.declared_name(skill / "SKILL.md", installer), name)
            docs.extend(skill.rglob("*.md"))
            ui = (skill / "agents/openai.yaml").read_text()
            values = {}
            for line in ui.splitlines():
                found = re.fullmatch(r'  (display_name|short_description|default_prompt): (".*")', line)
                if found:
                    values[found[1]] = json.loads(found[2])
            self.assertEqual(set(values), {"display_name", "short_description", "default_prompt"})
            self.assertTrue(25 <= len(values["short_description"]) <= 64)
            self.assertIn("$" + name, values["default_prompt"])
        for doc in docs:
            for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                self.assertFalse(Path(relative).is_absolute(), (doc, target))
                self.assertTrue((doc.parent / relative).is_file(), (doc, target))


class MarketingInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.repo = self.base / "repo"
        self.pack = packs.load_pack(ROOT, "marketing-cycle")
        self.copy_pack("marketing-cycle")
        scripts = self.repo / "scripts"
        scripts.mkdir()
        shutil.copyfile(ROOT / "scripts/business_pack.py", scripts / "business_pack.py")
        self.wsl = self.base / "wsl/.codex"
        self.desktop = self.base / "desktop/.codex"
        self.homes = [("wsl", self.wsl), ("desktop", self.desktop)]
        self.target = self.base / "shared/skills"
        self.target.mkdir(parents=True)
        self.protected = {}
        for _, home in self.homes:
            home.mkdir(parents=True)
            for name, value in (("config.toml", "model='keep-local-choice'\n"),
                                ("AGENTS.md", "local policy\n"),
                                ("auth.json", '{"synthetic":true}\n')):
                file = home / name
                file.write_text(value)
                self.protected[file] = file.read_bytes()
        other = self.target / "unrelated/SKILL.md"
        other.parent.mkdir()
        other.write_text("---\nname: unrelated\ndescription: Existing own skill\n---\n")
        self.protected[other] = other.read_bytes()
        for attr, value in (("REPO_ROOT", self.repo), ("SKILLS_ROOT", self.repo / "skills")):
            patcher = mock.patch.object(installer, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def copy_pack(self, pack_id):
        pack = packs.load_pack(ROOT, pack_id)
        product = self.repo / "products" / pack_id
        product.mkdir(parents=True)
        (product / "pack.json").write_text(json.dumps(pack))
        for name in pack["managed_skills"]:
            shutil.copytree(ROOT / "skills" / name, self.repo / "skills" / name,
                            dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def run_pack(self, action="install", pack_id="marketing-cycle"):
        return packs.run(action, self.homes, self.target, api=installer, pack_id=pack_id)

    def assert_protected(self):
        self.assertEqual(self.protected, {p: p.read_bytes() for p in self.protected})

    def test_plan_and_missing_verify_do_not_write(self):
        before = installer.directory_preimage(self.target)
        with mock.patch.object(installer, "replace_directory") as writes:
            self.assertEqual({x["status"] for x in self.run_pack("plan")["items"]}, {"missing"})
            self.assertEqual(self.run_pack("verify")["status"], "failed")
        writes.assert_not_called()
        self.assertEqual(before, installer.directory_preimage(self.target))
        self.assert_protected()

    def test_standalone_install_only_five_members_and_noop(self):
        result = self.run_pack()
        self.assertEqual(len(result["changes"]), 5)
        self.assertEqual({p.name for p in self.target.iterdir()}, set(self.pack["managed_skills"]) | {"unrelated"})
        for name in self.pack["managed_skills"]:
            self.assertEqual(installer.manifest(self.repo / "skills" / name), installer.manifest(self.target / name))
        times = {p: p.stat().st_mtime_ns for p in self.target.rglob("*")}
        repeat = self.run_pack()
        self.assertIsNone(repeat["backup"])
        self.assertTrue(all(x["status"] == "in-sync" for x in repeat["changes"]))
        self.assertEqual(times, {p: p.stat().st_mtime_ns for p in times})
        self.assertEqual(self.run_pack("verify")["status"], "ok")
        self.assert_protected()

    def test_coexists_with_business_model_without_rewriting_it(self):
        self.copy_pack("business-model")
        self.run_pack(pack_id="business-model")
        other = self.target / "business-work"
        before = installer.directory_preimage(other)
        self.run_pack()
        self.assertEqual(before, installer.directory_preimage(other))
        self.assertEqual(self.run_pack("verify", "business-model")["status"], "ok")
        self.assertEqual(self.run_pack("verify")["status"], "ok")
        self.assert_protected()

    def test_drift_blocks_before_install_writes(self):
        self.run_pack()
        file = self.target / "marketing-work/SKILL.md"
        file.write_text(file.read_text() + "\nLocal owner edit\n")
        before = installer.directory_preimage(self.target)
        with mock.patch.object(installer, "replace_directory") as writes:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        writes.assert_not_called()
        self.assertEqual(before, installer.directory_preimage(self.target))
        self.assert_protected()

    def test_legacy_duplicate_native_name_blocks_without_install(self):
        duplicate = self.wsl / "skills/renamed/SKILL.md"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text("---\nname: marketing-work\ndescription: Native duplicate\n---\n")
        before = installer.directory_preimage(self.target)
        with mock.patch.object(installer, "replace_directory") as writes:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        writes.assert_not_called()
        self.assertEqual(before, installer.directory_preimage(self.target))
        self.assert_protected()

    def test_manifest_rejects_changed_members_market_and_runtime(self):
        file = self.repo / "products/marketing-cycle/pack.json"
        for field, value in (("update_owner", "other"), ("managed_skills", ["marketing-work"]),
                             ("default_market", "US"), ("foreign_market_evidence", "demand-proof"),
                             ("runtime_dependencies", ["server"]),
                             ("reused_capabilities", {"required": True, "skills": []}),
                             ("reused_capabilities", {"required": False, "skills": ["marketing-work"]})):
            with self.subTest(field=field, value=value):
                file.write_text(json.dumps({**self.pack, field: value}))
                with self.assertRaises(ValueError):
                    packs.load_pack(self.repo, "marketing-cycle")
        file.write_text(json.dumps(self.pack))
        self.assert_protected()

    def test_concurrent_source_change_rejects_and_preserves_targets(self):
        original = installer.shutil.copytree
        source = self.repo / "skills/marketing-strategy/SKILL.md"
        changed = False

        def change_after_stage(*args, **kwargs):
            nonlocal changed
            result = original(*args, **kwargs)
            if not changed:
                changed = True
                source.write_text(source.read_text() + "\nConcurrent source edit\n")
            return result

        before = installer.directory_preimage(self.target)
        with mock.patch.object(installer.shutil, "copytree", side_effect=change_after_stage):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assertEqual(before, installer.directory_preimage(self.target))
        self.assert_protected()

    def test_native_cli_registers_pack_and_rejects_missing_scope(self):
        args = ["--skills-only", "--pack", "marketing-cycle", "--all",
                "--wsl-home", str(self.wsl), "--desktop-home", str(self.desktop),
                "--skill-root", str(self.target)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            for action in ("plan", "install", "verify"):
                self.assertEqual(installer.main([action, *args]), 0)
            self.assertEqual(installer.main(["plan", "--pack", "marketing-cycle"]), 2)
        self.assert_protected()


if __name__ == "__main__":
    unittest.main()
