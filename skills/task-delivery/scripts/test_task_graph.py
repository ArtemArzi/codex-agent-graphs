#!/usr/bin/env python3
"""Adversarial checks for the small Task Delivery v3 control graph."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
PROJECT_START_SCRIPT_DIR = SCRIPT_DIR.parents[1] / "project-start" / "scripts"
if str(PROJECT_START_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_START_SCRIPT_DIR))

import task_graph as graph  # noqa: E402


class TaskGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.write("src/app.py", "VALUE = 1\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def initialize(
        self,
        mode: str = "full",
        profile: str = "standard",
        task_id: str = "TD-1",
        plan: str | None = None,
        implementation_strategy: str = "auto",
        slice_budget: int | None = None,
    ) -> Path:
        payload = graph.initialize(
            str(self.root),
            mode,
            task_id,
            "Deliver behavior",
            "A verified observable behavior",
            plan,
            profile,
            implementation_strategy,
            slice_budget,
        )
        return Path(payload["data"]["run"])

    def initialize_with_engineering_standard(
        self,
        *,
        implementation_strategy: str = "auto",
    ) -> tuple[Path, str]:
        standard = "docs/architecture/ENGINEERING.md"
        self.write(
            standard,
            "# Engineering\n\nUse the module public interface, update focused tests, "
            "and run the exact project quality command.\n",
        )
        self.write(
            ".project-start/state.json",
            json.dumps(
                {
                    "graph_v3": {
                        "status": "operational",
                        "canonical_docs": [standard],
                        "coverage": {"engineering_standard": standard},
                    }
                },
                indent=2,
            )
            + "\n",
        )
        with mock.patch.object(graph.legacy, "reject_pending_project_reopen"):
            run = self.initialize(
                implementation_strategy=implementation_strategy,
            )
        return run, standard

    def plan(self, task_id: str = "TD-1", path: str | None = None, scope: str = "src/app.py") -> Path:
        relative = path or f"docs/tasks/{task_id}/PLAN.md"
        state_path = next(
            (
                candidate
                for candidate in (self.root / graph.RUNS_REL).glob(f"*/{graph.STATE_NAME}")
                if self.read(candidate).get("task_id") == task_id
            ),
            None,
        )
        standard = self.read(state_path).get("engineering_standard") if state_path else None
        standard_path = standard["path"] if isinstance(standard, dict) else "N/A: no canonical Project Start engineering standard"
        return self.write(
            relative,
            f"""# Deliver behavior

Status: REVIEWED
Task ID: {task_id}

<!-- task-delivery:plan:start -->
## Outcome

Deliver one verified observable behavior.

## Research basis

- Internal repository path and current tests inspected.
- External research is not needed because the change is local and version-stable.

## Engineering standard

- Canonical guide: {standard_path}
- Applicable rules and commands: use the owned public seam and run the narrow project check.

## Acceptance

- The implementation changes the declared behavior.
- The narrow test passes.

## Implementation plan

1. Change the declared source path.
2. Run the narrow test.

## Tests

- Run the narrow deterministic check.

## Stop conditions

- Stop on an authority decision or a failed invariant.

## Scope

<!-- task-delivery:scope
{scope}
-->
<!-- task-delivery:plan:end -->

## Plan review

The plan is proportionate and executable.

## Delivery result

Recorded in the Task Delivery receipt.
""",
        )

    def agent(self, role: str, phase: str, receipt: str) -> dict:
        return {"role": role, "phase": phase, "receipt": receipt, "outcome": "pass"}

    def slice_draft(
        self,
        run: Path,
        identifier: str = "implementation-app",
        *,
        owned: list[str] | None = None,
        supersedes: str | None = None,
        repair_for_work_sha256: str | None = None,
        strategy: str = "delegated-sequential",
    ) -> Path:
        state = self.read(run / graph.STATE_NAME)
        review_mode = (
            "reused"
            if state["mode"] == "implement"
            else ("independent" if state["profile"] in {"complex", "critical"} else "self")
        )
        payload = {
            "schema_version": 2,
            "slice_id": identifier,
            "strategy": strategy,
            "plan_review": {"mode": review_mode, "receipt": "/root/plan-review-before-worker"},
            "objective": "Implement the reviewed behavior in the owned application slice.",
            "owned_paths": owned or ["src/app.py"],
            "excluded_paths": ["src/schema.py"],
            "must_read": ["src/app.py"],
            "known_facts": [{"fact": "The current value is the verified implementation baseline.", "source": "src/app.py"}],
            "stop_questions": ["Stop if the reviewed plan no longer matches the owned runtime path."],
            "acceptance": ["The owned behavior changes and the narrow deterministic check passes."],
            "test_impact": [
                {"level": "unit", "action": "not-applicable", "paths": [], "reason": "The fixture uses a command-only smoke check."},
                {"level": "integration", "action": "not-applicable", "paths": [], "reason": "No integration boundary changes in this fixture."},
                {"level": "e2e", "action": "not-applicable", "paths": [], "reason": "No user journey changes in this fixture."},
            ],
            "slice_checks": [{"command": "python3 -m unittest", "purpose": "narrow behavior"}],
            "deferred_final_checks": [
                {"command": "python3 -m unittest discover", "purpose": "integrated final behavior"}
            ],
            "capability_context": {
                "skills": [{"name": "coding-standards", "reason": "Apply the repository coding conventions.", "required": True}],
                "mcp": [{"receipt": "mcp:context7", "mode": "provided", "purpose": "Use the already verified library context."}],
            },
            "supersedes": supersedes,
            **(
                {
                    "retry_evidence": "The previous worker receipt exposed a concrete missing context gap."
                }
                if supersedes is not None
                else {}
            ),
            **(
                {"repair_for_work_sha256": repair_for_work_sha256}
                if repair_for_work_sha256 is not None
                else {}
            ),
        }
        path = run / f"{identifier}-packet-draft.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def slice_receipt(
        self,
        run: Path,
        identifier: str = "implementation-app",
        *,
        status: str = "done",
        changed: list[str] | None = None,
        include_skill: bool = True,
        concerns: list[str] | None = None,
    ) -> Path:
        state = self.read(run / graph.STATE_NAME)
        record = state["slices"][identifier]
        capabilities = [
            {
                "kind": "mcp",
                "name": "mcp:context7",
                "status": "consumed",
                "evidence": "Used the verified library context supplied by root.",
            }
        ]
        if include_skill:
            capabilities.insert(
                0,
                {
                    "kind": "skill",
                    "name": "coding-standards",
                    "status": "applied",
                    "evidence": "Applied the selected coding conventions to the owned implementation.",
                },
            )
        payload = {
            "schema_version": 2,
            "slice_id": identifier,
            "packet_sha256": record["packet_sha256"],
            "worker_receipt": f"/root/{identifier}-worker",
            "status": status,
            "summary": "Implemented the bounded slice and reported its evidence to root.",
            "changed_paths": changed if changed is not None else (["src/app.py"] if status in {"done", "done_with_concerns"} else []),
            "tests": (
                [{"command": "python3 -m unittest", "purpose": "narrow behavior", "exit_code": 0, "status": "passed"}]
                if status in {"done", "done_with_concerns"}
                else []
            ),
            "test_changes": [
                {"level": "unit", "action": "not-applicable", "paths": []},
                {"level": "integration", "action": "not-applicable", "paths": []},
                {"level": "e2e", "action": "not-applicable", "paths": []},
            ],
            "deferred_final_checks": self.read(Path(record["packet_path"]))["deferred_final_checks"],
            "artifacts": [],
            "capabilities_used": capabilities,
            "concerns": concerns or [],
            "residual_risks": [],
            "discoveries": [{"fact": "The narrow behavior is covered by the assigned command.", "source": "src/app.py"}],
            "context_request": "Need the missing interface decision from root." if status == "needs_context" else None,
            "blocker": "The owned contract cannot be changed safely." if status == "blocked" else None,
        }
        path = run / f"{identifier}-worker-draft.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def worker_agent(self, run: Path, identifier: str = "implementation-app") -> dict:
        record = self.read(run / graph.STATE_NAME)["slices"][identifier]
        return {
            "role": "task_worker",
            "phase": "implementation",
            "receipt": record["worker_receipt"],
            "outcome": record["worker_status"],
            "slice_id": identifier,
            "packet_sha256": record["packet_sha256"],
            "receipt_sha256": record["receipt_sha256"],
        }

    def acceptance_draft(
        self,
        run: Path,
        identifier: str = "implementation-app",
        *,
        concerns_resolution: list[str] | None = None,
    ) -> Path:
        state = self.read(run / graph.STATE_NAME)
        record = state["slices"][identifier]
        default_resolution = (
            ["Root verified and bounded the reported concern."]
            if record["worker_status"] == "done_with_concerns"
            else []
        )
        acceptance = {
            "schema_version": 1,
            "slice_id": identifier,
            "packet_sha256": record["packet_sha256"],
            "receipt_sha256": record["receipt_sha256"],
            "verdict": "accepted_with_concerns" if record["worker_status"] == "done_with_concerns" else "accepted",
            "verified_changed_paths": record["changed_paths"],
            "tests": [
                {"command": "python3 -m unittest", "purpose": "narrow behavior", "exit_code": 0, "status": "passed"}
            ],
            "verified_discoveries": [],
            "concerns_resolution": default_resolution if concerns_resolution is None else concerns_resolution,
            "next_objective": "Continue with the next reviewed implementation slice or final integrated checks.",
        }
        path = run / f"{identifier}-acceptance-draft.json"
        path.write_text(json.dumps(acceptance, indent=2) + "\n", encoding="utf-8")
        return path

    def accepted_slice(
        self,
        run: Path,
        identifier: str = "implementation-app",
        *,
        concerns_resolution: list[str] | None = None,
    ) -> dict:
        record = self.read(run / graph.STATE_NAME)["slices"][identifier]
        if record["status"] != "accepted":
            graph.accept_slice(
                run,
                identifier,
                self.acceptance_draft(run, identifier, concerns_resolution=concerns_resolution),
            )
            record = self.read(run / graph.STATE_NAME)["slices"][identifier]
        return {
            "slice_id": identifier,
            "packet_sha256": record["packet_sha256"],
            "receipt_sha256": record["receipt_sha256"],
            "acceptance_sha256": record["acceptance_sha256"],
        }

    def delegated_run_after_verifier_reject(self) -> tuple[Path, str]:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run)],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run)],
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        graph.record(run, "work", "verify")
        self.write_verify(run, self.verify_payload(run, "reject"))
        graph.record(run, "verify", "failed")
        state = self.read(run / graph.STATE_NAME)
        return run, state["nodes"]["work"]["receipts"][-1]["sha256"]

    def work_payload(
        self,
        run: Path,
        *,
        agents: list[dict] | None = None,
        confidence: str = "high",
        review_mode: str = "self",
        decision: dict | None = None,
        external: dict | None = None,
        changed: list[str] | None = None,
        capabilities: list[str] | None = None,
        implementation: dict | None = None,
    ) -> dict:
        state = self.read(run / graph.STATE_NAME)
        plan = self.root / state["plan_path"]
        implementation = implementation or (
            {"status": "not-run", "changed_paths": [], "strategy": "root-only", "slices": []}
            if state["mode"] == "plan"
            else {
                "status": "complete",
                "changed_paths": changed or ["src/app.py"],
                "strategy": "root-only",
                "delegation_reason": "The implementation is one tightly coupled local seam with no independent worker result.",
                "slices": [],
            }
        )
        tests = [] if state["mode"] == "plan" else [
            {"command": "python3 -m unittest", "purpose": "narrow behavior", "exit_code": 0, "status": "passed"},
            {"command": "python3 -m unittest discover", "purpose": "integrated final behavior", "exit_code": 0, "status": "passed"},
        ]
        payload = {
            "schema_version": 3,
            "task_id": state["task_id"],
            "mode": state["mode"],
            "profile": state["profile"],
            "summary": "The requested behavior is implemented and verified against the current repository.",
            "confidence": confidence,
            "capabilities": capabilities or [
                "repository search",
                "project test command",
                "mcp:not-applicable:local-only-task",
            ],
            "agents": agents or [],
            "research": {
                "internal": ["src/app.py and the nearest project instructions were inspected"],
                "external": external or {"status": "not-needed", "reason": "The task depends only on stable local behavior."},
            },
            "plan": {
                "path": state["plan_path"],
                "digest": graph.plan_digest(
                    plan, graph_version=state.get("graph_version")
                ),
                "review": {"mode": review_mode, "verdict": "pass"},
            },
            "implementation": implementation,
            "tests": tests,
            "documentation_impact": {
                "class": "none",
                "summary": "No canonical documentation truth changed in this local fixture.",
            },
            "rollback": "Restore src/app.py to the exact baseline content and rerun the narrow test.",
            "residual_risks": [],
            "decision": decision,
        }
        if isinstance(state.get("engineering_standard"), dict):
            payload["engineering_standard"] = {
                **state["engineering_standard"],
                "status": "applied",
                "exceptions": [],
            }
        return payload

    def write_work(self, run: Path, payload: dict) -> None:
        (run / graph.WORK_NAME).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def verify_payload(self, run: Path, verdict: str = "pass") -> dict:
        state = self.read(run / graph.STATE_NAME)
        work = state["nodes"]["work"]["receipts"][-1]
        return {
            "schema_version": 3,
            "task_id": state["task_id"],
            "mode": state["mode"],
            "reviewer_role": "task_plan_reviewer" if state["mode"] == "plan" else "task_result_reviewer",
            "reviewer_receipt": "/root/reviewer-verified",
            "verdict": verdict,
            "work_sha256": work["sha256"],
            "plan_digest": work["plan_digest"],
            "implementation_digest": work["implementation_digest"],
            "checked_claims": ["scope, implementation delta, tests, rollback, and residual risks"],
            "residual_risks": [],
            "repair_list": [] if verdict == "pass" else ["Repair the rejected implementation claim."],
        }

    def write_verify(self, run: Path, payload: dict) -> None:
        (run / graph.VERIFY_NAME).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def scope_amendment(
        self,
        run: Path,
        *,
        added_paths: list[str],
        plan_review_receipt: str = "/root/plan-review-before-worker",
        impacts: dict[str, bool] | None = None,
    ) -> Path:
        payload = {
            "schema_version": 1,
            "authority": "root-technical",
            "plan_review_receipt": plan_review_receipt,
            "added_paths": added_paths,
            "evidence_paths": ["src/app.py"],
            "reason": "Runtime evidence proved that this technical owner is required by the reviewed implementation path.",
            "impacts": impacts
            or {
                "outcome_changed": False,
                "acceptance_changed": False,
                "public_contract_changed": False,
                "data_or_security_changed": False,
                "external_state_changed": False,
                "risk_profile_changed": False,
            },
        }
        path = run / "scope-amendment-draft.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def test_graph_has_only_three_control_nodes(self) -> None:
        contract = graph.graph_contract()
        self.assertEqual({"plan", "implement", "full"}, set(contract["routes"]))
        for mode in graph.MODES:
            self.assertEqual({"work", "verify", "complete"}, set(contract["routes"][mode]["nodes"]))
        self.assertEqual("adaptive", contract["delegation_policy"]["default_strategy"])
        self.assertEqual(
            "root-only",
            contract["delegation_policy"]["profile_preference"]["standard"],
        )
        self.assertEqual("root-only", contract["work_policy"]["fast_path"])
        self.assertEqual("skill-only", contract["execution_policy"]["default_tier"])
        self.assertEqual(0, contract["profiles"]["standard"]["result_reviewers"])
        self.assertEqual(0, contract["profiles"]["complex"]["result_reviewers"])
        self.assertFalse(contract["delegation_policy"]["parallel_write_enabled"])
        self.assertEqual(
            "actual-normal-starts-with-conditional-repair",
            contract["delegation_policy"]["budget_accounting"],
        )
        self.assertEqual("slice-accept", contract["context_policy"]["checkpoint_after"])
        self.assertFalse(contract["context_policy"]["global_hook_required"])
        self.assertEqual("exact-union-by-check-id", contract["test_policy"]["deferred_final_checks"])
        self.assertEqual("code-first", contract["control_plane_policy"]["task_priority"])
        self.assertEqual("explicit-suspend", contract["context_policy"]["task_checkpoint_after"])

    def test_cli_exposes_slice_commands_without_new_graph_nodes(self) -> None:
        created = graph.parser().parse_args(
            ["slice-create", "--run", "/tmp/run", "--packet", "/tmp/packet.json"]
        )
        recorded = graph.parser().parse_args(
            ["slice-record", "--run", "/tmp/run", "--slice-id", "implementation-app", "--receipt", "/tmp/receipt.json"]
        )
        accepted = graph.parser().parse_args(
            ["slice-accept", "--run", "/tmp/run", "--slice-id", "implementation-app", "--acceptance", "/tmp/acceptance.json"]
        )
        rehydrated = graph.parser().parse_args(["context-rehydrate", "--run", "/tmp/run"])
        amended = graph.parser().parse_args(
            ["scope-amend", "--run", "/tmp/run", "--amendment", "/tmp/amendment.json"]
        )
        suspended = graph.parser().parse_args(["suspend", "--run", "/tmp/run", "--reason", "switch task", "--next-objective", "resume code"])
        resumed = graph.parser().parse_args(["resume", "--run", "/tmp/run"])
        degraded = graph.parser().parse_args(["control-degrade", "--run", "/tmp/run", "--reason", "receipt mismatch"])
        self.assertEqual("slice-create", created.command)
        self.assertEqual("slice-record", recorded.command)
        self.assertEqual("slice-accept", accepted.command)
        self.assertEqual("context-rehydrate", rehydrated.command)
        self.assertEqual("scope-amend", amended.command)
        self.assertEqual("suspend", suspended.command)
        self.assertEqual("resume", resumed.command)
        self.assertEqual("control-degrade", degraded.command)
        initialized = graph.parser().parse_args(
            [
                "init",
                "--root",
                "/tmp/repo",
                "--task-id",
                "TD-1",
                "--title",
                "Deliver",
                "--outcome",
                "Deliver behavior",
                "--implementation-strategy",
                "delegated-sequential",
                "--slice-budget",
                "4",
            ]
        )
        self.assertEqual("delegated-sequential", initialized.implementation_strategy)
        self.assertEqual(4, initialized.slice_budget)

    def test_explicit_slice_request_rejects_root_only_completion(self) -> None:
        run = self.initialize(implementation_strategy="delegated-sequential")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        with self.assertRaisesRegex(graph.GraphError, "запрос на реализацию слайсами"):
            graph.record(run, "work", "verify")

    def test_slice_budget_requires_explicit_delegation_and_is_bounded(self) -> None:
        with self.assertRaisesRegex(graph.GraphError, "explicit delegated-sequential"):
            self.initialize(slice_budget=3)
        with self.assertRaisesRegex(graph.GraphError, "bounded explicit slice limit"):
            self.initialize(
                implementation_strategy="delegated-sequential",
                slice_budget=7,
            )
        critical = self.initialize(
            task_id="TD-CRITICAL-SIX",
            profile="critical",
            implementation_strategy="delegated-sequential",
            slice_budget=6,
        )
        self.assertEqual(6, self.read(critical / graph.STATE_NAME)["slice_budget"])

    def test_current_digest_ignores_start_marker_line_break_but_legacy_keeps_it(self) -> None:
        plan = self.write(
            "docs/tasks/TD-DIGEST/PLAN.md",
            """# Plan

<!-- task-delivery:plan:start -->
## Outcome

Same semantic contract.

<!-- task-delivery:scope
src/app.py
-->
<!-- task-delivery:plan:end -->
""",
        )
        current_contract = graph.plan_contract_text(plan)
        legacy_contract = graph.plan_contract_text(plan, graph_version="3.5.0")
        self.assertTrue(current_contract.startswith("## Outcome"))
        self.assertTrue(legacy_contract.startswith("\n## Outcome"))
        self.assertNotEqual(
            graph.plan_digest(plan),
            graph.plan_digest(plan, graph_version="3.5.0"),
        )

    def test_explicit_slice_budget_allows_third_sequential_slice(self) -> None:
        run = self.initialize(
            implementation_strategy="delegated-sequential",
            slice_budget=3,
        )
        self.plan()
        for index in range(1, 4):
            identifier = f"implementation-app-{index}"
            graph.register_slice(run, self.slice_draft(run, identifier))
            self.write("src/app.py", f"VALUE = {index + 1}\n")
            graph.record_slice(run, identifier, self.slice_receipt(run, identifier))
            graph.accept_slice(run, identifier, self.acceptance_draft(run, identifier))
            if index < 3:
                graph.rehydrate_context(run)
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual(3, state["slice_budget"])
        self.assertEqual(3, len(state["slices"]))

    def test_adaptive_standard_uses_root_only_fast_path_without_ritual_reason(self) -> None:
        run = self.initialize()
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload["implementation"].pop("delegation_reason")
        self.write_work(run, payload)
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_ready_keeps_root_only_fast_path_for_standard_and_light(self) -> None:
        standard = self.initialize(task_id="TD-STANDARD")
        standard_ready = graph.ready(standard)
        self.assertEqual("root-only", standard_ready["data"]["implementation_strategy_preferred"])
        self.assertNotIn("slice-create", " ".join(standard_ready["next_actions"]))

        light = self.initialize(profile="light", task_id="TD-LIGHT")
        light_ready = graph.ready(light)
        self.assertEqual("root-only", light_ready["data"]["implementation_strategy_preferred"])
        self.assertNotIn("slice-create", " ".join(light_ready["next_actions"]))

    def test_init_binds_project_start_engineering_standard(self) -> None:
        run, standard = self.initialize_with_engineering_standard()
        state = self.read(run / graph.STATE_NAME)
        expected = {
            "path": standard,
            "sha256": graph.sha256_file(self.root / standard),
        }
        self.assertEqual(expected, state["engineering_standard"])
        self.assertEqual(expected, graph.ready(run)["data"]["engineering_standard"])

    def test_work_requires_exact_engineering_standard_receipt_and_plan_reference(self) -> None:
        run, standard = self.initialize_with_engineering_standard()
        plan = self.plan()
        self.assertIn(standard, plan.read_text(encoding="utf-8"))
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload.pop("engineering_standard")
        self.write_work(run, payload)
        with mock.patch.object(graph.legacy, "reject_pending_project_reopen"):
            with self.assertRaisesRegex(graph.GraphError, "engineering_standard receipt"):
                graph.record(run, "work", "verify")

    def test_slice_packet_auto_includes_engineering_standard(self) -> None:
        run, standard = self.initialize_with_engineering_standard(
            implementation_strategy="delegated-sequential"
        )
        self.plan()
        with mock.patch.object(graph.legacy, "reject_pending_project_reopen"):
            registered = graph.register_slice(run, self.slice_draft(run))
        packet = self.read(Path(registered["artifacts"][0]))
        must_read = {item["path"] for item in packet["must_read"]}
        self.assertIn(standard, must_read)
        self.assertEqual(self.read(run / graph.STATE_NAME)["engineering_standard"], packet["engineering_standard"])

    def test_engineering_standard_drift_requires_fresh_run(self) -> None:
        run, standard = self.initialize_with_engineering_standard()
        self.plan()
        self.write(standard, "# Engineering\n\nThe canonical rules changed after planning.\n")
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        with mock.patch.object(graph.legacy, "reject_pending_project_reopen"):
            with self.assertRaisesRegex(graph.GraphError, "изменился после init"):
                graph.record(run, "work", "verify")

    def test_slice_contract_is_progressively_disclosed(self) -> None:
        skill = (graph.SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        reference = (graph.SKILL_DIR / "references/implementation-slices.md").read_text(encoding="utf-8")
        worker = (graph.SKILL_DIR.parents[1] / "agents/task_worker.toml").read_text(encoding="utf-8")
        self.assertIn("work → complete", skill)
        self.assertIn("implementation-slices.md", skill)
        self.assertIn("`plan` не запускает workers", reference)
        self.assertIn("`implement` переиспользует exact review", reference)
        self.assertIn("`full` создаёт packet", reference)
        self.assertIn("context-rehydrate → slice-create", reference)
        self.assertIn("deferred_final_checks", reference)
        self.assertIn("each selected required skill's SKILL.md", worker)
        self.assertIn("не выдаётся за вычисленный остаток", skill)

    def test_plan_mode_cannot_create_implementation_slice(self) -> None:
        run = self.initialize(mode="plan", profile="standard")
        self.plan()
        with self.assertRaisesRegex(graph.GraphError, "plan не запускает"):
            graph.register_slice(run, self.slice_draft(run))

    def test_full_mode_records_skill_bound_slice_and_root_acceptance(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run)],
        }
        payload = self.work_payload(
            run,
            agents=[self.worker_agent(run)],
            capabilities=["repository search", "project test command", "mcp:context7"],
            implementation=implementation,
        )
        self.write_work(run, payload)
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])
        work = self.read(run / graph.STATE_NAME)["nodes"]["work"]["receipts"][-1]
        self.assertEqual("delegated-sequential", work["implementation_strategy"])
        self.assertEqual("implementation-app", work["accepted_slices"][0]["slice_id"])

    def test_complex_full_slice_binds_independent_plan_review_before_worker(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        plan_reviewer = self.agent("task_plan_reviewer", "plan-review", "/root/plan-review-before-worker")
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run)],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[plan_reviewer, self.worker_agent(run)],
                review_mode="independent",
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_complex_full_slice_allows_self_review_before_worker(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        draft = self.slice_draft(run)
        payload = self.read(draft)
        payload["plan_review"] = {"mode": "self", "receipt": "root:self-review"}
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        created = graph.register_slice(run, draft)
        self.assertEqual("ready", created["status"])

    def test_implement_mode_can_delegate_after_exact_plan_reuse(self) -> None:
        plan_run = self.initialize(mode="plan", profile="standard")
        self.plan()
        self.write_work(plan_run, self.work_payload(plan_run))
        graph.record(plan_run, "work", "succeeded")
        graph.complete(plan_run)
        run = self.initialize(mode="implement", profile="standard", plan="docs/tasks/TD-1/PLAN.md")
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run)],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run)],
                review_mode="reused",
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_required_slice_skill_must_be_reported_as_applied(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        with self.assertRaisesRegex(graph.GraphError, "selected skill|обязательный skill"):
            graph.record_slice(run, "implementation-app", self.slice_receipt(run, include_skill=False))

    def test_worker_change_outside_slice_ownership_is_rejected(self) -> None:
        run = self.initialize(profile="standard")
        self.plan(scope="src")
        graph.register_slice(run, self.slice_draft(run, owned=["src/app.py"]))
        self.write("src/app.py", "VALUE = 2\n")
        self.write("src/other.py", "OUTSIDE = True\n")
        receipt = self.slice_receipt(run, changed=["src/app.py", "src/other.py"])
        with self.assertRaisesRegex(graph.GraphError, "вне slice ownership"):
            graph.record_slice(run, "implementation-app", receipt)

    def test_slice_packet_tampering_is_rejected(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        created = graph.register_slice(run, self.slice_draft(run))
        packet = Path(created["data"]["packet"])
        packet.write_text(packet.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.write("src/app.py", "VALUE = 2\n")
        with self.assertRaisesRegex(graph.GraphError, "packet изменился"):
            graph.record_slice(run, "implementation-app", self.slice_receipt(run))

    def test_slice_create_rolls_back_artifacts_when_state_save_fails(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        with mock.patch.object(graph, "save_run", side_effect=OSError("injected save failure")):
            with self.assertRaisesRegex(OSError, "injected save failure"):
                graph.register_slice(run, self.slice_draft(run))
        self.assertFalse((run / graph.SLICES_DIR / "implementation-app").exists())
        self.assertNotIn("implementation-app", self.read(run / graph.STATE_NAME)["slices"])

    def test_slice_accept_rolls_back_artifacts_when_state_save_fails(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        with mock.patch.object(graph, "save_run", side_effect=OSError("injected save failure")):
            with self.assertRaisesRegex(OSError, "injected save failure"):
                graph.accept_slice(run, "implementation-app", self.acceptance_draft(run))
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual("recorded", state["slices"]["implementation-app"]["status"])
        self.assertFalse((run / graph.SLICES_DIR / "implementation-app" / graph.SLICE_ACCEPTANCE_NAME).exists())
        self.assertFalse((run / graph.CONTEXT_CHECKPOINT_NAME).exists())

    def test_plan_drift_after_slice_issue_requires_new_packet(self) -> None:
        run = self.initialize(profile="standard")
        plan = self.plan()
        graph.register_slice(run, self.slice_draft(run))
        plan.write_text(plan.read_text(encoding="utf-8").replace("narrow test passes", "narrow test and lint pass"), encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "План изменился"):
            graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))

    def test_needs_context_can_be_superseded_by_one_bounded_slice(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        graph.register_slice(
            run,
            self.slice_draft(run, "implementation-app-v2", supersedes="implementation-app"),
        )
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app-v2", self.slice_receipt(run, "implementation-app-v2"))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run, "implementation-app-v2")],
        }
        agents = [self.worker_agent(run), self.worker_agent(run, "implementation-app-v2")]
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=agents,
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_second_unsuccessful_normal_slice_blocks_run_explicitly(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        graph.register_slice(
            run,
            self.slice_draft(run, "implementation-app-v2", supersedes="implementation-app"),
        )
        blocked = graph.record_slice(
            run,
            "implementation-app-v2",
            self.slice_receipt(run, "implementation-app-v2", status="needs_context"),
        )
        self.assertEqual("blocked", blocked["status"])
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual("blocked", state["status"])
        self.assertEqual("failed", state["nodes"]["work"]["status"])

    def test_unresolved_slice_rejects_unrelated_successor_before_worker_spawn(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        with self.assertRaisesRegex(graph.GraphError, "supersedes exact unresolved slice"):
            graph.register_slice(run, self.slice_draft(run, "implementation-other"))
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual(["implementation-app"], sorted(state["slices"]))

    def test_same_scope_successor_requires_new_evidence(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(
            run,
            "implementation-app",
            self.slice_receipt(run, status="needs_context"),
        )
        draft = self.slice_draft(
            run,
            "implementation-app-v2",
            supersedes="implementation-app",
        )
        payload = self.read(draft)
        payload.pop("retry_evidence")
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "retry_evidence"):
            graph.register_slice(run, draft)

    def test_ready_routes_unresolved_slice_to_exact_successor(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        ready = graph.ready(run)
        self.assertIn("supersedes=implementation-app", ready["next_actions"][0])
        self.assertFalse(any("task.json" in action for action in ready["next_actions"]))

    def test_successful_slice_requires_root_acceptance_before_next_packet(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src")
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        with self.assertRaisesRegex(graph.GraphError, "slice-accept"):
            graph.register_slice(
                run,
                self.slice_draft(run, "implementation-other", owned=["src/other.py"]),
            )

    def test_ready_routes_successful_slice_to_acceptance(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        ready = graph.ready(run)
        self.assertIn("slice-accept", ready["next_actions"][0])
        self.assertIn("implementation-app", ready["next_actions"][0])
        self.assertFalse(any("task.json" in action for action in ready["next_actions"]))

    def test_final_work_rejects_successful_slice_without_root_acceptance(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run)],
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        with self.assertRaisesRegex(graph.GraphError, "root acceptance"):
            graph.record(run, "work", "verify")

    def test_final_work_rejects_paths_outside_root_acceptance_union(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src")
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        accepted = self.accepted_slice(run)
        self.write("src/other.py", "OTHER = 2\n")
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py", "src/other.py"],
            "strategy": "delegated-sequential",
            "slices": [accepted],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run)],
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        with self.assertRaisesRegex(graph.GraphError, "accepted slice provenance"):
            graph.record(run, "work", "verify")

    def test_done_with_concerns_requires_root_resolution(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(
            run,
            "implementation-app",
            self.slice_receipt(run, status="done_with_concerns", concerns=["The neighboring adapter was not exercised."]),
        )
        with self.assertRaisesRegex(graph.GraphError, "concerns_resolution"):
            self.accepted_slice(run, concerns_resolution=[])

    def test_parallel_write_slice_is_fail_closed(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        with self.assertRaisesRegex(graph.GraphError, "worktree isolation"):
            graph.register_slice(run, self.slice_draft(run, strategy="delegated-parallel"))

    def test_second_slice_requires_exact_checkpoint_rehydrate(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src")
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        first = self.accepted_slice(run)
        first_checkpoint = self.read(run / graph.STATE_NAME)["context"]["latest_checkpoint_sha256"]

        with self.assertRaisesRegex(graph.GraphError, "context-rehydrate"):
            graph.register_slice(
                run,
                self.slice_draft(run, "implementation-other", owned=["src/other.py"]),
            )

        rehydrated = graph.rehydrate_context(run)
        self.assertEqual(first_checkpoint, rehydrated["data"]["checkpoint_sha256"])
        created = graph.register_slice(
            run,
            self.slice_draft(run, "implementation-other", owned=["src/other.py"]),
        )
        packet = self.read(Path(created["data"]["packet"]))
        self.assertEqual(first_checkpoint, packet["context_checkpoint"]["sha256"])
        self.write("src/other.py", "OTHER = 2\n")
        graph.record_slice(
            run,
            "implementation-other",
            self.slice_receipt(run, "implementation-other", changed=["src/other.py"]),
        )
        second = self.accepted_slice(run, "implementation-other")
        state = self.read(run / graph.STATE_NAME)
        checkpoint = self.read(Path(state["context"]["latest_checkpoint_path"]))
        self.assertEqual(["src"], checkpoint["plan_scope"])
        self.assertNotIn("remaining_scope", checkpoint)
        self.assertEqual(["src/app.py", "src/other.py"], checkpoint["accepted_changed_paths"])
        self.assertEqual(
            {"implementation-app", "implementation-other"},
            {item["slice_id"] for item in checkpoint["accepted_slices"]},
        )
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py", "src/other.py"],
            "strategy": "delegated-sequential",
            "slices": [first, second],
        }
        agents = [self.worker_agent(run), self.worker_agent(run, "implementation-other")]
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=agents,
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_context_checkpoint_tampering_blocks_rehydrate(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        self.accepted_slice(run)
        checkpoint = run / graph.CONTEXT_CHECKPOINT_NAME
        checkpoint.write_text(checkpoint.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "checkpoint отсутствует или изменился"):
            graph.rehydrate_context(run)

    def test_repository_drift_after_acceptance_blocks_rehydrate_and_next_slice(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src")
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        self.accepted_slice(run)
        self.write("src/app.py", "VALUE = 3\n")
        with self.assertRaisesRegex(graph.GraphError, "Repository изменился"):
            graph.rehydrate_context(run)
        with self.assertRaisesRegex(graph.GraphError, "Repository изменился"):
            graph.register_slice(
                run,
                self.slice_draft(run, "implementation-other", owned=["src/other.py"]),
            )

    def test_final_work_requires_deferred_check_union(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run)],
        }
        payload = self.work_payload(
            run,
            agents=[self.worker_agent(run)],
            capabilities=["repository search", "project test command", "mcp:context7"],
            implementation=implementation,
        )
        payload["tests"] = [payload["tests"][0]]
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "deferred_final_checks"):
            graph.record(run, "work", "verify")

    def test_update_test_impact_requires_actual_test_change(self) -> None:
        self.write("tests/test_app.py", "def test_app():\n    assert True\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src/app.py\ntests/test_app.py")
        draft = self.slice_draft(run, owned=["src/app.py", "tests/test_app.py"])
        payload = self.read(draft)
        payload["test_impact"][0] = {
            "level": "unit",
            "action": "update",
            "paths": ["tests/test_app.py"],
            "reason": "The changed unit behavior requires updating its focused test.",
        }
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        graph.register_slice(run, draft)
        self.write("src/app.py", "VALUE = 2\n")
        receipt = self.slice_receipt(run)
        receipt_payload = self.read(receipt)
        receipt_payload["test_changes"][0] = {
            "level": "unit",
            "action": "update",
            "paths": ["tests/test_app.py"],
        }
        receipt.write_text(json.dumps(receipt_payload, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "обязан изменить"):
            graph.record_slice(run, "implementation-app", receipt)

    def test_needs_context_may_stop_before_planned_test_update(self) -> None:
        self.write("tests/test_app.py", "def test_app():\n    assert True\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src/app.py\ntests/test_app.py")
        draft = self.slice_draft(run, owned=["src/app.py", "tests/test_app.py"])
        payload = self.read(draft)
        payload["test_impact"][0] = {
            "level": "unit",
            "action": "update",
            "paths": ["tests/test_app.py"],
            "reason": "The planned unit behavior will require a focused test update.",
        }
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        graph.register_slice(run, draft)
        receipt = self.slice_receipt(run, status="needs_context")
        receipt_payload = self.read(receipt)
        receipt_payload["test_changes"][0] = {
            "level": "unit",
            "action": "update",
            "paths": ["tests/test_app.py"],
        }
        receipt.write_text(json.dumps(receipt_payload, indent=2) + "\n", encoding="utf-8")
        recorded = graph.record_slice(run, "implementation-app", receipt)
        self.assertEqual("needs_context", recorded["data"]["status"])

    def test_needs_context_cannot_leave_unaccepted_delta(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        receipt = self.slice_receipt(run, status="needs_context", changed=["src/app.py"])
        with self.assertRaisesRegex(graph.GraphError, "непринятую дельту"):
            graph.record_slice(run, "implementation-app", receipt)

    def test_applicable_e2e_requires_deferred_final_check(self) -> None:
        self.write("tests/e2e/test_flow.py", "def test_flow():\n    assert True\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src/app.py\ntests/e2e/test_flow.py")
        draft = self.slice_draft(run, owned=["src/app.py", "tests/e2e/test_flow.py"])
        payload = self.read(draft)
        payload["test_impact"][2] = {
            "level": "e2e",
            "action": "reuse",
            "paths": ["tests/e2e/test_flow.py"],
            "reason": "The existing E2E flow covers the changed behavior.",
        }
        payload["deferred_final_checks"] = []
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "E2E impact"):
            graph.register_slice(run, draft)

    def test_reuse_test_path_must_remain_unchanged(self) -> None:
        self.write("tests/test_app.py", "def test_app():\n    assert True\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src/app.py\ntests/test_app.py")
        draft = self.slice_draft(run, owned=["src/app.py", "tests/test_app.py"])
        payload = self.read(draft)
        payload["test_impact"][0] = {
            "level": "unit",
            "action": "reuse",
            "paths": ["tests/test_app.py"],
            "reason": "The existing test is expected to remain unchanged.",
        }
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        graph.register_slice(run, draft)
        self.write("src/app.py", "VALUE = 2\n")
        self.write("tests/test_app.py", "def test_app():\n    assert 2 == 2\n")
        receipt = self.slice_receipt(run, changed=["src/app.py", "tests/test_app.py"])
        receipt_payload = self.read(receipt)
        receipt_payload["test_changes"][0] = {
            "level": "unit",
            "action": "reuse",
            "paths": ["tests/test_app.py"],
        }
        receipt.write_text(json.dumps(receipt_payload, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "объявленный reuse"):
            graph.record_slice(run, "implementation-app", receipt)

    def test_safe_scope_amendment_is_root_owned_and_digest_chained(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        amended = graph.amend_scope(
            run,
            self.scope_amendment(run, added_paths=["src/other.py"]),
        )
        self.assertEqual("amended", amended["status"])
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual(1, len(state["scope_amendments"]))
        chain = graph.validate_amendment_chain(state, run)
        self.assertEqual(amended["data"]["after_digest"], chain["effective_digest"])
        self.assertIn("src/other.py", graph.validate_plan(self.root / state["plan_path"])[1])

    def test_light_full_root_only_can_record_safe_technical_scope_amendment(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="light", implementation_strategy="root-only")
        self.plan()
        amended = graph.amend_scope(
            run,
            self.scope_amendment(
                run,
                added_paths=["src/other.py"],
                plan_review_receipt="root:self-review",
            ),
        )
        self.assertEqual("amended", amended["status"])
        self.assertIn("src/other.py", graph.validate_plan(self.root / self.read(run / graph.STATE_NAME)["plan_path"])[1])

    def test_scope_amendment_rejects_semantic_or_protected_expansion(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        impacts = {
            "outcome_changed": True,
            "acceptance_changed": False,
            "public_contract_changed": False,
            "data_or_security_changed": False,
            "external_state_changed": False,
            "risk_profile_changed": False,
        }
        with self.assertRaisesRegex(graph.GraphError, "user decision"):
            graph.amend_scope(
                run,
                self.scope_amendment(run, added_paths=["src/other.py"], impacts=impacts),
            )
        with self.assertRaisesRegex(graph.GraphError, "Protected path"):
            graph.amend_scope(
                run,
                self.scope_amendment(run, added_paths=["apps/core/migrations/0001.py"]),
            )
        with self.assertRaisesRegex(graph.GraphError, "exact file paths|parent tree"):
            graph.amend_scope(run, self.scope_amendment(run, added_paths=["src"]))
        for ci_path in (
            ".GITLAB-CI.YML",
            ".travis.yml",
            ".drone.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
            "db/migrate/001_add_users.rb",
            "alembic/versions/001_add_users.py",
            "prisma/schema.prisma",
            "db/schema.rb",
            "db/structure.sql",
            "schema.sql",
        ):
            with self.assertRaisesRegex(graph.GraphError, "Protected path"):
                graph.amend_scope(run, self.scope_amendment(run, added_paths=[ci_path]))

    def test_root_only_amendment_review_binding_survives_delegated_switch(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="complex", implementation_strategy="auto")
        self.plan()
        graph.amend_scope(
            run,
            self.scope_amendment(
                run,
                added_paths=["src/other.py"],
                plan_review_receipt="/root/original-independent-plan-review",
            ),
        )
        with self.assertRaisesRegex(graph.GraphError, "exact review receipt"):
            graph.register_slice(
                run,
                self.slice_draft(run, owned=["src/other.py"]),
            )
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual("root-only", state["implementation_strategy"])
        self.assertEqual({}, state["slices"])

    def test_implement_reuses_reviewed_base_through_safe_amendment_chain(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        plan_run = self.initialize(mode="plan", profile="standard")
        self.plan()
        self.write_work(plan_run, self.work_payload(plan_run))
        graph.record(plan_run, "work", "succeeded")
        graph.complete(plan_run)
        run = self.initialize(mode="implement", profile="standard", plan="docs/tasks/TD-1/PLAN.md")
        amended = graph.amend_scope(
            run,
            self.scope_amendment(
                run,
                added_paths=["src/other.py"],
                plan_review_receipt="task-state:plan-review",
            ),
        )
        self.assertEqual("amended", amended["status"])
        created = graph.register_slice(
            run,
            self.slice_draft(run, owned=["src/other.py"]),
        )
        packet = self.read(Path(created["data"]["packet"]))
        self.assertEqual("reused", packet["plan_review"]["mode"])
        state = self.read(run / graph.STATE_NAME)
        chain = graph.validate_amendment_chain(state, run)
        task = self.read(self.root / ".codex/task-delivery/TD-1/state.json")
        self.assertEqual(task["checkpoints"]["plan-review"]["plan_digest"], chain["base_digest"])

    def test_scope_amendment_receipt_tampering_is_rejected(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        graph.record_slice(run, "implementation-app", self.slice_receipt(run, status="needs_context"))
        graph.amend_scope(run, self.scope_amendment(run, added_paths=["src/other.py"]))
        state = self.read(run / graph.STATE_NAME)
        receipt = Path(state["scope_amendments"][0]["path"])
        receipt.write_text(receipt.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "изменился после record"):
            graph.validate_amendment_chain(state, run)

    def test_amendment_tampering_blocks_checkpoint_rehydrate(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        self.accepted_slice(run)
        graph.amend_scope(run, self.scope_amendment(run, added_paths=["src/other.py"]))
        state = self.read(run / graph.STATE_NAME)
        receipt = Path(state["scope_amendments"][0]["path"])
        receipt.write_text(receipt.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "изменился после record"):
            graph.rehydrate_context(run)

    def test_model_guidance_never_requests_user_hash_echo(self) -> None:
        research = (graph.SKILL_DIR.parents[1] / "docs/research/task-delivery-context-checkpoint-research.md").read_text(encoding="utf-8")
        reference = (graph.SKILL_DIR / "references/implementation-slices.md").read_text(encoding="utf-8")
        self.assertNotIn("exact user hash is useful", research)
        self.assertIn("must never ask the\nuser to echo an amendment hash", research)
        self.assertIn("Никакого «разреши случайный hash»", reference)

    def test_started_v3_3_slice_keeps_exact_legacy_contract(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        state = self.read(run / graph.STATE_NAME)
        state["graph_version"] = "3.3.0"
        state["graph_sha256"] = "07b19482bca36d54ace9a3cc470e76e421b2b1c14f0ee123c90a7792af79b7e8"
        state.pop("context")
        state.pop("scope_amendments")
        (run / graph.STATE_NAME).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        draft = self.slice_draft(run)
        draft_payload = self.read(draft)
        draft_payload["schema_version"] = 1
        draft_payload["verification_commands"] = draft_payload.pop("slice_checks")
        draft_payload.pop("test_impact")
        draft_payload.pop("deferred_final_checks")
        draft.write_text(json.dumps(draft_payload, indent=2) + "\n", encoding="utf-8")
        created = graph.register_slice(run, draft)
        packet_path = Path(created["data"]["packet"])
        packet = self.read(packet_path)
        self.assertNotIn("check_id", packet["verification_commands"][0])
        self.write("src/app.py", "VALUE = 2\n")
        record = self.read(run / graph.STATE_NAME)["slices"]["implementation-app"]
        receipt = {
            "schema_version": 1,
            "slice_id": "implementation-app",
            "packet_sha256": record["packet_sha256"],
            "worker_receipt": "/root/legacy-v33-worker",
            "status": "done",
            "summary": "The legacy slice completed with its exact historical receipt contract.",
            "changed_paths": ["src/app.py"],
            "tests": [{"command": "python3 -m unittest", "purpose": "narrow behavior", "status": "passed", "exit_code": 0}],
            "artifacts": [],
            "capabilities_used": [
                {"kind": "skill", "name": "coding-standards", "status": "applied", "evidence": "Applied legacy selected skill."},
                {"kind": "mcp", "name": "mcp:context7", "status": "consumed", "evidence": "Consumed legacy MCP context."},
            ],
            "concerns": [],
            "residual_risks": [],
            "discoveries": [],
            "context_request": None,
            "blocker": None,
        }
        receipt_path = run / "legacy-worker.json"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        graph.record_slice(run, "implementation-app", receipt_path)
        legacy_ready = graph.ready(run)
        self.assertTrue(any("task.json" in action for action in legacy_ready["next_actions"]))
        self.assertFalse(any("slice-accept" in action for action in legacy_ready["next_actions"]))
        self.assertFalse(any("context-rehydrate" in action for action in legacy_ready["next_actions"]))
        record = self.read(run / graph.STATE_NAME)["slices"]["implementation-app"]
        canonical_receipt = self.read(Path(record["receipt_path"]))
        self.assertNotIn("check_id", canonical_receipt["tests"][0])
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [
                {
                    "slice_id": "implementation-app",
                    "packet_sha256": record["packet_sha256"],
                    "receipt_sha256": record["receipt_sha256"],
                    "root_acceptance": {
                        "verdict": "accepted",
                        "verified_changed_paths": ["src/app.py"],
                        "tests": [{"command": "python3 -m unittest", "purpose": "root replay", "status": "passed", "exit_code": 0}],
                        "concerns_resolution": [],
                    },
                }
            ],
        }
        payload = self.work_payload(
            run,
            agents=[self.worker_agent(run)],
            capabilities=["repository search", "project test command", "mcp:context7"],
            implementation=implementation,
        )
        payload["tests"][0]["check_id"] = "legacy-extra-field-is-ignored"
        payload["tests"].append(dict(payload["tests"][0]))
        self.write_work(run, payload)
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])
        self.write_verify(run, self.verify_payload(run, "reject"))
        rejected = graph.record(run, "verify", "failed")
        self.assertIsNone(rejected["data"]["verification_repair_work_sha256"])
        self.assertNotIn("repair_for_work_sha256", " ".join(rejected["next_actions"]))
        self.assertIsNone(graph.status(run)["data"]["verification_repair_work_sha256"])

    def test_ready_exposes_conditional_mcp_policy(self) -> None:
        run = self.initialize(profile="light")
        ready = graph.ready(run)
        self.assertEqual("when-relevant", ready["data"]["mcp_policy"]["discovery"])

    def test_work_requires_an_mcp_receipt(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(
            run, capabilities=["repository search", "project test command"]
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "MCP receipt"):
            graph.record(run, "work", "succeeded")

    def test_light_full_completes_without_subagent(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        ready = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", ready["data"]["current"])
        completed = graph.complete(run)
        self.assertEqual("completed", completed["status"])
        self.assertEqual("completed", completed["data"]["task_status"])
        run_state = self.read(run / graph.STATE_NAME)
        self.assertEqual("completed", run_state["task_status"])
        task = self.read(self.root / ".codex/task-delivery/TD-1/state.json")
        self.assertEqual("completed", task["phase"])
        handoff = self.root / ".agent-graphs/task-delivery-handoffs/TD-1/HANDOFF.md"
        receipt = graph.legacy.load_project_start_runtime  # prove legacy module remains importable
        self.assertTrue(handoff.is_file())
        self.assertTrue(callable(receipt))

    def test_no_documentation_impact_skips_project_start_maintenance(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "succeeded")
        with mock.patch.object(
            graph.legacy, "mark_project_start_maintenance_required"
        ) as maintenance:
            completed = graph.complete(run)
        maintenance.assert_not_called()
        self.assertFalse(completed["data"]["documentation_maintenance_required"])
        self.assertFalse(
            (
                self.root
                / ".codex/task-delivery/TD-1/project-start-obligation.pending.json"
            ).exists()
        )

    def test_standard_full_completes_without_ritual_result_verifier(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        handoff = self.root / ".agent-graphs/task-delivery-handoffs/TD-1/HANDOFF.md"
        receipt = {"path": handoff.relative_to(self.root).as_posix(), "sha256": graph.sha256_file(handoff)}
        validated = __import__("project_maintenance").validate_task_delivery_receipt(self.root, receipt)
        self.assertEqual("TD-1", validated["task_id"])
        task = self.read(self.root / ".codex/task-delivery/TD-1/state.json")
        graph.legacy._MANIFEST_CACHE.clear()
        self.assertEqual(validated["implementation_sha256"], graph.legacy.implementation_repo_state(self.root, task)[1])

    def test_standard_root_can_escalate_to_independent_verify(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])
        self.write_verify(run, self.verify_payload(run))
        graph.record(run, "verify", "succeeded")

    def test_plan_mode_stops_then_implement_reuses_exact_reviewed_plan(self) -> None:
        plan_run = self.initialize(mode="plan", profile="complex")
        self.plan()
        self.write_work(plan_run, self.work_payload(
            plan_run,
            agents=[],
            review_mode="self",
        ))
        graph.record(plan_run, "work", "verify")
        self.write_verify(plan_run, self.verify_payload(plan_run))
        graph.record(plan_run, "verify", "succeeded")
        result = graph.complete(plan_run)
        self.assertEqual("awaiting_implementation", result["data"]["phase"])
        self.assertEqual("awaiting_implementation", result["data"]["task_status"])
        plan_state = self.read(plan_run / graph.STATE_NAME)
        self.assertEqual("awaiting_implementation", plan_state["task_status"])

        implement_run = self.initialize(mode="implement", profile="complex", plan="docs/tasks/TD-1/PLAN.md")
        self.write("src/app.py", "VALUE = 3\n")
        payload = self.work_payload(implement_run, review_mode="reused")
        self.write_work(implement_run, payload)
        graph.record(implement_run, "work", "verify")

    def test_complex_implement_can_reuse_light_self_review(self) -> None:
        run = self.initialize(mode="plan", profile="light")
        self.plan()
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        implement = self.initialize(mode="implement", profile="complex", plan="docs/tasks/TD-1/PLAN.md")
        self.write("src/app.py", "VALUE = 3\n")
        self.write_work(implement, self.work_payload(implement, review_mode="reused"))
        ready = graph.record(implement, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_implement_rejects_scope_drift_after_plan_review(self) -> None:
        run = self.initialize(mode="plan", profile="light")
        self.plan()
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        self.write("src/app.py", "DRIFT = True\n")
        with self.assertRaisesRegex(graph.GraphError, "Область реализации изменилась"):
            self.initialize(mode="implement", profile="light", plan="docs/tasks/TD-1/PLAN.md")

    def test_complex_full_defaults_to_self_review(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run, review_mode="self"))
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_critical_full_requires_risk_reviewer(self) -> None:
        run = self.initialize(profile="critical")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        agents = [self.agent("task_plan_reviewer", "plan-review", "/root/plan-reviewer")]
        self.write_work(run, self.work_payload(run, agents=agents, review_mode="independent"))
        with self.assertRaisesRegex(graph.GraphError, "task_risk_reviewer"):
            graph.record(run, "work", "verify")

    def test_out_of_scope_change_is_rejected(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write("other.py", "OUTSIDE = True\n")
        self.write_work(run, self.work_payload(run, changed=["other.py", "src/app.py"]))
        with self.assertRaisesRegex(graph.GraphError, "вышли за область"):
            graph.record(run, "work", "succeeded")

    def test_sibling_of_plan_is_not_hidden_from_scope(self) -> None:
        plan_path = "docs/plans/TD-1.md"
        run = self.initialize(profile="light", plan=plan_path)
        self.plan(path=plan_path)
        self.write("src/app.py", "VALUE = 2\n")
        self.write("docs/plans/neighbor.md", "Hidden sibling mutation\n")
        self.write_work(run, self.work_payload(run, changed=["docs/plans/neighbor.md", "src/app.py"]))
        with self.assertRaisesRegex(graph.GraphError, "вышли за область"):
            graph.record(run, "work", "succeeded")

    def test_root_plan_file_itself_is_excluded_but_not_the_repository(self) -> None:
        run = self.initialize(profile="light", plan="PLAN.md")
        self.plan(path="PLAN.md")
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        ready = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", ready["data"]["current"])

    def test_python_bytecode_is_not_implementation_delta(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write("src/__pycache__/app.cpython-312.pyc", "generated")
        self.write("tests/__pycache__/test_app.cpython-312.pyc", "generated")
        self.write_work(run, self.work_payload(run))
        ready = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", ready["data"]["current"])

    def test_complete_recovers_without_changing_task_receipt_after_interruption(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload["documentation_impact"] = {
            "class": "factual",
            "summary": "Canonical project documentation must record the delivered behavior.",
        }
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        with mock.patch.object(graph.legacy, "mark_project_start_maintenance_required", side_effect=graph.legacy.TaskError("injected crash")):
            with self.assertRaisesRegex(graph.GraphError, "injected crash"):
                graph.complete(run)
        task_path = self.root / ".codex/task-delivery/TD-1/state.json"
        before = graph.sha256_file(task_path)
        self.assertTrue((self.root / ".codex/task-delivery/TD-1/project-start-obligation.pending.json").is_file())
        recovered = graph.complete(run)
        self.assertEqual("completed", recovered["status"])
        self.assertEqual(before, graph.sha256_file(task_path))
        self.assertFalse((self.root / ".codex/task-delivery/TD-1/project-start-obligation.pending.json").exists())

    def test_interrupted_complete_rejects_post_receipt_implementation_drift(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload["documentation_impact"] = {
            "class": "factual",
            "summary": "Canonical project documentation must record the delivered behavior.",
        }
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        with mock.patch.object(graph.legacy, "mark_project_start_maintenance_required", side_effect=graph.legacy.TaskError("injected crash")):
            with self.assertRaises(graph.GraphError):
                graph.complete(run)
        self.write("src/app.py", "DRIFT = 99\n")
        with self.assertRaisesRegex(graph.GraphError, "изменил|дрейф"):
            graph.complete(run)

    def test_interrupted_complete_rejects_handoff_tampering(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload["documentation_impact"] = {
            "class": "factual",
            "summary": "Canonical project documentation must record the delivered behavior.",
        }
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        with mock.patch.object(graph.legacy, "mark_project_start_maintenance_required", side_effect=graph.legacy.TaskError("injected crash")):
            with self.assertRaises(graph.GraphError):
                graph.complete(run)
        handoff = self.root / ".agent-graphs/task-delivery-handoffs/TD-1/HANDOFF.md"
        handoff.write_text(handoff.read_text(encoding="utf-8") + "\nTAMPERED\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "handoff"):
            graph.complete(run)

    def test_plan_mode_rejects_production_delta(self) -> None:
        run = self.initialize(mode="plan", profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        with self.assertRaisesRegex(graph.GraphError, "Plan mode"):
            graph.record(run, "work", "succeeded")

    def test_external_research_requires_receipt(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run, external={"status": "used"})
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "research.*receipt"):
            graph.record(run, "work", "succeeded")

    def test_low_confidence_escalates_light_to_verifier(self) -> None:
        run = self.initialize(profile="light")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run, confidence="low"))
        with self.assertRaisesRegex(graph.GraphError, "требует независимый verify"):
            graph.record(run, "work", "succeeded")
        graph.record(run, "work", "verify")

    def test_one_verifier_repair_then_block(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "verify")
        self.write_verify(run, self.verify_payload(run, "reject"))
        graph.record(run, "verify", "failed")
        root_ready = graph.ready(run)
        self.assertIsNone(root_ready["data"]["verification_repair_work_sha256"])
        self.assertIn("root-owned candidate", " ".join(root_ready["next_actions"]))
        self.assertNotIn("slice-create", " ".join(root_ready["next_actions"]))
        rejected_work_sha = self.read(run / graph.STATE_NAME)["nodes"]["work"]["receipts"][-1]["sha256"]
        with self.assertRaisesRegex(graph.GraphError, "только для уже delegated candidate"):
            graph.register_slice(
                run,
                self.slice_draft(
                    run,
                    "invalid-root-repair-slice",
                    repair_for_work_sha256=rejected_work_sha,
                ),
            )
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "verify")
        self.write_verify(run, self.verify_payload(run, "reject"))
        blocked = graph.record(run, "verify", "failed")
        self.assertEqual("blocked", blocked["status"])
        with self.assertRaisesRegex(graph.GraphError, "терминален"):
            graph.retry(run, "verify")

    def test_delegated_verifier_repair_is_exact_bounded_and_reverified(self) -> None:
        run, rejected_work_sha = self.delegated_run_after_verifier_reject()
        repair_ready = graph.ready(run)
        self.assertEqual(rejected_work_sha, repair_ready["data"]["verification_repair_work_sha256"])
        self.assertIn("repair_for_work_sha256", " ".join(repair_ready["next_actions"]))
        graph.rehydrate_context(run)
        with self.assertRaisesRegex(graph.GraphError, "exact repair_for_work_sha256"):
            graph.register_slice(
                run,
                self.slice_draft(
                    run,
                    "verifier-repair-wrong",
                    repair_for_work_sha256="a" * 64,
                ),
            )
        graph.register_slice(
            run,
            self.slice_draft(
                run,
                "verifier-repair",
                repair_for_work_sha256=rejected_work_sha,
            ),
        )
        self.write("src/app.py", "VALUE = 3\n")
        graph.record_slice(run, "verifier-repair", self.slice_receipt(run, "verifier-repair"))
        self.accepted_slice(run, "verifier-repair")
        graph.rehydrate_context(run)
        with self.assertRaisesRegex(graph.GraphError, "лимит verifier repair"):
            graph.register_slice(
                run,
                self.slice_draft(
                    run,
                    "verifier-repair-second",
                    repair_for_work_sha256=rejected_work_sha,
                ),
            )
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [
                self.accepted_slice(run, "implementation-app"),
                self.accepted_slice(run, "verifier-repair"),
            ],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run), self.worker_agent(run, "verifier-repair")],
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])
        self.write_verify(run, self.verify_payload(run, "pass"))
        completed = graph.record(run, "verify", "succeeded")
        self.assertEqual("complete", completed["data"]["current"])

    def test_unsuccessful_verifier_repair_slice_blocks_run(self) -> None:
        run, rejected_work_sha = self.delegated_run_after_verifier_reject()
        graph.rehydrate_context(run)
        graph.register_slice(
            run,
            self.slice_draft(
                run,
                "verifier-repair",
                repair_for_work_sha256=rejected_work_sha,
            ),
        )
        blocked = graph.record_slice(
            run,
            "verifier-repair",
            self.slice_receipt(run, "verifier-repair", status="needs_context"),
        )
        self.assertEqual("blocked", blocked["status"])
        self.assertEqual("blocked", self.read(run / graph.STATE_NAME)["status"])

    def test_started_v3_0_run_can_finish_without_new_mcp_receipt(self) -> None:
        run = self.initialize(profile="light")
        state_path = run / graph.STATE_NAME
        state = self.read(state_path)
        state["graph_version"] = "3.0.0"
        state["graph_sha256"] = dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["3.0.0"]
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(
            run, capabilities=["repository search", "project test command"]
        )
        self.write_work(run, payload)
        ready = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", ready["data"]["current"])

    def test_started_v3_1_run_can_finish_without_slice_contract(self) -> None:
        run = self.initialize(profile="light")
        state_path = run / graph.STATE_NAME
        state = self.read(state_path)
        state["graph_version"] = "3.1.0"
        state["graph_sha256"] = dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["3.1.0"]
        state.pop("implementation_strategy", None)
        state.pop("slices", None)
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload["implementation"].pop("strategy")
        payload["implementation"].pop("slices")
        self.write_work(run, payload)
        ready = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", ready["data"]["current"])

    def test_started_v3_4_run_keeps_staged_slice_commands(self) -> None:
        run = self.initialize(profile="standard")
        state_path = run / graph.STATE_NAME
        state = self.read(state_path)
        state["graph_version"] = "3.4.0"
        state["graph_sha256"] = dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["3.4.0"]
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        ready = graph.ready(run)
        self.assertEqual("3.4.0", self.read(state_path)["graph_version"])
        self.assertEqual("work", ready["data"]["current"])

    def test_started_v3_5_run_keeps_legacy_digest_and_staged_slice_commands(self) -> None:
        run = self.initialize(profile="standard")
        state_path = run / graph.STATE_NAME
        state = self.read(state_path)
        state["graph_version"] = "3.5.0"
        state["graph_sha256"] = dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["3.5.0"]
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        plan = self.plan()
        self.assertTrue(
            graph.plan_contract_text(plan, graph_version="3.5.0").startswith("\n")
        )
        ready = graph.ready(run)
        self.assertEqual("3.5.0", self.read(state_path)["graph_version"])
        self.assertEqual("work", ready["data"]["current"])

    def test_slice_receipt_tampering_blocks_complete(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
            "strategy": "delegated-sequential",
            "slices": [self.accepted_slice(run)],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run)],
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        graph.record(run, "work", "verify")
        self.write_verify(run, self.verify_payload(run))
        graph.record(run, "verify", "succeeded")
        receipt = Path(self.read(run / graph.STATE_NAME)["slices"]["implementation-app"]["receipt_path"])
        receipt.write_text(receipt.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "Worker receipt изменился"):
            graph.complete(run)

    def test_declared_root_integration_path_is_allowed(self) -> None:
        self.write("src/other.py", "OTHER = 1\n")
        run = self.initialize(profile="standard")
        self.plan(scope="src")
        graph.register_slice(run, self.slice_draft(run))
        self.write("src/app.py", "VALUE = 2\n")
        graph.record_slice(run, "implementation-app", self.slice_receipt(run))
        self.write("src/other.py", "OTHER = 2\n")
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py", "src/other.py"],
            "strategy": "delegated-sequential",
            "integration_paths": ["src/other.py"],
            "slices": [self.accepted_slice(run)],
        }
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.worker_agent(run)],
                capabilities=["repository search", "project test command", "mcp:context7"],
                implementation=implementation,
            ),
        )
        ready = graph.record(run, "work", "verify")
        self.assertEqual("verify", ready["data"]["current"])

    def test_suspend_and_resume_keep_task_and_control_state_separate(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        suspended = graph.suspend(
            run,
            "Switch to an unrelated urgent task.",
            "Resume implementation from the current code checkpoint.",
        )
        self.assertEqual("suspended", suspended["status"])
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual("suspended", state["task_status"])
        self.assertEqual("healthy", state["control_status"])
        self.assertTrue((run / graph.TASK_CHECKPOINT_NAME).is_file())
        resumed = graph.resume(run)
        self.assertEqual("running", resumed["status"])
        self.assertEqual("active", resumed["data"]["task_status"])

    def test_control_degradation_does_not_block_code_work(self) -> None:
        run = self.initialize(profile="standard")
        degraded = graph.degrade_control(run, "Controller receipt format is incompatible.")
        self.assertEqual("degraded", degraded["status"])
        state = self.read(run / graph.STATE_NAME)
        self.assertEqual("running", state["status"])
        self.assertEqual("active", state["task_status"])
        self.assertEqual("degraded", state["control_status"])
        ready = graph.ready(run)
        self.assertEqual("running", ready["status"])
        self.assertEqual("degraded", ready["data"]["control_status"])
        self.plan()
        created = graph.register_slice(run, self.slice_draft(run))
        self.assertEqual("ready", created["status"])
        state = self.read(run / graph.STATE_NAME)
        state["verification_required"] = True
        state["current"] = "complete"
        (run / graph.STATE_NAME).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "Verified completion requires healthy control"):
            graph.complete(run)

    def test_v2_task_id_is_not_silently_migrated(self) -> None:
        state = self.root / ".codex/task-delivery/TD-1/state.json"
        state.parent.mkdir(parents=True)
        state.write_text('{"schema_version": 2, "task_id": "TD-1"}\n', encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "v2"):
            self.initialize()


if __name__ == "__main__":
    unittest.main()
