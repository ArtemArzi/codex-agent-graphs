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

    def write_artifact(self, node: str, value: object | None = None) -> Path:
        contract = graph.graph_contract()
        path = self.run_dir / contract["nodes"][node]["artifact"]
        if isinstance(value, (dict, list)):
            path.write_text(json.dumps(value), encoding="utf-8")
        else:
            path.write_text(str(value or f"artifact for {node}"), encoding="utf-8")
        return path

    def record(self, node: str, outcome: str = "succeeded", value: object | None = None) -> None:
        path = self.write_artifact(node, value)
        graph.record_node(self.run_dir, node, str(path), outcome)

    def advance_to_gap(self) -> None:
        self.record("intake")
        self.record("capability_discovery", value={"tools": ["web"]})
        self.record("plan")
        self.record("collect", value={"branches": []})
        self.record("evidence", value=valid_evidence())
        self.record("reconcile")

    def advance_to_verify(self) -> None:
        self.advance_to_gap()
        self.record("gap_check", "succeeded", {"gaps": []})
        self.record("synthesize", value="draft with sources")

    def test_init_is_idempotent(self) -> None:
        second = graph.initialize("What is supported?", str(self.workspace), "report.md")
        self.assertEqual(second["data"]["run_dir"], str(self.run_dir))
        self.assertIn("resumed", second["summary"])

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
        self.assertEqual(state["current"], "intake")
        self.assertEqual(state["nodes"]["intake"]["attempts"], 0)

    def test_init_keeps_target_git_status_clean(self) -> None:
        repository = Path(self.temp.name) / "git-workspace"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        graph.initialize("Git cleanliness", str(repository), "report.md")
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repository, check=True, text=True, capture_output=True
        )
        self.assertEqual(status.stdout, "")

    def test_workspace_relative_artifact_path_is_accepted(self) -> None:
        artifact = self.write_artifact("intake")
        workspace_relative = artifact.relative_to(self.workspace)
        graph.record_node(self.run_dir, "intake", str(workspace_relative), "succeeded")
        self.assertEqual(graph.load_state(self.run_dir)["current"], "capability_discovery")

    def test_rejects_output_escape(self) -> None:
        with self.assertRaises(graph.GraphError):
            graph.initialize("escape", str(self.workspace), "../outside.md")

    def test_rejects_out_of_order_transition(self) -> None:
        artifact = self.write_artifact("plan")
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "plan", str(artifact), "succeeded")

    def test_rejects_invalid_json_artifact(self) -> None:
        self.record("intake")
        artifact = self.write_artifact("capability_discovery", "not-json")
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "capability_discovery", str(artifact), "succeeded")

    def test_rejects_receipt_symlink_escape(self) -> None:
        outside = self.workspace / "outside-receipts"
        outside.mkdir()
        (self.run_dir / "receipts").symlink_to(outside, target_is_directory=True)
        artifact = self.write_artifact("intake")
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "intake", str(artifact), "succeeded")

    def test_failed_node_can_retry_with_bound(self) -> None:
        failed = self.write_artifact("intake", "source unavailable")
        graph.record_node(self.run_dir, "intake", str(failed), "failed")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "blocked")
        graph.retry_node(self.run_dir, "use the local source fallback")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "running")
        self.record("intake")

    def test_retry_bound_is_enforced(self) -> None:
        for retry in range(2):
            failed = self.write_artifact("intake", f"failure {retry}")
            graph.record_node(self.run_dir, "intake", str(failed), "failed")
            graph.retry_node(self.run_dir, f"fallback {retry}")
        failed = self.write_artifact("intake", "failure final")
        graph.record_node(self.run_dir, "intake", str(failed), "failed")
        with self.assertRaises(graph.GraphError):
            graph.retry_node(self.run_dir, "too many")

    def test_gap_loop_is_bounded(self) -> None:
        self.advance_to_gap()
        self.record("gap_check", "needs-more", {"gaps": ["one"]})
        self.assertEqual(graph.load_state(self.run_dir)["current"], "collect")
        self.record("collect", value={"branches": []})
        self.record("evidence", value=valid_evidence())
        self.record("reconcile")
        self.record("gap_check", "needs-more", {"gaps": ["residual"]})
        state = graph.load_state(self.run_dir)
        self.assertEqual(state["current"], "synthesize")
        self.assertEqual(state["collection_retries"], 1)
        self.record("synthesize", value="draft after second collection")
        self.record(
            "verify",
            value={"verdict": "pass", "checked_claims": 1, "residual_risks": ["residual gap"]},
        )
        (self.workspace / "report.md").write_text(
            "# Answer\n\n" + "Bounded research conclusion with context. " * 8
            + "[Primary source](https://example.com/source).\n\n"
            + "## Confidence and gaps\n\nMedium confidence; one residual gap.",
            encoding="utf-8",
        )
        self.assertEqual(graph.check_report(self.run_dir)["status"], "ok")

    def test_verification_repair_is_bounded(self) -> None:
        self.advance_to_verify()
        for repair in range(2):
            self.record(
                "verify",
                "rejected",
                {
                    "verdict": "reject",
                    "checked_claims": 1,
                    "residual_risks": ["unsupported"],
                    "repair_list": ["remove unsupported claim"],
                },
            )
            self.assertEqual(graph.load_state(self.run_dir)["current"], "synthesize")
            self.record("synthesize", value=f"repair {repair}")
        self.record(
            "verify",
            "rejected",
            {
                "verdict": "reject",
                "checked_claims": 1,
                "residual_risks": ["unsupported"],
                "repair_list": ["remove unsupported claim"],
            },
        )
        self.assertEqual(graph.load_state(self.run_dir)["status"], "blocked")

    def test_verifier_schema_is_checked_before_transition(self) -> None:
        self.advance_to_verify()
        invalid_values = [
            {"verdict": "pass", "checked_claims": [], "residual_risks": []},
            {"verdict": "pass", "checked_claims": True, "residual_risks": []},
        ]
        for invalid_value in invalid_values:
            invalid = self.write_artifact("verify", invalid_value)
            with self.assertRaises(graph.GraphError):
                graph.record_node(self.run_dir, "verify", str(invalid), "succeeded")
            state = graph.load_state(self.run_dir)
            self.assertEqual(state["current"], "verify")
            self.assertEqual(state["nodes"]["verify"]["status"], "ready")
            self.assertEqual(state["nodes"]["verify"]["receipts"], [])

    def test_rejected_verifier_requires_exact_verdict_before_transition(self) -> None:
        self.advance_to_verify()
        invalid = self.write_artifact(
            "verify",
            {
                "verdict": "bogus",
                "checked_claims": 1,
                "residual_risks": ["unsupported"],
                "repair_list": ["remove unsupported claim"],
            },
        )
        with self.assertRaises(graph.GraphError):
            graph.record_node(self.run_dir, "verify", str(invalid), "rejected")
        state = graph.load_state(self.run_dir)
        self.assertEqual(state["current"], "verify")
        self.assertEqual(state["nodes"]["verify"]["status"], "ready")
        self.assertEqual(state["nodes"]["verify"]["receipts"], [])

    def test_verifier_accepts_claim_check_array(self) -> None:
        self.advance_to_verify()
        self.record(
            "verify",
            value={
                "verdict": "pass",
                "checked_claims": [{"claim_id": "C-001", "status": "supported"}],
                "residual_risks": [],
            },
        )
        self.assertEqual(graph.load_state(self.run_dir)["current"], "complete")

    def test_happy_path_completes_and_detects_tamper(self) -> None:
        self.advance_to_verify()
        self.record(
            "verify",
            value={"verdict": "pass", "checked_claims": 1, "residual_risks": []},
        )
        report = self.workspace / "report.md"
        report.write_text(
            "# Answer\n\n" + "A supported conclusion with context. " * 8
            + "[Primary source](https://example.com/source).\n\n"
            + "## Confidence and gaps\n\nHigh confidence; no material residual gaps.",
            encoding="utf-8",
        )
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "ok", checked)
        completed = graph.complete_run(self.run_dir)
        self.assertEqual(completed["status"], "ok")
        self.assertIn("already completed", graph.complete_run(self.run_dir)["summary"])
        self.assertEqual(graph.check_report(self.run_dir)["status"], "ok")
        self.assertEqual(graph.load_state(self.run_dir)["status"], "completed")
        evidence = self.run_dir / "evidence.json"
        evidence.write_text('{"items": []}', encoding="utf-8")
        self.assertTrue(graph.validate_receipt_hashes(graph.load_state(self.run_dir)))

    def test_report_citation_must_match_evidence_ledger(self) -> None:
        self.advance_to_verify()
        self.record(
            "verify",
            value={"verdict": "pass", "checked_claims": 1, "residual_risks": []},
        )
        (self.workspace / "report.md").write_text(
            "# Answer\n\n" + "Unsupported but sufficiently long conclusion. " * 8
            + "[Unrelated](https://unrelated.example/source).\n\n"
            + "## Confidence and gaps\n\nClaimed high confidence.",
            encoding="utf-8",
        )
        checked = graph.check_report(self.run_dir)
        self.assertEqual(checked["status"], "failed")
        self.assertTrue(any("evidence ledger" in issue for issue in checked["next_actions"]))

    def test_parenthesized_commonmark_url_matches_ledger(self) -> None:
        evidence = valid_evidence()
        evidence["items"][0]["source_url"] = "https://example.com/Foo_(bar)"
        self.record("intake")
        self.record("capability_discovery", value={"tools": ["web"]})
        self.record("plan")
        self.record("collect", value={"branches": []})
        self.record("evidence", value=evidence)
        self.record("reconcile")
        self.record("gap_check", "succeeded", {"gaps": []})
        self.record("synthesize", value="draft with parenthesized source")
        self.record(
            "verify",
            value={"verdict": "pass", "checked_claims": 1, "residual_risks": []},
        )
        (self.workspace / "report.md").write_text(
            "# Answer\n\n" + "Supported conclusion with sufficient context. " * 8
            + "[Source](https://example.com/Foo_(bar)).\n\n"
            + "## Confidence and gaps\n\nHigh confidence; no material residual gaps.",
            encoding="utf-8",
        )
        self.assertEqual(graph.check_report(self.run_dir)["status"], "ok")


def valid_evidence() -> dict[str, object]:
    return {
        "items": [
            {
                "claim_id": "C-001",
                "claim": "Supported claim",
                "stance": "supports",
                "source_url": "https://example.com/source",
                "source_title": "Primary source",
                "publisher": "Example",
                "published_at": "2026-07-01",
                "accessed_at": "2026-07-19",
                "source_class": "primary",
                "paraphrase": "The source supports the claim.",
                "confidence": "high",
                "branch": "official",
                "notes": "",
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
