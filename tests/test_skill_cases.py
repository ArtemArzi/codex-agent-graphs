"""Offline case preparation verifies fixtures, not model reasoning."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("skill_cases", ROOT / "scripts/skill_cases.py")
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class SkillCaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo = self.base / "repo"
        entry = self.repo / "skills/example/SKILL.md"
        entry.parent.mkdir(parents=True)
        entry.write_text("---\nname: example\ndescription: Example task.\n---\nUse the supplied input.\n")
        self.catalog = self.repo / cases.CATALOG
        self.catalog.parent.mkdir(parents=True)
        (self.catalog.parent / "input.txt").write_text("Synthetic input\n")
        self.case = {"id": "example", "skills": ["example"], "request": "Solve the example.",
                     "files": {"input.txt": "input.txt"}, "rubric": ["ASSESSMENT_ONLY"]}
        self.save()

    def save(self, entries=None):
        self.catalog.write_text(json.dumps({"schema_version": 1, "cases": entries if entries is not None else [self.case]}))

    def test_preparation_copies_inputs_but_withholds_assessment(self):
        output = self.base / "exercise"
        result = cases.prepare(self.repo, "example", output)
        self.assertEqual(result["status"], "prepared")
        self.assertEqual((output / "input.txt").read_text(), "Synthetic input\n")
        task = (output / "TASK.md").read_text()
        self.assertIn("Solve the example.", task)
        self.assertIn(str(self.repo / "skills/example/SKILL.md"), task)
        self.assertNotIn("ASSESSMENT_ONLY", task)
        self.assertEqual({p.name for p in output.iterdir()}, {"input.txt", "TASK.md"})

    def test_existing_destination_and_broken_alias_are_preserved(self):
        output = self.base / "exercise"
        output.mkdir()
        marker = output / "owner.txt"
        marker.write_text("Keep my work")
        with self.assertRaises(ValueError):
            cases.prepare(self.repo, "example", output)
        self.assertEqual(marker.read_text(), "Keep my work")
        alias = self.base / "alias"
        alias.symlink_to(self.base / "absent")
        with self.assertRaises(ValueError):
            cases.prepare(self.repo, "example", alias)
        self.assertTrue(alias.is_symlink())

    def test_unknown_case_does_not_create_destination(self):
        output = self.base / "exercise"
        with self.assertRaises(ValueError):
            cases.prepare(self.repo, "unknown", output)
        self.assertFalse(output.exists())

    def test_invalid_source_and_target_paths_fail_before_writing(self):
        output = self.base / "exercise"
        for mapping in ({"../outside": "input.txt"}, {"/absolute": "input.txt"},
                        {"input": "../outside.txt"}, {"input": str(self.catalog)},
                        {"TASK.md": "input.txt"}, {"TASK.md/nested": "input.txt"},
                        {"input": "cases.json"}, {"input": "missing.txt"},
                        {"a": "input.txt", "a/b": "input.txt"},
                        {"C:\\input": "input.txt"}):
            with self.subTest(mapping=mapping):
                self.case["files"] = mapping
                self.save()
                with self.assertRaises(ValueError):
                    cases.prepare(self.repo, "example", output)
                self.assertFalse(output.exists())

    def test_fixture_alias_cannot_export_an_outside_file(self):
        outside = self.base / "owner.txt"
        outside.write_text("Synthetic owner data, not a fixture")
        (self.catalog.parent / "alias.txt").symlink_to(outside)
        self.case["files"] = {"input.txt": "alias.txt"}
        self.save()
        with self.assertRaises(ValueError):
            cases.load_cases(self.repo)

    def test_bad_catalogue_does_not_hide_duplicate_or_missing_contracts(self):
        for field, value in (("skills", ["unknown"]), ("skills", [{}]),
                             ("skills", ["example", "example"]), ("request", ""),
                             ("rubric", []), ("files", [])):
            with self.subTest(field=field, value=value):
                original = self.case[field]
                self.case[field] = value
                self.save()
                with self.assertRaises(ValueError):
                    cases.load_cases(self.repo)
                self.case[field] = original
        self.save([self.case, self.case])
        with self.assertRaises(ValueError):
            cases.load_cases(self.repo)

    def test_shipped_cases_prepare_from_actual_repository(self):
        for name, definition in cases.load_cases(ROOT).items():
            with self.subTest(case=name):
                output = self.base / name
                cases.prepare(ROOT, name, output)
                task = (output / "TASK.md").read_text()
                for criterion in definition["rubric"]:
                    self.assertNotIn(criterion, task)
                for target, source in definition.get("files", {}).items():
                    self.assertEqual((output / target).read_bytes(), (ROOT / cases.CATALOG.parent / source).read_bytes())

    def test_cli_check_and_unknown_case_have_clear_outcomes(self):
        checked = subprocess.run([sys.executable, str(ROOT / "scripts/skill_cases.py"), "check"], text=True, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["coverage"], "fixture-structure-only")
        output = self.base / "exercise"
        refused = subprocess.run([sys.executable, str(ROOT / "scripts/skill_cases.py"), "prepare", "unknown", "--output", str(output)], text=True, capture_output=True)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("Unknown case", refused.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
