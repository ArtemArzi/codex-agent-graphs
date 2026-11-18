#!/usr/bin/env python3
"""Tests for the shared agent-graph artifact lifecycle."""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
from argparse import Namespace
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "agent-graph-runtime" / "artifact_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("artifact_lifecycle", MODULE_PATH)
assert SPEC and SPEC.loader
lifecycle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lifecycle
SPEC.loader.exec_module(lifecycle)


MARKETING_SPEC = importlib.util.spec_from_file_location(
    "marketing_lifecycle_fixture",
    MODULE_PATH.parents[1] / "skills/marketing-work/scripts/marketing_graph.py",
)
assert MARKETING_SPEC and MARKETING_SPEC.loader
marketing = importlib.util.module_from_spec(MARKETING_SPEC)
MARKETING_SPEC.loader.exec_module(marketing)


class ArtifactLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.completed_at = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_json(self, path: Path, value: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def research_run(
        self,
        identifier: str = "research-01",
        *,
        status: str = "completed",
        completed_at: dt.datetime | None = None,
        output_inside: bool = False,
    ) -> Path:
        run = self.root / ".agent-graphs" / "research-runs" / identifier
        run.mkdir(parents=True)
        report = run / "report.md" if output_inside else self.root / "reports" / f"{identifier}.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("# Verified report\n", encoding="utf-8")
        stamp = completed_at or self.completed_at
        state = {
            "schema_version": 2,
            "graph_id": "research",
            "graph_version": "2.2.0",
            "run_id": identifier,
            "root": str(self.root),
            "status": status,
            "current": "complete" if status == "completed" else "work",
            "output": str(report),
            "created_at": lifecycle.iso(stamp - dt.timedelta(hours=1)),
            "updated_at": lifecycle.iso(stamp),
            "nodes": {
                "complete": {
                    "receipts": [
                        {
                            "artifact": str(report),
                            "artifact_sha256": lifecycle.sha256_file(report),
                        }
                    ]
                }
            },
        }
        self.write_json(run / "state.json", state)
        (run / "raw.json").write_text('{"large":"evidence"}\n', encoding="utf-8")
        return run

    def test_inventory_classifies_active_terminal_and_legacy_state(self) -> None:
        self.research_run("completed")
        self.research_run("blocked", status="blocked")
        legacy = self.root / ".codex" / "task-delivery" / "legacy-task"
        legacy.mkdir(parents=True)
        self.write_json(
            legacy / "state.json",
            {
                "schema_version": 2,
                "task_id": "legacy-task",
                "phase": "completed",
                "updated_at": lifecycle.iso(self.completed_at),
            },
        )
        payload = lifecycle.inventory(self.root)
        records = {Path(item["run"]).name: item for item in payload["data"]["runs"]}
        self.assertTrue(records["completed"]["eligible_for_compaction"])
        self.assertEqual("blocked", records["blocked"]["hold_reason"])
        self.assertTrue(records["legacy-task"]["eligible_for_compaction"])
        self.assertFalse((self.root / ".agent-graphs" / "history").exists())

    def test_compact_creates_verified_archive_and_final_receipt(self) -> None:
        run = self.research_run()
        payload = lifecycle.compact(self.root, run)
        final = Path(payload["artifacts"][0])
        archive = Path(payload["artifacts"][1])
        self.assertTrue(final.is_file())
        self.assertTrue(archive.is_file())
        receipt = lifecycle.final_receipt_valid(self.root, final)
        lifecycle.verify_archive_against_receipt(self.root, receipt)
        self.assertEqual("completed", receipt["terminal_status"])
        self.assertEqual(2, receipt["raw"]["files"])
        self.assertTrue(run.is_dir(), "Compaction must not delete raw state")
        self.assertEqual(
            str(self.root / "reports" / "research-01.md"),
            str(self.root / receipt["canonical_outputs"][0]["path"]),
        )
        self.assertIsNone(receipt["canonical_outputs"][0]["preserved_copy"])

    def test_compact_preserves_terminal_output_that_lives_inside_run(self) -> None:
        run = self.research_run(output_inside=True)
        receipt = lifecycle.compact(self.root, run)["data"]["final"]
        output = receipt["canonical_outputs"][0]
        self.assertIsNotNone(output["preserved_copy"])
        preserved = self.root / output["preserved_copy"]
        self.assertEqual("# Verified report\n", preserved.read_text(encoding="utf-8"))

    def test_continuous_improvement_completion_is_preserved_from_raw_run(self) -> None:
        run = self.root / ".agent-graphs" / "continuous-improvement-runs" / "improve-01"
        run.mkdir(parents=True)
        (run / "IMPROVEMENT.md").write_text("# Improvement\n", encoding="utf-8")
        self.write_json(
            run / "state.json",
            {
                "schema_version": 2,
                "graph_id": "continuous-improvement",
                "run_id": "improve-01",
                "root": str(self.root),
                "status": "completed",
                "updated_at": lifecycle.iso(self.completed_at),
                "nodes": {"complete": {"status": "completed", "receipts": []}},
            },
        )
        receipt = lifecycle.compact(self.root, run)["data"]["final"]
        output = next(
            item for item in receipt["canonical_outputs"] if item["path"].endswith("IMPROVEMENT.md")
        )
        self.assertIsNotNone(output["preserved_copy"])
        self.assertEqual(
            "# Improvement\n",
            (self.root / output["preserved_copy"]).read_text(encoding="utf-8"),
        )

    def test_compact_is_idempotent_when_run_and_archive_are_unchanged(self) -> None:
        run = self.research_run()
        lifecycle.compact(self.root, run)
        second = lifecycle.compact(self.root, run)
        self.assertTrue(second["data"]["idempotent"])

    def test_marketing_run_holds_active_state_and_preserves_canonical_output(self) -> None:
        parent = self.root / ".agent-graphs/marketing-work-runs"
        output = self.root / "campaign/funnel.md"
        output.parent.mkdir(parents=True)
        output.write_text("# Marketing design, not a live campaign\n")
        foreign = self.root / "foreign-evidence.txt"
        foreign.write_text("keep foreign evidence\n")
        for status in ("running", "completed"):
            run = parent / status
            self.write_json(run / "state.json", {
                "schema_version": 1, "graph_id": "marketing-work", "run_id": status,
                "root": str(self.root), "status": status, "output": str(output),
                "updated_at": lifecycle.iso(self.completed_at),
            })
        before = (parent / "running/state.json").read_bytes()
        records = {Path(item["run"]).name: item for item in lifecycle.inventory(self.root)["data"]["runs"]}
        self.assertEqual(records["running"]["hold_reason"], "running")
        with self.assertRaises(lifecycle.ArtifactError):
            lifecycle.compact(self.root, parent / "running")
        result = lifecycle.compact(self.root, parent / "completed")["data"]["final"]
        self.assertEqual(result["graph_id"], "marketing-work")
        self.assertEqual(result["canonical_outputs"][0]["path"], "campaign/funnel.md")
        self.assertEqual(before, (parent / "running/state.json").read_bytes())
        self.assertEqual(foreign.read_text(), "keep foreign evidence\n")
        self.assertEqual(output.read_text(), "# Marketing design, not a live campaign\n")

    def marketing_run(self, run_id):
        for name, content in {"brief.md": "Brief", "output.md": "Accepted A",
                              "work.md": "Work evidence", "review.md": "Review evidence"}.items():
            (self.root / name).write_text(content)
        common = dict(run=run_id)
        marketing.init(Namespace(**common, company="Fixture", objective="Test archived acceptance",
                                 input=["brief.md"], output="output.md", tier="verified"), self.root)
        worked = marketing.transition(
            Namespace(**common, command="work", evidence=["work.md"], author="author",
                      capability=["mcp:not-applicable:local-fixture"], verify=False,
                      first_false_assumption=None), self.root)
        marketing.transition(
            Namespace(**common, command="verify", verdict="accept", reviewer="independent",
                      role="block_reviewer", work_sha=worked["receipts"][worked["work"]],
                      output_sha=lifecycle.sha256_file(self.root / "output.md"), reason="Reviewed fixture",
                      evidence=["review.md"]), self.root)
        marketing.transition(Namespace(**common, command="complete"), self.root)
        return self.root / marketing.MANAGED / run_id

    def test_marketing_compaction_binds_accepted_content_and_reports_current_path(self):
        for change in ("unchanged", "modified", "missing"):
            with self.subTest(change=change):
                run = self.marketing_run(change)
                output = self.root / "output.md"
                accepted = output.read_bytes()
                accepted_sha = lifecycle.sha256_file(output)
                if change == "modified":
                    output.write_text("Current B")
                elif change == "missing":
                    output.unlink()
                final = lifecycle.compact(self.root, run)["data"]["final"]
                record = final["canonical_outputs"][0]
                self.assertEqual(record["sha256"], accepted_sha)
                self.assertEqual(record["current_status"], change)
                if change == "unchanged":
                    self.assertEqual((self.root / record["preserved_copy"]).read_bytes(), accepted)
                else:
                    self.assertIsNone(record["preserved_copy"])
                if change == "modified":
                    self.assertEqual(record["current_sha256"], lifecycle.sha256_file(output))
                    self.assertNotEqual(record["current_sha256"], accepted_sha)

    def test_marketing_preserved_copy_drift_fails_recheck(self):
        run = self.marketing_run("copy-drift")
        final = lifecycle.compact(self.root, run)["data"]["final"]
        copy = self.root / final["canonical_outputs"][0]["preserved_copy"]
        copy.write_text("Unexpected bytes")
        with self.assertRaisesRegex(lifecycle.ArtifactError, "Marketing accepted history copy"):
            lifecycle.compact(self.root, run)
        self.assertEqual((self.root / "output.md").read_text(), "Accepted A")

    def test_marketing_legacy_archive_misstatement_is_detected_without_rewriting(self):
        run = self.marketing_run("legacy-archive")
        final = lifecycle.compact(self.root, run)["data"]["final"]
        final_path = lifecycle.history_final_path(self.root, "marketing-work", run.name)
        # Recreate the old canonical_outputs record, which used current B.
        final["canonical_outputs"] = [{"path": "output.md", "sha256": "0" * 64,
                                       "bytes": 8, "preserved_copy": None}]
        self.write_json(final_path, final)
        before = final_path.read_bytes()
        with self.assertRaisesRegex(lifecycle.ArtifactError, "misstates the accepted"):
            lifecycle.compact(self.root, run)
        unrelated = self.research_run()
        lifecycle.compact(self.root, unrelated)
        due = lifecycle.utc_now() + dt.timedelta(days=60)
        prune = lifecycle.prune(self.root, apply=False, now=due)["data"]
        self.assertIn("misstates the accepted", prune["holds"][0]["reason"])
        self.assertIn(str(unrelated), [action["target"] for action in prune["actions"]])
        self.assertEqual(final_path.read_bytes(), before)
        self.assertTrue(run.exists())

    def test_expired_marketing_archives_recheck_acceptance_after_raw_prune(self):
        finished = lifecycle.utc_now()
        records = {}
        for run_id in ("unbound", "wrong-digest", "verified"):
            if run_id == "unbound":
                run = self.root / marketing.MANAGED / run_id
                self.write_json(run / lifecycle.STATE_NAME, {
                    "schema_version": 1, "graph_id": "marketing-work", "run_id": run_id,
                    "root": str(self.root), "status": "completed", "output": "output.md",
                    "updated_at": lifecycle.iso(finished),
                })
            else:
                run = self.marketing_run(run_id)
            output = self.root / "output.md"
            output.write_text("Current B")
            final = lifecycle.compact(self.root, run)["data"]["final"]
            records[run_id] = (run, final)

        lifecycle.prune(self.root, apply=True, now=finished + dt.timedelta(days=14))
        for run_id, (run, final) in records.items():
            self.assertFalse(run.exists())
            archive = self.root / final["raw"]["archive"]
            self.assertTrue(archive.is_file())
            final_path = lifecycle.history_final_path(self.root, "marketing-work", run_id)
            if run_id != "unbound":
                recorded_digest = lifecycle.sha256_file(output) if run_id == "wrong-digest" else final["canonical_outputs"][0]["sha256"]
                # Model a pre-fix final emitted before the raw run expired.
                final["canonical_outputs"] = [{"path": "output.md", "sha256": recorded_digest,
                                               "bytes": output.stat().st_size, "preserved_copy": None}]
            final["retention"]["archive_cleanup_after"] = lifecycle.iso(finished - dt.timedelta(days=1))
            self.write_json(final_path, final)
            records[run_id] = (final_path, final_path.read_bytes(), archive)

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = lifecycle.main(["prune", "--root", str(self.root), "--apply"])
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())["data"]
        self.assertEqual([("verified", "prune-archive")],
                         [(item["run_id"], item["action"]) for item in result["actions"]])
        self.assertEqual({"unbound", "wrong-digest"},
                         {Path(item["path"]).parent.name for item in result["holds"]})
        for run_id, (final_path, original, archive) in records.items():
            self.assertEqual(final_path.read_bytes(), original)
            self.assertEqual(archive.exists(), run_id != "verified")
        self.assertEqual(output.read_text(), "Current B")

    def test_marketing_compaction_refuses_tampered_receipts(self):
        run = self.marketing_run("tampered")
        for name in ("FINAL.json", "work-0.json", "verification-0.json"):
            artifact = run / name
            original = artifact.read_bytes()
            artifact.write_bytes(original + b" ")
            with self.assertRaisesRegex(lifecycle.ArtifactError, "Marketing"):
                lifecycle.compact(self.root, run)
            artifact.write_bytes(original)

    def test_active_blocked_and_awaiting_implementation_are_refused(self) -> None:
        for identifier, status in (("active", "running"), ("blocked", "blocked"), ("retired", "retired")):
            with self.subTest(status=status):
                run = self.research_run(identifier, status=status)
                with self.assertRaisesRegex(lifecycle.ArtifactError, "not safe to compact"):
                    lifecycle.compact(self.root, run)
                if status == "retired":
                    record = next(
                        item
                        for item in lifecycle.inventory(self.root)["data"]["runs"]
                        if Path(item["run"]).name == identifier
                    )
                    self.assertEqual("unsupported-status:retired", record["hold_reason"])
                    self.assertFalse((self.root / ".agent-graphs/history").exists())
        plan_run = self.root / ".agent-graphs" / "task-delivery-runs" / "plan-run"
        plan_run.mkdir(parents=True)
        self.write_json(
            plan_run / "state.json",
            {
                "schema_version": 3,
                "graph_id": "task-delivery",
                "run_id": "plan-run",
                "task_id": "future-work",
                "mode": "plan",
                "status": "completed",
                "updated_at": lifecycle.iso(self.completed_at),
            },
        )
        self.write_json(
            self.root / ".codex" / "task-delivery" / "future-work" / "state.json",
            {
                "schema_version": 3,
                "task_id": "future-work",
                "phase": "awaiting_implementation",
                "updated_at": lifecycle.iso(self.completed_at),
            },
        )
        with self.assertRaisesRegex(lifecycle.ArtifactError, "awaiting-implementation"):
            lifecycle.compact(self.root, plan_run)

    def test_unverified_superseded_run_is_refused(self) -> None:
        run = self.root / ".agent-graphs" / "project-start-runs" / "old-run"
        run.mkdir(parents=True)
        self.write_json(
            run / "state.json",
            {
                "schema_version": 3,
                "graph_id": "project-start",
                "run_id": "old-run",
                "status": "superseded",
                "updated_at": lifecycle.iso(self.completed_at),
            },
        )
        with self.assertRaisesRegex(lifecycle.ArtifactError, "successor-unverified"):
            lifecycle.compact(self.root, run)

    def test_symlinked_run_content_is_refused(self) -> None:
        run = self.research_run()
        target = self.root / "outside.txt"
        target.write_text("outside\n", encoding="utf-8")
        (run / "unsafe").symlink_to(target)
        with self.assertRaisesRegex(lifecycle.ArtifactError, "unsafe file"):
            lifecycle.compact(self.root, run)

    def test_managed_path_traversal_is_refused(self) -> None:
        with self.assertRaisesRegex(lifecycle.ArtifactError, "unsafe"):
            lifecycle.safe_managed(
                self.root,
                lifecycle.PurePosixPath(".agent-graphs/../outside"),
            )

    def test_mismatched_run_identity_is_refused(self) -> None:
        run = self.research_run()
        state_path = run / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["run_id"] = "another-run"
        self.write_json(state_path, state)
        with self.assertRaisesRegex(lifecycle.ArtifactError, "identity"):
            lifecycle.compact(self.root, run)

    def test_prune_is_dry_run_then_removes_only_due_verified_data(self) -> None:
        ten_days_ago = dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc)
        now = ten_days_ago + dt.timedelta(days=10)
        run = self.research_run(completed_at=ten_days_ago)
        report = self.root / "reports" / "research-01.md"
        compacted = lifecycle.compact(self.root, run)["data"]["final"]
        archive = self.root / compacted["raw"]["archive"]
        dry = lifecycle.prune(self.root, False, now=now)
        self.assertEqual(["prune-raw"], [item["action"] for item in dry["data"]["actions"]])
        self.assertTrue(run.exists())
        applied = lifecycle.prune(self.root, True, now=now)
        self.assertEqual(["prune-raw"], [item["action"] for item in applied["data"]["actions"]])
        self.assertFalse(run.exists())
        self.assertTrue(archive.exists())
        self.assertTrue(report.exists(), "Canonical user output must survive raw pruning")
        later = lifecycle.prune(self.root, True, now=ten_days_ago + dt.timedelta(days=31))
        self.assertEqual(["prune-archive"], [item["action"] for item in later["data"]["actions"]])
        self.assertFalse(archive.exists())
        final = lifecycle.history_final_path(self.root, "research", "research-01")
        self.assertTrue(final.exists(), "Permanent final receipt must survive all pruning")
        self.assertGreaterEqual(len(list((final.parent / "gc-receipts").glob("*.json"))), 2)

    def test_archive_tampering_blocks_prune(self) -> None:
        run = self.research_run(completed_at=self.completed_at)
        receipt = lifecycle.compact(self.root, run)["data"]["final"]
        archive = self.root / receipt["raw"]["archive"]
        archive.write_bytes(b"tampered")
        with self.assertRaisesRegex(lifecycle.ArtifactError, "archive digest"):
            lifecycle.prune(
                self.root,
                False,
                now=self.completed_at + dt.timedelta(days=10),
            )
        self.assertTrue(run.exists())

    def test_relative_run_argument_is_supported_by_cli(self) -> None:
        run = self.research_run()
        with contextlib.redirect_stdout(io.StringIO()):
            code = lifecycle.main(
                [
                    "compact",
                    "--root",
                    str(self.root),
                    "--run",
                    run.relative_to(self.root).as_posix(),
                ]
            )
        self.assertEqual(0, code)


if __name__ == "__main__":
    unittest.main()
