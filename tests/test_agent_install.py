"""Agent-pack integration with the existing shared installer, isolated homes only."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


installer = module("agent_test_installer", REPO / "scripts/install.py")
shared = module("agent_test_shared", REPO / "scripts/business_pack.py")
checker = module("agent_test_checker", REPO / "scripts/check_agent_pack.py")


class AgentInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        for name, source in checker.owned_files(REPO).items():
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(REPO / "scripts/business_pack.py", self.repo / "scripts/business_pack.py")
        checker.write_manifest(self.repo)
        self.wsl = self.base / "linux-user/.codex"
        self.desktop = self.base / "desktop-user/.codex"
        self.root = self.desktop / ".agents/skills"
        self.root.mkdir(parents=True)
        self.alias = self.wsl.parent / ".agents/skills"
        self.alias.parent.mkdir(parents=True)
        self.alias.symlink_to(self.root, target_is_directory=True)
        self.homes = [("wsl", self.wsl), ("desktop", self.desktop)]
        self.protected = {}
        for home in [self.wsl, self.desktop]:
            home.mkdir(parents=True, exist_ok=True)
            for name, value in {"config.toml": "model='owner-choice'\n", "AGENTS.md": "owner policy",
                                "auth.json": '{"fixture":"unchanged"}'}.items():
                path = home / name
                path.write_text(value)
                self.protected[path] = path.read_bytes()
        unrelated = self.root / "business-work/SKILL.md"
        unrelated.parent.mkdir()
        unrelated.write_text("---\nname: business-work\ndescription: fixture\n---\nExisting business skill\n")
        self.protected[unrelated] = unrelated.read_bytes()

    def run_pack(self, action, requested=None):
        with mock.patch.multiple(installer, REPO_ROOT=self.repo, SKILLS_ROOT=self.repo / "skills"):
            return shared.run(action, self.homes, requested, api=installer, pack_id="agent-lifecycle")

    def assert_protected(self):
        for path, value in self.protected.items():
            self.assertEqual(path.read_bytes(), value)

    def test_plan_install_verify_shared_once_and_repeat_noop(self):
        plan = self.run_pack("plan")
        self.assertEqual(plan["pack"], "agent-lifecycle")
        self.assertEqual(plan["resolved_root"], str(self.root))
        self.assertEqual({item["status"] for item in plan["items"]}, {"missing"})
        self.assertEqual(len(plan["items"]), 4)
        result = self.run_pack("install")
        self.assertEqual({item["status"] for item in result["changes"]}, {"installed"})
        self.assertEqual(self.run_pack("verify")["status"], "ok")
        before = {name: (self.root / name / "SKILL.md").stat().st_mtime_ns for name in checker.SKILLS}
        again = self.run_pack("install")
        self.assertEqual({item["status"] for item in again["changes"]}, {"in-sync"})
        self.assertIsNone(again["backup"])
        for name in checker.SKILLS:
            self.assertEqual(installer.manifest(self.repo / "skills" / name), installer.manifest(self.root / name))
            self.assertEqual(before[name], (self.root / name / "SKILL.md").stat().st_mtime_ns)
            self.assertFalse((self.wsl / "skills" / name).exists())
            self.assertFalse((self.desktop / "skills" / name).exists())
        self.assertEqual(self.alias.resolve(), self.root)
        self.assert_protected()

    def test_existing_drift_reported_but_install_refuses_before_writes(self):
        target = self.root / checker.SKILLS[0]
        target.mkdir()
        (target / "SKILL.md").write_text("local owner change")
        self.assertEqual(self.run_pack("plan")["items"][0]["status"], "drift")
        with self.assertRaisesRegex(installer.InstallError, "drift"):
            self.run_pack("install")
        self.assertEqual((target / "SKILL.md").read_text(), "local owner change")
        self.assertEqual(len([n for n in checker.SKILLS if (self.root / n).exists()]), 1)
        self.assertFalse((self.root.parent / "backups").exists())
        self.assert_protected()

    def test_legacy_duplicate_rejected_without_mutation(self):
        target = self.wsl / "skills" / checker.SKILLS[0]
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text(f"---\nname: {checker.SKILLS[0]}\ndescription: fixture\n---\nLocal\n")
        with self.assertRaises(installer.InstallError):
            self.run_pack("install")
        self.assertTrue((target / "SKILL.md").exists())
        self.assertFalse((self.root / checker.SKILLS[0]).exists())

    def test_nested_declared_duplicate_in_different_directory_rejected(self):
        target = self.desktop / "skills/other-directory/nested/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text(f"---\nname: '{checker.SKILLS[1]}'\ndescription: fixture\n---\nLocal\n")
        with self.assertRaises(installer.InstallError):
            self.run_pack("plan")
        self.assertFalse((self.root / checker.SKILLS[1]).exists())

    def test_source_byte_tamper_rejected_by_complete_manifest(self):
        target = self.repo / "skills" / checker.SKILLS[0] / "references/agent-contract.md"
        target.write_text(target.read_text() + "\nchanged\n")
        with self.assertRaises(ValueError):
            self.run_pack("install")
        self.assertFalse((self.root / checker.SKILLS[0]).exists())

    def test_manifest_tamper_rejected_before_installation(self):
        path = self.repo / checker.MANIFEST
        data = json.loads(path.read_text())
        data["files"]["skills/agent-project-design/SKILL.md"] = "0" * 64
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.run_pack("install")
        self.assertFalse((self.root / checker.SKILLS[0]).exists())

    def test_shared_physical_parent_lock_blocks_agent_pack(self):
        with installer.skills_install_lock(self.root.parent):
            with self.assertRaises(installer.InstallError):
                self.run_pack("install")
        self.assertFalse((self.root / checker.SKILLS[0]).exists())

    def test_source_change_during_staging_is_rejected(self):
        original = installer.shutil.copytree
        source = self.repo / "skills" / checker.SKILLS[0]
        fired = False

        def changed_copy(src, dest, *args, **kwargs):
            nonlocal fired
            result = original(src, dest, *args, **kwargs)
            if Path(src) == source and not fired:
                fired = True
                path = source / "SKILL.md"
                path.write_text(path.read_text() + "\nconcurrent source\n")
            return result

        with mock.patch.object(installer.shutil, "copytree", changed_copy):
            with self.assertRaises(installer.InstallError):
                self.run_pack("install")
        self.assertTrue(fired)
        self.assertFalse((self.root / checker.SKILLS[0]).exists())
        self.assert_protected()

    def test_manifest_change_after_first_write_rolls_back_owned_bytes(self):
        original = installer.replace_directory
        fired = False

        def changed_replace(*args, **kwargs):
            nonlocal fired
            result = original(*args, **kwargs)
            if result == "installed" and not fired:
                fired = True
                path = self.repo / checker.MANIFEST
                data = json.loads(path.read_text())
                data["files"] = {}
                path.write_text(json.dumps(data))
            return result

        with mock.patch.object(installer, "replace_directory", changed_replace):
            with self.assertRaises(installer.InstallError):
                self.run_pack("install")
        self.assertTrue(fired)
        self.assertFalse(any((self.root / name).exists() for name in checker.SKILLS))
        self.assert_protected()

    def test_late_foreign_target_edit_is_preserved_on_failure(self):
        original = installer.replace_directory
        fired = False

        def changed_replace(*args, **kwargs):
            nonlocal fired
            result = original(*args, **kwargs)
            if result == "installed" and not fired:
                fired = True
                (self.root / checker.SKILLS[0] / "SKILL.md").write_text("concurrent owner edit")
            return result

        with mock.patch.object(installer, "replace_directory", changed_replace):
            with self.assertRaises(installer.InstallError) as caught:
                self.run_pack("install")
        self.assertIn("rollback conflicts", str(caught.exception))
        self.assertEqual((self.root / checker.SKILLS[0] / "SKILL.md").read_text(), "concurrent owner edit")
        self.assertFalse((self.root / checker.SKILLS[1]).exists())
        self.assert_protected()

    def test_fresh_roots_without_aliases_require_explicit_choice(self):
        self.alias.unlink()
        with self.assertRaises(installer.InstallError):
            self.run_pack("plan")
        self.assertEqual(self.run_pack("plan", self.root)["resolved_root"], str(self.root))

    def test_cli_pack_and_root_alias_plan_install_verify(self):
        common = ["--skills-only", "--pack", "agent-lifecycle", "--all", "--wsl-home", str(self.wsl),
                  "--desktop-home", str(self.desktop), "--skill-root", str(self.root)]
        with mock.patch.multiple(installer, REPO_ROOT=self.repo, SKILLS_ROOT=self.repo / "skills"):
            for action in ["plan", "install", "verify", "install"]:
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(installer.main([action, *common]), 0)
                data = json.loads(stream.getvalue())
                self.assertEqual(data["data"]["environments"][0]["pack"], "agent-lifecycle")
        self.assert_protected()

    def test_pack_does_not_enter_legacy_or_business_membership(self):
        self.assertTrue(set(checker.SKILLS).isdisjoint(installer.SKILLS))
        business_names = shared.load_pack(REPO)["managed_skills"]
        self.assertTrue(set(checker.SKILLS).isdisjoint(business_names))
        with self.assertRaises(ValueError):
            shared.load_pack(REPO, "../untrusted")


if __name__ == "__main__":
    unittest.main()
