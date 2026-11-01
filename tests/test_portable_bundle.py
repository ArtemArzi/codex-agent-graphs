from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import portable_bundle as bundle
import portable_sources as sources


class PortableBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="portable-bundle-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "source"
        self.repo.mkdir()
        for name in ("agents", "policies"):
            shutil.copytree(ROOT / name, self.repo / name, ignore=shutil.ignore_patterns("__pycache__"))
        (self.repo / "scripts").mkdir()
        for name in (*bundle.BOOTSTRAP, "install.py", "model_routing.py"):
            shutil.copy2(ROOT / "scripts" / name, self.repo / "scripts" / name)
        (self.repo / "agent-graph-runtime").mkdir()
        (self.repo / "agent-graph-runtime" / "helper.py").write_text("print('runtime')\n")
        self.skill("first", "first")
        self.profile = self.base / "profile.json"
        self.write_profile({"schema_version": 1, "skill_roots": [{"path": str(self.repo / "skills")}]})

    def skill(self, folder, name, body=""):
        root = self.repo / "skills" / folder
        root.mkdir(parents=True, exist_ok=True)
        (root / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Portable example\n---\n{body}\n")
        return root

    def write_profile(self, value):
        self.profile.write_text(json.dumps(value))

    def build(self, name="bundle"):
        output = self.base / name
        bundle.build(self.profile, output, self.repo)
        return output

    def cli(self, entry, *args):
        result = subprocess.run([sys.executable, "-B", str(entry), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_standalone_relocation_and_preserved_resources(self):
        root = self.repo / "skills/first"
        (root / "references").mkdir()
        (root / "references/nested.md").write_text("nested context")
        original = self.build()
        moved = self.base / "moved"
        original.rename(moved)
        shutil.rmtree(self.repo)
        target = self.base / "home"
        self.cli(moved / "portable_kit.py", "install", "--bundle", moved, "--target", target)
        self.cli(moved / "portable_kit.py", "verify", "--target", target)
        self.assertEqual((target / "skills/first/references/nested.md").read_text(), "nested context")
        self.assertIn("task_result_reviewer", (target / "config.toml").read_text())
        self.assertIn("Unified model routing", (target / "AGENTS.md").read_text())

    def test_new_skills_and_nested_resources_enter_next_build(self):
        first = self.build("one")
        self.skill("second", "second")
        (self.repo / "skills/first/new.md").write_text("new context")
        second = self.build("two")
        self.assertNotEqual(bundle.verify_bundle(first)["id"], bundle.verify_bundle(second)["id"])
        self.assertFalse((first / "payload/skills/second").exists())
        self.assertTrue((second / "payload/skills/first/new.md").is_file())

    def test_transitive_required_dependency_and_missing_dependency(self):
        deps = self.base / "dependencies"
        for name, required in (("second", "third"), ("third", None)):
            root = deps / name
            root.mkdir(parents=True)
            (root / "SKILL.md").write_text(f"---\nname: {name}\ndescription: dependency\n---\n")
            if required:
                (root / "skill-dependencies.json").write_text(json.dumps({"required_skills": [{"name": required}]}))
        (self.repo / "skills/first/skill-dependencies.json").write_text(json.dumps({"required_skills": [{"name": "second"}]}))
        with self.assertRaises(bundle.KitError):
            self.build("missing")
        data = json.loads(self.profile.read_text())
        data["dependency_roots"] = [str(deps)]
        self.write_profile(data)
        lock = bundle.verify_bundle(self.build())
        self.assertEqual({s["name"] for s in lock["skills"]}, {"first", "second", "third"})

    def test_ambiguous_alias_dependency_refused(self):
        data = json.loads(self.profile.read_text())
        a = self.skill("plugin-a", "helper")
        b = self.skill("plugin-b", "helper")
        data["skill_roots"] = []
        data["skills"] = [{"name": "first", "path": str(self.repo / "skills/first/SKILL.md")},
                          {"name": "a-helper", "path": str(a / "SKILL.md")},
                          {"name": "b-helper", "path": str(b / "SKILL.md")}]
        self.write_profile(data)
        (self.repo / "skills/first/skill-dependencies.json").write_text(json.dumps({"required_skills": [{"name": "helper"}]}))
        with self.assertRaisesRegex(bundle.KitError, "Ambiguous"):
            self.build()

    def test_conflicting_resource_requires_exact_preference(self):
        other = self.base / "other"
        shutil.copytree(self.repo / "skills/first", other)
        (other / "extra.md").write_text("different")
        data = json.loads(self.profile.read_text())
        data["skills"] = [{"path": str(other / "SKILL.md")}]
        self.write_profile(data)
        with self.assertRaisesRegex(bundle.KitError, "Conflicting"):
            self.build("conflict")
        data["prefer"] = {"first": str(other / "SKILL.md")}
        self.write_profile(data)
        self.assertTrue((self.build() / "payload/skills/first/extra.md").is_file())

    def test_symlink_private_state_and_secret_refused(self):
        root = self.repo / "skills/first"
        foreign = self.base / "foreign"
        foreign.write_text("preserve")
        (root / "link").symlink_to(foreign)
        with self.assertRaises(bundle.KitError):
            self.build("symlink")
        (root / "link").unlink()
        (root / ".env").write_text("fixture")
        with self.assertRaises(bundle.KitError):
            self.build("state")
        (root / ".env").unlink()
        (root / "secret.txt").write_bytes(b"-----BEGIN " + b"PRIVATE KEY-----")
        with self.assertRaises(bundle.KitError):
            self.build("secret")
        self.assertEqual(foreign.read_text(), "preserve")

    def test_verify_detects_payload_bootstrap_and_cache_tamper(self):
        for name, relative, data in (("payload", "payload/skills/first/SKILL.md", "drift"),
                                     ("bootstrap", "portable_kit.py", "drift"),
                                     ("cache", "payload/skills/first/__pycache__/foreign.pyc", "unexpected")):
            output = self.build(name)
            path = output / relative
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_text(data)
            with self.assertRaises(bundle.KitError):
                bundle.verify_bundle(output)

    def test_repeated_build_is_identical_and_output_overlap_refused(self):
        cache = self.repo / "skills/first/__pycache__"
        cache.mkdir()
        (cache / "ignored.pyc").write_text("rebuildable")
        one, two = self.build("one"), self.build("two")
        self.assertEqual(bundle.verify_bundle(one)["id"], bundle.verify_bundle(two)["id"])
        with self.assertRaises(bundle.KitError):
            bundle.build(self.profile, self.repo / "output", self.repo)

    def test_empty_foreign_directory_refused(self):
        output = self.build()
        (output / "payload/skills/first/foreign-empty").mkdir()
        with self.assertRaisesRegex(bundle.KitError, "Undeclared"):
            bundle.verify_bundle(output)

    def test_symlinked_output_parent_cannot_write_into_source(self):
        alias = self.base / "source-alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(bundle.KitError, "overlaps"):
            bundle.build(self.profile, alias / "unexpected-output", self.repo)
        self.assertFalse((self.repo / "unexpected-output").exists())
        self.assertTrue(alias.is_symlink())

    def test_dependency_path_escape_refused_before_scan(self):
        (self.repo / "skills/first/skill-dependencies.json").write_text(json.dumps({"required_skills": [{"name": "../outside"}]}))
        with self.assertRaisesRegex(bundle.KitError, "Invalid skill dependency"):
            self.build()

    def test_private_support_files_and_instructions_refused(self):
        for name in ("auth.json", ".env", "private.key", ".env.local"):
            source = self.base / name
            source.write_text("synthetic-private-state")
            data = json.loads(self.profile.read_text())
            data["support_files"] = [{"path": str(source), "destination": "knowledge/fixture.txt"}]
            self.write_profile(data)
            with self.assertRaisesRegex(bundle.KitError, "Private state"):
                self.build("refused-" + name)
            self.assertEqual(source.read_text(), "synthetic-private-state")
        data.pop("support_files")
        data["instructions"] = str(self.base / "auth.json")
        self.write_profile(data)
        with self.assertRaisesRegex(bundle.KitError, "Private state"):
            self.build("refused-instructions")

    def test_failed_build_preserves_unknown_output(self):
        output = self.base / "bundle"
        def fail(source, target, selection=None):
            (output / "foreign").write_text("preserve")
            raise bundle.KitError("injected failure")
        with patch.object(bundle, "copy_selected", fail):
            with self.assertRaises(bundle.KitError):
                self.build()
        self.assertEqual((output / "foreign").read_text(), "preserve")

    def test_changed_source_detected(self):
        original = bundle.canonical_standard
        def changing(repo, payload, *args):
            original(repo, payload, *args)
            (self.repo / "skills/first/new.md").write_text("late source change")
        with patch.object(bundle, "canonical_standard", changing):
            with self.assertRaisesRegex(bundle.KitError, "changed"):
                self.build()

    def test_native_projection_disabled_entries_and_knowledge_allowlist(self):
        plugin = self.base / "plugin"
        skill = plugin / "skills/helper"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: helper\ndescription: plugin helper\n---\nCall sample:helper\n")
        (plugin / "LICENSE").write_text("fixture licence")
        project = self.base / "project"
        knowledge = project / "knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "keep.md").write_text("selected")
        (knowledge / "private.md").write_text("excluded")
        (project / "company").mkdir()
        policy = project / "company/sync-policy.json"
        policy.write_text(json.dumps({"files": ["knowledge/keep.md"]}))
        catalog = {"result": {"data": [{"skills": [
            {"name": "sample:helper", "path": str(skill / "SKILL.md"), "pluginId": "sample@test", "enabled": True},
            {"name": "first", "path": str(self.repo / "skills/first/SKILL.md"), "enabled": False}], "errors": []}]}}
        sources.profile_from_catalog(catalog, self.base / "generated.json", self.repo, knowledge, policy)
        self.profile = self.base / "generated.json"
        lock = bundle.verify_bundle(self.build())
        self.assertEqual({s["name"] for s in lock["skills"]}, {"sample-helper"})
        self.assertTrue(any(name.endswith("LICENSE") for name in lock["files"]))
        self.assertNotIn("knowledge/work/private.md", lock["files"])
        self.assertIn("Call sample-helper", (self.base / "bundle/payload/skills/plugins/sample-test/skills/helper/SKILL.md").read_text())

    def test_catalog_errors_refused(self):
        with self.assertRaises(bundle.KitError):
            sources.catalog_entries({"result": {"data": [{"errors": ["fixture discovery failure"], "skills": []}]}})

    def test_capture_requests_metadata_only_and_disables_mcp(self):
        home = self.base / "native-home"
        home.mkdir()
        (home / "config-data.toml").write_text('model = "gpt-6.1-sol"\n[mcp_servers.fixture]\ncommand = "never-run"\n')
        (home / "config.toml").symlink_to("config-data.toml")
        skill_path = str(self.repo / "skills/first/SKILL.md")
        catalog = {"data": [{"errors": [], "skills": [{"name": "first", "path": skill_path, "enabled": True}]}]}
        script = "import sys,json\nfor line in sys.stdin:\n m=json.loads(line)\n if 'id' in m:\n  assert m['method'] in ('initialize','skills/list')\n  print(json.dumps({'id':m['id'],'result':" + repr(catalog) + " if m['method']=='skills/list' else {}}),flush=True)\n"
        original = asyncio.create_subprocess_exec
        seen = {}
        async def fake(*argv, **kwargs):
            seen["argv"] = argv
            seen["environment"] = kwargs["env"]
            return await original(sys.executable, "-u", "-c", script, **kwargs)
        with patch.object(asyncio, "create_subprocess_exec", fake), patch.dict(os.environ, {"FIXTURE_API_KEY": "synthetic-value"}):
            value = asyncio.run(sources.native_catalog(home, self.base, sys.executable))
        self.assertEqual(value["result"], catalog)
        self.assertIn("mcp_servers.fixture.enabled=false", seen["argv"])
        self.assertNotIn("FIXTURE_API_KEY", seen["environment"])
        self.assertFalse(Path(seen["environment"]["CODEX_SQLITE_HOME"]).exists())
        sources.profile_from_catalog(value, self.base / "captured-profile.json", self.repo)
        profile = json.loads((self.base / "captured-profile.json").read_text())
        self.assertEqual(profile["settings"], {"model": "gpt-6.1-sol"})

    def test_personal_instructions_and_model_only(self):
        instructions = self.base / "AGENTS.md"
        instructions.write_text("Use Russian. Preserve project data.\n")
        data = json.loads(self.profile.read_text())
        data.update(instructions=str(instructions), settings={"model": "gpt-6.1-sol", "model_reasoning_effort": "high"})
        self.write_profile(data)
        output = self.build()
        self.assertIn("Use Russian", (output / "payload/AGENTS.md").read_text())
        self.assertIn('model_reasoning_effort = "high"', (output / "payload/config.toml").read_text())
        data["settings"]["mcp_servers"] = "forbidden"
        self.write_profile(data)
        with self.assertRaises(bundle.KitError):
            self.build("unsafe-settings")


if __name__ == "__main__":
    unittest.main()
