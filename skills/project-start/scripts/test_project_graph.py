#!/usr/bin/env python3
"""Adversarial checks for the small Project Start v3 control graph."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import project_graph as graph  # noqa: E402


class ProjectGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def init(self, mode: str = "auto", reason: str = "Prepare project") -> Path:
        payload = graph.initialize(str(self.root), mode, reason, "manual", None)
        return Path(payload["data"]["run"])

    def bootstrap_docs(self) -> list[str]:
        self.write(
            "AGENTS.md",
            "# Agent map\n\n## Scope\nWhole repository scope and its canonical documentation.\n\n"
            "## Map\nStart with docs/README.md and then read the nearest module AGENTS.md.\n\n"
            "## Commands\nRun the declared project checks before claiming completion.\n\n"
            "## Boundaries\nPreserve user work, project contracts, and canonical authority.\n\n"
            "## Agent skills\nDomain layout: docs/agents/domain.md. "
            "Issue tracker: docs/agents/issue-tracker.md.\n",
        )
        self.write(
            "CONTEXT.md",
            "# Project context\n\nA concise glossary for the project domain.\n\n"
            "## Language\n\n**Project**: The product represented by this repository.\n",
        )
        self.write(
            "docs/README.md",
            "# Documentation map\n\n"
            "- [Business](project/PROJECT.md)\n"
            "- [Domain context](../CONTEXT.md)\n"
            "- [Foundation](project/FOUNDATION.md)\n"
            "- [Engineering standard](project/ENGINEERING.md)\n"
            "- [Codebase](project/CODEBASE.md)\n"
            "- [Quality](project/QUALITY.md)\n"
            "- [Plan](project/PLAN.md)\n"
            "- [Agent context](../AGENTS.md)\n"
            "- [Domain skill contract](agents/domain.md)\n"
            "- [Issue tracker contract](agents/issue-tracker.md)\n",
        )
        self.write(
            "docs/agents/domain.md",
            "# Domain docs\n\nUse the root CONTEXT.md as the single domain glossary.\n",
        )
        self.write(
            "docs/agents/issue-tracker.md",
            "# Issue tracker\n\nUse local Markdown plans unless the repository declares a remote tracker.\n",
        )
        self.write("docs/project/PROJECT.md", "# Product\n\nOutcome and business invariants are explicit.\n")
        self.write("docs/project/FOUNDATION.md", "# Foundation\n\nArchitecture and ownership are explicit.\n")
        self.write(
            "docs/project/ENGINEERING.md",
            "# Engineering standard\n\nProject-specific module boundaries, framework patterns, "
            "test obligations, and exact quality commands are explicit.\n",
        )
        self.write("docs/project/CODEBASE.md", "# Codebase\n\nModules, interfaces, seams, and paths are explicit.\n")
        self.write("docs/project/QUALITY.md", "# Quality\n\nRisks and verification commands are explicit.\n")
        self.write("docs/project/PLAN.md", "# Plan\n\nThe next observable delivery slice is explicit.\n")
        return sorted([
            "AGENTS.md",
            "CONTEXT.md",
            "docs/README.md",
            "docs/agents/domain.md",
            "docs/agents/issue-tracker.md",
            "docs/project/CODEBASE.md",
            "docs/project/ENGINEERING.md",
            "docs/project/FOUNDATION.md",
            "docs/project/PLAN.md",
            "docs/project/PROJECT.md",
            "docs/project/QUALITY.md",
        ])

    def work_payload(
        self,
        mode: str,
        canonical: list[str],
        *,
        classification: str,
        changed: list[str] | None = None,
        created: list[str] | None = None,
        verification: str = "self",
        decision: dict | None = None,
        agents: list[str] | None = None,
        capabilities: list[str] | None = None,
        confidence: str = "high",
        gaps: list[str] | None = None,
    ) -> dict:
        coverage = {
            "business": "docs/project/PROJECT.md",
            "documentation_map": "docs/README.md",
            "domain_context": "CONTEXT.md",
            "foundation": "docs/project/FOUNDATION.md",
            "engineering_standard": "docs/project/ENGINEERING.md",
            "codebase": "docs/project/CODEBASE.md",
            "quality": "docs/project/QUALITY.md",
            "plan": "docs/project/PLAN.md",
            "agent_context": "AGENTS.md",
            "skill_contract": "docs/agents/domain.md",
        }
        default_capabilities = ["rg"]
        if mode == "bootstrap":
            default_capabilities.extend(
                [
                    "mcp:context7",
                    "project-start:skill-contract-fallback",
                    "coding-standards",
                    "domain-modeling",
                    "codebase-design",
                ]
            )
        else:
            default_capabilities.append("mcp:fallback:local-only-maintenance")
            changed_set = set(changed or []) | set(created or [])
            if changed_set & {
                "AGENTS.md",
                "docs/README.md",
                "docs/agents/domain.md",
                "docs/agents/issue-tracker.md",
            }:
                default_capabilities.append("project-start:skill-contract-fallback")
            if "CONTEXT.md" in changed_set or "CONTEXT-MAP.md" in changed_set:
                default_capabilities.append("domain-modeling")
            if changed_set & {"docs/project/FOUNDATION.md", "docs/project/CODEBASE.md"}:
                default_capabilities.append("codebase-design")
            if "docs/project/ENGINEERING.md" in changed_set:
                default_capabilities.append("coding-standards")
        pending_decision = isinstance(decision, dict) and isinstance(decision.get("question"), str)
        return {
            "schema_version": 3,
            "mode": mode,
            "summary": "Canonical project context is current and usable.",
            "classification": classification,
            "capabilities": capabilities if capabilities is not None else default_capabilities,
            "agents": agents or [],
            "canonical_docs": canonical,
            "changed_docs": changed or [],
            "created_docs": created or [],
            "evidence": [canonical[0]],
            "coverage": {} if pending_decision else coverage,
            "verification": verification,
            "confidence": confidence,
            "gaps": gaps or [],
            "decision": decision,
        }

    def write_work(self, run: Path, payload: dict) -> None:
        (run / graph.WORK_NAME).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def decision_payload(self, mode: str, classification: str, decision: dict) -> dict:
        return {
            "schema_version": 3,
            "mode": mode,
            "summary": "A material documentation decision must be resolved before edits.",
            "classification": classification,
            "capabilities": ["rg", "mcp:fallback:decision-only-pass"],
            "agents": [],
            "canonical_docs": [],
            "changed_docs": [],
            "created_docs": [],
            "evidence": [],
            "coverage": {},
            "verification": "self",
            "confidence": "high",
            "gaps": [],
            "decision": decision,
        }

    def completed_bootstrap(self) -> tuple[Path, list[str]]:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        return run, docs

    def maintenance(self, reason: str = "Refresh docs") -> tuple[Path, list[str]]:
        _, docs = self.completed_bootstrap()
        return self.init("auto", reason), docs

    def task_delivery_obligation(self, task_id: str = "TD-BOUND") -> tuple[str, Path, list[str]]:
        _, docs = self.completed_bootstrap()
        self.write("src/module.py", "VALUE = 1\n")
        plan = self.write(
            f"docs/tasks/{task_id}/PLAN.md",
            "# Plan\n\n<!-- task-delivery:scope\nsrc/module.py\n-->\n",
        )
        task_state = self.root / f".codex/task-delivery/{task_id}/state.json"
        task_state.parent.mkdir(parents=True, exist_ok=True)
        task = {
            "schema_version": 2,
            "task_id": task_id,
            "phase": "completed",
            "completed_at": "2026-07-20T10:00:00+00:00",
            "artifacts": {"plan": plan.relative_to(self.root).as_posix()},
            "checkpoints": {},
        }
        graph.task_delivery_runtime._MANIFEST_CACHE.clear()
        implementation = graph.task_delivery_runtime.implementation_repo_state(self.root, task)[1]
        handoff = self.write(
            f"docs/tasks/{task_id}/HANDOFF.md",
            "Status: READY\nCriteria passed: YES\nRollback documented: YES\n"
            "Residual risks documented: YES\nCanonical docs changed: NO\n"
            f"Implementation SHA-256: {implementation}\n"
            "Proposed documentation maintenance: Refresh the foundation facts.\n",
        )
        handoff_rel = handoff.relative_to(self.root).as_posix()
        handoff_sha = graph.sha256_file(handoff)
        task["checkpoints"]["handoff"] = {
            "path": handoff_rel,
            "sha256": handoff_sha,
            "implementation_repo_digest": implementation,
        }
        task_state.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        task_rel = task_state.relative_to(self.root).as_posix()
        task_sha = graph.sha256_file(task_state)
        project_path = self.root / ".project-start/state.json"
        project = self.read_json(project_path)
        project["maintenance"] = {
            "status": "maintenance-required",
            "history": [],
            "maintenance_required": {
                "task_id": task_id,
                "handoff_path": handoff_rel,
                "handoff_sha256": handoff_sha,
                "task_state_path": task_rel,
                "task_state_sha256": task_sha,
            },
        }
        project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        return handoff_rel, task_state, docs

    def test_graph_has_only_three_active_nodes(self) -> None:
        contract = graph.graph_contract()
        self.assertEqual("auto", contract["default_mode"])
        for mode in ("bootstrap", "maintenance"):
            self.assertEqual({"work", "verify", "complete"}, set(contract["routes"][mode]["nodes"]))

    def test_ready_exposes_the_unified_documentation_contract(self) -> None:
        run = self.init("bootstrap")
        ready = graph.ready(run)
        contract = ready["data"]["documentation_contract"]
        self.assertEqual(graph.BOOTSTRAP_COVERAGE, set(contract["coverage"]))
        self.assertEqual("AGENTS.md", contract["anchors"]["agent_context"])
        self.assertEqual("docs/README.md", contract["anchors"]["documentation_map"])
        self.assertEqual({"domain-modeling", "codebase-design"}, set(contract["required_bootstrap_skills"]))
        self.assertEqual(
            {"setup-matt-pocock-skills", "project-start:skill-contract-fallback"},
            set(contract["skill_contract_providers"]),
        )
        self.assertEqual(
            {"coding-standards", "project-start:engineering-standard-fallback"},
            set(contract["engineering_standard_providers"]),
        )
        self.assertEqual("when-relevant", ready["data"]["mcp_policy"]["discovery"])
        self.assertEqual("required", ready["data"]["mcp_policy"]["relevant_use"])
        self.assertEqual(
            {"tracked", "verified"},
            set(graph.graph_contract()["execution_policy"]["tiers"]),
        )

    def test_bootstrap_requires_an_mcp_receipt(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
            capabilities=[
                "rg",
                "project-start:skill-contract-fallback",
                "coding-standards",
                "domain-modeling",
                "codebase-design",
            ],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "MCP receipt"):
            graph.record(run, "work", "succeeded")

    def test_local_bootstrap_accepts_not_applicable_mcp_receipt(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
            capabilities=[
                "rg",
                "mcp:not-applicable:local-repository-only",
                "project-start:skill-contract-fallback",
                "coding-standards",
                "domain-modeling",
                "codebase-design",
            ],
        )
        self.write_work(run, payload)
        response = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", response["data"]["node"])

    def test_bootstrap_requires_matt_pocock_documentation_skills(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
            capabilities=["rg", "project-start:skill-contract-fallback"],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "обязательные documentation skills"):
            graph.record(run, "work", "succeeded")

    def test_bootstrap_requires_available_or_internal_skill_contract_provider(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
            capabilities=["rg", "mcp:context7", "domain-modeling", "codebase-design"],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "provider skill contract"):
            graph.record(run, "work", "succeeded")

    def test_bootstrap_accepts_external_skill_contract_provider_when_available(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
            capabilities=[
                "rg",
                "mcp:context7",
                "setup-matt-pocock-skills",
                "coding-standards",
                "domain-modeling",
                "codebase-design",
            ],
        )
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")

    def test_bootstrap_requires_engineering_standard_provider(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
            capabilities=[
                "rg",
                "mcp:context7",
                "project-start:skill-contract-fallback",
                "domain-modeling",
                "codebase-design",
            ],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "provider engineering standard"):
            graph.record(run, "work", "succeeded")

    def test_large_repo_instruction_guidance_is_part_of_the_contract(self) -> None:
        skill = (graph.SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        contract = (graph.SKILL_DIR / "references/documentation-contract.md").read_text(encoding="utf-8")
        maintenance = (graph.SKILL_DIR / "references/maintenance.md").read_text(encoding="utf-8")
        template = (graph.SKILL_DIR / "assets/templates/NESTED-AGENTS.md").read_text(encoding="utf-8")
        verifier = (graph.SKILL_DIR.parents[1] / "agents/project_docs_verifier.toml").read_text(encoding="utf-8")
        for required in ("project root", "project_doc_max_bytes", "ниже cwd", "runtime flows"):
            self.assertIn(required, skill)
        for required in ("execution-flow index", "entry interface", "owning spec"):
            self.assertIn(required, contract)
        for required in ("representative chains", "orphaned nested", "current card"):
            self.assertIn(required, maintenance)
        self.assertIn("Do not list every file", template)
        self.assertIn("Do not duplicate parent guidance", template)
        self.assertIn("effective project_doc_max_bytes", verifier)

    def test_bootstrap_requires_docs_map_to_route_every_role(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        path = self.root / "docs/README.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("- [Codebase](project/CODEBASE.md)\n", ""),
            encoding="utf-8",
        )
        self.write_work(
            run,
            self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs),
        )
        with self.assertRaisesRegex(graph.GraphError, "docs/README.md"):
            graph.record(run, "work", "succeeded")

    def test_maintenance_requires_only_the_skill_for_the_changed_layer(self) -> None:
        run, docs = self.maintenance()
        target = "docs/project/CODEBASE.md"
        self.write(target, "# Codebase\n\nA verified module boundary was added.\n")
        payload = self.work_payload(
            "maintenance",
            docs,
            classification="factual",
            changed=[target],
            capabilities=["rg"],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "codebase-design"):
            graph.record(run, "work", "succeeded")

    def test_bootstrap_self_path_completes_and_opens_execution(self) -> None:
        run, docs = self.completed_bootstrap()
        state = self.read_json(run / graph.STATE_NAME)
        project = self.read_json(self.root / ".project-start/state.json")
        self.assertEqual("completed", state["status"])
        self.assertEqual("execution", project["phase"])
        self.assertEqual("operational", project["maintenance"]["status"])
        self.assertEqual(docs, project["graph_v3"]["canonical_docs"])

    def test_auto_selects_maintenance_and_no_change_is_fast(self) -> None:
        run, docs = self.maintenance()
        self.write_work(run, self.work_payload("maintenance", docs, classification="no-change"))
        ready = graph.record(run, "work", "succeeded")
        self.assertEqual("complete", ready["data"]["node"])
        graph.complete(run)

    def test_factual_maintenance_requires_exact_delta(self) -> None:
        run, docs = self.maintenance()
        target = "docs/project/PROJECT.md"
        self.write(target, "# Product\n\nVerified behavior now includes the delivered path.\n")
        payload = self.work_payload("maintenance", docs, classification="factual", changed=[target])
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")
        graph.complete(run)

    def test_maintenance_cannot_drop_existing_canonical_doc(self) -> None:
        run, docs = self.maintenance()
        reduced = [path for path in docs if path != "docs/project/QUALITY.md"]
        self.write_work(run, self.work_payload("maintenance", reduced, classification="no-change"))
        with self.assertRaisesRegex(graph.GraphError, "канонический"):
            graph.record(run, "work", "succeeded")

    def test_same_reason_gets_new_run_after_repository_change(self) -> None:
        _, docs = self.completed_bootstrap()
        first = self.init("maintenance", "Scheduled refresh")
        self.write_work(first, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(first, "work", "succeeded")
        graph.complete(first)
        self.write("src/module.py", "VALUE = 1\n")
        second = self.init("maintenance", "Scheduled refresh")
        self.assertNotEqual(first, second)

    def test_concurrent_source_change_rejects_work_receipt(self) -> None:
        run, docs = self.maintenance()
        self.write("src/module.py", "VALUE = 1\n")
        self.write_work(run, self.work_payload("maintenance", docs, classification="no-change"))
        with self.assertRaisesRegex(graph.GraphError, "изменились после init"):
            graph.record(run, "work", "succeeded")

    def test_python_cache_does_not_create_false_source_drift(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write("src/__pycache__/service.cpython-314.pyc", "derived bytecode")
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs))
        graph.record(run, "work", "succeeded")

    def test_next_action_uses_absolute_runner_path(self) -> None:
        payload = graph.initialize(str(self.root), "bootstrap", "Prepare project", "manual", None)
        action = payload["next_actions"][0]
        self.assertIn(str(Path(graph.__file__).resolve()), action)
        self.assertNotIn("python3 project_graph.py", action)

    def test_false_delta_is_rejected(self) -> None:
        run, docs = self.maintenance()
        payload = self.work_payload("maintenance", docs, classification="factual", changed=["docs/project/PROJECT.md"])
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "delta"):
            graph.record(run, "work", "succeeded")

    def test_new_nested_agents_must_be_substantive(self) -> None:
        run, docs = self.maintenance()
        self.write("services/api/README.md", "# API\n")
        self.write("services/api/AGENTS.md", "# TODO\n")
        canonical = sorted(docs + ["services/api/AGENTS.md", "services/api/README.md"])
        created = ["services/api/AGENTS.md", "services/api/README.md"]
        payload = self.work_payload("maintenance", canonical, classification="factual", created=created)
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "Scope|TODO"):
            graph.record(run, "work", "succeeded")

    def test_valid_nested_agents_is_accepted(self) -> None:
        run, docs = self.maintenance()
        self.write(
            "services/api/AGENTS.md",
            "# API agent map\n\n## Scope\nAPI module ownership.\n\n## Map\nHandlers live in this module.\n\n"
            "## Commands\nRun API unit tests.\n\n## Boundaries\nDo not access storage directly.\n",
        )
        canonical = sorted(docs + ["services/api/AGENTS.md"])
        payload = self.work_payload("maintenance", canonical, classification="factual", created=["services/api/AGENTS.md"])
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")

    def test_semantic_change_requires_decision_first(self) -> None:
        run, docs = self.maintenance()
        target = "docs/project/FOUNDATION.md"
        self.write(target, "# Foundation\n\nA new public architecture contract.\n")
        payload = self.work_payload(
            "maintenance", docs, classification="semantic", changed=[target], decision={"question": "Choose contract", "recommended": "Keep compatibility", "scope": [target]}
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "resolved decision"):
            graph.record(run, "work", "succeeded")

    def test_decision_resumes_semantic_work(self) -> None:
        run, docs = self.maintenance()
        target = "docs/project/FOUNDATION.md"
        pending = {"question": "Which public contract should be canonical?", "recommended": "Keep compatibility", "scope": [target]}
        self.write_work(run, self.work_payload("maintenance", docs, classification="semantic", decision=pending))
        response = graph.record(run, "work", "decision")
        self.assertEqual("decision-required", response["status"])
        graph.decide(run, "Use the compatible contract")
        decision_id = self.read_json(run / graph.STATE_NAME)["decisions"][-1]["id"]
        self.write(target, "# Foundation\n\nThe compatible public contract is canonical.\n")
        payload = self.work_payload(
            "maintenance",
            docs,
            classification="semantic",
            changed=[target],
            decision={"id": decision_id},
            verification="independent",
        )
        self.write_work(run, payload)
        graph.record(run, "work", "verify")
        state = self.read_json(run / graph.STATE_NAME)
        receipt = state["nodes"]["work"]["receipts"][-1]
        verification = {
            "schema_version": 3,
            "verdict": "pass",
            "work_sha256": receipt["sha256"],
            "docs_sha256": receipt["docs_sha256"],
            "checked_docs": receipt["canonical_docs"],
            "residual_risks": [],
            "repair_list": [],
        }
        (run / graph.VERIFY_NAME).write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
        graph.record(run, "verify", "succeeded")
        graph.complete(run)

    def test_low_confidence_cannot_self_complete(self) -> None:
        run, docs = self.maintenance()
        payload = self.work_payload(
            "maintenance",
            docs,
            classification="no-change",
            confidence="low",
            gaps=["One repository boundary remains uncertain"],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "independent verify"):
            graph.record(run, "work", "succeeded")

    def test_resolved_decision_cannot_edit_outside_scope(self) -> None:
        run, docs = self.maintenance()
        allowed = "docs/project/FOUNDATION.md"
        changed = "docs/project/PROJECT.md"
        pending = {"question": "Which foundation is canonical?", "recommended": "Keep compatibility", "scope": [allowed]}
        self.write_work(run, self.work_payload("maintenance", docs, classification="semantic", decision=pending))
        graph.record(run, "work", "decision")
        graph.decide(run, "Keep the compatible foundation")
        decision_id = self.read_json(run / graph.STATE_NAME)["decisions"][-1]["id"]
        self.write(changed, "# Product\n\nUnrelated semantic product change.\n")
        payload = self.work_payload("maintenance", docs, classification="semantic", changed=[changed], decision={"id": decision_id})
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "decision scope"):
            graph.record(run, "work", "succeeded")

    def test_manual_run_cannot_consume_task_delivery_obligation(self) -> None:
        self.completed_bootstrap()
        state_path = self.root / ".project-start/state.json"
        project = self.read_json(state_path)
        project["maintenance"] = {
            "status": "maintenance-required",
            "history": [],
            "maintenance_required": {
                "task_id": "task-7",
                "handoff_path": ".codex/task-delivery/task-7/HANDOFF.md",
                "handoff_sha256": "a" * 64,
            },
        }
        state_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "Task Delivery obligation"):
            graph.initialize(str(self.root), "maintenance", "Manual refresh", "manual", None)
        preserved = self.read_json(state_path)["maintenance"]
        self.assertEqual("maintenance-required", preserved["status"])
        self.assertEqual("task-7", preserved["maintenance_required"]["task_id"])

    def test_task_delivery_state_is_bound_after_init(self) -> None:
        handoff_rel, task_state, _ = self.task_delivery_obligation()
        payload = graph.initialize(
            str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
        )
        run = Path(payload["data"]["run"])
        task = self.read_json(task_state)
        task["tampered"] = True
        task_state.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "Task Delivery state"):
            graph.ready(run)

    def test_task_delivery_receipt_rejects_later_source_drift(self) -> None:
        handoff_rel, _, _ = self.task_delivery_obligation("TD-STALE")
        self.write("src/module.py", "VALUE = 2\n")
        with self.assertRaisesRegex(graph.GraphError, "новый Task Delivery checkpoint"):
            graph.initialize(
                str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
            )

    def test_task_delivery_freshness_is_rechecked_after_baseline_capture(self) -> None:
        handoff_rel, _, _ = self.task_delivery_obligation("TD-TOCTOU")
        original = graph.validate_task_delivery_freshness
        calls = 0

        def mutate_after_first(root: Path, receipt: dict | None) -> None:
            nonlocal calls
            calls += 1
            original(root, receipt)
            if calls == 1:
                self.write("src/module.py", "VALUE = 3\n")

        with mock.patch.object(graph, "validate_task_delivery_freshness", side_effect=mutate_after_first):
            with self.assertRaisesRegex(graph.GraphError, "новый Task Delivery checkpoint"):
                graph.initialize(
                    str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
                )
        self.assertEqual(2, calls)

    def test_conditional_verifier_is_bound_to_exact_receipts(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs, verification="independent"))
        graph.record(run, "work", "verify")
        state = self.read_json(run / graph.STATE_NAME)
        receipt = state["nodes"]["work"]["receipts"][-1]
        verification = {
            "schema_version": 3,
            "verdict": "pass",
            "work_sha256": receipt["sha256"],
            "docs_sha256": receipt["docs_sha256"],
            "checked_docs": receipt["canonical_docs"],
            "residual_risks": [],
            "repair_list": [],
        }
        (run / graph.VERIFY_NAME).write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
        graph.record(run, "verify", "succeeded")
        graph.complete(run)

    def test_verifier_reject_returns_to_work_once(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs, verification="independent"))
        graph.record(run, "work", "verify")
        state = self.read_json(run / graph.STATE_NAME)
        receipt = state["nodes"]["work"]["receipts"][-1]
        verification = {
            "schema_version": 3,
            "verdict": "reject",
            "work_sha256": receipt["sha256"],
            "docs_sha256": receipt["docs_sha256"],
            "checked_docs": receipt["canonical_docs"],
            "residual_risks": ["One claim is weak"],
            "repair_list": ["Ground the claim"],
        }
        (run / graph.VERIFY_NAME).write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
        response = graph.record(run, "verify", "failed")
        self.assertEqual("work", response["data"]["node"])
        self.assertEqual(1, self.read_json(run / graph.STATE_NAME)["verification_repairs"])

    def test_verifier_reject_cannot_be_bypassed_with_self_completion(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs, verification="independent"))
        graph.record(run, "work", "verify")
        state = self.read_json(run / graph.STATE_NAME)
        receipt = state["nodes"]["work"]["receipts"][-1]
        verification = {
            "schema_version": 3,
            "verdict": "reject",
            "work_sha256": receipt["sha256"],
            "docs_sha256": receipt["docs_sha256"],
            "checked_docs": receipt["canonical_docs"],
            "residual_risks": ["Claim needs repair"],
            "repair_list": ["Repair and reverify"],
        }
        (run / graph.VERIFY_NAME).write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
        graph.record(run, "verify", "failed")
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs, verification="self"))
        with self.assertRaisesRegex(graph.GraphError, "independent verify"):
            graph.record(run, "work", "succeeded")

    def test_failed_work_has_only_one_retry(self) -> None:
        run = self.init("bootstrap")
        graph.record(run, "work", "failed")
        graph.retry(run, "work")
        graph.record(run, "work", "failed")
        with self.assertRaisesRegex(graph.GraphError, "Retry limit"):
            graph.retry(run, "work")

    def test_tampered_document_blocks_complete(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs))
        graph.record(run, "work", "succeeded")
        self.write("docs/project/PLAN.md", "# Plan\n\nTampered after receipt.\n")
        with self.assertRaisesRegex(graph.GraphError, "изменились"):
            graph.complete(run)

    def test_new_noncanonical_document_after_receipt_blocks_complete(self) -> None:
        run, docs = self.maintenance()
        self.write_work(run, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(run, "work", "succeeded")
        self.write("README.md", "# Added after work receipt\n")
        with self.assertRaisesRegex(graph.GraphError, "Набор или содержимое документов"):
            graph.complete(run)

    def test_bootstrap_decision_binds_post_answer_scope(self) -> None:
        run = self.init("bootstrap")
        pending = {
            "question": "Which agent contract should be canonical?",
            "recommended": "Keep the narrow root contract",
            "scope": ["AGENTS.md"],
        }
        self.write_work(run, self.decision_payload("bootstrap", "bootstrap-ready", pending))
        graph.record(run, "work", "decision")
        graph.decide(run, "Change only AGENTS.md")
        decision_id = self.read_json(run / graph.STATE_NAME)["decisions"][-1]["id"]
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap", docs, classification="bootstrap-ready", created=docs, decision={"id": decision_id}
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "resolved decision scope"):
            graph.record(run, "work", "succeeded")

    def test_bootstrap_decision_requires_independent_verification(self) -> None:
        run = self.init("bootstrap")
        scope = sorted([
            "AGENTS.md",
            "CONTEXT.md",
            "docs/README.md",
            "docs/agents/domain.md",
            "docs/agents/issue-tracker.md",
            "docs/project/CODEBASE.md",
            "docs/project/ENGINEERING.md",
            "docs/project/FOUNDATION.md",
            "docs/project/PLAN.md",
            "docs/project/PROJECT.md",
            "docs/project/QUALITY.md",
        ])
        pending = {
            "question": "Which initial project authority should be canonical?",
            "recommended": "Use the unified documentation contract",
            "scope": scope,
        }
        self.write_work(run, self.decision_payload("bootstrap", "bootstrap-ready", pending))
        graph.record(run, "work", "decision")
        graph.decide(run, "Use the compact authority")
        decision_id = self.read_json(run / graph.STATE_NAME)["decisions"][-1]["id"]
        docs = self.bootstrap_docs()
        payload = self.work_payload(
            "bootstrap", docs, classification="bootstrap-ready", created=docs, decision={"id": decision_id}
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "independent verify"):
            graph.record(run, "work", "succeeded")

    def test_between_run_canonical_drift_cannot_be_rebaselined_as_no_change(self) -> None:
        _, docs = self.completed_bootstrap()
        target = "docs/project/PROJECT.md"
        self.write(target, "# Product\n\nAn external semantic authority edit happened between runs.\n")
        run = self.init("maintenance", "Audit external documentation drift")
        self.write_work(run, self.work_payload("maintenance", docs, classification="no-change"))
        with self.assertRaisesRegex(graph.GraphError, "delta"):
            graph.record(run, "work", "succeeded")
        payload = self.work_payload(
            "maintenance",
            docs,
            classification="factual",
            changed=[target],
            verification="self",
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "independent verify"):
            graph.record(run, "work", "succeeded")

    def test_between_run_nested_agents_is_validated_before_admission(self) -> None:
        _, docs = self.completed_bootstrap()
        self.write("module/AGENTS.md", "# TODO\n")
        run = self.init("maintenance", "Audit new module instructions")
        path = "module/AGENTS.md"
        payload = self.work_payload(
            "maintenance",
            sorted(docs + [path]),
            classification="factual",
            created=[path],
            verification="independent",
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "TODO|Scope"):
            graph.record(run, "work", "verify")

    def test_preexisting_broken_root_agents_cannot_bootstrap(self) -> None:
        self.write("AGENTS.md", "# TODO\n")
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write("AGENTS.md", "# TODO\n")
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=[path for path in docs if path != "AGENTS.md"],
        )
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "placeholder|Scope"):
            graph.record(run, "work", "succeeded")

    def test_bootstrap_cannot_omit_preexisting_nested_agents(self) -> None:
        self.write("module/AGENTS.md", "# TODO\n")
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(
            run,
            self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs),
        )
        with self.assertRaisesRegex(graph.GraphError, "все обнаруженные AGENTS"):
            graph.record(run, "work", "succeeded")

    def test_v3_status_and_task_delivery_gate_detect_authority_drift(self) -> None:
        self.completed_bootstrap()
        state = graph.project_runtime.load_state(self.root)
        self.assertEqual([], graph.project_runtime.v3_integrity_issues(self.root, state))
        self.write("docs/project/PROJECT.md", "# Product\n\nOut-of-band authority drift.\n")
        state = graph.project_runtime.load_state(self.root)
        self.assertTrue(graph.project_runtime.v3_integrity_issues(self.root, state))
        with self.assertRaises(graph.task_delivery_runtime.TaskError):
            graph.task_delivery_runtime.reject_pending_project_reopen(self.root)

    def test_unknown_shared_maintenance_status_is_fail_closed(self) -> None:
        self.completed_bootstrap()
        project_path = self.root / ".project-start/state.json"
        project = self.read_json(project_path)
        project["maintenance"]["status"] = "future-unknown-state"
        project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "fail-closed"):
            self.init("maintenance")

    def test_completed_historical_run_status_survives_later_run(self) -> None:
        old_run, docs = self.completed_bootstrap()
        new_run = self.init("maintenance", "Refresh project docs")
        self.write_work(new_run, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(new_run, "work", "succeeded")
        graph.complete(new_run)
        self.assertEqual("completed", graph.status(old_run)["status"])

    def test_abandon_releases_drifted_run_for_fresh_init(self) -> None:
        run, _ = self.maintenance("Refresh after change")
        self.write("src/new_module.py", "VALUE = 1\n")
        graph.abandon(run, "Source changed during documentation work")
        project = self.read_json(self.root / ".project-start/state.json")
        self.assertEqual("restart-required", project["maintenance"]["status"])
        self.assertNotIn("active_run", project["maintenance"])
        with self.assertRaises(graph.task_delivery_runtime.TaskError):
            graph.task_delivery_runtime.reject_pending_project_reopen(self.root)
        fresh = self.init("maintenance", "Refresh after change")
        self.assertNotEqual(run, fresh)

    def test_abandon_keeps_task_delivery_blocked_for_unverified_doc_drift(self) -> None:
        run, _ = self.maintenance("Refresh docs")
        original = (self.root / "docs/project/PROJECT.md").read_text(encoding="utf-8")
        self.write("docs/project/PROJECT.md", "# Product\n\nUnverified authority change.\n")
        graph.abandon(run, "Need a fresh documentation baseline")
        maintenance = self.read_json(self.root / ".project-start/state.json")["maintenance"]
        self.assertEqual("restart-required", maintenance["status"])
        self.assertEqual(["docs/project/PROJECT.md"], maintenance["pending_drift"]["changed_docs"])
        with self.assertRaisesRegex(graph.GraphError, "восстанови документы"):
            self.init("maintenance", "Refresh docs")
        self.write("docs/project/PROJECT.md", original)
        fresh = self.init("maintenance", "Refresh docs")
        self.assertNotEqual(run, fresh)

    def test_abandon_cannot_bypass_unresolved_decision(self) -> None:
        run, docs = self.maintenance()
        pending = {
            "question": "Which foundation contract is canonical?",
            "recommended": "Keep compatibility",
            "scope": ["docs/project/FOUNDATION.md"],
        }
        self.write_work(
            run,
            self.work_payload("maintenance", docs, classification="semantic", decision=pending),
        )
        graph.record(run, "work", "decision")
        with self.assertRaisesRegex(graph.GraphError, "существенное решение"):
            graph.abandon(run, "Try another run")
        with self.assertRaises(graph.task_delivery_runtime.TaskError):
            graph.task_delivery_runtime.reject_pending_project_reopen(self.root)

    def test_task_obligation_keeps_verifier_risk_across_abandon(self) -> None:
        handoff_rel, _, docs = self.task_delivery_obligation("TD-VERIFY")
        payload = graph.initialize(
            str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
        )
        run = Path(payload["data"]["run"])
        self.write_work(
            run,
            self.work_payload("maintenance", docs, classification="no-change", verification="independent"),
        )
        graph.record(run, "work", "verify")
        state = self.read_json(run / graph.STATE_NAME)
        work = state["nodes"]["work"]["receipts"][-1]
        verification = {
            "schema_version": 3,
            "verdict": "reject",
            "work_sha256": work["sha256"],
            "docs_sha256": work["docs_sha256"],
            "checked_docs": work["canonical_docs"],
            "residual_risks": ["Authority remains uncertain"],
            "repair_list": ["Recheck the authority"],
        }
        (run / graph.VERIFY_NAME).write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
        graph.record(run, "verify", "failed")
        graph.abandon(run, "Restart after verifier rejection")
        replacement = graph.initialize(
            str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
        )
        replacement_run = Path(replacement["data"]["run"])
        (replacement_run / graph.STATE_NAME).unlink()
        self.assertEqual("recovered", graph.recover(str(self.root))["status"])
        replacement = graph.initialize(
            str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
        )
        replacement_run = Path(replacement["data"]["run"])
        self.write_work(
            replacement_run,
            self.work_payload("maintenance", docs, classification="no-change"),
        )
        with self.assertRaisesRegex(graph.GraphError, "обязана снова пройти independent verify"):
            graph.record(replacement_run, "work", "succeeded")

    def test_processed_task_handoff_is_not_reopened_by_repeated_complete(self) -> None:
        handoff_rel, task_state, docs = self.task_delivery_obligation("TD-PROCESSED")
        payload = graph.initialize(
            str(self.root), "maintenance", "Task completed", "task-delivery", handoff_rel
        )
        run = Path(payload["data"]["run"])
        self.write_work(run, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        task = self.read_json(task_state)
        graph.task_delivery_runtime.mark_project_start_maintenance_required(
            self.root, task_state, task
        )
        maintenance = self.read_json(self.root / ".project-start/state.json")["maintenance"]
        self.assertEqual("operational", maintenance["status"])
        self.assertEqual("TD-PROCESSED", maintenance["processed_handoffs"][-1]["task_id"])

    def test_legacy_missing_canonical_doc_cannot_be_silently_retired(self) -> None:
        state = graph.project_runtime.new_state("docs/project", None, None)
        state["phase"] = "execution"
        state["maintenance"] = {"status": "operational", "history": []}
        graph.project_runtime.save_project_state(self.root, state, require_absent=True)
        self.write(
            "AGENTS.md",
            "# Agent map\n\n## Scope\nWhole repository scope and canonical documentation.\n\n"
            "## Map\nStart with docs/README.md and follow the canonical project map.\n\n"
            "## Commands\nRun the declared checks before completion.\n\n"
            "## Boundaries\nPreserve project authority and user-owned work.\n\n"
            "## Agent skills\nDomain layout: docs/agents/domain.md. "
            "Issue tracker: docs/agents/issue-tracker.md.\n",
        )
        payload = graph.initialize(
            str(self.root), "maintenance", "Adopt legacy project", "manual", None
        )
        run = Path(payload["data"]["run"])
        run_state = self.read_json(run / graph.STATE_NAME)
        missing = "docs/project/DECISIONS.md"
        self.assertIn(missing, run_state["baseline_canonical"])
        self.write_work(
            run,
            self.work_payload("maintenance", ["AGENTS.md"], classification="no-change"),
        )
        with self.assertRaisesRegex(graph.GraphError, "ранее канонический"):
            graph.record(run, "work", "succeeded")

    def test_noncanonical_changelog_does_not_become_authority(self) -> None:
        self.write("CHANGELOG.md", "# Changelog\n\nInitial release.\n")
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        self.write_work(run, self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs))
        graph.record(run, "work", "succeeded")
        graph.complete(run)
        maintenance = self.init("maintenance", "No authority change")
        self.write_work(maintenance, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(maintenance, "work", "succeeded")

    def test_recover_rolls_shared_state_back_to_durable_run(self) -> None:
        run = self.init("bootstrap")
        project_path = self.root / ".project-start/state.json"
        project = self.read_json(project_path)
        project["maintenance"]["status"] = "blocked"
        project["maintenance"]["active_run"]["node"] = "verify"
        project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        self.assertEqual("recovered", graph.recover(str(self.root))["status"])
        self.assertEqual("work", graph.ready(run)["data"]["node"])

    def test_recover_finalizes_committed_complete_after_later_source_change(self) -> None:
        run, docs = self.maintenance()
        self.write_work(run, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(run, "work", "succeeded")
        precomplete = self.read_json(run / graph.STATE_NAME)
        graph.complete(run)
        (run / graph.STATE_NAME).write_text(json.dumps(precomplete, indent=2) + "\n", encoding="utf-8")
        self.write("src/after-complete.py", "VALUE = 2\n")
        self.assertEqual("recovered", graph.recover(str(self.root))["status"])
        self.assertEqual("completed", graph.status(run)["status"])

    def test_recover_releases_interrupted_initial_activation(self) -> None:
        run = self.init("bootstrap")
        (run / graph.STATE_NAME).unlink()
        self.assertEqual("recovered", graph.recover(str(self.root))["status"])
        project = self.read_json(self.root / ".project-start/state.json")
        self.assertEqual("not-ready", project["maintenance"]["status"])
        replacement = self.init("bootstrap")
        self.assertNotEqual(run, replacement)

    def test_recover_rejects_mismatched_graph_identity(self) -> None:
        run = self.init("bootstrap")
        state = self.read_json(run / graph.STATE_NAME)
        state["graph_sha256"] = "0" * 64
        (run / graph.STATE_NAME).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "неподдерживаем"):
            graph.recover(str(self.root))

    def test_started_v3_4_run_keeps_legacy_coverage_contract(self) -> None:
        run = self.init("bootstrap")
        state_path = run / graph.STATE_NAME
        state = self.read_json(state_path)
        state["graph_version"] = "3.4.0"
        state["graph_sha256"] = dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)["3.4.0"]
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        contract = graph.ready(run)["data"]["documentation_contract"]
        self.assertEqual(graph.LEGACY_BOOTSTRAP_COVERAGE, set(contract["coverage"]))
        self.assertNotIn("engineering_standard_providers", contract)
        docs = self.bootstrap_docs()
        (self.root / "docs/project/ENGINEERING.md").unlink()
        docs.remove("docs/project/ENGINEERING.md")
        map_path = self.root / "docs/README.md"
        map_path.write_text(
            map_path.read_text(encoding="utf-8").replace(
                "- [Engineering standard](project/ENGINEERING.md)\n", ""
            ),
            encoding="utf-8",
        )
        payload = self.work_payload(
            "bootstrap",
            docs,
            classification="bootstrap-ready",
            created=docs,
        )
        payload["coverage"].pop("engineering_standard")
        self.write_work(run, payload)
        graph.record(run, "work", "succeeded")

    def test_init_reclaims_only_empty_unreferenced_orphan(self) -> None:
        contract = graph.graph_contract()
        run_id = graph.run_id_for(
            self.root,
            "bootstrap",
            "Prepare project",
            None,
            contract["graph_version"],
            graph.repository_sha(self.root),
            "manual",
            "",
            "",
        )
        orphan = self.root / graph.RUNTIME_REL / run_id
        orphan.mkdir(parents=True)
        payload = graph.initialize(
            str(self.root), "bootstrap", "Prepare project", "manual", None
        )
        self.assertEqual(orphan, Path(payload["data"]["run"]))
        self.assertTrue((orphan / graph.STATE_NAME).is_file())

    def test_concurrent_init_loser_can_retry_after_winner_completes(self) -> None:
        barrier = threading.Barrier(2)
        original = graph.repository_sha

        def synchronized_repository_sha(root: Path, *, include_docs: bool = True) -> str:
            value = original(root, include_docs=include_docs)
            if include_docs:
                barrier.wait(timeout=5)
            return value

        def start(reason: str) -> tuple[str, object]:
            try:
                return "ok", graph.initialize(str(self.root), "auto", reason, "manual", None)
            except graph.GraphError as exc:
                return "error", exc

        with mock.patch.object(graph, "repository_sha", side_effect=synchronized_repository_sha):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(start, ("Request A", "Request B")))
        winners = [value for status, value in results if status == "ok"]
        losers = [value for status, value in results if status == "error"]
        self.assertEqual(1, len(winners))
        self.assertEqual(1, len(losers))
        winner = Path(winners[0]["data"]["run"])
        docs = self.bootstrap_docs()
        self.write_work(
            winner,
            self.work_payload("bootstrap", docs, classification="bootstrap-ready", created=docs),
        )
        graph.record(winner, "work", "succeeded")
        graph.complete(winner)
        # The loser is identified by the winner's deterministic reason recorded in run state.
        winner_reason = self.read_json(winner / graph.STATE_NAME)["reason"]
        losing_reason = "Request B" if winner_reason == "Request A" else "Request A"
        retry = graph.initialize(str(self.root), "auto", losing_reason, "manual", None)
        self.assertEqual("maintenance", retry["data"]["mode"])

    def test_task_admission_lock_serializes_project_activation(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        initialized = threading.Event()
        outcomes: list[object] = []

        def hold_task_admission() -> None:
            with graph.task_delivery_runtime.admission_guard(self.root):
                entered.set()
                release.wait(timeout=5)

        def start_project() -> None:
            try:
                outcomes.append(
                    graph.initialize(
                        str(self.root), "bootstrap", "Prepare project", "manual", None
                    )
                )
            finally:
                initialized.set()

        holder = threading.Thread(target=hold_task_admission)
        starter = threading.Thread(target=start_project)
        holder.start()
        self.assertTrue(entered.wait(timeout=5))
        starter.start()
        self.assertFalse(initialized.wait(timeout=0.2))
        release.set()
        holder.join(timeout=5)
        starter.join(timeout=5)
        self.assertTrue(initialized.is_set())
        self.assertEqual("running", outcomes[0]["status"])

    def test_pending_task_obligation_marker_blocks_admission(self) -> None:
        marker = (
            self.root
            / ".codex/task-delivery/old-task"
            / graph.task_delivery_runtime.PROJECT_START_OBLIGATION_MARKER
        )
        marker.parent.mkdir(parents=True)
        marker.write_text('{"schema_version": 1}\n', encoding="utf-8")
        with self.assertRaises(graph.task_delivery_runtime.TaskError):
            graph.task_delivery_runtime.reject_pending_project_reopen(self.root)

    def test_restart_nonce_never_returns_pre_abandon_run(self) -> None:
        _, docs = self.completed_bootstrap()
        first = self.init("maintenance", "Repeatable refresh")
        graph.abandon(first, "Restart cleanly")
        second = self.init("maintenance", "Repeatable refresh")
        self.write_work(second, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(second, "work", "succeeded")
        graph.complete(second)
        repeated = self.init("maintenance", "Repeatable refresh")
        self.assertNotEqual(first, repeated)
        self.assertEqual(second, repeated)

    def test_scheduled_cycle_creates_a_fresh_run(self) -> None:
        _, docs = self.completed_bootstrap()
        first_payload = graph.initialize(
            str(self.root), "maintenance", "Scheduled audit", "scheduled", None, "cycle-a"
        )
        first = Path(first_payload["data"]["run"])
        self.write_work(first, self.work_payload("maintenance", docs, classification="no-change"))
        graph.record(first, "work", "succeeded")
        graph.complete(first)
        second_payload = graph.initialize(
            str(self.root), "maintenance", "Scheduled audit", "scheduled", None, "cycle-b"
        )
        self.assertNotEqual(first, Path(second_payload["data"]["run"]))

    def test_path_escape_and_explorer_overflow_are_rejected(self) -> None:
        run = self.init("bootstrap")
        docs = self.bootstrap_docs()
        payload = self.work_payload("bootstrap", docs + ["../outside.md"], classification="bootstrap-ready", created=docs, agents=["explorer:a", "explorer:b", "explorer:c"])
        self.write_work(run, payload)
        with self.assertRaisesRegex(graph.GraphError, "лимит explorer"):
            graph.record(run, "work", "succeeded")

    def test_runtime_is_gitignored(self) -> None:
        self.init("bootstrap")
        self.assertEqual("*\n", (self.root / ".agent-graphs/.gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
