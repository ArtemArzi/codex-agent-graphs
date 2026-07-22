#!/usr/bin/env python3
"""Focused adversarial checks for the Continuous Improvement controller."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import continuous_improvement_graph as graph  # noqa: E402


class ContinuousImprovementGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.write("README.md", "fixture\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, path: Path, value: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def init(self, mode: str = "audit", focus: str = "Inspect fixture regression") -> Path:
        if mode == "full":
            self.init_git()
        result = graph.initialize(str(self.root), mode, focus)
        return Path(result["data"]["run"])

    def init_git(self) -> None:
        if (self.root / ".git").exists():
            return
        for args in (
            ["git", "init"],
            ["git", "config", "user.email", "fixture@example.test"],
            ["git", "config", "user.name", "Fixture"],
            ["git", "add", "README.md"],
            ["git", "commit", "-m", "initial"],
        ):
            subprocess.run(args, cwd=self.root, check=True, capture_output=True)

    def artifact(
        self,
        run: Path,
        disposition: str,
        *,
        candidate: dict | None = None,
        issue: dict | None = None,
        task_delivery: dict | None = None,
        git: dict | None = None,
    ) -> dict:
        state = graph.load_state(run)
        return {
            "schema_version": 1,
            "run_id": state["run_id"],
            "mode": state["mode"],
            "focus": state["focus"],
            "disposition": disposition,
            "confidence": "high",
            "capabilities": ["rg", "mcp:fallback:local-only"],
            "agents": [],
            "scan": {
                "sources_checked": ["fixture test evidence"],
                "no_candidate_reason": "No actionable low-risk defect was observed." if disposition == "no-op" else None,
            },
            "candidate": candidate,
            "issue": issue,
            "task_delivery": task_delivery,
            "git": git,
            "residual_risks": [],
        }

    def candidate(self, *, scope: list[str] | None = None, risk: str = "low", protected_domains: list[str] | None = None) -> dict:
        return {
            "candidate_id": "fixture-regression",
            "title": "Fixture regression is observable",
            "source_kind": "failing-test",
            "risk": risk,
            "protected_domains": protected_domains or [],
            "evidence": [{"kind": "command", "reference": "python -m unittest fixture", "observation": "fails before the repair"}],
            "reproduction_commands": ["python -m unittest fixture"],
            "acceptance": ["The fixture regression passes without weakening the contract."],
            "scope": scope or ["src/fix.py"],
        }

    def write_work(self, run: Path, payload: dict) -> None:
        self.write_json(run / graph.WORK_NAME, payload)

    def verification(self, run: Path, verdict: str, repairs: list[str] | None = None) -> dict:
        work_sha = graph.load_state(run)["nodes"]["work"]["receipts"][-1]["sha256"]
        return {
            "schema_version": 1,
            "run_id": graph.load_state(run)["run_id"],
            "reviewer_role": "improvement_verifier",
            "reviewer_receipt": "/root/fixture-verifier",
            "verdict": verdict,
            "work_sha256": work_sha,
            "checked_claims": ["candidate evidence and risk boundary"],
            "residual_risks": [],
            "repair_list": repairs or [],
        }

    def test_init_and_status_are_resumable_without_mutation(self) -> None:
        run = self.init()
        original = (run / graph.STATE_NAME).read_bytes()
        status = graph.status(run)
        self.assertEqual(status["status"], "running")
        self.assertEqual(status["data"]["current"], "work")
        self.assertEqual((run / graph.STATE_NAME).read_bytes(), original)
        self.assertEqual(graph.initialize(str(self.root), "audit", "Inspect fixture regression")["data"]["run"], str(run))

    def test_audit_no_op_completes_and_rechecks_result(self) -> None:
        run = self.init()
        self.write_work(run, self.artifact(run, "no-op"))
        graph.record(run, "work", "succeeded")
        completed = graph.complete(run)
        self.assertEqual(completed["status"], "completed")
        output = run / graph.COMPLETE_NAME
        self.assertIn("Status: no-op", output.read_text(encoding="utf-8"))
        self.assertIn("No candidate: No actionable low-risk defect was observed.", output.read_text(encoding="utf-8"))
        self.assertEqual(graph.complete(run)["status"], "completed")

    def test_identical_trigger_starts_fresh_after_completion_but_resumes_active_run(self) -> None:
        first = self.init()
        self.write_work(first, self.artifact(first, "no-op"))
        graph.record(first, "work", "succeeded")
        graph.complete(first)

        second_result = graph.initialize(str(self.root), "audit", "Inspect fixture regression")
        second = Path(second_result["data"]["run"])
        self.assertNotEqual(second, first)
        self.assertEqual(second_result["status"], "ready")
        self.assertEqual(graph.load_state(second)["trigger_sequence"], 1)
        self.assertEqual(graph.initialize(str(self.root), "audit", "Inspect fixture regression")["data"]["run"], str(second))

    def test_no_op_rejects_repository_drift(self) -> None:
        run = self.init()
        self.write("src/unexpected.py", "drift = True\n")
        self.write_work(run, self.artifact(run, "no-op"))
        with self.assertRaisesRegex(graph.GraphError, "zero repository drift"):
            graph.record(run, "work", "succeeded")

    def test_issue_ready_rejects_repository_drift_and_accepts_clean_audit(self) -> None:
        run = self.init()
        issue = {"title": "Escalate fixture risk", "body": "The observed defect needs a human decision.", "reason": "Risk is outside autonomous delivery."}
        self.write_work(run, self.artifact(run, "issue-ready", candidate=self.candidate(risk="high"), issue=issue))
        graph.record(run, "work", "succeeded")
        self.assertEqual(graph.complete(run)["data"]["disposition"], "issue-ready")

        drifted = self.init(focus="Inspect separate fixture regression")
        self.write("src/unexpected.py", "drift = True\n")
        self.write_work(drifted, self.artifact(drifted, "issue-ready", candidate=self.candidate(risk="high"), issue=issue))
        with self.assertRaisesRegex(graph.GraphError, "zero repository drift"):
            graph.record(drifted, "work", "succeeded")

    def test_delivered_requires_exact_completed_task_delivery_and_one_commit(self) -> None:
        run = self.init("full")
        state = graph.load_state(run)
        branch = graph.graph_contract()["delivery_policy"]["branch_prefix"] + state["run_id"]
        subprocess.run(["git", "checkout", "-b", branch], cwd=self.root, check=True, capture_output=True)
        self.write("src/fix.py", "VALUE = 2\n")
        subprocess.run(["git", "add", "src/fix.py"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "repair fixture"], cwd=self.root, check=True, capture_output=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

        task_id = "TD-FIXTURE"
        td_run_id = "a1b2c3d4e5f60708"
        td_run = self.root / ".agent-graphs" / "task-delivery-runs" / td_run_id
        task_receipt = self.write_json(td_run / "task.json", {"fixture": "immutable task receipt"})
        handoff = self.write(".agent-graphs/task-delivery-handoffs/TD-FIXTURE/HANDOFF.md", "Status: READY\n")
        work_record = {"path": str(task_receipt), "sha256": graph.sha256_file(task_receipt), "changed_paths": ["src/fix.py"]}
        task_state = {
            "schema_version": 3,
            "task_id": task_id,
            "phase": "completed",
            "last_work_receipt": str(task_receipt),
            "checkpoints": {"handoff": {"path": handoff.relative_to(self.root).as_posix(), "sha256": graph.sha256_file(handoff)}},
        }
        self.write_json(self.root / ".codex" / "task-delivery" / task_id / "state.json", task_state)
        td_state = {
            "schema_version": 3,
            "graph_id": "task-delivery",
            "status": "completed",
            "run_id": td_run_id,
            "root": str(self.root),
            "profile": "standard",
            "task_id": task_id,
            "plan_path": f".agent-graphs/continuous-improvement-runs/{state['run_id']}/task-delivery/PLAN.md",
            "nodes": {"work": {"receipts": [work_record]}},
        }
        td_state_path = self.write_json(td_run / "state.json", td_state)
        td_receipt = {
            "run_dir": td_run.relative_to(self.root).as_posix(),
            "state_sha256": graph.sha256_file(td_state_path),
            "task_sha256": graph.sha256_file(task_receipt),
            "handoff_sha256": graph.sha256_file(handoff),
            "changed_paths": ["src/fix.py"],
            "tests": [{"command": "python -m unittest fixture", "status": "passed", "exit_code": 0}],
        }
        self.write_work(run, self.artifact(run, "delivered", candidate=self.candidate(), task_delivery=td_receipt, git={"branch": branch, "commit": commit}))
        graph.record(run, "work", "succeeded")
        self.assertEqual(graph.complete(run)["data"]["disposition"], "delivered")
        result_text = (run / graph.COMPLETE_NAME).read_text(encoding="utf-8")
        self.assertIn("Fixture regression is observable", result_text)
        self.assertIn("PASS: `python -m unittest fixture`", result_text)

    def test_audit_rejects_delivered_work(self) -> None:
        run = self.init()
        self.write_work(run, self.artifact(run, "delivered", candidate=self.candidate()))
        with self.assertRaisesRegex(graph.GraphError, "low-risk candidate boundary"):
            graph.record(run, "work", "succeeded")

    def test_protected_scope_and_tampered_receipt_fail_closed(self) -> None:
        run = self.init()
        issue = {"title": "Escalate protected change", "body": "This must remain issue-only.", "reason": "Protected domain."}
        self.write_work(run, self.artifact(run, "issue-ready", candidate=self.candidate(scope=["auth/token.py"], protected_domains=["security"]), issue=issue))
        graph.record(run, "work", "succeeded")
        receipt = Path(graph.load_state(run)["nodes"]["work"]["receipts"][-1]["path"])
        receipt.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "tampered"):
            graph.complete(run)

    def test_verifier_repair_and_retry_bounds_fail_closed(self) -> None:
        run = self.init()
        issue = {"title": "Escalate uncertain fixture", "body": "Independent verification is required.", "reason": "Evidence is incomplete."}
        work = self.artifact(run, "issue-ready", candidate=self.candidate(risk="medium"), issue=issue)
        self.write_work(run, work)
        graph.record(run, "work", "verify")
        self.write_json(run / graph.VERIFY_NAME, self.verification(run, "reject", ["Clarify the evidence."]))
        graph.record(run, "verify", "failed")
        self.assertEqual(graph.load_state(run)["current"], "work")
        self.write_work(run, work)
        graph.record(run, "work", "verify")
        self.write_json(run / graph.VERIFY_NAME, self.verification(run, "reject", ["Evidence remains incomplete."]))
        graph.record(run, "verify", "failed")
        self.assertEqual(graph.load_state(run)["status"], "blocked")
        with self.assertRaisesRegex(graph.GraphError, "Retry bound"):
            graph.retry(run, "verify")

    def test_unsafe_paths_and_incompatible_identity_are_rejected(self) -> None:
        with self.assertRaisesRegex(graph.GraphError, "Unsafe"):
            graph.safe_relative("../escape", "scope")
        run = self.init()
        state_path = run / graph.STATE_NAME
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["graph_sha256"] = "0" * 64
        self.write_json(state_path, state)
        with self.assertRaisesRegex(graph.GraphError, "graph.json changed"):
            graph.status(run)


if __name__ == "__main__":
    unittest.main()
