#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from task_delivery_inventory import parse_safe_config


SCRIPT = Path(__file__).resolve().parent / "task_delivery.py"


class TaskDeliveryCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.task_id = "sample-task"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_project_start_state(
        self, maintenance_status: str = "operational", phase: str = "execution"
    ) -> Path:
        artifacts = {
            "business": "docs/project/PROJECT.md",
            "decisions": "docs/project/DECISIONS.md",
            "context": "CONTEXT.md",
            "adr_dir": "docs/adr",
            "foundation_manifest": ".project-start/foundation.json",
            "foundation": "docs/project/FOUNDATION.md",
            "codebase": "docs/project/CODEBASE.md",
            "quality": "docs/project/QUALITY.md",
            "authority": "docs/project/AUTHORITY.md",
            "agent_operations": "docs/project/AGENT-OPERATIONS.md",
            "plan": "docs/project/PLAN.md",
            "verification": "docs/project/VERIFICATION.md",
        }
        path = self.root / ".project-start/state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "phase": phase,
                    "approvals": {},
                    "records": {},
                    "maintenance": {"status": maintenance_status, "history": []},
                    "artifacts": artifacts,
                    "history": [],
                }
            ),
            encoding="utf-8",
        )
        return path

    def invoke(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def run_cli(self, *args: str, expected: int = 0) -> dict:
        result = self.invoke(*args)
        self.assertEqual(
            result.returncode,
            expected,
            msg=f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertTrue(result.stdout.strip(), msg=f"missing JSON; stderr={result.stderr}")
        return json.loads(result.stdout)

    @property
    def directory(self) -> Path:
        return self.root / "docs" / "tasks" / self.task_id

    def bootstrap(self, mode: str = "plan", priority: str = "P2", plan_source: str = "LOCAL") -> Path:
        base = [
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--title",
            "Sample task",
            "--outcome",
            "Public function returns the corrected value",
            "--mode",
            mode,
            "--priority",
            priority,
            "--plan-source",
            plan_source,
        ]
        preview = self.run_cli(*base)
        self.assertEqual(preview["status"], "preview")
        self.assertFalse(self.directory.exists())
        self.run_cli(*base, "--apply")
        return self.directory

    def write(self, name: str, text: str) -> Path:
        path = self.directory / name
        path.write_text(text.strip() + "\n", encoding="utf-8")
        return path

    def record(self, event: str, expected: int = 0) -> dict:
        names = {
            "capabilities": "CAPABILITIES.md",
            "internal-research": "INTERNAL-RESEARCH.md",
            "external-research": "EXTERNAL-RESEARCH.md",
            "plan": "PLAN.md",
            "plan-review": "PLAN-REVIEW.md",
            "verification": "VERIFICATION.md",
            "code-review": "CODE-REVIEW.md",
            "handoff": "HANDOFF.md",
        }
        return self.run_cli(
            "record",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--event",
            event,
            "--evidence",
            str(self.directory / names[event]),
            "--apply",
            expected=expected,
        )

    def write_capabilities(
        self,
        external_status: str | None = None,
        external_access: str = "read-only",
        authorization: dict | None = None,
    ) -> None:
        selected = [
            {
                "name": "local-shell",
                "kind": "local",
                "status": "verified-callable",
                "access": "read-only",
                "receipt": "process:inventory-ok",
                "authorization": None,
            }
        ]
        if external_status is not None:
            selected.append(
                {
                    "name": "documentation-mcp",
                    "kind": "mcp",
                    "status": external_status,
                    "access": external_access,
                    "receipt": "call:documentation-read",
                    "authorization": authorization,
                }
            )
        block = json.dumps(
            {
                "selected": selected,
                "hooks": [
                    {
                        "name": "local-guardrails",
                        "status": "observed",
                        "receipt": "event:pre-tool-use",
                    }
                ],
                "gaps": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        self.write(
            "CAPABILITIES.md",
            f"""
# Capabilities
Status: READY
Checked at: 2026-07-19
Environment: isolated fixture

The applicable instructions, targeted local tool, permissions, fallback, and observed hook were checked. No external write is authorized.

<!-- task-delivery:capabilities
{block}
-->
""",
        )

    def write_research(self, applicability: str = "N/A", reason: str | None = None) -> None:
        self.write(
            "INTERNAL-RESEARCH.md",
            """
# Internal research
Status: READY
Baseline: PASS

The public execution path, its caller, nearby tests, error handling, and current behavior were inspected. The baseline command completed and the planned seam is narrow. Facts and assumptions are separated.
""",
        )
        reason = reason or "The synthetic task depends only on stable local behavior and no external changing fact."
        self.write(
            "EXTERNAL-RESEARCH.md",
            f"""
# External research
Status: READY
Applicability: {applicability}
Checked at: 2026-07-19
Reason: {reason}

Primary-source applicability was considered. This fixture records why external evidence is required or safely not applicable, and the independent plan reviewer checks that decision.
""",
        )

    def write_plan(
        self,
        mode: str,
        scope: str = "src/new.py\ntests/test_new.py",
        source: str = "LOCAL",
        reference: str = "N/A",
        revision: str = "N/A",
        suffix: str = "",
    ) -> Path:
        return self.write(
            "PLAN.md",
            f"""
# Plan
Status: READY
Mode: {mode}
Priority: P2
Outcome: Public function returns the corrected value
Plan source: {source}
Canonical reference: {reference}
Canonical revision: {revision}

The plan changes one observable behavior through the existing public seam, keeps unrelated work out of scope, and verifies a positive path, a negative case, rollback, and documentation impact. One serious alternative was rejected as broader than necessary. {suffix}

<!-- task-delivery:scope
{scope}
-->
""",
        )

    def write_plan_review(
        self,
        canonical_revision: str = "N/A",
        receipt: str = "/root/plan-review-fixture",
        canonical_checked_at: str | None = None,
    ) -> None:
        plan = self.directory / "PLAN.md"
        digest = hashlib.sha256(plan.read_bytes()).hexdigest()
        is_canonical = canonical_revision != "N/A"
        revision_source = "documentation-mcp" if is_canonical else "N/A"
        revision_receipt = "call:canonical-revision-read" if is_canonical else "N/A"
        checked_at = canonical_checked_at or (datetime.now(timezone.utc).replace(microsecond=0).isoformat() if is_canonical else "N/A")
        self.write(
            "PLAN-REVIEW.md",
            f"""
# Plan review
Verdict: PASS
Reviewed plan SHA-256: {digest}
Canonical revision checked: {canonical_revision}
Canonical revision source: {revision_source}
Canonical revision receipt: {revision_receipt}
Canonical checked at: {checked_at}
Critical open: 0
High open: 0
Independent review: YES
Review origin: subagent
Reviewer receipt: {receipt}
Reviewer: independent-plan-reviewer
Reviewed at: 2026-07-19

The independent reviewer compared the exact plan with the request, repository path, instructions, source decision, acceptance oracle, rollback, and scope. No hidden side effect or broader design change remains.
""",
        )

    def prepare_plan_review(
        self,
        mode: str = "plan",
        scope: str = "src/new.py\ntests/test_new.py",
        source: str = "LOCAL",
        reference: str = "N/A",
        revision: str = "N/A",
        priority: str = "P2",
    ) -> Path:
        self.bootstrap(mode, priority, source)
        self.write_capabilities(external_status="verified-callable" if source == "CANONICAL" else None)
        self.record("capabilities")
        self.write_research()
        self.record("internal-research")
        self.record("external-research")
        self.write_plan(mode, scope, source, reference, revision)
        self.record("plan")
        self.write_plan_review(revision if source == "CANONICAL" else "N/A")
        self.record("plan-review")
        return self.directory

    def begin_and_approve(self) -> None:
        self.run_cli(
            "begin-implement",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--note",
            "User asked to implement this exact reviewed plan",
            "--apply",
        )
        self.run_cli(
            "approve-plan",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--source",
            "user-invocation",
            "--apply",
        )

    def approve_full(self) -> None:
        self.run_cli(
            "approve-plan",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--source",
            "full-mode-request",
            "--apply",
        )

    def write_implementation(self) -> None:
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "src" / "new.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.root / "tests" / "test_new.py").write_text("assert 1 == 1\n", encoding="utf-8")

    def checkpoint(self, status: str = "COMPLETE", expected: int = 0) -> dict:
        self.write(
            "PROGRESS.md",
            f"""
# Progress
Status: {status}
Last completed slice: public behavior and its regression test
Best-known checks: python syntax and fixture oracle pass
Next action: record verification and request independent result review
Resume command: python3 scripts/task_delivery.py status --root fixture --task-id sample-task
Updated at: 2026-07-19

The approved plan stayed unchanged. Current changed paths, failed hypotheses, remaining risk, and the next safe action are recorded for resumption.
""",
        )
        return self.run_cli(
            "checkpoint",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--apply",
            expected=expected,
        )

    def write_verification(self, commands: list[dict] | None = None, baseline: str = "PASS", sanity: str = "PASS") -> Path:
        if commands is None:
            command_run = subprocess.run(
                [sys.executable, "-c", "assert 2 + 2 == 4"],
                cwd=self.root,
                check=False,
            )
            commands = [
                {
                    "command": f"{sys.executable} -c 'assert 2 + 2 == 4'",
                    "cwd": str(self.root),
                    "purpose": "positive",
                    "exit_code": command_run.returncode,
                    "expected_exit_codes": [0],
                    "expectation_met": command_run.returncode == 0,
                    "result": "The public fixture oracle completed successfully.",
                    "criterion": "The corrected observable result is present.",
                }
            ]
        data = {
            "commands": commands,
            "baseline": (
                {"status": "PASS", "evidence": "Baseline behavior was reproduced before the implementation.", "reason": ""}
                if baseline == "PASS"
                else {"status": "N/A", "evidence": "", "reason": "No executable baseline exists for this documentation-only change."}
            ),
            "test_sanity": (
                {"status": "PASS", "evidence": "A deliberately wrong variant caused the new test to fail.", "reason": ""}
                if sanity == "PASS"
                else {"status": "N/A", "evidence": "", "reason": "No new or changed test oracle exists for this documentation-only change."}
            ),
            "active_verifier": {
                "status": "PASS",
                "case": "A deliberately wrong return value was exercised.",
                "result": "The negative case failed while the corrected case passed.",
            },
        }
        state = json.loads(
            (self.root / ".codex" / "task-delivery" / self.task_id / "state.json").read_text(encoding="utf-8")
        )
        plan_text = (self.directory / "PLAN.md").read_text(encoding="utf-8")
        if state.get("plan_source") == "CANONICAL":
            def plan_field(label: str) -> str:
                for line in plan_text.splitlines():
                    if line.startswith(label + ":"):
                        return line.split(":", 1)[1].strip()
                raise AssertionError(label)

            data["canonical_revision"] = {
                "status": "PASS",
                "reference": plan_field("Canonical reference"),
                "revision": plan_field("Canonical revision"),
                "source": "documentation-mcp",
                "receipt": "call:canonical-revision-refresh",
                "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
        else:
            data["canonical_revision"] = {
                "status": "N/A",
                "reference": "N/A",
                "revision": "N/A",
                "source": "N/A",
                "receipt": "N/A",
                "checked_at": "N/A",
            }
        return self.write(
            "VERIFICATION.md",
            f"""
# Verification
Verdict: PASS
Real commands: YES
Baseline checked: {baseline}
Test sanity: {sanity}
Verified at: 2026-07-19

Commands, exit codes, baseline evidence, test-oracle sanity, active counterexample, hook outcome, and residual risk were recorded without embedding large logs.

<!-- task-delivery:verification
{json.dumps(data, ensure_ascii=False, indent=2)}
-->
""",
        )

    def record_verification(self, **kwargs: object) -> dict:
        self.write_verification(**kwargs)
        return self.record("verification")

    def write_code_review(
        self,
        implementation_digest: str,
        verification_path: Path | None = None,
        force_single: bool = False,
    ) -> None:
        verification_path = verification_path or self.directory / "VERIFICATION.md"
        verification_digest = hashlib.sha256(verification_path.read_bytes()).hexdigest()
        state = json.loads(
            (self.root / ".codex" / "task-delivery" / self.task_id / "state.json").read_text(encoding="utf-8")
        )
        reviewers = [
            {
                "role": "whole-system",
                "origin": "subagent",
                "receipt": "/root/code-review-fixture",
                "verdict": "PASS",
            }
        ]
        if not force_single and state["priority"] == "P1":
            reviewers.append(
                {
                    "role": "risk-block",
                    "origin": "subagent",
                    "receipt": "/root/risk-review-fixture",
                    "verdict": "PASS",
                }
            )
        if not force_single and state["priority"] == "P0":
            reviewers.append(
                {
                    "role": "root-cause",
                    "origin": "subagent",
                    "receipt": "/root/root-cause-review-fixture",
                    "verdict": "PASS",
                }
            )
        self.write(
            "CODE-REVIEW.md",
            f"""
# Code review
Verdict: PASS
Reviewed implementation SHA-256: {implementation_digest}
Reviewed verification SHA-256: {verification_digest}
Critical open: 0
High open: 0
Independent review: YES
Active verifier: YES
Review origin: subagent
Reviewer receipt: /root/code-review-fixture
Reviewed at: 2026-07-19

The independent result reviewer inspected the exact implementation snapshot and verification evidence, checked the public path, tried a counterexample, and confirmed that tests and CI gates were not weakened.

<!-- task-delivery:reviewers
{json.dumps({"reviewers": reviewers}, ensure_ascii=False, indent=2)}
-->
""",
        )

    def finish(self) -> str:
        verification = self.record_verification()
        implementation_digest = verification["data"]["implementation_repo_digest"]
        self.write_code_review(implementation_digest)
        self.record("code-review")
        self.write(
            "HANDOFF.md",
            f"""
# Handoff
Status: READY
Implementation SHA-256: {implementation_digest}
Criteria passed: YES
Rollback documented: YES
Residual risks documented: YES
Canonical docs changed: NO
Proposed documentation maintenance: NONE: no Project Start canonical impact in this fixture
Completed at: 2026-07-19

The requested behavior, exact changed paths, commands, independent result review, rollback procedure, capability use, hook outcome, and bounded residual risk are recorded for the next operator.
""",
        )
        self.record("handoff")
        self.run_cli("complete", "--root", str(self.root), "--task-id", self.task_id, "--apply")
        return implementation_digest

    def test_bootstrap_preview_requires_outcome_and_refuses_overwrite(self) -> None:
        missing = self.invoke(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            "missing-outcome",
            "--title",
            "Missing",
            "--mode",
            "plan",
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--outcome", missing.stderr)
        self.bootstrap("plan")
        duplicate = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--title",
            "Again",
            "--outcome",
            "Another observable outcome",
            "--mode",
            "plan",
            "--apply",
            expected=2,
        )
        self.assertIn("перезаписывает", duplicate["summary"])
        no_new_implement = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            "implement-only",
            "--title",
            "No prior plan",
            "--outcome",
            "Previously reviewed behavior is implemented",
            "--mode",
            "implement",
            expected=2,
        )
        self.assertIn("существующий", no_new_implement["summary"])

    def test_pending_project_start_reopen_blocks_new_task(self) -> None:
        state = self.root / ".project-start/state.json"
        state.parent.mkdir()
        state.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "maintenance": {
                        "status": "reopen-required",
                        "pending_reopen": {
                            "stage": "foundation",
                            "rationale": "A module boundary changed.",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        result = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            "blocked-by-reopen",
            "--title",
            "Blocked",
            "--outcome",
            "A complete observable result",
            "--mode",
            "full",
            expected=2,
        )
        self.assertIn("reopen foundation", result["summary"])

    def test_unsettled_project_start_maintenance_blocks_new_task(self) -> None:
        for status, details in (
            ("maintenance-required", {"maintenance_required": {"task_id": "TD-OLD"}}),
            ("running", {"active_run": {"run_id": "run-running"}}),
            ("blocked", {"active_run": {"run_id": "run-blocked"}}),
        ):
            with self.subTest(status=status):
                state = self.root / ".project-start/state.json"
                state.parent.mkdir(exist_ok=True)
                state.write_text(
                    json.dumps({"schema_version": 2, "maintenance": {"status": status, **details}}),
                    encoding="utf-8",
                )
                result = self.run_cli(
                    "bootstrap",
                    "--root",
                    str(self.root),
                    "--task-id",
                    f"blocked-{status}",
                    "--title",
                    "Blocked",
                    "--outcome",
                    "A complete observable result",
                    "--mode",
                    "full",
                    expected=2,
                )
                self.assertIn("заблокирована", result["summary"])

    def test_state_symlink_escape_is_rejected(self) -> None:
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / ".codex").symlink_to(outside, target_is_directory=True)
        result = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--title",
            "Escape",
            "--outcome",
            "No state can escape the repository root",
            "--mode",
            "plan",
            expected=2,
        )
        self.assertTrue(
            "выходит за корень" in result["summary"] or "Симлинк запрещён" in result["summary"]
        )
        self.assertEqual(list(outside.iterdir()), [])

    def test_internal_state_symlink_is_also_rejected(self) -> None:
        inside = self.root / "state-target"
        inside.mkdir()
        (self.root / ".codex").symlink_to(inside, target_is_directory=True)
        result = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--title",
            "Internal state alias",
            "--outcome",
            "Machine state cannot overwrite an aliased path",
            "--mode",
            "plan",
            expected=2,
        )
        self.assertIn("Симлинк запрещён", result["summary"])

    def test_event_order_is_enforced(self) -> None:
        self.bootstrap()
        self.write_plan("plan", scope="src/example.py")
        result = self.record("plan", expected=2)
        self.assertIn("зависимости", result["summary"])

    def test_plan_mode_keeps_production_tree_unchanged(self) -> None:
        (self.root / "src").mkdir()
        production = self.root / "src" / "existing.py"
        production.write_text("VALUE = 1\n", encoding="utf-8")
        before = production.read_bytes()
        self.prepare_plan_review("plan", scope="src/existing.py")
        self.assertEqual(production.read_bytes(), before)
        status = self.run_cli("status", "--root", str(self.root), "--task-id", self.task_id)
        self.assertEqual(status["data"]["effective_phase"], "awaiting_approval")

    def test_selected_mcp_requires_verified_callable_preflight(self) -> None:
        self.bootstrap()
        self.write_capabilities(external_status="advertised")
        result = self.record("capabilities", expected=2)
        self.assertIn("verified-callable", result["summary"])
        self.write_capabilities(external_status="verified-callable")
        accepted = self.record("capabilities")
        self.assertEqual(accepted["data"]["verified_external_capabilities"], 1)

    def test_external_write_requires_explicit_authorization_receipt(self) -> None:
        self.bootstrap()
        self.write_capabilities(external_status="verified-callable", external_access="read-write")
        result = self.record("capabilities", expected=2)
        self.assertIn("authorization", result["summary"])
        self.write_capabilities(
            external_status="verified-callable",
            external_access="read-write",
            authorization={
                "source": "user-turn:fixture",
                "scope": "issue:fixture-only",
                "receipt": "turn:write-authorized",
            },
        )
        accepted = self.record("capabilities")
        self.assertEqual(accepted["status"], "ok")

    def test_external_na_requires_a_real_reason(self) -> None:
        self.bootstrap()
        self.write_capabilities()
        self.record("capabilities")
        self.write_research(reason="too short")
        self.record("internal-research")
        result = self.record("external-research", expected=2)
        self.assertIn("Reason", result["summary"])

    def test_canonical_plan_binds_exact_revision(self) -> None:
        self.prepare_plan_review(
            "plan",
            source="CANONICAL",
            reference="linear:ENG-4321",
            revision="revision:8f39b7d2",
        )
        state = json.loads(
            (self.root / ".codex" / "task-delivery" / self.task_id / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["checkpoints"]["plan-review"]["canonical_revision"], "revision:8f39b7d2")

    def test_canonical_bootstrap_uses_thin_template_and_stale_receipt_fails(self) -> None:
        self.bootstrap(plan_source="CANONICAL")
        template = (self.directory / "PLAN.md").read_text(encoding="utf-8")
        self.assertIn("Plan source: CANONICAL", template)
        self.assertNotIn("## Критерии приёмки", template)
        self.write_capabilities(external_status="verified-callable")
        self.record("capabilities")
        self.write_research()
        self.record("internal-research")
        self.record("external-research")
        self.write_plan(
            "plan",
            source="CANONICAL",
            reference="linear:ENG-4321",
            revision="revision:8f39b7d2",
        )
        self.record("plan")
        self.write_plan_review("revision:8f39b7d2", canonical_checked_at="2000-01-01T00:00:00+00:00")
        result = self.record("plan-review", expected=2)
        self.assertIn("старше 24", result["summary"])

    def test_review_receipt_must_match_origin(self) -> None:
        self.bootstrap()
        self.write_capabilities()
        self.record("capabilities")
        self.write_research()
        self.record("internal-research")
        self.record("external-research")
        self.write_plan("plan")
        self.record("plan")
        self.write_plan_review(receipt="fake")
        result = self.record("plan-review", expected=2)
        self.assertIn("Reviewer receipt", result["summary"])

    def test_begin_implement_binds_exact_plan_before_approval(self) -> None:
        self.prepare_plan_review("plan")
        no_intent = self.run_cli(
            "approve-plan",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--source",
            "user-invocation",
            "--apply",
            expected=2,
        )
        self.assertIn("begin-implement", no_intent["summary"])
        self.begin_and_approve()
        status = self.run_cli("status", "--root", str(self.root), "--task-id", self.task_id)
        self.assertEqual(status["data"]["mode"], "implement")
        self.assertTrue(status["data"]["approval_valid"])

    def test_plan_change_after_begin_requires_a_new_user_request(self) -> None:
        self.prepare_plan_review("plan")
        self.run_cli(
            "begin-implement",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--note",
            "turn:fixture user requested this exact reviewed plan",
            "--apply",
        )
        self.write_plan("plan", suffix="The plan changed after the user invocation was captured.")
        self.record("plan")
        state = json.loads(
            (self.root / ".codex" / "task-delivery" / self.task_id / "state.json").read_text(encoding="utf-8")
        )
        self.assertIsNone(state["implementation_intent"])

    def test_full_authorization_is_consumed_by_any_first_implementation_transition(self) -> None:
        self.prepare_plan_review(
            "full", scope="src/new.py\ntests/test_new.py\ndocs/project/PROJECT.md"
        )
        self.run_cli(
            "begin-implement",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--note",
            "turn:fixture explicit implementation request",
            "--apply",
        )
        self.run_cli(
            "approve-plan",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--source",
            "user-invocation",
            "--apply",
        )
        self.write_plan("full", suffix="A newly reviewed version requires a new user request.")
        self.record("plan")
        self.write_plan_review()
        self.record("plan-review")
        result = self.run_cli(
            "approve-plan",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--source",
            "full-mode-request",
            "--apply",
            expected=2,
        )
        self.assertIn("уже использовано", result["summary"])

    def test_begin_implement_rejects_missing_request_receipt(self) -> None:
        self.prepare_plan_review("plan")
        missing = self.invoke(
            "begin-implement",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--apply",
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--note", missing.stderr)
        short = self.run_cli(
            "begin-implement",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--note",
            "old",
            "--apply",
            expected=2,
        )
        self.assertIn("нового пользовательского запроса", short["summary"])

    def test_progress_checkpoint_is_required_before_verification(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.write_verification()
        result = self.record("verification", expected=2)
        self.assertIn("PROGRESS", result["summary"])

    def test_scope_drift_blocks_checkpoint(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        (self.root / "outside.txt").write_text("unexpected\n", encoding="utf-8")
        result = self.checkpoint(expected=2)
        self.assertIn("вне плана", result["summary"])

    def test_blocked_progress_cannot_enter_verification(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint(status="BLOCKED")
        self.write_verification()
        result = self.record("verification", expected=2)
        self.assertIn("Status: COMPLETE", result["summary"])

    def test_unexecutable_command_cannot_be_a_passing_oracle(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.write_verification(
            commands=[
                {
                    "command": "missing-runner --test",
                    "cwd": str(self.root),
                    "purpose": "positive",
                    "exit_code": 127,
                    "expected_exit_codes": [127],
                    "expectation_met": True,
                    "result": "The command could not be executed.",
                    "criterion": "The final public oracle must run.",
                }
            ]
        )
        result = self.record("verification", expected=2)
        self.assertIn("126/127", result["summary"])
        self.write_verification(
            commands=[
                {
                    "command": "python -c 'raise SystemExit(1)'",
                    "cwd": str(self.root),
                    "purpose": "baseline",
                    "exit_code": 1,
                    "expected_exit_codes": [1],
                    "expectation_met": True,
                    "result": "The known-bad baseline failed as expected.",
                    "criterion": "The original defect is reproducible.",
                }
            ]
        )
        result = self.record("verification", expected=2)
        self.assertIn("положительный оракул", result["summary"])

    def test_scope_cannot_overlap_task_artifacts(self) -> None:
        self.bootstrap()
        self.write_capabilities()
        self.record("capabilities")
        self.write_research()
        self.record("internal-research")
        self.record("external-research")
        self.write_plan("plan", scope="docs")
        result = self.record("plan", expected=2)
        self.assertIn("пересекает", result["summary"])

    def test_nested_external_symlink_in_scope_is_rejected(self) -> None:
        external = Path(self.temp.name) / "external-code"
        external.mkdir()
        (self.root / "src").mkdir()
        (self.root / "src" / "external").symlink_to(external, target_is_directory=True)
        self.bootstrap()
        self.write_capabilities()
        self.record("capabilities")
        self.write_research()
        self.record("internal-research")
        self.record("external-research")
        self.write_plan("plan", scope="src")
        result = self.record("plan", expected=2)
        self.assertIn("Симлинк области выходит", result["summary"])

    def test_gitignored_scoped_file_drift_is_detected(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / ".gitignore").write_text("ignored.cfg\n", encoding="utf-8")
        ignored = self.root / "ignored.cfg"
        ignored.write_text("VALUE=before\n", encoding="utf-8")
        self.prepare_plan_review("full", scope="ignored.cfg")
        self.approve_full()
        ignored.write_text("VALUE=implemented\n", encoding="utf-8")
        self.checkpoint()
        self.finish()
        ignored.write_text("VALUE=drifted\n", encoding="utf-8")
        status = self.run_cli("status", "--root", str(self.root), "--task-id", self.task_id)
        self.assertEqual(status["data"]["effective_phase"], "completed_with_drift")

    def test_gitignored_file_outside_scope_blocks_checkpoint(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / ".gitignore").write_text("outside-ignored.cfg\n", encoding="utf-8")
        outside = self.root / "outside-ignored.cfg"
        outside.write_text("VALUE=before\n", encoding="utf-8")
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        outside.write_text("VALUE=changed\n", encoding="utf-8")
        result = self.checkpoint(expected=2)
        self.assertIn("вне плана", result["summary"])

    def test_tampered_baseline_manifest_is_rejected(self) -> None:
        self.bootstrap()
        self.write_capabilities()
        self.record("capabilities")
        self.write_research()
        self.record("internal-research")
        self.record("external-research")
        self.write_plan("plan")
        self.record("plan")
        baseline = self.root / ".codex" / "task-delivery" / self.task_id / "baseline-manifest.json"
        baseline.write_text('{"tampered.py":{"kind":"missing"}}\n', encoding="utf-8")
        self.write_plan_review()
        result = self.record("plan-review", expected=2)
        self.assertIn("подменён", result["summary"])

    def test_full_happy_path_binds_all_result_evidence(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        expected_digest = self.finish()
        status = self.run_cli("status", "--root", str(self.root), "--task-id", self.task_id)
        self.assertEqual(status["data"]["phase"], "completed")
        state = json.loads(
            (self.root / ".codex" / "task-delivery" / self.task_id / "state.json").read_text(encoding="utf-8")
        )
        for event in ("verification", "code-review", "handoff"):
            self.assertEqual(state["checkpoints"][event]["implementation_repo_digest"], expected_digest)

    def test_completed_task_creates_project_start_maintenance_obligation(self) -> None:
        project_state = self.create_project_start_state()
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.finish()
        project = json.loads(project_state.read_text(encoding="utf-8"))
        self.assertEqual(project["maintenance"]["status"], "maintenance-required")
        self.assertEqual(
            project["maintenance"]["maintenance_required"]["task_id"], self.task_id
        )
        blocked = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            "next-task",
            "--title",
            "Next task",
            "--outcome",
            "A second result",
            "--mode",
            "full",
            expected=2,
        )
        self.assertIn("maintenance", blocked["summary"])

    def test_completed_task_can_restore_missing_maintenance_obligation(self) -> None:
        project_state = self.create_project_start_state()
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.finish()
        project = json.loads(project_state.read_text(encoding="utf-8"))
        project["maintenance"] = {"status": "operational", "history": []}
        project_state.write_text(json.dumps(project), encoding="utf-8")
        recovered = self.run_cli(
            "complete", "--root", str(self.root), "--task-id", self.task_id, "--apply"
        )
        self.assertEqual(recovered["data"]["phase"], "completed")
        project = json.loads(project_state.read_text(encoding="utf-8"))
        self.assertEqual(project["maintenance"]["status"], "maintenance-required")

    def test_project_start_phase_must_open_execution_before_task_bootstrap(self) -> None:
        self.create_project_start_state(phase="discovery")
        result = self.run_cli(
            "bootstrap",
            "--root",
            str(self.root),
            "--task-id",
            "too-early",
            "--title",
            "Too early",
            "--outcome",
            "A result that must wait for project gates",
            "--mode",
            "full",
            expected=2,
        )
        self.assertIn("execution", result["summary"])

    def test_nested_agents_change_is_project_start_canonical_drift(self) -> None:
        self.create_project_start_state()
        agents = self.root / "services/api/AGENTS.md"
        agents.parent.mkdir(parents=True)
        agents.write_text("# API context\n", encoding="utf-8")
        self.prepare_plan_review(
            "full", scope="src/new.py\ntests/test_new.py\nservices/api/AGENTS.md"
        )
        self.approve_full()
        self.write_implementation()
        agents.write_text("# Silently changed API authority\n", encoding="utf-8")
        self.checkpoint()
        verification = self.record_verification()
        implementation_digest = verification["data"]["implementation_repo_digest"]
        self.write_code_review(implementation_digest)
        self.record("code-review")
        self.write(
            "HANDOFF.md",
            f"""
# Handoff
Status: READY
Implementation SHA-256: {implementation_digest}
Criteria passed: YES
Rollback documented: YES
Residual risks documented: YES
Canonical docs changed: NO
Proposed documentation maintenance: Update nested agent context through Project Start.
Completed at: 2026-07-20
""",
        )
        result = self.record("handoff", expected=2)
        self.assertIn("AGENTS.md", result["summary"])

    def test_project_start_canonical_doc_change_is_rejected_at_handoff(self) -> None:
        business = self.root / "docs/project/PROJECT.md"
        business.parent.mkdir(parents=True)
        business.write_text("# Approved project\n", encoding="utf-8")
        project_state = self.root / ".project-start/state.json"
        project_state.parent.mkdir()
        project_state.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "phase": "execution",
                    "maintenance": {"status": "operational", "history": []},
                    "artifacts": {"business": "docs/project/PROJECT.md", "adr_dir": "docs/adr"},
                }
            ),
            encoding="utf-8",
        )
        self.prepare_plan_review(
            "full", scope="src/new.py\ntests/test_new.py\ndocs/project/PROJECT.md"
        )
        self.approve_full()
        self.write_implementation()
        business.write_text("# Silently changed project meaning\n", encoding="utf-8")
        self.checkpoint()
        verification = self.record_verification()
        implementation_digest = verification["data"]["implementation_repo_digest"]
        self.write_code_review(implementation_digest)
        self.record("code-review")
        self.write(
            "HANDOFF.md",
            f"""
# Handoff
Status: READY
Implementation SHA-256: {implementation_digest}
Criteria passed: YES
Rollback documented: YES
Residual risks documented: YES
Canonical docs changed: NO
Proposed documentation maintenance: Update the affected business document through Project Start maintenance.
Completed at: 2026-07-19
""",
        )
        result = self.record("handoff", expected=2)
        self.assertIn("канонические документы", result["summary"])

    def test_code_review_rejects_code_changed_after_verification(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        verification = self.record_verification()
        old_digest = verification["data"]["implementation_repo_digest"]
        self.write_code_review(old_digest)
        (self.root / "src" / "new.py").write_text("VALUE = 2\n", encoding="utf-8")
        result = self.record("code-review", expected=2)
        self.assertTrue("снимком" in result["summary"] or "зависимости" in result["summary"])

    def test_plan_and_result_reviews_require_different_receipts(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        verification = self.record_verification()
        implementation_digest = verification["data"]["implementation_repo_digest"]
        self.write_code_review(implementation_digest)
        review = self.directory / "CODE-REVIEW.md"
        review.write_text(
            review.read_text(encoding="utf-8").replace(
                "/root/code-review-fixture", "/root/plan-review-fixture"
            ),
            encoding="utf-8",
        )
        result = self.record("code-review", expected=2)
        self.assertIn("отдельного запуска", result["summary"])

    def test_p0_and_p1_require_priority_specific_result_review(self) -> None:
        for priority, role in (("P1", "risk-block"), ("P0", "root-cause")):
            with self.subTest(priority=priority):
                if self.directory.exists():
                    self.tearDown()
                    self.setUp()
                self.prepare_plan_review("full", priority=priority)
                self.approve_full()
                self.write_implementation()
                self.checkpoint()
                verification = self.record_verification()
                self.write_code_review(
                    verification["data"]["implementation_repo_digest"], force_single=True
                )
                result = self.record("code-review", expected=2)
                self.assertIn(role, result["summary"])

    def test_canonical_verification_rejects_revision_drift(self) -> None:
        self.prepare_plan_review(
            "full",
            source="CANONICAL",
            reference="linear:ENG-4321",
            revision="revision:8f39b7d2",
        )
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        verification = self.write_verification()
        verification.write_text(
            verification.read_text(encoding="utf-8").replace(
                '"revision": "revision:8f39b7d2"', '"revision": "revision:changed"'
            ),
            encoding="utf-8",
        )
        result = self.record("verification", expected=2)
        self.assertIn("точные reference/revision", result["summary"])

    def test_completed_task_reports_content_and_mode_drift(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.finish()
        target = self.root / "src" / "new.py"
        target.chmod(0o755)
        status = self.run_cli("status", "--root", str(self.root), "--task-id", self.task_id)
        self.assertEqual(status["data"]["effective_phase"], "completed_with_drift")
        self.assertIn("verification", status["data"]["stale_events"])
        blocked = self.run_cli(
            "complete",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--apply",
            expected=2,
        )
        self.assertIn("несвеж", blocked["summary"])

    def test_verification_requires_structured_commands_and_p1_evidence(self) -> None:
        self.prepare_plan_review("full", priority="P1")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.write_verification(commands=[], baseline="N/A", sanity="N/A")
        result = self.record("verification", expected=2)
        self.assertIn("commands", result["summary"])
        self.write_verification(baseline="N/A", sanity="PASS")
        result = self.record("verification", expected=2)
        self.assertIn("P1", result["summary"])

    def test_changed_test_path_cannot_claim_test_sanity_na(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.write_verification(sanity="N/A")
        result = self.record("verification", expected=2)
        self.assertIn("изменён путь теста", result["summary"])

    def test_re_recording_early_evidence_invalidates_later_gates(self) -> None:
        self.prepare_plan_review("full")
        self.approve_full()
        self.write_implementation()
        self.checkpoint()
        self.finish()
        self.write_research()
        self.record("internal-research")
        status = self.run_cli("status", "--root", str(self.root), "--task-id", self.task_id)
        self.assertFalse(status["data"]["approval_valid"])
        self.assertEqual(status["data"]["recorded_events"], ["capabilities", "internal-research"])

    def test_lock_contention_rejects_a_second_writer(self) -> None:
        self.bootstrap()
        lock = self.root / ".codex" / "task-delivery" / f"{self.task_id}.lock"
        lock.mkdir()
        result = self.run_cli(
            "checkpoint",
            "--root",
            str(self.root),
            "--task-id",
            self.task_id,
            "--apply",
            expected=2,
        )
        self.assertIn("другой процесс", result["summary"])

    def test_stale_lock_has_safe_preview_and_recovery(self) -> None:
        self.bootstrap()
        lock = self.root / ".codex" / "task-delivery" / f"{self.task_id}.lock"
        lock.mkdir()
        (lock / "owner.json").write_text(
            json.dumps({"pid": 99999999, "started_at": "2000-01-01T00:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        os.utime(lock, (1, 1))
        preview = self.run_cli(
            "recover-lock", "--root", str(self.root), "--task-id", self.task_id
        )
        self.assertEqual(preview["status"], "preview")
        self.assertTrue(lock.exists())
        self.run_cli(
            "recover-lock", "--root", str(self.root), "--task-id", self.task_id, "--apply"
        )
        self.assertFalse(lock.exists())

    def test_inventory_is_secret_safe_targeted_and_does_not_touch_git_index(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        tracked = self.root / "tracked.txt"
        tracked.write_text("safe\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.root, check=True)
        index = self.root / ".git" / "index"
        before = index.stat().st_mtime_ns

        codex_home = Path(self.temp.name) / "explicit-codex-home"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text(
            """
[mcp_servers.exa]
enabled = true
command = "super-secret-command"
[mcp_servers.exa.env]
EXA_API_KEY = "super-secret-token"
[plugins."github@openai-curated"]
enabled = true
[features]
hooks = true
multi_agent = true
[agents]
max_threads = 5
max_depth = 1
""".strip()
            + "\n",
            encoding="utf-8",
        )
        result = self.run_cli(
            "inventory",
            "--root",
            str(self.root),
            "--codex-home",
            str(codex_home),
            "--match",
            "exa",
        )
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("super-secret", encoded)
        self.assertIn("exa", encoded)
        self.assertEqual(index.stat().st_mtime_ns, before)
        self.assertNotIn("/mnt/c/Users/", " ".join(result["data"]["codex_homes"]))

    def test_config_parser_returns_names_and_keys_not_values(self) -> None:
        codex_home = Path(self.temp.name) / "config-home"
        codex_home.mkdir()
        config = codex_home / "config.toml"
        config.write_text(
            """
[mcp_servers.context7]
command = "private-binary-path"
[mcp_servers.context7.env]
FIXTURE_LABEL = "private-value"
[hooks.state."x:pre_tool_use:y"]
enabled = true
[agents]
max_depth = 1
""".strip()
            + "\n",
            encoding="utf-8",
        )
        parsed = parse_safe_config(config)
        encoded = json.dumps(parsed)
        self.assertNotIn("private-", encoded)
        self.assertEqual(parsed["mcp_servers"], ["context7"])
        self.assertEqual(parsed["agent_keys"], ["max_depth"])
        self.assertEqual(parsed["hook_state_events"], ["pre_tool_use"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
