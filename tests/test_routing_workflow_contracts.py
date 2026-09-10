"""Ensure published routing examples are accepted by released controllers."""
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_routing_example_test", ROOT / "skills/research/scripts/research_graph.py")
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)


class RoutingWorkflowContractTests(unittest.TestCase):
    def test_research_documented_fast_examples_and_deep_route_validate(self):
        for reference in ("control-artifact.md", "source-policy.md"):
            with self.subTest(reference=reference), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                initialized = graph.initialize("Validate the documented receipt", str(workspace), "report.md")
                run = Path(initialized["data"]["run_dir"])
                text = (ROOT / "skills/research/references" / reference).read_text()
                example = json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))
                urls = [source["url"] if isinstance(source, dict) else source for source in example["sources"]]
                (workspace / "report.md").write_text(
                    "A bounded fixture report whose explicit claims can be checked against the declared primary sources. " * 3
                    + " ".join(f"[Source]({url})" for url in urls) + "\n")
                artifact = run / "research.json"
                artifact.write_text(json.dumps(example))
                errors, _ = graph.validate_work(artifact, graph.load_state(run), "succeeded")
                self.assertEqual(errors, [])
                self.assertEqual(example["agents"], [])
                self.assertEqual(example["verification"], "self")
                deep = {**example, "mode": "deep", "verification": "independent", "agents": ["research_scout"]}
                artifact.write_text(json.dumps(deep))
                errors, _ = graph.validate_work(artifact, graph.load_state(run), "verify")
                self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
