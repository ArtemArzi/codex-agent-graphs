#!/usr/bin/env python3
"""Behavioral tests using disposable project and installed-skill fixtures."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


class MarketingGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "company"
        self.root.mkdir()
        self.skill = self.base / "marketing-work"
        (self.skill / "scripts").mkdir(parents=True)
        for relative in ["graph.json", "scripts/marketing_graph.py"]:
            shutil.copyfile(SOURCE / relative, self.skill / relative)
        spec = importlib.util.spec_from_file_location("marketing_fixture", self.skill / "scripts/marketing_graph.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        for name, text in {"brief.md": "Company facts", "result.md": "Candidate A",
                           "checks.md": "Source readback and bounded calculation",
                           "review.md": "Independent exact candidate review"}.items():
            self.write(name, text)
        self.run_dir = self.root / ".agent-graphs/marketing-work-runs/case"

    def write(self, relative, text):
        (self.root / relative).write_text(text, encoding="utf-8")

    def call(self, command, *args, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = self.module.main([command, "--root", str(self.root), "--run", "case", *args])
        self.assertEqual(code, 0 if ok else 2, err.getvalue())
        return json.loads(out.getvalue()) if code == 0 else err.getvalue()

    def init(self, tier="tracked", *extra):
        return self.call("init", "--tier", tier, "--company", "Brand A", "--objective", "Choose useful next step",
                         "--input", "brief.md", "--output", "result.md", *extra)

    def work(self, *extra, ok=True):
        return self.call("work", "--author", "root-session", "--evidence", "checks.md",
                         "--capability", "mcp:not-applicable:local-project", *extra, ok=ok)

    def verify(self, verdict="accept", *extra, ok=True, work=None, output=None):
        state = json.loads((self.run_dir / "state.json").read_text())
        receipt = json.loads((self.run_dir / state["work"]).read_text())
        return self.call("verify", "--reviewer", "independent-session", "--role", "block_reviewer",
                         "--reason", "Evidence supports conclusion" if verdict == "accept" else "Wrong assumption",
                         "--work-sha", work or state["receipts"][state["work"]],
                         "--output-sha", output or receipt["output_sha256"],
                         "--verdict", verdict, "--evidence", "review.md", *extra, ok=ok)

    def inventory(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_default_no_run_and_explicit_init_binds_context(self):
        graph = json.loads((self.skill / "graph.json").read_text())
        self.assertEqual(graph["execution_policy"]["default_tier"], "skill-only")
        self.assertFalse((self.root / ".agent-graphs").exists())
        result = self.init()
        self.assertEqual(result["next"], "work")
        state = json.loads((self.run_dir / "state.json").read_text())
        self.assertEqual(state["company"], "Brand A")
        self.assertEqual(state["objective"], "Choose useful next step")
        self.assertEqual(state["output"], "result.md")
        self.assertEqual(set(state["inputs"]), {"brief.md"})
        before = self.inventory()
        self.call("init", "--tier", "tracked", "--company", "Foreign", "--objective", "Other",
                  "--input", "brief.md", "--output", "result.md", ok=False)
        self.assertEqual(before, self.inventory())

    def test_read_only_resume_and_tracked_happy_completion(self):
        self.init()
        before = self.inventory()
        self.call("ready")
        self.call("resume")
        self.assertEqual(before, self.inventory())
        self.work()
        self.assertEqual(self.call("complete")["status"], "completed")
        before = self.inventory()
        self.call("resume")
        self.assertEqual(before, self.inventory())
        final = json.loads((self.run_dir / "FINAL.json").read_text())
        self.assertEqual(final["output"], "result.md")
        self.assertEqual(final["binding"]["company"], "Brand A")
        self.assertIsNone(final["verification_sha256"])
        self.assertEqual((self.root / "result.md").read_text(), "Candidate A")

    def test_verified_and_conditional_review_bind_exact_candidate(self):
        self.init("verified")
        self.work()
        self.call("complete", ok=False)
        self.verify(work="0" * 64, ok=False)
        self.verify(output="0" * 64, ok=False)
        self.verify("accept", "--reviewer", "root-session", ok=False)
        self.verify()
        self.call("complete")
        self.assertIsNotNone(json.loads((self.run_dir / "FINAL.json").read_text())["verification_sha256"])

    def test_tracked_can_admit_review(self):
        self.init()
        self.work("--verify")
        self.verify()
        self.call("complete")

    def test_reject_repair_needs_false_assumption_changed_output_and_new_evidence(self):
        self.init("verified")
        self.work()
        self.verify("reject")
        self.call("complete", ok=False)
        self.work(ok=False)
        self.work("--first-false-assumption", "Demand was not observed", ok=False)
        self.write("result.md", "Candidate B")
        self.work("--first-false-assumption", "Demand was not observed", ok=False)
        self.write("checks-new.md", "New observed counterexample")
        self.work("--first-false-assumption", "Demand was not observed", "--evidence", "checks-new.md")
        self.write("review-new.md", "Independent review of candidate B")
        self.verify("accept", "--evidence", "review-new.md")
        self.call("complete")

    def test_second_rejection_exhausts_and_never_completes(self):
        self.init("verified")
        self.work()
        self.verify("reject")
        self.write("result.md", "Candidate B")
        self.write("checks-new.md", "New discriminating evidence")
        self.work("--first-false-assumption", "Wrong boundary", "--evidence", "checks-new.md")
        self.write("review-new.md", "Still insufficient")
        result = self.verify("reject", "--evidence", "review-new.md")
        self.assertEqual(result["phase"], "exhausted")
        self.work(ok=False)
        self.call("complete", ok=False)
        self.assertFalse((self.run_dir / "FINAL.json").exists())

    def test_invalid_transitions_do_not_change_state(self):
        self.init()
        before = self.inventory()
        self.call("complete", ok=False)
        self.assertEqual(before, self.inventory())
        self.work()
        before = self.inventory()
        self.work(ok=False)
        self.verify(ok=False)
        self.assertEqual(before, self.inventory())

    def test_sources_candidate_and_evidence_changes_fail_closed(self):
        self.init("verified")
        self.work()
        for path in ["brief.md", "result.md", "checks.md"]:
            before = (self.root / path).read_text()
            self.write(path, "Changed")
            self.call("resume", ok=False)
            self.call("complete", ok=False)
            self.write(path, before)
        self.verify()
        self.write("review.md", "Changed review evidence")
        self.call("complete", ok=False)

    def test_graph_controller_receipt_and_completed_final_tamper(self):
        self.init()
        self.work()
        for path in [self.skill / "graph.json", self.skill / "scripts/marketing_graph.py", self.run_dir / "work-0.json"]:
            old = path.read_bytes()
            path.write_bytes(old + b" ")
            self.call("resume", ok=False)
            path.write_bytes(old)
        self.call("complete")
        (self.run_dir / "FINAL.json").write_text("{}")
        self.call("resume", ok=False)

    def test_unknown_legacy_and_company_objective_state_tamper(self):
        self.init()
        self.work()
        path = self.run_dir / "state.json"
        old = path.read_bytes()
        for field, value in [("schema_version", 0), ("graph_id", "other"), ("company", "Other"), ("objective", "Other")]:
            state = json.loads(old)
            state[field] = value
            path.write_text(json.dumps(state))
            self.call("resume", ok=False)
            # Even a syntactically valid, resealed foreign identity/context
            # cannot reinterpret this run or its already bound work receipt.
            path.write_text(json.dumps(self.module.seal(state)))
            self.call("resume", ok=False)
        path.write_bytes(old)

    def test_traversal_symlinks_and_foreign_outputs_preserved(self):
        sentinel = self.base / "foreign.md"
        sentinel.write_text("Foreign sentinel")
        for output in ["../foreign.md", str(sentinel), ".agent-graphs/result.md"]:
            self.call("init", "--tier", "tracked", "--company", "A", "--objective", "B",
                      "--input", "brief.md", "--output", output, ok=False)
        (self.root / "linked.md").symlink_to(sentinel)
        self.call("init", "--tier", "tracked", "--company", "A", "--objective", "B",
                  "--input", "brief.md", "--output", "linked.md", ok=False)
        self.call("init", "--run", "../escape", "--tier", "tracked", "--company", "A", "--objective", "B",
                  "--input", "brief.md", "--output", "result.md", ok=False)
        self.assertEqual(sentinel.read_text(), "Foreign sentinel")
        self.init()
        self.work()
        before = (self.root / "result.md").read_bytes()
        self.call("complete")
        self.assertEqual((self.root / "result.md").read_bytes(), before)

    def test_managed_and_receipt_symlinks_rejected(self):
        (self.root / ".agent-graphs").symlink_to(self.base, target_is_directory=True)
        self.call("init", "--tier", "tracked", "--company", "A", "--objective", "B",
                  "--input", "brief.md", "--output", "result.md", ok=False)
        (self.root / ".agent-graphs").unlink()
        self.init()
        self.work()
        receipt = self.run_dir / "work-0.json"
        foreign = self.base / "foreign-receipt.json"
        foreign.write_bytes(receipt.read_bytes())
        receipt.unlink()
        receipt.symlink_to(foreign)
        self.call("complete", ok=False)

    def test_nonregular_input_refused_before_run_allocation(self):
        os.mkfifo(self.root / "pipe")
        self.call("init", "--tier", "tracked", "--company", "A", "--objective", "B",
                  "--input", "pipe", "--output", "result.md", ok=False)
        self.assertFalse(self.run_dir.exists())

    def test_noncanonical_paths_cannot_alias_inputs_output_or_evidence(self):
        (self.root / "doc").mkdir()
        self.write("doc/result.md", "Candidate A")
        self.write("doc/checks.md", "Separate work checks")
        self.write("doc/review.md", "Separate review")
        for field, value in [("--input", "doc//result.md"),
                             ("--output", "doc//result.md"),
                             ("--output", "doc/result.md/")]:
            self.call("init", "--tier", "verified", "--company", "A", "--objective", "B",
                      "--input", "brief.md", "--output", "doc/result.md", field, value, ok=False)
            self.assertFalse(self.run_dir.exists())
        self.init("verified", "--output", "doc/result.md")
        before = self.inventory()
        for path in ["doc//result.md", "doc//checks.md"]:
            self.work("--evidence", path, ok=False)
            self.assertEqual(before, self.inventory())
        self.work("--evidence", "doc/checks.md")
        before = self.inventory()
        for path in ["doc///result.md", "doc//checks.md", "doc//review.md"]:
            self.verify("accept", "--evidence", path, ok=False)
            self.assertEqual(before, self.inventory())
        self.verify("accept", "--evidence", "doc/review.md")
        self.call("complete")

    def make_hardlink(self, source, target):
        try:
            os.link(self.root / source, self.root / target)
        except OSError as exc:
            self.skipTest(f"Hardlinks unavailable on fixture filesystem: {exc}")

    def test_hardlinks_cannot_alias_source_output_work_or_review(self):
        self.make_hardlink("brief.md", "input-alias.md")
        self.make_hardlink("result.md", "output-alias.md")
        self.make_hardlink("checks.md", "checks-alias.md")
        self.make_hardlink("review.md", "review-alias.md")
        for extra in [("--output", "input-alias.md"), ("--input", "input-alias.md")]:
            self.call("init", "--tier", "verified", "--company", "A", "--objective", "B",
                      "--input", "brief.md", "--output", "result.md", *extra, ok=False)
            self.assertFalse(self.run_dir.exists())
        self.init("verified")
        before = self.inventory()
        for evidence in ["input-alias.md", "output-alias.md", "checks-alias.md"]:
            self.work("--evidence", evidence, ok=False)
            self.assertEqual(before, self.inventory())
        self.work()
        before = self.inventory()
        for evidence in ["input-alias.md", "output-alias.md", "checks-alias.md", "review-alias.md"]:
            self.verify("accept", "--evidence", evidence, ok=False)
            self.assertEqual(before, self.inventory())
        self.verify()
        self.call("complete")

    def test_same_content_hardlink_replacement_refused_on_resume_and_complete(self):
        self.write("checks.md", "Candidate A")
        self.init("verified")
        self.work()
        self.verify()
        (self.root / "checks.md").unlink()
        self.make_hardlink("result.md", "checks.md")
        before = self.inventory()
        self.call("resume", ok=False)
        self.call("complete", ok=False)
        self.assertEqual(before, self.inventory())
        self.assertFalse((self.run_dir / "FINAL.json").exists())

    def test_lock_and_interrupted_or_foreign_write_preserved(self):
        self.init()
        lock = self.run_dir / ".lock"
        lock.write_text("Other writer")
        before = self.inventory()
        self.call("resume", ok=False)
        self.work(ok=False)
        self.assertEqual(before, self.inventory())
        lock.unlink()
        foreign = self.run_dir / "FINAL.json"
        foreign.write_text("Foreign sentinel")
        self.work(ok=False)
        self.assertEqual(foreign.read_text(), "Foreign sentinel")
        self.assertEqual(json.loads((self.run_dir / "state.json").read_text())["phase"], "work")


if __name__ == "__main__":
    unittest.main()
