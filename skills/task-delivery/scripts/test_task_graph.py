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
        )
        return Path(payload["data"]["run"])

    def plan(self, task_id: str = "TD-1", path: str | None = None, scope: str = "src/app.py") -> Path:
        relative = path or f"docs/tasks/{task_id}/PLAN.md"
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
        strategy: str = "delegated-sequential",
    ) -> Path:
        state = self.read(run / graph.STATE_NAME)
        review_mode = (
            "reused"
            if state["mode"] == "implement"
            else ("independent" if state["profile"] in {"complex", "critical"} else "self")
        )
        payload = {
            "schema_version": 1,
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
            "verification_commands": [{"command": "python3 -m unittest", "purpose": "narrow behavior"}],
            "capability_context": {
                "skills": [{"name": "coding-standards", "reason": "Apply the repository coding conventions.", "required": True}],
                "mcp": [{"receipt": "mcp:context7", "mode": "provided", "purpose": "Use the already verified library context."}],
            },
            "supersedes": supersedes,
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
            "schema_version": 1,
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

    def accepted_slice(self, run: Path, identifier: str = "implementation-app") -> dict:
        record = self.read(run / graph.STATE_NAME)["slices"][identifier]
        return {
            "slice_id": identifier,
            "packet_sha256": record["packet_sha256"],
            "receipt_sha256": record["receipt_sha256"],
            "root_acceptance": {
                "verdict": "accepted_with_concerns" if record["worker_status"] == "done_with_concerns" else "accepted",
                "verified_changed_paths": record["changed_paths"],
                "tests": [{"command": "python3 -m unittest", "purpose": "root replay", "exit_code": 0, "status": "passed"}],
                "concerns_resolution": ["Root verified and bounded the reported concern."] if record["worker_status"] == "done_with_concerns" else [],
            },
        }

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
            {"command": "python3 -m unittest", "purpose": "narrow behavior", "exit_code": 0, "status": "passed"}
        ]
        return {
            "schema_version": 3,
            "task_id": state["task_id"],
            "mode": state["mode"],
            "profile": state["profile"],
            "summary": "The requested behavior is implemented and verified against the current repository.",
            "confidence": confidence,
            "capabilities": capabilities or [
                "repository search",
                "project test command",
                "mcp:fallback:local-only-task",
            ],
            "agents": agents or [],
            "research": {
                "internal": ["src/app.py and the nearest project instructions were inspected"],
                "external": external or {"status": "not-needed", "reason": "The task depends only on stable local behavior."},
            },
            "plan": {
                "path": state["plan_path"],
                "digest": graph.plan_digest(plan),
                "review": {"mode": review_mode, "verdict": "pass"},
            },
            "implementation": implementation,
            "tests": tests,
            "documentation_impact": "Synchronize the canonical project docs with the delivered behavior.",
            "rollback": "Restore src/app.py to the exact baseline content and rerun the narrow test.",
            "residual_risks": [],
            "decision": decision,
        }

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

    def test_graph_has_only_three_control_nodes(self) -> None:
        contract = graph.graph_contract()
        self.assertEqual({"plan", "implement", "full"}, set(contract["routes"]))
        for mode in graph.MODES:
            self.assertEqual({"work", "verify", "complete"}, set(contract["routes"][mode]["nodes"]))
        self.assertEqual("adaptive", contract["delegation_policy"]["default_strategy"])
        self.assertEqual(
            "delegated-sequential",
            contract["delegation_policy"]["profile_preference"]["standard"],
        )
        self.assertFalse(contract["delegation_policy"]["parallel_write_enabled"])

    def test_cli_exposes_slice_commands_without_new_graph_nodes(self) -> None:
        created = graph.parser().parse_args(
            ["slice-create", "--run", "/tmp/run", "--packet", "/tmp/packet.json"]
        )
        recorded = graph.parser().parse_args(
            ["slice-record", "--run", "/tmp/run", "--slice-id", "implementation-app", "--receipt", "/tmp/receipt.json"]
        )
        self.assertEqual("slice-create", created.command)
        self.assertEqual("slice-record", recorded.command)
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
            ]
        )
        self.assertEqual("delegated-sequential", initialized.implementation_strategy)

    def test_explicit_slice_request_rejects_root_only_completion(self) -> None:
        run = self.initialize(implementation_strategy="delegated-sequential")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        with self.assertRaisesRegex(graph.GraphError, "запрос на реализацию слайсами"):
            graph.record(run, "work", "verify")

    def test_adaptive_standard_root_only_requires_reason(self) -> None:
        run = self.initialize()
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        payload = self.work_payload(run)
        payload["implementation"].pop("delegation_reason")
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "delegation_reason"):
            graph.record(run, "work", "verify")

    def test_ready_prefers_slice_for_standard_but_not_light(self) -> None:
        standard = self.initialize(task_id="TD-STANDARD")
        standard_ready = graph.ready(standard)
        self.assertEqual("delegated-sequential", standard_ready["data"]["implementation_strategy_preferred"])
        self.assertIn("slice-create", standard_ready["next_actions"][0])

        light = self.initialize(profile="light", task_id="TD-LIGHT")
        light_ready = graph.ready(light)
        self.assertEqual("root-only", light_ready["data"]["implementation_strategy_preferred"])
        self.assertNotIn("slice-create", " ".join(light_ready["next_actions"]))

    def test_slice_contract_is_progressively_disclosed(self) -> None:
        skill = (graph.SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        reference = (graph.SKILL_DIR / "references/implementation-slices.md").read_text(encoding="utf-8")
        worker = (graph.SKILL_DIR.parents[1] / "agents/task_worker.toml").read_text(encoding="utf-8")
        self.assertIn("work → complete", skill)
        self.assertIn("implementation-slices.md", skill)
        self.assertIn("`plan` никогда не запускает implementation workers", reference)
        self.assertIn("implement` выдаёт packet", reference)
        self.assertIn("`full` сначала", reference)
        self.assertIn("each selected required skill's SKILL.md", worker)

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

    def test_complex_full_slice_rejects_self_review_before_worker(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        draft = self.slice_draft(run)
        payload = self.read(draft)
        payload["plan_review"] = {"mode": "self", "receipt": "root:self-review"}
        draft.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "independent plan review"):
            graph.register_slice(run, draft)

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
        accepted = self.accepted_slice(run)
        accepted["root_acceptance"]["concerns_resolution"] = []
        implementation = {
            "status": "complete",
            "changed_paths": ["src/app.py"],
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
        with self.assertRaisesRegex(graph.GraphError, "concerns_resolution"):
            graph.record(run, "work", "verify")

    def test_parallel_write_slice_is_fail_closed(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        with self.assertRaisesRegex(graph.GraphError, "worktree isolation"):
            graph.register_slice(run, self.slice_draft(run, strategy="delegated-parallel"))

    def test_ready_exposes_mcp_first_policy(self) -> None:
        run = self.initialize(profile="light")
        ready = graph.ready(run)
        self.assertEqual("required", ready["data"]["mcp_policy"]["discovery"])

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
        task = self.read(self.root / ".codex/task-delivery/TD-1/state.json")
        self.assertEqual("completed", task["phase"])
        handoff = self.root / ".agent-graphs/task-delivery-handoffs/TD-1/HANDOFF.md"
        receipt = graph.legacy.load_project_start_runtime  # prove legacy module remains importable
        self.assertTrue(handoff.is_file())
        self.assertTrue(callable(receipt))

    def test_standard_full_requires_result_verifier_and_receipt_is_legacy_compatible(self) -> None:
        run = self.initialize(profile="standard")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run))
        with self.assertRaisesRegex(graph.GraphError, "требует независимый verify"):
            graph.record(run, "work", "succeeded")
        graph.record(run, "work", "verify")
        self.write_verify(run, self.verify_payload(run))
        graph.record(run, "verify", "succeeded")
        graph.complete(run)
        handoff = self.root / ".agent-graphs/task-delivery-handoffs/TD-1/HANDOFF.md"
        receipt = {"path": handoff.relative_to(self.root).as_posix(), "sha256": graph.sha256_file(handoff)}
        validated = __import__("project_maintenance").validate_task_delivery_receipt(self.root, receipt)
        self.assertEqual("TD-1", validated["task_id"])
        task = self.read(self.root / ".codex/task-delivery/TD-1/state.json")
        graph.legacy._MANIFEST_CACHE.clear()
        self.assertEqual(validated["implementation_sha256"], graph.legacy.implementation_repo_state(self.root, task)[1])

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

        implement_run = self.initialize(mode="implement", profile="complex", plan="docs/tasks/TD-1/PLAN.md")
        self.write("src/app.py", "VALUE = 3\n")
        payload = self.work_payload(implement_run, review_mode="reused")
        self.write_work(implement_run, payload)
        graph.record(implement_run, "work", "verify")

    def test_complex_implement_cannot_reuse_light_self_review(self) -> None:
        run = self.initialize(mode="plan", profile="light")
        self.plan()
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        implement = self.initialize(mode="implement", profile="complex", plan="docs/tasks/TD-1/PLAN.md")
        self.write("src/app.py", "VALUE = 3\n")
        self.write_work(implement, self.work_payload(implement, review_mode="reused"))
        with self.assertRaisesRegex(graph.GraphError, "self-review"):
            graph.record(implement, "work", "verify")

    def test_implement_rejects_scope_drift_after_plan_review(self) -> None:
        run = self.initialize(mode="plan", profile="light")
        self.plan()
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        self.write("src/app.py", "DRIFT = True\n")
        with self.assertRaisesRegex(graph.GraphError, "Область реализации изменилась"):
            self.initialize(mode="implement", profile="light", plan="docs/tasks/TD-1/PLAN.md")

    def test_complex_full_requires_plan_reviewer_receipt(self) -> None:
        run = self.initialize(profile="complex")
        self.plan()
        self.write("src/app.py", "VALUE = 2\n")
        self.write_work(run, self.work_payload(run, review_mode="independent"))
        with self.assertRaisesRegex(graph.GraphError, "requires a separate plan review|требует отдельный plan review"):
            graph.record(run, "work", "verify")
        self.write_work(
            run,
            self.work_payload(
                run,
                agents=[self.agent("task_plan_reviewer", "plan-review", "/root/plan-reviewer")],
                review_mode="independent",
            ),
        )
        graph.record(run, "work", "verify")

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
        self.write_work(run, self.work_payload(run))
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
        self.write_work(run, self.work_payload(run))
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
        self.write_work(run, self.work_payload(run))
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
        self.write_work(run, self.work_payload(run))
        graph.record(run, "work", "verify")
        self.write_verify(run, self.verify_payload(run, "reject"))
        blocked = graph.record(run, "verify", "failed")
        self.assertEqual("blocked", blocked["status"])
        with self.assertRaisesRegex(graph.GraphError, "терминален"):
            graph.retry(run, "verify")

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

    def test_v2_task_id_is_not_silently_migrated(self) -> None:
        state = self.root / ".codex/task-delivery/TD-1/state.json"
        state.parent.mkdir(parents=True)
        state.write_text('{"schema_version": 2, "task_id": "TD-1"}\n', encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "v2"):
            self.initialize()


if __name__ == "__main__":
    unittest.main()
