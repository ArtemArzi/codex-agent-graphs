#!/usr/bin/env python3
"""Tests for the shared agent-graph artifact lifecycle."""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
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
