"""Public-source integrity and offline behavior of the business collection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/business-automation"


class BusinessPackageTests(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads((PRODUCT / "pack.json").read_text())

    def test_import_preserves_all_undeliberately_changed_baseline_files(self):
        record = json.loads((PRODUCT / "imported-baseline.json").read_text())
        for relative, before in record["files"].items():
            if relative in record["changed_files"]:
                continue
            source = ROOT / relative
            self.assertTrue(source.is_file(), relative)
            self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest(), relative)
        self.assertEqual(set(record["changed_files"]),
                         {p for p, before in record["files"].items()
                          if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != before})

    def test_collection_owns_one_source_per_member_and_reuses_companions(self):
        names = self.pack["managed_skills"]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn(self.pack["entrypoint"], names)
        self.assertFalse(list(PRODUCT.rglob("SKILL.md")))
        self.assertFalse(set(names) & set(self.pack["reused_capabilities"]["skills"]))
        self.assertIs(self.pack["reused_capabilities"]["required"], False)
        for name in names + self.pack["reused_capabilities"]["skills"]:
            source = ROOT / "skills" / name / "SKILL.md"
            self.assertTrue(source.is_file(), name)
            frontmatter = source.read_text().split("---", 2)[1]
            self.assertRegex(frontmatter, rf"(?m)^name: {re.escape(name)}$")

    def test_product_and_install_metadata_describe_same_reviewed_source(self):
        metadata = json.loads((ROOT / "skills/business-work/references/installation.json").read_text())
        self.assertEqual(self.pack["version"], metadata["package_version"])
        self.assertEqual(self.pack["managed_skills"], metadata["skills"])
        self.assertEqual("canonical-repository-first", self.pack["update_owner"])
        self.assertEqual(self.pack["update_owner"], metadata["update_owner"])
        for name, origin in self.pack["upstream_pins"].items():
            self.assertEqual(origin["commit"], metadata["pins"][name]["commit"])
        for name in self.pack["managed_skills"]:
            if name.startswith("nmt-"):
                self.assertIn("Attribution-NonCommercial-ShareAlike",
                              (ROOT / "skills" / name / "LICENSE").read_text())
        self.assertIn("Copyright (c) 2026 Matt Van Horn",
                      (ROOT / "skills/last30days/LICENSE").read_text())

    def test_authored_routing_and_product_links_resolve_without_private_work(self):
        docs = list(PRODUCT.glob("*.md")) + list((ROOT / "skills/business-work").rglob("*.md"))
        docs += [ROOT / "skills/nmt-update/SKILL.md"]
        for doc in docs:
            for link in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if "://" in link or link.startswith("#"):
                    continue
                target = link.split("#", 1)[0]
                self.assertFalse(Path(target).is_absolute(), (doc, link))
                self.assertTrue((doc.parent / target).is_file(), (doc, link))

    def test_missing_observations_stay_open_in_shipped_hypothesis_helper(self):
        script = ROOT / "skills/business-hypothesis-check/scripts/hypothesis_report.py"
        payload = {"hypothesis": "Employees use the changed process", "expectations": [
            {"id": "usage", "expected": "A real order is completed", "status": "confirmed"}]}
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            evidence.write_text(json.dumps(payload))
            result = subprocess.run([sys.executable, "-B", str(script), str(evidence), "--json"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("open", json.loads(result.stdout)["overall"])

    def test_safe_research_launcher_keeps_optional_modes_off(self):
        prepare = runpy.run_path(str(ROOT / "skills/last30days/scripts/run_local.py"))["prepare"]
        with tempfile.TemporaryDirectory() as directory:
            for args in (["setup"], ["--browser"], ["--store"], ["library search", "x"]):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    prepare([*args, "--project-root", directory, "--no-save"])
            args = prepare(["business process", "--project-root", directory, "--no-save"])
            self.assertIn("--no-browser-cookies", args)
            self.assertEqual("", args[args.index("--save-dir") + 1])


if __name__ == "__main__":
    unittest.main()
