#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import graph_contract as contract  # noqa: E402


REPO_ROOT = SCRIPT_DIR.parents[2]


class GraphContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def base_skill(self, name: str = "example-graph") -> Path:
        skill = self.root / name
        (skill / "agents").mkdir(parents=True)
        (skill / "scripts").mkdir()
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Create a verified example graph for contract tests.\n---\n\n# Example\n",
            encoding="utf-8",
        )
        (skill / "agents" / "openai.yaml").write_text(
            "interface:\n"
            '  display_name: "Example Graph"\n'
            '  short_description: "Builds one verified example graph"\n'
            f'  default_prompt: "Use ${name} to run the example."\n',
            encoding="utf-8",
        )
        return skill

    def finish_controller(self, skill: Path) -> None:
        (skill / "scripts" / "example_graph.py").write_text(
            '"""Deterministic example controller."""\n\nSTATE_SCHEMA_VERSION = 1\n',
            encoding="utf-8",
        )
        (skill / "scripts" / "test_example_graph.py").write_text(
            '"""Example contract test."""\n\ndef test_contract():\n    assert True\n',
            encoding="utf-8",
        )

    def test_scaffold_requires_skill_creator_base_and_refuses_overwrite(self) -> None:
        skill = self.base_skill()
        result = contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.assertEqual("scaffolded", result["status"])
        self.assertTrue((skill / "graph.json").is_file())
        self.assertTrue((skill / "references" / "control-artifact.md").is_file())
        with self.assertRaisesRegex(contract.ContractError, "Refusing to overwrite"):
            contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")

    def test_unfinished_skill_creator_template_is_rejected_clearly(self) -> None:
        skill = self.base_skill()
        (skill / "SKILL.md").write_text(
            "---\nname: example-graph\ndescription: [TODO: finish]\n---\n\n# Example\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(contract.ContractError, "Finish the \\$skill-creator template"):
            contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")

    def test_scaffolded_graph_passes_after_domain_controller_and_test_exist(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        result = contract.validate_graph_skill(skill, require_work_policy=True)
        self.assertEqual("ok", result["status"])
        self.assertEqual(["full"], result["routes"])
        self.assertEqual("current", result["work_policy"])
        self.assertEqual("current", result["execution_policy"])

    def test_legacy_graph_is_readable_but_not_current(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        graph_path = skill / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph.pop("work_policy")
        graph.pop("execution_policy")
        graph["mcp_policy"] = {
            "discovery": "required",
            "relevant_use": "required",
            "receipt_prefix": "mcp:",
            "fallback_prefix": "mcp:fallback:",
            "selection_order": ["provider-specific-mcp"],
        }
        graph_path.write_text(json.dumps(graph), encoding="utf-8")

        result = contract.validate_graph_skill(skill)
        self.assertEqual("legacy", result["work_policy"])
        self.assertEqual("legacy", result["execution_policy"])
        with self.assertRaisesRegex(contract.ContractError, "requires work_policy"):
            contract.validate_graph_skill(skill, require_work_policy=True)

    def test_unbounded_work_policy_is_rejected(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        graph_path = skill / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["work_policy"]["budgets"]["max_no_new_evidence_iterations"] = 3
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(contract.ContractError, "integer from 1 to 2"):
            contract.validate_graph_skill(skill, require_work_policy=True)

    def test_current_policy_requires_conditional_mcp_discovery(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        graph_path = skill / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["mcp_policy"]["discovery"] = "required"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(contract.ContractError, "need-based MCP"):
            contract.validate_graph_skill(skill, require_work_policy=True)

    def test_execution_policy_rejects_ritual_verified_default(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        graph_path = skill / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["execution_policy"]["tiers"]["verified"]["verification"] = "conditional"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(contract.ContractError, "shared tier contract"):
            contract.validate_graph_skill(skill, require_work_policy=True)

    def test_extra_graph_node_is_rejected(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        graph_path = skill / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["routes"]["full"]["nodes"]["plan"] = {"role": "root", "artifact": "plan.md"}
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(contract.ContractError, "exactly work, verify and complete"):
            contract.validate_graph_skill(skill)

    def test_hard_coded_model_is_rejected(self) -> None:
        skill = self.base_skill()
        contract.scaffold(skill, "full", "work.json", "result.md", "example_verifier")
        self.finish_controller(skill)
        graph_path = skill / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["model"] = "expensive-model"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        with self.assertRaisesRegex(contract.ContractError, "hard-code model"):
            contract.validate_graph_skill(skill)

    def test_current_operational_graphs_share_the_contract(self) -> None:
        for name in (
            "continuous-improvement",
            "project-start",
            "research",
            "task-delivery",
        ):
            with self.subTest(name=name):
                result = contract.validate_graph_skill(
                    REPO_ROOT / "skills" / name,
                    require_work_policy=True,
                )
                self.assertEqual("ok", result["status"])
                self.assertEqual("current", result["work_policy"])
                self.assertEqual("current", result["execution_policy"])

    def test_builder_declares_skill_creator_dependency(self) -> None:
        dependency = json.loads((SCRIPT_DIR.parents[0] / "skill-dependencies.json").read_text(encoding="utf-8"))
        self.assertEqual(1, dependency["schema_version"])
        self.assertEqual("skill-creator", dependency["required_skills"][0]["name"])


if __name__ == "__main__":
    unittest.main()
