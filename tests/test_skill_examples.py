"""Behavioral checks for maintained executable skill examples, no external calls."""
import importlib.util
import json
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


class SkillExamplesTest(unittest.TestCase):
    def scraper_client(self):
        text = (ROOT / "skills/data-scraper-agent/SKILL.md").read_text()
        code = re.search(r"```python\n(# ai/client.py.*?)\n```", text, re.S).group(1)
        requests = types.ModuleType("requests")
        requests.RequestException = type("RequestException", (Exception,), {})
        context = {}
        with patch.dict(sys.modules, {"requests": requests}):
            exec(compile(code, "skill-example:ai/client.py", "exec"), context)
        return requests, context["generate"]

    def test_quota_and_missing_model_do_not_switch_model_or_log_key_in_url(self):
        requests, generate = self.scraper_client()
        calls = []
        requests.post = lambda *a, **kw: (calls.append((a, kw)) or types.SimpleNamespace(status_code=429))
        with patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-test-only", "GEMINI_MODEL": "approved-model"}, clear=True):
            self.assertEqual(generate("test", rate_limit=0), {"enrichment_error": "provider_status_429"})
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][0][0].endswith("/approved-model:generateContent"))
        self.assertNotIn("synthetic-test-only", calls[0][0][0])
        with patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-test-only"}, clear=True):
            self.assertEqual(generate("test", rate_limit=0), {"enrichment_error": "missing_model_or_credential"})
        self.assertEqual(len(calls), 1)

    def test_network_and_invalid_response_are_observable(self):
        requests, generate = self.scraper_client()
        def unavailable(*a, **kw):
            raise requests.RequestException("synthetic failure")
        requests.post = unavailable
        with patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-test-only"}, clear=True):
            self.assertEqual(generate("test", "approved-model", 0), {"enrichment_error": "network_failure"})
            requests.post = lambda *a, **kw: types.SimpleNamespace(status_code=200, json=lambda: {})
            self.assertEqual(generate("test", "approved-model", 0), {"enrichment_error": "invalid_provider_response"})
            requests.post = lambda *a, **kw: types.SimpleNamespace(status_code=200, json=lambda: {
                "candidates": [{"content": {"parts": [{"text": json.dumps({"analyses": []})}]}}]})
            self.assertEqual(generate("test", "approved-model", 0), {"analyses": []})

    def test_inventory_aliases_exact_versions_and_multiline_description(self):
        path = ROOT / "skills/skill-stocktake/scripts/inventory.py"
        spec = importlib.util.spec_from_file_location("stocktake_inventory", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "skills"
            (root / "one").mkdir(parents=True)
            body = "---\nname: one\ndescription: >-\n  First line\n  second line\n---\nBody\n"
            (root / "one/SKILL.md").write_text(body)
            alias = base / "alias"
            alias.symlink_to(root, target_is_directory=True)
            plugin = base / "plugins/cache/provider/v1/skills/demo/SKILL.md"
            plugin.parent.mkdir(parents=True)
            plugin.write_text(body)
            result = module.inventory([root, alias], [plugin])
            self.assertEqual((result["copies"], result["distinct_bodies"]), (2, 1))
            self.assertEqual(result["skills"][0]["description"], "First line second line")
            self.assertEqual(result["skills"][0]["enabled"], "unknown")
            with self.assertRaises(ValueError):
                module.inventory([base / "plugins/cache"], [])


if __name__ == "__main__":
    unittest.main()
