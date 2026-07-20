#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("research_graph.py")
SPEC = importlib.util.spec_from_file_location("research_graph", MODULE_PATH)
assert SPEC and SPEC.loader
graph = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graph)


class ResearchGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        payload = graph.initialize("What is supported?", str(self.workspace), "report.md")
        self.run_dir = Path(payload["data"]["run_dir"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_artifact(self, node: str, value: object) -> Path:
        contract = graph.graph_contract()
        path = self.run_dir / contract["nodes"][node]["artifact"]
        if isinstance(value, (dict, list)):
            path.write_text(json.dumps(value), encoding="utf-8")
        else:
            path.write_text(str(value), encoding="utf-8")
        return path

    def write_report(self, sources: list[str] | None = None) -> Path:
        sources = sources or ["https://example.com/source"]
        citations = []
        for index, source in enumerate(sources, start=1):
            citations.append(f"[Source {index}]({source})")
        report = self.workspace / "report.md"
        report.write_text(
            "# Answer\n\n"
            + "A direct evidence-backed conclusion with enough decision context. " * 4
            + " ".join(citations)
            + "\n\n## Confidence and gaps\n\nHigh confidence; no decision-relevant gaps.",
            encoding="utf-8",
        )
        return report

    def valid_work(
        self,
        *,
        mode: str = "fast",
        reason: str | None = None,
        capabilities: list[str] | None = None,
        agents: list[str] | None = None,
        sources: list[str] | None = None,
        verification: str = "self",
        confidence: str = "high",
        gaps: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "schema_version": 2,
            "mode": mode,
            "reason": reason or ("default narrow research" if mode == "fast" else "multiple branches"),
            "capabilities": capabilities or ["research", "native-web"],
            "agents": agents or [],
            "sources": sources or ["https://example.com/source"],
            "verification": verification,
            "confidence": confidence,
            "gaps": gaps or [],
        }

    def record_work(self, value: dict[str, object] | None = None, outcome: str = "succeeded") -> None:
        work = value or self.valid_work()
        path = self.write_artifact("work", work)
        graph.record_node(self.run_dir, "work", str(path), outcome)

    def advance_to_verify(self) -> None:
        self.write_report()
        self.record_work(
            self.valid_work(
                mode="deep",
                reason="high-stakes decision",
                verification="independent",
            ),
            "verify",
        )

    def valid_verification(self, verdict: str = "pass") -> dict[str, object]:
        payload: dict[str, object] = {
            "verdict": verdict,
            "report_sha256": graph.sha256_file(self.workspace / "report.md"),
            "checked_claims": 1,
            "residual_risks": [],
        }
        if verdict == "reject":
            payload["repair_list"] = ["Narrow the unsupported claim"]
            payload["residual_risks"] = ["unsupported claim"]
        return payload

    def record_verification(self, verdict: str = "pass") -> None:
        outcome = "succeeded" if verdict == "pass" else "rejected"
        artifact = self.write_artifact("verify", self.valid_verification(verdict))
        graph.record_node(self.run_dir, "verify", str(artifact), outcome)

    def test_graph_contract_is_three_durable_states(self) -> None:
        contract = graph.graph_contract()
        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(set(contract["nodes"]), {"work", "verify", "complete"})
        self.assertEqual(contract["limits"]["fast"]["max_parallel_scouts"], 0)

    def test_init_is_idempotent(self) -> None:
        second = graph.initialize("What is supported?", str(self.workspace), "report.md")
        self.assertEqual(second["data"]["run_dir"], str(self.run_dir))
        self.assertIn("resumed", second["summary"])

    def test_explicit_deep_run_gets_separate_state(self) -> None:
        deep = graph.initialize("What is supported?", str(self.workspace), "report.md", "deep")
        self.assertNotEqual(deep["data"]["run_dir"], str(self.run_dir))
        deep_state = graph.load_state(Path(deep["data"]["run_dir"]))
        self.assertEqual(deep_state["requested_depth"], "deep")
        self.assertEqual(deep_state["mode"], "deep")

    def test_concurrent_init_converges_on_one_state(self) -> None:
        concurrent_workspace = Path(self.temp.name) / "concurrent"
        concurrent_workspace.mkdir()

        def initialize() -> dict[str, object]:
            return graph.initialize("Concurrent question", str(concurrent_workspace), "report.md")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: initialize(), range(2)))
        run_dirs = {str(item["data"]["run_dir"]) for item in results}
        self.assertEqual(len(run_dirs), 1)
        state = graph.load_state(Path(run_dirs.pop()))
        self.assertEqual(state["current"], "work")
        self.assertEqual(state["nodes"]["work"]["attempts"], 0)

    def test_init_keeps_target_git_status_clean(self) -> None:
        repository = Path(self.temp.name) / "git-workspace"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        graph.initialize("Git cleanliness", str(repository), "report.md")
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repository, check=True, text=True, capture_output=True
        )
        self.assertEqual(status.stdout, "")

    def test_ready_describes_one_native_fast_loop(self) -> None:
        ready = graph.ready_node(self.run_dir)
        self.assertEqual(ready["data"]["node"], "work")
        self.assertEqual(ready["data"]["execution"], "one native root-agent loop")
        self.assertEqual(ready["data"]["default_mode"], "fast")
        self.assertEqual(ready["data"]["budgets"]["max_parallel_scouts"], 0)

    def test_workspace_relative_artifact_path_is_accepted(self) -> None:
        self.write_report()
        artifact = self.write_artifact("work", self.valid_work())
        relative = artifact.relative_to(self.workspace)
        graph.record_node(self.run_dir, "work", str(relative), "succeeded")
        self.assertEqual(graph.load_state(self.run_dir)["current"], "complete")

    def test_rejects_output_escape(self) -> None:
        with self.assertRaises(graph.GraphError):
            graph.initialize("escape", str(self.workspace), "../outside.md")

    def test_rejects_out_of_order_transition(self) -> None:
        artifact = self.write_artifact("verify", {"verdict": "pass"})
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "verify", str(artifact), "succeeded")

    def test_rejects_invalid_json_artifact(self) -> None:
        self.write_report()
        artifact = self.write_artifact("work", "not-json")
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_rejects_receipt_symlink_escape(self) -> None:
        outside = self.workspace / "outside-receipts"
        outside.mkdir()
        (self.run_dir / "receipts").symlink_to(outside, target_is_directory=True)
        self.write_report()
        artifact = self.write_artifact("work", self.valid_work())
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_failed_node_can_retry_with_bound(self) -> None:
        failed = self.write_artifact("work", {"error": "source unavailable"})
        graph.record_node(self.run_dir, "work", str(failed), "failed")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "blocked")
        graph.retry_node(self.run_dir, "use the native web fallback")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "running")

    def test_retry_bound_is_enforced(self) -> None:
        for retry in range(2):
            failed = self.write_artifact("work", {"error": f"failure {retry}"})
            graph.record_node(self.run_dir, "work", str(failed), "failed")
            graph.retry_node(self.run_dir, f"fallback {retry}")
        failed = self.write_artifact("work", {"error": "failure final"})
        graph.record_node(self.run_dir, "work", str(failed), "failed")
        with self.assertRaises(graph.GraphError):
            graph.retry_node(self.run_dir, "too many")

    def test_fast_path_completes_without_verifier(self) -> None:
        self.write_report()
        self.record_work()
        state = graph.load_state(self.run_dir)
        self.assertEqual(state["current"], "complete")
        self.assertFalse(state["verification_required"])
        self.assertEqual(state["nodes"]["verify"]["attempts"], 0)
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "ok", checked)
        self.assertEqual(checked["data"]["mode"], "fast")
        self.assertFalse(checked["data"]["verification_required"])
        completed = graph.complete_run(self.run_dir)
        self.assertEqual(completed["status"], "ok")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "completed")
        rechecked = graph.check_report(self.run_dir)
        self.assertEqual(rechecked["status"], "ok")
        self.assertEqual(rechecked["next_actions"], [])
        self.assertIn("Completed", rechecked["summary"])

    def test_fast_path_rejects_internal_agents(self) -> None:
        self.write_report()
        artifact = self.write_artifact(
            "work", self.valid_work(agents=["research_scout"])
        )
        with self.assertRaisesRegex(graph.GraphError, "Fast mode"):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_fast_source_bound_requires_deep_mode(self) -> None:
        sources = [f"https://example.com/source-{index}" for index in range(7)]
        self.write_report(sources)
        artifact = self.write_artifact("work", self.valid_work(sources=sources))
        with self.assertRaisesRegex(graph.GraphError, "source limit"):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_explicit_deep_run_cannot_record_fast_work(self) -> None:
        deep = graph.initialize("Deep question", str(self.workspace), "deep-report.md", "deep")
        self.run_dir = Path(deep["data"]["run_dir"])
        (self.workspace / "deep-report.md").write_text(
            "# Answer\n\n" + "Deep evidence-backed answer. " * 8
            + "[Source](https://example.com/source).",
            encoding="utf-8",
        )
        artifact = self.write_artifact("work", self.valid_work())
        with self.assertRaisesRegex(graph.GraphError, "explicitly deep"):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_deep_work_allows_three_scouts(self) -> None:
        self.write_report()
        work = self.valid_work(
            mode="deep",
            agents=["research_scout", "research_scout", "research_scout"],
        )
        self.record_work(work)
        state = graph.load_state(self.run_dir)
        self.assertEqual(state["mode"], "deep")
        self.assertEqual(state["agents_used"].count("research_scout"), 3)
        self.assertEqual(state["current"], "complete")

    def test_deep_work_rejects_four_scouts(self) -> None:
        self.write_report()
        work = self.valid_work(mode="deep", agents=["research_scout"] * 4)
        artifact = self.write_artifact("work", work)
        with self.assertRaisesRegex(graph.GraphError, "scout limit"):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_verify_outcome_requires_deep_independent_work(self) -> None:
        self.write_report()
        artifact = self.write_artifact("work", self.valid_work(verification="independent"))
        with self.assertRaisesRegex(graph.GraphError, "requires deep mode"):
            graph.record_node(self.run_dir, "work", str(artifact), "verify")

    def test_independent_work_must_use_verify_outcome(self) -> None:
        self.write_report()
        artifact = self.write_artifact(
            "work", self.valid_work(mode="deep", verification="independent")
        )
        with self.assertRaisesRegex(graph.GraphError, "Record outcome verify"):
            graph.record_node(self.run_dir, "work", str(artifact), "succeeded")

    def test_verifier_report_hash_is_enforced(self) -> None:
        self.advance_to_verify()
        payload = self.valid_verification()
        payload["report_sha256"] = "0" * 64
        artifact = self.write_artifact("verify", payload)
        with self.assertRaisesRegex(graph.GraphError, "report_sha256"):
            graph.record_node(self.run_dir, "verify", str(artifact), "succeeded")

    def test_verification_path_completes(self) -> None:
        self.advance_to_verify()
        self.record_verification()
        state = graph.load_state(self.run_dir)
        self.assertEqual(state["current"], "complete")
        self.assertTrue(state["verification_required"])
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "ok", checked)
        self.assertTrue(checked["data"]["verification_required"])

    def test_one_delta_repair_is_bounded(self) -> None:
        self.advance_to_verify()
        self.record_verification("reject")
        state = graph.load_state(self.run_dir)
        self.assertEqual(state["current"], "work")
        self.assertEqual(state["verification_repairs"], 1)
        self.write_report()
        self.record_work(
            self.valid_work(
                mode="deep",
                reason="delta repair",
                verification="independent",
            ),
            "verify",
        )
        self.record_verification("reject")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "blocked")

    def test_verifier_reject_requires_nonempty_repair_list(self) -> None:
        self.advance_to_verify()
        payload = self.valid_verification("reject")
        payload["repair_list"] = []
        artifact = self.write_artifact("verify", payload)
        with self.assertRaisesRegex(graph.GraphError, "non-empty repair_list"):
            graph.record_node(self.run_dir, "verify", str(artifact), "rejected")

    def test_report_and_declared_sources_must_match(self) -> None:
        self.write_report(["https://unrelated.example/source"])
        self.record_work(self.valid_work())
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "failed")
        self.assertTrue(any("declared" in issue or "report citation" in issue for issue in checked["next_actions"]))

    def test_report_can_include_non_evidence_links(self) -> None:
        self.write_report(
            ["https://example.com/source", "https://extra.example/source"]
        )
        self.record_work(self.valid_work())
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "ok")

    def test_local_source_is_supported(self) -> None:
        local = self.workspace / "truth.md"
        local.write_text("local project truth", encoding="utf-8")
        self.write_report([str(local)])
        self.record_work(
            self.valid_work(
                capabilities=["research", "local-files"],
                sources=[str(local)],
            )
        )
        self.assertEqual(graph.check_report(self.run_dir)["status"], "ok")

    def test_parenthesized_commonmark_url_matches_sources(self) -> None:
        source = "https://example.com/Foo_(bar)"
        self.write_report([source])
        self.record_work(self.valid_work(sources=[source]))
        self.assertEqual(graph.check_report(self.run_dir)["status"], "ok")

    def test_report_tamper_after_work_is_detected(self) -> None:
        report = self.write_report()
        self.record_work()
        report.write_text(report.read_text(encoding="utf-8") + "\nchanged", encoding="utf-8")
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "failed")
        self.assertTrue(any("differs" in issue for issue in checked["next_actions"]))

    def test_completed_report_tamper_is_detected(self) -> None:
        report = self.write_report()
        self.record_work()
        graph.complete_run(self.run_dir)
        report.write_text(report.read_text(encoding="utf-8") + "\nchanged", encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "integrity"):
            graph.complete_run(self.run_dir)

    def test_v1_state_has_actionable_restart_message(self) -> None:
        state_path = self.run_dir / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["schema_version"] = 1
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(graph.GraphError, "retired Research v1"):
            graph.load_state(self.run_dir)


if __name__ == "__main__":
    unittest.main()
