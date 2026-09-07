#!/usr/bin/env python3
"""Focused adversarial checks for the Continuous Improvement controller."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import shutil
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
            "capabilities": ["rg", "mcp:not-applicable:local-signal-only"],
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
            "benefit": {"affected": "Fixture users", "consequence": "Regression prevents expected result", "frequency": "Unknown frequency; observed in fixture", "effort": "small", "why_now": "Fresh failing test; one bounded fixture repair"},
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

    def test_started_v1_0_run_remains_readable(self) -> None:
        run = self.init()
        state_path = run / graph.STATE_NAME
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["graph_version"] = "1.0.0"
        state["graph_sha256"] = dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["1.0.0"]
        self.write_json(state_path, state)
        self.assertEqual("running", graph.status(run)["status"])

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

    def completed_issue(self, focus="Historical fixture issue"):
        run = self.init(focus=focus)
        issue = {"title": "Fixture issue", "body": "Evidence requires future repair", "reason": "Audit only"}
        self.write_work(run, self.artifact(run, "issue-ready", candidate=self.candidate(), issue=issue))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        return run

    def test_benefit_required_only_for_new_candidates(self):
        candidate = self.candidate()
        for field in candidate["benefit"]:
            invalid = json.loads(json.dumps(candidate))
            del invalid["benefit"][field]
            with self.assertRaises(graph.GraphError):
                graph.validate_candidate(invalid)
        for effort in ("medium", "large"):
            candidate["benefit"]["effort"] = effort
            graph.validate_candidate(candidate)
        del candidate["benefit"]
        graph.validate_candidate(candidate, require_benefit=False)
        with self.assertRaises(graph.GraphError):
            graph.validate_candidate(candidate)

    def test_legacy_v11_noop_and_candidate_complete_without_benefit(self):
        legacy = graph.SKILL_DIR / "assets/legacy-graph-v1.1.json"
        self.assertEqual(graph.sha256_file(legacy), dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["1.1.0"])
        for disposition in ("no-op", "issue-ready"):
            run = self.init("full", focus="Legacy fixture " + disposition)
            state = graph.load_state(run)
            state.update(graph_version="1.1.0", graph_sha256=graph.sha256_file(legacy))
            self.write_json(run / graph.STATE_NAME, state)
            candidate = self.candidate()
            del candidate["benefit"]
            issue = {"title": "Legacy issue", "body": "Existing evidence remains valid", "reason": "Audit before delivery"}
            self.write_work(run, self.artifact(run, disposition, candidate=candidate if disposition == "issue-ready" else None, issue=issue if disposition == "issue-ready" else None))
            graph.record(run, "work", "succeeded")
            graph.complete(run)

    def test_history_readonly_and_changed_code_never_skips_new_run(self):
        run = self.completed_issue()
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch.object(graph, "manifest", side_effect=AssertionError("history must not scan repository")):
            data = graph.history(str(self.root))["data"]
        self.assertEqual(data["runs"][0]["status"], "historical_only")
        self.assertIn("benefit", data["runs"][0]["summary"]["candidate"])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.write("README.md", "changed relevant code")
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "historical_only")
        new = self.init(focus="Historical fixture issue")
        self.assertNotEqual(new, run)
        self.assertEqual(graph.load_state(new)["current"], "work")

    def test_history_compacted_raw_and_pruned(self):
        run = self.completed_issue()
        self.write_json(self.root / ".agent-graphs/history/continuous-improvement" / run.name / "FINAL.json", {
            "schema_version": 1, "kind": "agent-graph-final", "terminal_status": "completed",
            "graph_id": "continuous-improvement", "run_id": run.name,
            "state_sha256": graph.sha256_file(run / graph.STATE_NAME),
            "source_run": run.relative_to(self.root).as_posix(),
        })
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "historical_only")
        shutil.rmtree(run)
        entry = graph.history(str(self.root))["data"]["runs"][0]
        self.assertEqual(entry["status"], "unavailable")
        self.assertTrue(entry["reason"])

    def test_history_partial_corrupt_and_symlink_are_unavailable(self):
        run = self.init()
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "unavailable")
        self.write_work(run, self.artifact(run, "no-op"))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        receipt = Path(graph.load_state(run)["nodes"]["work"]["receipts"][-1]["path"])
        original = receipt.read_bytes()
        receipt.write_text("{}")
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "unavailable")
        receipt.unlink()
        target = self.write("external.json", original.decode())
        receipt.symlink_to(target)
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "unavailable")
        receipt.unlink()
        receipt.write_bytes(original)
        (run / graph.STATE_NAME).write_text("{")
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "unavailable")

    def test_history_verifier_hash_and_binding(self):
        run = self.init()
        self.write_work(run, self.artifact(run, "no-op"))
        graph.record(run, "work", "verify")
        self.write_json(run / graph.VERIFY_NAME, self.verification(run, "pass"))
        graph.record(run, "verify", "succeeded")
        graph.complete(run)
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "historical_only")
        receipt = Path(graph.load_state(run)["nodes"]["verify"]["receipts"][-1]["path"])
        receipt.write_text("{}")
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "unavailable")

    def test_delivery_rejects_larger_effort_before_td(self):
        run = self.init("full")
        candidate = self.candidate()
        candidate["benefit"]["effort"] = "medium"
        self.write_work(run, self.artifact(run, "delivered", candidate=candidate))
        with self.assertRaisesRegex(graph.GraphError, "small justified"):
            graph.record(run, "work", "succeeded")

    def test_history_order_uses_newest_artifact_not_hash(self):
        older = self.completed_issue("First recency issue")
        newer = self.completed_issue("Second recency issue")
        # Make the lexically smaller identifier newest, independent of fixture hashes.
        newer, older = sorted((older, newer), key=lambda run: run.name)
        os.utime(older / graph.STATE_NAME, ns=(1000000000, 1000000000))
        os.utime(newer / graph.STATE_NAME, ns=(2000000000, 2000000000))
        data = graph.history(str(self.root), 1)["data"]
        self.assertEqual(data["order"], "latest_artifact_mtime")
        self.assertEqual(data["runs"][0]["run_id"], newer.name)
        self.assertEqual(data["runs"][0]["status"], "historical_only")
        # A new corrupt state remains visible rather than disappearing from history.
        (newer / graph.STATE_NAME).write_text("{")
        self.assertEqual(graph.history(str(self.root), 1)["data"]["runs"][0]["status"], "unavailable")

    def test_history_order_does_not_follow_symlink(self):
        run = self.completed_issue()
        os.utime(run / graph.STATE_NAME, ns=(2000000000, 2000000000))
        linked_id = "ffffffffffffffff"
        linked = self.root / str(graph.RUNS_REL) / linked_id
        linked.mkdir()
        target = self.write("outside-state.json", "{}")
        os.utime(target, ns=(9000000000, 9000000000))
        (linked / graph.STATE_NAME).symlink_to(target)
        self.assertEqual(graph.history(str(self.root), 1)["data"]["runs"][0]["run_id"], run.name)
        all_runs = graph.history(str(self.root))["data"]["runs"]
        self.assertEqual(next(item for item in all_runs if item["run_id"] == linked_id)["status"], "unavailable")

    def test_history_retains_deferred_issue_context(self):
        run = self.init()
        candidate = self.candidate(protected_domains=["security"])
        issue = {"title": "Protected fixture issue", "body": "Evidence requires separate repair", "reason": "Protected domain needs explicit authorization"}
        payload = self.artifact(run, "issue-ready", candidate=candidate, issue=issue)
        payload["residual_risks"] = ["Observed fixture defect remains unresolved"]
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        summary = graph.history(str(self.root))["data"]["runs"][0]["summary"]
        self.assertEqual(summary["candidate"]["protected_domains"], ["security"])
        self.assertEqual(summary["issue"], {"title": issue["title"], "reason": issue["reason"]})
        self.assertEqual(summary["residual_risks"], payload["residual_risks"])

    def test_task_delivery_id_contract_is_versioned(self):
        for task_id in ("singular-label", "fix.label_2", "9", "a" * 80, "TD-FIXTURE"):
            self.assertEqual(graph.validate_task_id(task_id, "1.2.0"), task_id)
        for task_id in ("../escape", "a/b", "a\\b", ".hidden", "a" * 81, "", None, "a\n"):
            with self.assertRaises(graph.GraphError):
                graph.validate_task_id(task_id, "1.2.0")
        self.assertEqual(graph.validate_task_id("A" * 128, "1.1.0"), "A" * 128)
        for task_id in ("singular-label", "fix.label_2", "9"):
            with self.assertRaises(graph.GraphError):
                graph.validate_task_id(task_id, "1.1.0")

    def test_history_fifo_final_returns_unavailable_promptly(self):
        run = self.completed_issue()
        final = self.root / ".agent-graphs/history/continuous-improvement" / run.name / "FINAL.json"
        final.parent.mkdir(parents=True)
        os.mkfifo(final)
        completed = subprocess.run(
            [sys.executable, str(Path(graph.__file__)), "history", "--root", str(self.root)],
            capture_output=True, text=True, timeout=3, check=True,
        )
        entry = json.loads(completed.stdout)["data"]["runs"][0]
        self.assertEqual(entry["status"], "unavailable")
        self.assertIn("ordinary file", entry["reason"])

    def test_legacy_completion_with_optional_benefit_keeps_old_bytes(self):
        run = self.init(focus="Legacy optional benefit fixture")
        state = graph.load_state(run)
        state.update(graph_version="1.1.0", graph_sha256=dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["1.1.0"])
        self.write_json(run / graph.STATE_NAME, state)
        issue = {"title": "Legacy fixture issue", "body": "Legacy accepted optional fields", "reason": "Audit only"}
        payload = self.artifact(run, "issue-ready", candidate=self.candidate(), issue=issue)
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        # Exact pre-1.2 Markdown fixture: optional candidate benefit was accepted
        # in the immutable work JSON but deliberately absent from this renderer.
        old_output = """# Continuous Improvement result

Status: issue-ready

## Summary

Focus: Legacy optional benefit fixture

## Evidence

- Source checked: fixture test evidence
- Candidate: Fixture regression is observable (failing-test, risk=low)
- command: python -m unittest fixture — fails before the repair

## Changed paths

- None

## Verification

- No implementation tests required

## Residual risks

- None recorded
"""
        # New controller completing a legacy active run must retain old rendering.
        graph.complete(run)
        output = run / graph.COMPLETE_NAME
        self.assertEqual(output.read_text(encoding="utf-8"), old_output)
        before_state = (run / graph.STATE_NAME).read_bytes()
        before_output = output.read_bytes()
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "historical_only")
        graph.complete(run)
        self.assertEqual((run / graph.STATE_NAME).read_bytes(), before_state)
        self.assertEqual(output.read_bytes(), before_output)
        output.write_text(old_output + "tamper", encoding="utf-8")
        self.assertEqual(graph.history(str(self.root))["data"]["runs"][0]["status"], "unavailable")

    def test_history_limits_and_summary_truncation(self):
        run = self.init()
        payload = self.artifact(run, "no-op")
        payload["scan"]["sources_checked"] = [str(i) + "x" * 10000 for i in range(30)]
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        entry = graph.history(str(self.root))["data"]["runs"][0]
        self.assertTrue(entry["truncated"])
        self.assertLess(len(json.dumps(entry)), 9000)
        for i in range(25):
            self.write_json(self.root / ".agent-graphs/history/continuous-improvement" / f"{i:016x}" / "FINAL.json", {})
        self.assertEqual(len(graph.history(str(self.root))["data"]["runs"]), 10)
        self.assertEqual(len(graph.history(str(self.root), 20)["data"]["runs"]), 20)
        for limit in (0, 21, -1):
            with self.assertRaises(graph.GraphError):
                graph.history(str(self.root), limit)


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
