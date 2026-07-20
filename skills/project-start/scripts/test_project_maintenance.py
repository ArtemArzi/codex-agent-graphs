#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("project_maintenance.py")
SPEC = importlib.util.spec_from_file_location("project_maintenance", MODULE_PATH)
assert SPEC and SPEC.loader
maintenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maintenance)


class ProjectMaintenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.artifacts = {
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
        for key, relative in self.artifacts.items():
            if key == "adr_dir":
                (self.root / relative).mkdir(parents=True)
                (self.root / relative / "0001-foundation.md").write_text(
                    "# ADR\n\nAccepted foundation decision.\n", encoding="utf-8"
                )
                continue
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if key == "foundation_manifest":
                path.write_text('{"schema_version": 1}\n', encoding="utf-8")
            else:
                path.write_text(f"# {key}\n\nCanonical {key} content.\n", encoding="utf-8")
        stamp = maintenance.now()
        self.project_state = {
            "schema_version": 2,
            "phase": "complete",
            "created_at": stamp,
            "updated_at": stamp,
            "approvals": {"business": None, "foundation": None, "plan": None},
            "records": {},
            "maintenance": {"status": "operational", "history": []},
            "artifacts": self.artifacts,
            "history": [],
        }
        evidence_rel = self.artifacts["verification"]
        evidence_hash = maintenance.sha256_file(self.root / evidence_rel)
        for event in (
            *maintenance.project_start_runtime.FOUNDATION_EVENTS,
            *maintenance.project_start_runtime.TICKET_EVENTS,
            *maintenance.project_start_runtime.COMPLETION_EVENTS,
        ):
            self.project_state["records"][event] = {
                "evidence": evidence_rel,
                "sha256": evidence_hash,
                "at": stamp,
                "note": "fixture evidence",
            }
        for gate in ("business", "foundation", "plan"):
            snapshot = maintenance.project_start_runtime.gate_snapshot(self.root, self.project_state, gate)
            self.project_state["approvals"][gate] = {"at": stamp, "note": "fixture approval", **snapshot}
        maintenance.write_json_atomic(self.root / ".project-start/state.json", self.project_state)
        payload = maintenance.initialize(
            str(self.root),
            "Keep canonical docs aligned with the repository",
            "repository-change",
            skills_root=str(Path(__file__).parents[3] / "skills"),
            allow_new=True,
        )
        self.run_dir = Path(payload["data"]["run_dir"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    @property
    def baseline(self) -> list[str]:
        return sorted(maintenance.load_state(self.run_dir)["baseline_docs"])

    def task_delivery_receipt(self, task_id: str = "TD-001") -> Path:
        implementation = "a" * 64
        handoff = self.root / "docs/tasks" / task_id / "HANDOFF.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "# Handoff\n\n"
            "Status: READY\n"
            f"Implementation SHA-256: {implementation}\n"
            "Criteria passed: YES\n"
            "Rollback documented: YES\n"
            "Residual risks documented: YES\n"
            "Canonical docs changed: NO\n"
            "Proposed documentation maintenance: Update canonical docs through the maintenance graph.\n"
            "Completed at: 2026-07-19T12:00:00+00:00\n",
            encoding="utf-8",
        )
        relative = handoff.relative_to(self.root).as_posix()
        task_state = self.root / ".codex/task-delivery" / task_id / "state.json"
        maintenance.write_json_atomic(
            task_state,
            {
                "schema_version": 3,
                "task_id": task_id,
                "phase": "completed",
                "completed_at": "2026-07-19T12:01:00+00:00",
                "checkpoints": {
                    "handoff": {
                        "path": relative,
                        "sha256": maintenance.sha256_file(handoff),
                        "implementation_repo_digest": implementation,
                    }
                },
            },
        )
        return handoff

    def write(self, node: str, value: dict) -> Path:
        name = maintenance.maintenance_route()["nodes"][node]["artifact"]
        path = self.run_dir / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def record(self, node: str, value: dict, outcome: str = "succeeded") -> dict:
        path = self.write(node, value)
        return maintenance.record(self.run_dir, node, str(path), outcome)

    def advance_to_classification(self, finding_doc: str | None = None) -> None:
        run_state = maintenance.load_state(self.run_dir)
        self.record(
            "maintenance-intake",
            {
                "schema_version": 1,
                "reason": run_state["reason"],
                "trigger": run_state["trigger"],
                "canonical_docs": self.baseline,
            },
        )
        capabilities = maintenance.load_json(self.run_dir / "capabilities.json")
        self.record("capability-discovery", capabilities)
        self.record(
            "drift-audit",
            {
                "schema_version": 1,
                "checked_docs": self.baseline,
                "findings": []
                if finding_doc is None
                else [
                    {
                        "document": finding_doc,
                        "claim": "A documented repository fact is stale.",
                        "evidence": "repository:path:src/app",
                        "impact": "The canonical instruction no longer matches the repository.",
                    }
                ],
            },
        )

    def verify(self, verdict: str = "pass") -> dict:
        value = {
            "schema_version": 1,
            "verdict": verdict,
            "checked_docs": maintenance.managed_doc_relatives(maintenance.load_state(self.run_dir)),
            "stale_claims": [],
            "contradictions": [],
            "residual_risks": [],
        }
        if verdict == "reject":
            value["repair_list"] = ["Repair the stale factual statement."]
        return value

    def test_graph_contract_has_bootstrap_and_maintenance_routes(self) -> None:
        graph = maintenance.graph_contract()
        self.assertEqual(graph["routes"]["bootstrap"]["terminal"], "complete")
        self.assertEqual(graph["routes"]["maintenance"]["entry"], "maintenance-intake")
        self.assertEqual(len(graph["capability_registry"]["skills"]), 11)

    def test_initialize_is_idempotent_and_git_ignores_runtime(self) -> None:
        second = maintenance.initialize(
            str(self.root),
            "Keep canonical docs aligned with the repository",
            "repository-change",
            skills_root=str(Path(__file__).parents[3] / "skills"),
            allow_new=True,
        )
        self.assertEqual(second["data"]["run_dir"], str(self.run_dir))
        self.assertEqual((self.root / ".agent-graphs/.gitignore").read_text(encoding="utf-8"), "*\n")

    def test_repository_change_creates_fresh_run_only_after_active_run_completes(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Initial audit is current.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        source = self.root / "src/app.py"
        source.parent.mkdir()
        source.write_text("VERSION = 1\n", encoding="utf-8")
        changed = maintenance.initialize(
            str(self.root), "Keep canonical docs aligned with the repository", "repository-change", allow_new=True
        )
        self.assertNotEqual(changed["data"]["run_dir"], str(self.run_dir))
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.initialize(str(self.root), "Periodic audit", "scheduled", cycle="2026-W29-a", allow_new=True)

    def test_repository_fingerprint_hashes_internal_symlink_without_following_it(self) -> None:
        target = self.root / "src/target.txt"
        target.parent.mkdir()
        target.write_text("target\n", encoding="utf-8")
        link = self.root / "src/link.txt"
        link.symlink_to("target.txt")
        first = maintenance.repository_fingerprint(self.root, set(self.baseline))
        link.unlink()
        link.symlink_to("other.txt")
        second = maintenance.repository_fingerprint(self.root, set(self.baseline))
        self.assertNotEqual(first, second)

    def test_no_change_path_completes_and_updates_operational_ledger(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "All checked claims match current repository facts.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        payload = maintenance.complete(self.run_dir)
        self.assertEqual(payload["status"], "ok")
        state = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(state["maintenance"]["status"], "operational")
        self.assertEqual(state["maintenance"]["last_run"]["classification"], "no-change")

    def test_completion_refuses_an_invalid_project_start_predecessor(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "All checked claims match current repository facts.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        state = maintenance.load_json(self.root / ".project-start/state.json")
        state["approvals"]["business"] = None
        maintenance.write_json_atomic(self.root / ".project-start/state.json", state)
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.complete(self.run_dir)

    def test_completion_refuses_repository_change_after_verification(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "All checked claims match current repository facts.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        source = self.root / "src/app.py"
        source.parent.mkdir()
        source.write_text("changed after verification\n", encoding="utf-8")
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.complete(self.run_dir)

    def test_factual_update_refreshes_affected_approval_without_reopen(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "factual",
                "rationale": "One repository path was renamed without changing product meaning.",
                "affected_docs": [self.artifacts["business"]],
            },
            "factual",
        )
        business = self.root / self.artifacts["business"]
        business.write_text(business.read_text(encoding="utf-8") + "\nCurrent path: src/app.\n", encoding="utf-8")
        self.record(
            "documentation-update",
            {
                "schema_version": 1,
                "changed_docs": [self.artifacts["business"]],
                "source_receipts": ["repository:path:src/app"],
                "summary": "Updated the factual repository path.",
            },
        )
        self.record("documentation-verify", self.verify())
        payload = maintenance.complete(self.run_dir)
        self.assertEqual(payload["data"]["refreshed_approvals"], ["business"])
        updated = maintenance.load_json(self.root / ".project-start/state.json")
        issues = maintenance.project_start_runtime.approval_issues(self.root, updated, "business")
        self.assertEqual(issues, [])
        self.assertEqual(updated["phase"], "complete")

    def test_semantic_drift_routes_to_explicit_reopen_without_editing_docs(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        payload = self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "semantic",
                "rationale": "The accepted product boundary changed.",
                "affected_docs": [self.artifacts["business"]],
                "reopen_stage": "discovery",
            },
            "semantic",
        )
        self.assertEqual(payload["status"], "reopen-required")
        state = maintenance.load_state(self.run_dir)
        self.assertEqual(state["reopen_stage"], "discovery")
        self.assertEqual(state["status"], "reopen-required")
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(project["maintenance"]["status"], "reopen-required")
        self.assertEqual(project["maintenance"]["pending_reopen"]["stage"], "discovery")
        too_late = subprocess.run(
            [
                "python3",
                str(Path(__file__).with_name("project_start.py")),
                "reopen",
                "--root",
                str(self.root),
                "--stage",
                "planning",
                "--note",
                "Attempt to bypass required discovery",
                "--apply",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(too_late.returncode, 2)
        self.assertIn("слишком поздняя", too_late.stdout)
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.initialize(str(self.root), "Try to overwrite pending semantic run", "manual", allow_new=True)
        reopened = subprocess.run(
            [
                "python3",
                str(Path(__file__).with_name("project_start.py")),
                "reopen",
                "--root",
                str(self.root),
                "--stage",
                "discovery",
                "--note",
                "Accepted semantic documentation change",
                "--apply",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(reopened.returncode, 0, reopened.stdout + reopened.stderr)
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(project["maintenance"]["status"], "not-ready")
        self.assertNotIn("pending_reopen", project["maintenance"])

    def test_semantic_classification_rejects_source_drift_after_audit(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        source = self.root / "src/app.py"
        source.parent.mkdir()
        source.write_text("changed after audit\n", encoding="utf-8")
        path = self.write(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "semantic",
                "rationale": "The product boundary changed.",
                "affected_docs": [self.artifacts["business"]],
                "reopen_stage": "discovery",
            },
        )
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "impact-classification", str(path), "semantic")

    def test_factual_route_can_create_and_then_manage_nested_agents_context(self) -> None:
        module = self.root / "services/api"
        module.mkdir(parents=True)
        relative = "services/api/AGENTS.md"
        self.advance_to_classification(relative)
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "factual",
                "rationale": "A stable module boundary now needs a local context map derived from accepted contracts.",
                "affected_docs": [relative],
            },
            "factual",
        )
        (self.root / relative).write_text(
            "# API agent context\n\n"
            "## Scope\n\nApplies to the API module.\n\n"
            "## Map\n\n- `src/` owns request handling.\n\n"
            "## Commands\n\n- `python -m pytest services/api`\n\n"
            "## Boundaries\n\nInherit root policy; do not access sibling internals.\n",
            encoding="utf-8",
        )
        self.record(
            "documentation-update",
            {
                "schema_version": 1,
                "changed_docs": [],
                "created_docs": [relative],
                "source_receipts": ["repository:path:services/api"],
                "summary": "Created the inherited module context without adding new policy.",
            },
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertIn(relative, project["maintenance"]["agent_instruction_docs"])
        next_run = maintenance.initialize(str(self.root), "Audit the new module context", "repository-change", allow_new=True)
        next_state = maintenance.load_state(Path(next_run["data"]["run_dir"]))
        self.assertIn(relative, next_state["baseline_docs"])

    def test_new_nested_agents_context_rejects_generated_or_placeholder_content(self) -> None:
        generated = self.root / "generated/module"
        generated.mkdir(parents=True)
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.validate_new_agent_doc_path(
                self.root, "generated/module/AGENTS.md", must_exist=False
            )
        module = self.root / "services/billing"
        module.mkdir(parents=True)
        path = module / "AGENTS.md"
        path.write_text("# PENDING\n", encoding="utf-8")
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.validate_new_agent_doc_path(
                self.root, "services/billing/AGENTS.md", must_exist=True
            )
        path.write_text(
            (Path(__file__).parents[1] / "assets/templates/NESTED-AGENTS.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.validate_new_agent_doc_path(
                self.root, "services/billing/AGENTS.md", must_exist=True
            )

    def test_out_of_order_and_undeclared_changes_are_rejected(self) -> None:
        path = self.write(
            "drift-audit", {"schema_version": 1, "checked_docs": self.baseline, "findings": []}
        )
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "drift-audit", str(path), "succeeded")
        (self.root / self.artifacts["business"]).write_text("changed too early", encoding="utf-8")
        intake = self.write(
            "maintenance-intake",
            {
                "schema_version": 1,
                "reason": maintenance.load_state(self.run_dir)["reason"],
                "trigger": maintenance.load_state(self.run_dir)["trigger"],
                "canonical_docs": self.baseline,
            },
        )
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "maintenance-intake", str(intake), "succeeded")

    def test_capability_contract_requires_every_routed_skill(self) -> None:
        self.record(
            "maintenance-intake",
            {
                "schema_version": 1,
                "reason": maintenance.load_state(self.run_dir)["reason"],
                "trigger": maintenance.load_state(self.run_dir)["trigger"],
                "canonical_docs": self.baseline,
            },
        )
        capabilities = maintenance.load_json(self.run_dir / "capabilities.json")
        capabilities["skills"].pop("to-tickets")
        path = self.write("capability-discovery", capabilities)
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "capability-discovery", str(path), "succeeded")

    def test_no_change_cannot_contradict_drift_findings(self) -> None:
        self.record(
            "maintenance-intake",
            {
                "schema_version": 1,
                "reason": maintenance.load_state(self.run_dir)["reason"],
                "trigger": maintenance.load_state(self.run_dir)["trigger"],
                "canonical_docs": self.baseline,
            },
        )
        self.record("capability-discovery", maintenance.load_json(self.run_dir / "capabilities.json"))
        self.record(
            "drift-audit",
            {
                "schema_version": 1,
                "checked_docs": self.baseline,
                "findings": [
                    {
                        "document": self.artifacts["business"],
                        "claim": "The path is stale.",
                        "evidence": "repository:path:src/app",
                        "impact": "Readers get the wrong command.",
                    }
                ],
            },
        )
        path = self.write(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Incorrectly ignored the finding.",
                "affected_docs": [],
            },
        )
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "impact-classification", str(path), "no-change")

    def test_verification_repair_loop_is_bounded(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "factual",
                "rationale": "A factual path changed.",
                "affected_docs": [self.artifacts["business"]],
            },
            "factual",
        )
        business = self.root / self.artifacts["business"]
        business.write_text(business.read_text(encoding="utf-8") + "\nPath: src/app.\n", encoding="utf-8")
        update = {
            "schema_version": 1,
            "changed_docs": [self.artifacts["business"]],
            "source_receipts": ["repository:path:src/app"],
            "summary": "Updated the path.",
        }
        self.record("documentation-update", update)
        for repair in range(2):
            self.record("documentation-verify", self.verify("reject"), "rejected")
            self.record("documentation-update", update)
        payload = self.record("documentation-verify", self.verify("reject"), "rejected")
        self.assertEqual(payload["status"], "blocked")

    def test_failed_node_persists_blocked_status_and_retry_restores_running(self) -> None:
        run_state = maintenance.load_state(self.run_dir)
        payload = self.record(
            "maintenance-intake",
            {
                "schema_version": 1,
                "error": "The intake worker failed before producing a trustworthy receipt.",
                "reason": run_state["reason"],
                "trigger": run_state["trigger"],
                "canonical_docs": self.baseline,
            },
            "failed",
        )
        self.assertEqual(payload["status"], "blocked")
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(project["maintenance"]["status"], "blocked")
        maintenance.retry(self.run_dir, "Correct the intake artifact and retry once.")
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(project["maintenance"]["status"], "running")

    def test_failed_classification_is_recorded_and_can_be_retried(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        payload = self.record(
            "impact-classification",
            {"schema_version": 1, "error": "Classifier could not reconcile evidence."},
            "failed",
        )
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(maintenance.load_state(self.run_dir)["status"], "blocked")

    def test_deleted_declared_document_remains_auditable_and_routes_semantic(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Initial audit is current.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        deleted = self.artifacts["business"]
        (self.root / deleted).unlink()
        payload = maintenance.initialize(str(self.root), "Canonical document was deleted", "repository-change", allow_new=True)
        self.run_dir = Path(payload["data"]["run_dir"])
        self.assertEqual(maintenance.load_state(self.run_dir)["baseline_docs"][deleted], "missing")
        self.advance_to_classification(deleted)
        result = self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "semantic",
                "rationale": "A declared business contract was deleted.",
                "affected_docs": [deleted],
                "reopen_stage": "discovery",
            },
            "semantic",
        )
        self.assertEqual(result["status"], "reopen-required")

    def test_gitignored_agents_file_is_still_in_canonical_audit_set(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Initial audit is current.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        (self.root / ".gitignore").write_text("private/\n", encoding="utf-8")
        agents = self.root / "private/service/AGENTS.md"
        agents.parent.mkdir(parents=True)
        agents.write_text("# Private service context\n", encoding="utf-8")
        payload = maintenance.initialize(str(self.root), "Audit ignored local instructions", "repository-change", allow_new=True)
        state = maintenance.load_state(Path(payload["data"]["run_dir"]))
        self.assertIn("private/service/AGENTS.md", state["baseline_docs"])

    def test_no_change_verifier_rejection_returns_to_drift_audit(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Initial audit found no drift.",
                "affected_docs": [],
            },
            "no-change",
        )
        payload = self.record("documentation-verify", self.verify("reject"), "rejected")
        self.assertEqual(payload["data"]["current"], "drift-audit")
        self.assertIsNone(maintenance.load_state(self.run_dir)["classification"])

    def test_document_change_after_verifier_pass_is_rejected(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "factual",
                "rationale": "A factual path changed.",
                "affected_docs": [self.artifacts["business"]],
            },
            "factual",
        )
        business = self.root / self.artifacts["business"]
        business.write_text(business.read_text(encoding="utf-8") + "\nPath: src/app.\n", encoding="utf-8")
        self.record(
            "documentation-update",
            {
                "schema_version": 1,
                "changed_docs": [self.artifacts["business"]],
                "source_receipts": ["repository:path:src/app"],
                "summary": "Updated the path.",
            },
        )
        self.record("documentation-verify", self.verify())
        business.write_text("# Replaced\n\nSemantic content after PASS.\n", encoding="utf-8")
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.complete(self.run_dir)

    def test_document_change_between_update_and_verifier_requires_new_update_receipt(self) -> None:
        self.advance_to_classification(self.artifacts["business"])
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "factual",
                "rationale": "A factual path changed.",
                "affected_docs": [self.artifacts["business"]],
            },
            "factual",
        )
        business = self.root / self.artifacts["business"]
        business.write_text(business.read_text(encoding="utf-8") + "\nPath: src/app.\n", encoding="utf-8")
        self.record(
            "documentation-update",
            {
                "schema_version": 1,
                "changed_docs": [self.artifacts["business"]],
                "source_receipts": ["repository:path:src/app"],
                "summary": "Updated the path.",
            },
        )
        business.write_text("# Semantic replacement before verifier\n", encoding="utf-8")
        path = self.write("documentation-verify", self.verify())
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "documentation-verify", str(path), "succeeded")
        self.assertEqual(maintenance.load_state(self.run_dir)["current"], "documentation-verify")

    def test_change_receipt_tampering_is_detected(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Initial audit is current.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        receipt = self.task_delivery_receipt()
        payload = maintenance.initialize(
            str(self.root), "Task finished", "task-delivery", str(receipt), allow_new=True
        )
        run_dir = Path(payload["data"]["run_dir"])
        receipt.write_text("tampered", encoding="utf-8")
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.load_state(run_dir)

    def test_node_receipt_tampering_is_detected(self) -> None:
        self.record(
            "maintenance-intake",
            {
                "schema_version": 1,
                "reason": maintenance.load_state(self.run_dir)["reason"],
                "trigger": maintenance.load_state(self.run_dir)["trigger"],
                "canonical_docs": self.baseline,
            },
        )
        state = maintenance.load_state(self.run_dir)
        node_receipt = Path(state["nodes"]["maintenance-intake"]["receipts"][0]["artifact"])
        node_receipt.write_text("{}", encoding="utf-8")
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.validate_receipts(state)

    def test_task_delivery_trigger_requires_a_completed_bound_receipt(self) -> None:
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.initialize(str(self.root), "Task finished", "task-delivery", allow_new=True)
        handoff = self.task_delivery_receipt("TD-002")
        task_state = self.root / ".codex/task-delivery/TD-002/state.json"
        state = maintenance.load_json(task_state)
        state["phase"] = "ready_to_complete"
        maintenance.write_json_atomic(task_state, state)
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.initialize(str(self.root), "Task finished", "task-delivery", str(handoff), allow_new=True)

    def test_task_delivery_obligation_moves_required_to_running_to_operational(self) -> None:
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Initial audit is current.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        handoff = self.task_delivery_receipt("TD-OBLIGATION")
        task_state = self.root / ".codex/task-delivery/TD-OBLIGATION/state.json"
        project = maintenance.load_json(self.root / ".project-start/state.json")
        project["maintenance"]["status"] = "maintenance-required"
        project["maintenance"]["maintenance_required"] = {
            "task_id": "TD-OBLIGATION",
            "handoff_path": handoff.relative_to(self.root).as_posix(),
            "handoff_sha256": maintenance.sha256_file(handoff),
            "task_state_path": task_state.relative_to(self.root).as_posix(),
            "task_state_sha256": maintenance.sha256_file(task_state),
            "created_at": maintenance.now(),
        }
        maintenance.write_json_atomic(self.root / ".project-start/state.json", project)
        payload = maintenance.initialize(
            str(self.root), "Task TD-OBLIGATION completed", "task-delivery", str(handoff), allow_new=True
        )
        self.run_dir = Path(payload["data"]["run_dir"])
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(project["maintenance"]["status"], "running")
        self.advance_to_classification()
        self.record(
            "impact-classification",
            {
                "schema_version": 1,
                "classification": "no-change",
                "rationale": "Task did not invalidate canonical claims.",
                "affected_docs": [],
            },
            "no-change",
        )
        self.record("documentation-verify", self.verify())
        maintenance.complete(self.run_dir)
        project = maintenance.load_json(self.root / ".project-start/state.json")
        self.assertEqual(project["maintenance"]["status"], "operational")
        self.assertNotIn("maintenance_required", project["maintenance"])

    def test_receipt_symlink_escape_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.run_dir / "receipts").symlink_to(outside, target_is_directory=True)
        intake = self.write(
            "maintenance-intake",
            {
                "schema_version": 1,
                "reason": maintenance.load_state(self.run_dir)["reason"],
                "trigger": maintenance.load_state(self.run_dir)["trigger"],
                "canonical_docs": self.baseline,
            },
        )
        with self.assertRaises(maintenance.MaintenanceError):
            maintenance.record(self.run_dir, "maintenance-intake", str(intake), "succeeded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
