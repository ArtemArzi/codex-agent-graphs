"""Public-source integrity and offline behavior of the business collection."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
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


    @unittest.skipIf(sys.version_info < (3, 12), "last30days requires Python 3.12+")
    def test_packaged_last30days_mock_retrieval_exposes_coverage_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            installed = project / "skills" / "last30days"
            shutil.copytree(ROOT / "skills" / "last30days", installed)

            def run(*args):
                result = subprocess.run(
                    [sys.executable, str(installed / "scripts/run_local.py"), *args],
                    capture_output=True, text=True, cwd=project,
                    env={"PATH": os.defpath}, timeout=20,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                return json.loads(result.stdout)

            plan = run("--preflight", "--no-save", "--emit=json")
            self.assertTrue(plan["safe"])
            self.assertEqual([], plan["local_writes"])
            self.assertNotIn("x", plan["network"]["available_sources"])
            report = run("synthetic example customer scheduling", "--mock",
                         "--search=web,reddit,x", "--web-backend=none", "--no-save", "--emit=json")
            self.assertEqual(30, report["window_days"])
            self.assertEqual("skipped-unconfigured", report["source_status"]["grounding"])
            self.assertEqual({"reddit", "x"}, {item["source"] for item in report["results"]})
            self.assertTrue(all(item["url"].startswith("https://") for item in report["results"]))
            self.assertEqual(["skills"], [entry.name for entry in project.iterdir()])

    @unittest.skipIf(sys.version_info < (3, 12), "last30days requires Python 3.12+")
    def test_last30days_mock_discovery_keeps_project_handoff(self):
        launcher = ROOT / "skills/last30days/scripts/run_local.py"
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            def run(*args):
                result = subprocess.run(
                    [sys.executable, str(launcher), *args, "--mock",
                     "--project-root", directory, "--save-dir", directory],
                    capture_output=True, text=True, cwd=project,
                    env={"PATH": os.defpath}, timeout=20,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                return result.stdout

            run("--discover", "AI agents", "--discover-shallow", "--nominate-only")
            bundle = json.loads((project / "discover-nominations.json").read_text())
            selected, *others = bundle["nominations"]
            judgments = project / "judgments.json"
            judgments.write_text(json.dumps({
                "bundle_id": bundle["bundle_id"],
                "judgments": [
                    {"id": item["id"], "name": item["heuristic_name"],
                     "junk": item in others, "worthiness": 85 if item == selected else 0}
                    for item in bundle["nominations"]
                ],
            }))
            run("--discover", "--judgments", str(judgments))
            pending = json.loads((project / "discover-pending.json").read_text())
            self.assertEqual(bundle["bundle_id"], pending["bundle_id"])
            self.assertEqual({selected["id"]}, set(pending["angle_inputs"]))
            angles = project / "angles.json"
            angles.write_text(json.dumps({
                "bundle_id": bundle["bundle_id"],
                "angles": [{"id": selected["id"], "podcast": "Compare the memory workflows.",
                            "x_article": "Review the memory protocols."}],
            }))
            report = run("--discover", "--finalize", "--angles", str(angles), "--emit=compact")
            self.assertIn(selected["heuristic_name"], report)
            self.assertIn("Compare the memory workflows.", report)
            self.assertTrue((project / "ai-agents-discover-raw.md").is_file())


if __name__ == "__main__":
    unittest.main()
