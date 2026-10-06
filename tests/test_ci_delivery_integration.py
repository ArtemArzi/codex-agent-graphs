"""Exercise actual Task Delivery completion as a Continuous Improvement input."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for relative in ("skills/task-delivery/scripts", "skills/continuous-improvement/scripts", "agent-graph-runtime"):
    sys.path.insert(0, str(ROOT / relative))

import test_task_graph as td_fixture  # noqa: E402
import continuous_improvement_graph as ci  # noqa: E402
import artifact_lifecycle as lifecycle  # noqa: E402


class ImprovementDeliveryIntegrationTests(unittest.TestCase):
    def test_real_td_completion_and_compaction_preserve_ci_acceptance(self) -> None:
        fixture = td_fixture.TaskGraphTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        root = fixture.root
        fixture.write(".gitignore", "__pycache__/\n")
        fixture.write("test_app.py", "import unittest\nfrom src.app import VALUE\n\n"
                      "class AppTests(unittest.TestCase):\n"
                      "    def test_default_value(self):\n"
                      "        self.assertEqual(2, VALUE)\n")

        def git(*args: str) -> str:
            return subprocess.run(["git", *args], cwd=root, check=True,
                                  capture_output=True, text=True).stdout.strip()

        git("init")
        git("config", "user.name", "Fixture")
        git("config", "user.email", "fixture@example.test")
        git("add", ".gitignore", "src/app.py", "test_app.py")
        git("commit", "-m", "baseline with reproducible defect")
        command = "python3 -B -m unittest test_app -v"
        before = subprocess.run(command.split(), cwd=root, capture_output=True, text=True)
        self.assertEqual(1, before.returncode)
        self.assertIn("AssertionError: 2 != 1", before.stderr)

        ci_run = Path(ci.initialize(str(root), "full", "Fix the reproduced default-value regression")["data"]["run"])
        ci_state = ci.load_state(ci_run)
        branch = "codex/continuous-improvement-" + ci_state["run_id"]
        git("checkout", "-b", branch)
        plan = f".agent-graphs/continuous-improvement-runs/{ci_state['run_id']}/task-delivery/PLAN.md"
        td_run = fixture.initialize(task_id="ci.fix-1", plan=plan)
        plan_path = fixture.plan(task_id="ci.fix-1", path=plan)
        plan_path.write_text(plan_path.read_text().replace(
            "- Internal repository path and current tests inspected.",
            f"- CI reproduction: `{command}` exited 1 with `AssertionError: 2 != 1`.\n"
            "- Current src/app.py and test_app.py confirm the same local defect; reuse this finding."))
        fixture.write("src/app.py", "VALUE = 2\n")
        after = subprocess.run(command.split(), cwd=root, capture_output=True, text=True)
        self.assertEqual(0, after.returncode, after.stderr)
        work = fixture.work_payload(td_run)
        work["tests"] = [{"command": command, "purpose": "reproduced default-value regression",
                          "exit_code": after.returncode, "status": "passed"}]
        fixture.write_work(td_run, work)
        td_fixture.graph.record(td_run, "work", "succeeded")
        td_fixture.graph.complete(td_run)
        td_state_path = td_run / "state.json"
        td_state = fixture.read(td_state_path)
        self.assertEqual("3.9.1", td_state["graph_version"])
        self.assertEqual("completed", td_state["status"])
        td_work = td_state["nodes"]["work"]["receipts"][-1]
        task_state = fixture.read(root / ".codex/task-delivery/ci.fix-1/state.json")
        handoff = task_state["checkpoints"]["handoff"]
        git("add", "src/app.py")
        git("commit", "-m", "Fix reproduced default-value regression")

        artifact = {
            "schema_version": 1, "run_id": ci_state["run_id"], "mode": "full",
            "focus": ci_state["focus"], "disposition": "delivered", "confidence": "high",
            "capabilities": ["mcp:not-applicable:local-regression"], "agents": [],
            "scan": {"sources_checked": ["current failing test and source"], "no_candidate_reason": None},
            "candidate": {
                "candidate_id": "default-value-regression", "title": "Default value violates tested contract",
                "source_kind": "failing-test", "risk": "low", "protected_domains": [],
                "evidence": [{"kind": "command", "reference": command, "observation": "Before fix: AssertionError: 2 != 1"}],
                "reproduction_commands": [command], "acceptance": ["Existing regression passes without changing its assertion"],
                "scope": ["src/app.py"],
                "benefit": {"affected": "Callers using the default value", "consequence": "Wrong result violates the existing test",
                            "frequency": "Every default call in this fixture", "effort": "small",
                            "why_now": "A reproduced one-line defect with an existing check is worth repairing"},
            },
            "issue": None,
            "task_delivery": {
                "run_dir": td_run.relative_to(root).as_posix(), "state_sha256": ci.sha256_file(td_state_path),
                "task_sha256": td_work["sha256"], "handoff_sha256": handoff["sha256"],
                "changed_paths": ["src/app.py"], "tests": [{"command": command, "status": "passed", "exit_code": 0}],
            },
            "git": {"branch": branch, "commit": git("rev-parse", "HEAD")}, "residual_risks": [],
        }
        (ci_run / ci.WORK_NAME).write_text(json.dumps(artifact, indent=2) + "\n")
        ci.record(ci_run, "work", "succeeded")
        self.assertEqual("delivered", ci.complete(ci_run)["data"]["disposition"])
        self.assertEqual("ok", lifecycle.compact(root, td_run)["status"])
        self.assertEqual("ok", lifecycle.compact(root, ci_run)["status"])
        self.assertEqual("completed", ci.complete(ci_run)["status"])
        entry = ci.history(str(root))["data"]["runs"][0]
        self.assertEqual("historical_only", entry["status"])
        self.assertEqual("delivered", entry["disposition"])
        self.assertIsNotNone(entry["final_receipt"])
        self.assertEqual("default-value-regression", entry["summary"]["candidate"]["candidate_id"])


if __name__ == "__main__":
    unittest.main()
