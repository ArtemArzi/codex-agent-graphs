"""Lifecycle restart proofs, separate from ordinary identity admission."""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import test_task_graph as fixtures
import task_graph as graph


class TaskRestartTests(fixtures.TaskGraphTests):
    # Import fixture helpers, not the complete parent test suite.
    def old_run(self, mode="full", version="unrecognized"):
        run = self.initialize(mode=mode)
        plan = self.plan()
        state = self.read(run / graph.STATE_NAME)
        if version == "unrecognized":
            state.update(graph_version="3.0.1-unreleased", graph_sha256="1" * 64)
        else:
            state.update(graph_version=version, graph_sha256=dict(graph.LEGACY_ACTIVE_GRAPH_IDENTITIES)[version])
        graph.atomic_json(run / graph.STATE_NAME, state)
        return run, plan

    def restart(self, run, **kwargs):
        return graph.restart(run, "Owner explicitly replaces this unfinished instance", True, **kwargs)

    def addressed(self, state):
        record = state["restart_inheritance"]
        constraints = self.read(self.root / record["path"])
        return {"sha256": record["sha256"], "decisions": constraints["decisions"],
                "repair_requirements": [r for item in constraints["rejected_reviews"] for r in item["repair_list"]]}

    def test_restart_unknown_identity_preserves_old_plan_code_and_fresh_successor(self):
        run, plan = self.old_run()
        before = (run / graph.STATE_NAME).read_bytes()
        original = plan.read_bytes()
        code = (self.root / "src/app.py").read_bytes()
        with self.assertRaises(graph.GraphProvenanceError):
            graph.load_run_state(run)
        payload = self.restart(run)
        successor = Path(payload["data"]["run"])
        state = graph.load_run_state(successor)
        self.assertEqual("3.9.2", state["graph_version"])
        self.assertEqual("full", state["mode"])
        self.assertEqual("retired", self.read(run / graph.STATE_NAME)["status"])
        self.assertEqual(before, (run / "restart/pre-run-state.json").read_bytes())
        self.assertEqual(original, plan.read_bytes())
        self.assertEqual(code, (self.root / "src/app.py").read_bytes())
        self.assertTrue(all(not n["receipts"] for n in state["nodes"].values()))
        self.assertEqual({}, state["task_state_snapshot"]["checkpoints"])
        self.assertTrue(self.restart(run)["data"]["idempotent"])
        self.assertEqual(2, len(list((self.root / graph.RUNS_REL).iterdir())))

    def test_restart_decisions_repairs_and_verification_are_mandatory(self):
        run, _ = self.old_run(mode="plan")
        state = self.read(run / graph.STATE_NAME)
        decision = {"id": "owner-choice", "question": "Which behavior is intended?", "answer": "Keep exact business behavior", "scope": ["src/app.py"], "source": "human owner", "resolved_at": "2026-10-06T00:00:00+00:00"}
        state["decisions"] = [decision]
        state["verification_required"] = True
        artifact = run / "receipts/verify-1.json"
        graph.atomic_json(artifact, {"verdict": "reject", "repair_list": ["Verify exact business decision against the actual source."]})
        state["nodes"]["verify"]["receipts"] = [{"path": str(artifact), "sha256": graph.sha256_file(artifact), "outcome": "failed"}]
        graph.atomic_json(run / graph.STATE_NAME, state)
        successor = Path(self.restart(run)["data"]["run"])
        fresh = graph.load_run_state(successor)
        self.assertTrue(fresh["verification_required"])
        self.assertEqual([decision], self.addressed(fresh)["decisions"])
        self.plan(fresh["task_id"])
        payload = self.work_payload(successor)
        with self.assertRaisesRegex(graph.GraphError, "inherited"):
            graph.validate_work(fresh, payload, "verify", successor)
        payload["restart_constraints"] = self.addressed(fresh)
        with self.assertRaises(graph.GraphError):
            graph.validate_work(fresh, payload, "succeeded", successor)
        self.write_work(successor, payload)
        graph.record(successor, "work", "verify")
        verify = self.verify_payload(successor)
        with self.assertRaisesRegex(graph.GraphError, "inherited"):
            graph.validate_verification(graph.load_run_state(successor), verify, "succeeded")
        verify["restart_constraints"] = self.addressed(fresh)
        self.write_verify(successor, verify)
        graph.record(successor, "verify", "succeeded")
        graph.complete(successor)
        self.assertEqual("completed", graph.load_run_state(successor)["status"])
        # Plan-to-implement admission must not reset carried verification/constraints.
        admitted = graph.initialize(str(self.root), "implement", fresh["task_id"], "Same intended outcome", "The same accepted intended business behavior", fresh["plan_path"], fresh["profile"])
        implement_state = graph.load_run_state(Path(admitted["data"]["run"]))
        self.assertTrue(implement_state["verification_required"])
        self.assertEqual(fresh["restart_inheritance"], implement_state["restart_inheritance"])

    def test_restart_interrupted_retirement_blocks_init_legacy_recover_then_resumes(self):
        run, _ = self.old_run()
        atomic = graph.atomic_bytes
        def interrupt(target, content):
            if target == graph.task_state_path(self.root, "TD-1"):
                raise OSError("simulated interruption after old run retirement")
            atomic(target, content)
        with mock.patch.object(graph, "atomic_bytes", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.restart(run)
        self.assertEqual("pending", self.read(self.root / graph.RESTART_MARKER_REL)["status"])
        self.assertEqual("retired", self.read(run / graph.STATE_NAME)["status"])
        with self.assertRaisesRegex(graph.legacy.TaskError, "Restart"):
            self.initialize(task_id="other-task")
        with self.assertRaisesRegex(graph.legacy.TaskError, "Restart"):
            graph.legacy.cmd_recover_lock(type("Args", (), {"root": str(self.root), "task_id": "TD-1", "apply": True})())
        self.assertEqual("restarted", self.restart(run)["status"])
        self.assertEqual("completed", self.read(self.root / graph.RESTART_MARKER_REL)["status"])

    def test_restart_interrupted_target_tamper_and_source_drift_do_not_overwrite(self):
        for tamper in ("target", "source"):
            with self.subTest(tamper=tamper):
                run, _ = self.old_run() if tamper == "target" else (run, None)
                atomic = graph.atomic_bytes
                def interrupt(target, content):
                    if target == graph.task_state_path(self.root, "TD-1"):
                        raise OSError("simulated interruption")
                    atomic(target, content)
                if tamper == "target":
                    with mock.patch.object(graph, "atomic_bytes", side_effect=interrupt):
                        with self.assertRaises(OSError):
                            self.restart(run)
                    task = graph.task_state_path(self.root, "TD-1")
                    original = task.read_bytes()
                    task.write_bytes(b'{"external": "edit"}\n')
                    with self.assertRaisesRegex(graph.GraphError, "preimage"):
                        self.restart(run)
                    self.assertEqual(b'{"external": "edit"}\n', task.read_bytes())
                    task.write_bytes(original)
                else:
                    self.write("src/app.py", "EXTERNAL = 42\n")
                    with self.assertRaisesRegex(graph.GraphError, "basis"):
                        self.restart(run)
                    self.assertEqual("pending", self.read(self.root / graph.RESTART_MARKER_REL)["status"])

    def test_restart_rejects_unresolved_obligation_collision_symlink_before_retirement(self):
        run, plan = self.old_run()
        before = (run / graph.STATE_NAME).read_bytes()
        with self.assertRaises(graph.GraphError):
            graph.restart(run, "Explicit requested replacement", False)
        with self.assertRaises(graph.GraphError):
            self.restart(run, successor_task_id="TD-1")
        self.write("docs/tasks/collision/PLAN.md", "external plan")
        with self.assertRaisesRegex(graph.GraphError, "collision"):
            self.restart(run, successor_task_id="collision")
        plan.unlink()
        plan.symlink_to(self.root / "src/app.py")
        with self.assertRaises(graph.snapshots.SnapshotError):
            self.restart(run)
        plan.unlink()
        self.plan()
        state = self.read(run / graph.STATE_NAME)
        state["decisions"] = [{"question": "Open business decision", "answer": None}]
        graph.atomic_json(run / graph.STATE_NAME, state)
        with self.assertRaisesRegex(graph.GraphError, "unresolved"):
            self.restart(run)
        (run / graph.STATE_NAME).write_bytes(before)
        marker = graph.legacy.obligation_marker(self.root, "TD-1")
        graph.atomic_json(marker, {"status": "pending"})
        with self.assertRaises(graph.legacy.TaskError):
            self.restart(run)
        self.assertEqual(before, (run / graph.STATE_NAME).read_bytes())

    def test_restart_scope_outside_old_region_normalized_only_in_copy(self):
        run, plan = self.old_run(version="3.0.0")
        text = plan.read_text()
        scope = "<!-- task-delivery:scope\nsrc/app.py\n-->"
        plan.write_text(text.replace(scope, "").replace("## Plan review", scope + "\n\n## Plan review"))
        original = plan.read_bytes()
        successor = Path(self.restart(run)["data"]["run"])
        newplan = self.root / graph.load_run_state(successor)["plan_path"]
        graph.validate_plan(newplan)
        self.assertEqual(original, plan.read_bytes())
        self.assertEqual(["src/app.py"], graph.snapshots.parse_scope(newplan.read_text()))

    def test_restart_successive_operations_roll_marker_and_keep_prior_idempotence(self):
        oldrun, _ = self.old_run()
        first = Path(self.restart(oldrun)["data"]["run"])
        second = Path(self.restart(first)["data"]["run"])
        self.assertNotEqual(first, second)
        self.assertEqual(str(first), self.read(self.root / graph.RESTART_MARKER_REL)["source_run"])
        self.assertEqual(str(first), self.restart(oldrun)["data"]["run"])
        self.assertTrue(self.restart(oldrun)["data"]["idempotent"])
        self.assertEqual(3, len(list((self.root / graph.RUNS_REL).iterdir())))

    def test_restart_chain_keeps_decisions_repairs_and_mandatory_verification(self):
        oldrun, _ = self.old_run()
        state = self.read(oldrun / graph.STATE_NAME)
        decision = {"question": "Preserve original business behavior?", "answer": "Keep it exactly", "resolved_at": "2026-10-06", "scope": ["src/app.py"], "source": "owner"}
        state["decisions"] = [decision]
        rejected = oldrun / "receipts/verify-1.json"
        graph.atomic_json(rejected, {"verdict": "reject", "repair_list": ["Check the original failure before acceptance."]})
        state["nodes"]["verify"]["receipts"] = [{"path": str(rejected), "sha256": graph.sha256_file(rejected), "outcome": "failed"}]
        graph.atomic_json(oldrun / graph.STATE_NAME, state)
        first = Path(self.restart(oldrun)["data"]["run"])
        second = Path(self.restart(first)["data"]["run"])
        inherited = self.addressed(graph.load_run_state(second))
        self.assertEqual([decision], inherited["decisions"])
        self.assertEqual(["Check the original failure before acceptance."], inherited["repair_requirements"])
        self.assertTrue(graph.load_run_state(second)["verification_required"])
        self.assertTrue(all(not node["receipts"] for node in graph.load_run_state(second)["nodes"].values()))

    def test_restart_live_task_lock_and_captured_scope_change_rejected(self):
        oldrun, plan = self.old_run()
        before = (oldrun / graph.STATE_NAME).read_bytes()
        lock = graph.legacy.lock_path(self.root, "TD-1")
        lock.mkdir()
        graph.atomic_json(lock / "owner.json", {"pid": __import__("os").getpid()})
        with self.assertRaisesRegex(graph.legacy.TaskError, "другой процесс"):
            self.restart(oldrun)
        self.assertEqual(before, (oldrun / graph.STATE_NAME).read_bytes())
        (lock / "owner.json").unlink()
        lock.rmdir()
        state = self.read(oldrun / graph.STATE_NAME)
        state["scope_authority"] = {"plan_digest": graph.plan_digest(plan), "scope": ["src/app.py"]}
        graph.atomic_json(oldrun / graph.STATE_NAME, state)
        plan.write_text(plan.read_text().replace("src/app.py\n-->", "src/other.py\n-->"))
        with self.assertRaisesRegex(graph.GraphError, "captured scope"):
            self.restart(oldrun)
        self.assertFalse((self.root / graph.RESTART_MARKER_REL).exists())

    def test_restart_preparation_and_final_marker_interruptions_are_resumable(self):
        oldrun, _ = self.old_run()
        atomic_bytes = graph.atomic_bytes
        def fail_preparation(target, content):
            if target.name == "write-2.bin":
                raise OSError("preparation interruption")
            atomic_bytes(target, content)
        with mock.patch.object(graph, "atomic_bytes", side_effect=fail_preparation):
            with self.assertRaises(OSError):
                self.restart(oldrun)
        self.assertFalse((self.root / graph.RESTART_MARKER_REL).exists())
        self.assertEqual("running", self.read(oldrun / graph.STATE_NAME)["status"])
        atomic_json = graph.atomic_json
        def fail_completed_marker(target, value):
            if target == self.root / graph.RESTART_MARKER_REL and value.get("status") == "completed":
                raise OSError("completed marker interruption")
            atomic_json(target, value)
        with mock.patch.object(graph, "atomic_json", side_effect=fail_completed_marker):
            with self.assertRaises(OSError):
                self.restart(oldrun)
        operation = self.read(oldrun / "restart/operation.json")
        successor = self.root / operation["successor_run"]
        self.assertTrue((successor / graph.STATE_NAME).is_file())
        with self.assertRaisesRegex(graph.legacy.TaskError, "Restart"):
            graph.load_run_state(successor)
        self.assertEqual(str(successor), self.restart(oldrun)["data"]["run"])

    def test_restart_pending_staged_and_marker_tamper_refuse_overwrite(self):
        oldrun, _ = self.old_run()
        atomic = graph.atomic_bytes
        def fail_index(target, content):
            if target == graph.task_state_path(self.root, "TD-1"):
                raise OSError("index interruption")
            atomic(target, content)
        with mock.patch.object(graph, "atomic_bytes", side_effect=fail_index):
            with self.assertRaises(OSError):
                self.restart(oldrun)
        staged = oldrun / "restart/write-9.bin"
        content = staged.read_bytes()
        staged.write_bytes(b"external tampering")
        with self.assertRaisesRegex(graph.GraphError, "staged bytes"):
            self.restart(oldrun)
        staged.write_bytes(content)
        marker = self.root / graph.RESTART_MARKER_REL
        value = self.read(marker)
        value["operation_sha256"] = "a" * 64
        graph.atomic_json(marker, value)
        with self.assertRaisesRegex(graph.GraphError, "tampered"):
            self.restart(oldrun)
        self.assertEqual("pending", self.read(marker)["status"])

    def test_restart_actual_historical_30_constructor_shape(self):
        # Captured by executing the released constructor itself. A fixture does
        # not depend on Git history or an installed skill having a checkout.
        fixture = json.loads((graph.SKILL_DIR / "assets/legacy-v3.0-restart-fixture.json").read_text())
        for relative, content in fixture["files"].items():
            self.write(relative, content.replace("__ROOT__", str(self.root)))
        oldrun = self.root / fixture["source_run"]
        oldstate = self.read(oldrun / graph.STATE_NAME)
        self.assertEqual("3.0.0", oldstate["graph_version"])
        self.assertEqual(fixture["graph_sha256"], oldstate["graph_sha256"])
        self.assertNotIn("control_status", oldstate)
        self.assertNotIn("slices", oldstate)
        successor = Path(self.restart(oldrun)["data"]["run"])
        self.assertEqual("Historical behavior", graph.load_run_state(successor)["task_state_snapshot"]["title"])


def load_tests(loader, tests, pattern):
    import unittest
    return unittest.TestSuite(
        TaskRestartTests(name) for name, method in sorted(TaskRestartTests.__dict__.items())
        if name.startswith("test_") and callable(method)
    )

if __name__ == "__main__":
    import unittest
    unittest.main()
