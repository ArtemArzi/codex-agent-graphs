"""Packaging behavior on isolated files; these are not agent E2E tests."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("agent_pack_checker", ROOT / "scripts/check_agent_pack.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class AgentPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        # Fixture scope is only owned files, even after integration into a larger repo.
        for name, source in checker.owned_files(ROOT).items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        checker.write_manifest(self.root)

    def test_valid_relocated_overlay_and_unrelated_repository_files(self):
        foreign = self.root / "unrelated-private.txt"
        foreign.write_text("unrelated data")
        checker.verify_manifest(self.root)
        self.assertNotIn("unrelated-private.txt", checker.owned_files(self.root))

    def test_changed_byte_is_not_accepted_by_old_manifest(self):
        target = self.root / "skills/agent-project-design/SKILL.md"
        target.write_text(target.read_text() + "\nchanged\n")
        with self.assertRaises(checker.PackError):
            checker.verify_manifest(self.root)

    def test_extra_owned_file_is_not_accepted_by_old_manifest(self):
        (self.root / checker.PRODUCT / "unexpected.txt").write_text("extra")
        with self.assertRaises(checker.PackError):
            checker.verify_manifest(self.root)

    def test_missing_file_is_not_accepted(self):
        (self.root / "skills/agent-memory-lifecycle/references/memory-checks.md").unlink()
        with self.assertRaises(checker.PackError):
            checker.verify_manifest(self.root)

    def test_broken_local_reference_is_rejected_before_manifest_update(self):
        (self.root / checker.PRODUCT / "extra.md").write_text("[missing](absent.md)")
        with self.assertRaises(checker.PackError):
            checker.write_manifest(self.root)

    def test_existing_unowned_reference_is_rejected(self):
        (self.root / "other.md").write_text("outside the overlay")
        (self.root / checker.PRODUCT / "extra.md").write_text("[other](../../other.md)")
        with self.assertRaises(checker.PackError):
            checker.write_manifest(self.root)

    def test_escape_reference_is_rejected(self):
        (self.root / checker.PRODUCT / "extra.md").write_text("[escape](../../../outside.md)")
        with self.assertRaises(checker.PackError):
            checker.write_manifest(self.root)

    def test_symlinked_source_file_and_parent_are_rejected(self):
        target = self.root / checker.PRODUCT / "link.md"
        target.symlink_to(self.root / checker.PRODUCT / "README.md")
        with self.assertRaises(checker.PackError):
            checker.owned_files(self.root)
        target.unlink()
        skills = self.root / "skills"
        moved = self.base / "moved-skills"
        skills.rename(moved)
        skills.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(checker.PackError):
            checker.owned_files(self.root)

    def test_duplicate_managed_and_reused_member_is_rejected(self):
        path = self.root / checker.PRODUCT / "pack.json"
        data = json.loads(path.read_text())
        data["reused_capabilities"]["skills"].append(checker.SKILLS[0])
        path.write_text(json.dumps(data))
        with self.assertRaises(checker.PackError):
            checker.load_pack(self.root)

    def test_duplicate_installed_names_are_rejected_without_writes(self):
        roots = [self.base / "home-a/skills", self.base / "home-b/skills"]
        name = checker.SKILLS[0]
        for folder in roots:
            shutil.copytree(self.root / "skills" / name, folder / name)
        before = (roots[0] / name / "SKILL.md").read_bytes()
        with self.assertRaises(checker.PackError):
            checker.inspect_installed(self.root, roots)
        self.assertEqual(before, (roots[0] / name / "SKILL.md").read_bytes())

    def test_root_alias_is_one_installation_and_drift_is_preserved(self):
        folder = self.base / "home/skills"
        name = checker.SKILLS[0]
        shutil.copytree(self.root / "skills" / name, folder / name)
        alias = self.base / "shared-skills"
        alias.symlink_to(folder, target_is_directory=True)
        result = checker.inspect_installed(self.root, [folder, alias])
        self.assertEqual(result[name], "in-sync")
        changed = folder / name / "SKILL.md"
        changed.write_text("local owner edit")
        with self.assertRaises(checker.PackError):
            checker.inspect_installed(self.root, [folder])
        self.assertEqual(changed.read_text(), "local owner edit")

    def test_archive_readback_exact_members_and_reproducibility(self):
        (self.root / "private-unowned.txt").write_text("must not enter archive")
        cache = self.root / "scripts/__pycache__"
        cache.mkdir(exist_ok=True)
        (cache / "ignored.pyc").write_bytes(b"cache")
        first, second = self.base / "first.zip", self.base / "second.zip"
        count = checker.archive(self.root, first)
        checker.archive(self.root, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as output:
            self.assertEqual(len(output.namelist()), count)
            self.assertFalse(any("private-unowned" in name or "__pycache__" in name for name in output.namelist()))
            self.assertIsNone(output.testzip())

    def test_archive_refuses_overwrite_and_recursive_destination(self):
        destination = self.base / "kept.zip"
        destination.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            checker.archive(self.root, destination)
        self.assertEqual(destination.read_bytes(), b"keep")
        with self.assertRaises(checker.PackError):
            checker.archive(self.root, self.root / "recursive.zip")

    def test_archive_refuses_tampered_candidate(self):
        target = self.root / checker.PRODUCT / "README.md"
        target.write_text(target.read_text() + "\nchanged\n")
        destination = self.base / "not-created.zip"
        with self.assertRaises(checker.PackError):
            checker.archive(self.root, destination)
        self.assertFalse(destination.exists())

    def test_source_change_during_archive_never_reports_success(self):
        target = self.root / "skills/agent-project-design/SKILL.md"
        destination = self.base / "raced.zip"
        original = zipfile.ZipFile.writestr
        changed = False

        def mutate_then_write(output, *args, **kwargs):
            nonlocal changed
            if not changed:
                target.write_text(target.read_text() + "\nconcurrent source edit\n")
                changed = True
            return original(output, *args, **kwargs)

        with mock.patch.object(zipfile.ZipFile, "writestr", mutate_then_write):
            with self.assertRaises(checker.PackError):
                checker.archive(self.root, destination)


if __name__ == "__main__":
    unittest.main()
