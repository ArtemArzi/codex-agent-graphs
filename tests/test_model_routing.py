"""Routing migration checks: preserve user state and fail before writes."""
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("routing_install_test", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
routing = installer.routing


class RoutingTests(unittest.TestCase):
    def test_root_manual_effort_survives_install_and_repeat(self):
        for effort in ("high", "xhigh", "max"):
            with self.subTest(effort=effort), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                (home / "config.toml").write_text(
                    f'model="gpt-6.1-sol"\nmodel_reasoning_effort="{effort}"\n')
                installer.install_environment(home)
                self.assertEqual(effort, tomllib.loads((home / "config.toml").read_text())["model_reasoning_effort"])
                self.assertEqual("ok", installer.verify_environment(home)["status"])
                result = installer.install_environment(home)
                self.assertTrue(all(c["status"] == "in-sync" for c in result["changes"]))

    def test_invalid_effort_and_unknown_role_fields_fail_closed(self):
        source = routing.POLICY_PATH.read_text()
        candidates = [source.replace('effort = "max"', 'effort = "typo"', 1),
                      source.replace('[roles.worker]', '[roles.worker]\nreasoning = "high"'),
                      source.replace('[roles.worker]', '[roles.worker]\nmodel = "gpt-6-astra"')]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.toml"
            for candidate in candidates:
                path.write_text(candidate)
                with self.subTest(candidate=candidate[-200:]), self.assertRaises(ValueError):
                    routing.load_policy(path)

    @staticmethod
    def retired_reviewer():
        template = (ROOT / "tests/fixtures/retired-reviewer.template.toml").read_text()
        return ('# Generated from policies/model-routing.toml and the role template.\n'
                'model = "gpt-6-astra"\nmodel_reasoning_effort = "medium"\n' + template)

    def test_retired_role_is_archived_outside_discovery_and_registration_removed(self):
        content = self.retired_reviewer()
        self.assertEqual(routing.load_policy()["retired_roles"]["reviewer"]["sha256"],
                         hashlib.sha256(content.encode()).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "agents").mkdir()
            (home / "agents/reviewer.toml").write_text(content)
            (home / "config.toml").write_text('[agents.reviewer]\nconfig_file="./agents/reviewer.toml"\n')
            result = installer.install_environment(home)
            self.assertFalse((home / "agents/reviewer.toml").exists())
            self.assertEqual(content, (Path(result["backup"]) / "retired-agents/reviewer.toml").read_text())
            self.assertNotIn("reviewer", tomllib.loads((home / "config.toml").read_text())["agents"])
            self.assertEqual(20, len(list((home / "agents").glob("*.toml"))))

    def test_unknown_retired_role_drift_prevents_all_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "agents").mkdir()
            target = home / "agents/reviewer.toml"
            target.write_text(self.retired_reviewer() + "\n# User customization\n")
            before = target.read_bytes()
            with self.assertRaises(installer.InstallError):
                installer.install_environment(home)
            self.assertEqual(before, target.read_bytes())
            self.assertFalse((home / "skills").exists())

    def test_retirement_is_restored_when_config_write_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "agents").mkdir()
            retired = home / "agents/reviewer.toml"
            retired.write_text(self.retired_reviewer())
            write = installer.atomic_write
            def fail_config(path, content):
                if path == home / "config.toml":
                    raise OSError("fixture config write failure")
                return write(path, content)
            with patch.object(installer, "atomic_write", side_effect=fail_config), self.assertRaises(installer.InstallError):
                installer.install_environment(home)
            self.assertEqual(self.retired_reviewer(), retired.read_text())

    def test_multiline_array_projection_keeps_unrelated_prompt(self):
        original = 'names = [\n "old",\n "second",\n]\nprompt = """\n[agents]\nmodel="example"\n"""\n'
        updated = routing.rewrite_fields(original, (), {"names": ["new"]})
        self.assertEqual({"names": ["new"], "prompt": tomllib.loads(original)["prompt"]}, tomllib.loads(updated))

    def test_all_roles_resolve_from_one_policy_and_keep_permissions(self):
        policy = routing.load_policy()
        self.assertEqual(20, len(policy["roles"]))
        acceptors = {"task_plan_reviewer", "task_result_reviewer", "research_verifier",
                     "project_docs_verifier", "improvement_verifier"}
        for role, description in installer.role_descriptions().items():
            with self.subTest(role=role):
                rendered = tomllib.loads(routing.render_agent(role, description))
                template = tomllib.loads(routing.role_template(role).read_text())
                expected = ("gpt-6-astra", "medium") if role == "deep_reviewer" else (
                    "gpt-6.1-sol", "high" if role in acceptors | {"worker", "task_worker",
                        "research_synthesizer", "task_risk_reviewer"} else "medium")
                self.assertEqual(expected, (rendered["model"], rendered["model_reasoning_effort"]))
                for key, value in template.items():
                    self.assertEqual(value, rendered[key])

    def test_migration_preserves_multiline_examples_and_unrelated_values(self):
        original = '''model = "old"
model_reasoning_effort = "medium"
developer_instructions = """
[agents.worker]
model = "keep this example"
# BEGIN codex-agent-graphs: graph agents
# END codex-agent-graphs: graph agents
"""
[agents]
max_threads = 6
max_depth = 1
[agents.worker]
config_file = './agents/worker.toml'
nickname_candidates = ["One", "Two"]
[features.multi_agent_v2]
tool_namespace = 'agents'
usage_hint_text = """old
hint"""
[mcp_servers.example]
command = 'unchanged'
env = { TEST_TOKEN = 'fixture-only' }
'''
        updated = installer.config_with_block(original)
        old, new = tomllib.loads(original), tomllib.loads(updated)
        self.assertEqual(new["developer_instructions"], old["developer_instructions"])
        self.assertEqual(new["mcp_servers"], old["mcp_servers"])
        self.assertEqual(new["agents"]["worker"]["nickname_candidates"], ["One", "Two"])
        self.assertEqual(new["features"]["multi_agent_v2"]["tool_namespace"], "agents")
        self.assertEqual(new["agents"]["max_threads"], 6)
        self.assertEqual(new["model_reasoning_effort"], "max")
        self.assertEqual(installer.config_with_block(updated), updated)

    def test_malformed_markers_and_unknown_native_registration_refused(self):
        for original in (installer.BLOCK_START + "\n", installer.BLOCK_END + "\n",
                         installer.managed_block() + installer.BLOCK_START + "\n",
                         "[agents.'worker']\nconfig_file='custom.toml'\n"):
            with self.subTest(original=original[:80]), self.assertRaises(installer.InstallError):
                installer.config_with_block(original)

    def test_known_alias_migration_preserves_unrelated_fields(self):
        original = '''model = 'old'
model_reasoning_effort = 'medium'
developer_instructions = """user-requested model-routing experiment
[example]
model = 'old'
"""
sandbox_mode = 'read-only'
[agents.worker]
config_file = '/old/experiment.toml'
[history]
persistence = 'none'
'''
        result = routing.profile_candidate(original, "astra-luna-xhigh")
        data = tomllib.loads(result)
        self.assertNotIn("model", data)
        self.assertNotIn("agents", data)
        self.assertEqual(data["sandbox_mode"], "read-only")
        self.assertEqual(data["history"], {"persistence": "none"})
        self.assertEqual(routing.profile_candidate(result, "astra-luna-xhigh"), result)

    def test_profile_inline_registrations_cannot_keep_model_overrides(self):
        for source in ('[agents]\nworker={config_file="/custom.toml"}\n',
                       'agents={worker={config_file="/custom.toml"}}\n'):
            migrated = tomllib.loads(routing.profile_candidate(source, "astra-luna"))
            self.assertFalse(routing.has_routing_override(migrated))
            self.assertNotIn("agents", migrated)
        for source in ('[agents]\ncustom={config_file="/custom.toml"}\n',
                       '[agents]\nworker={model="custom",config_file="/custom.toml"}\n'):
            with self.assertRaises(ValueError):
                routing.profile_candidate(source, "astra-luna")

    def test_profile_custom_instructions_fail_closed_without_model_heuristic(self):
        with self.assertRaisesRegex(ValueError, "custom developer instructions"):
            routing.profile_candidate('developer_instructions="Use o3 for workers"\n', "astra-luna")

    def test_profile_nicknames_survive_both_table_and_inline_migration(self):
        for source in ('[agents.worker]\nconfig_file="old.toml"\nnickname_candidates=["One"]\n',
                       '[agents]\nworker={config_file="old.toml",nickname_candidates=["One"]}\n'):
            migrated = routing.profile_candidate(source, "astra-luna")
            self.assertEqual(tomllib.loads(migrated)["agents"]["worker"], {"nickname_candidates": ["One"]})
            self.assertFalse(routing.has_routing_override(tomllib.loads(migrated)))
            self.assertEqual(migrated, routing.profile_candidate(migrated, "astra-luna"))

    def test_verify_and_plan_refuse_an_identical_tree_through_symlink_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            installer.install_environment(home)
            (home / "skills").rename(base / "other-skills")
            (home / "skills").symlink_to(base / "other-skills", target_is_directory=True)
            verification = installer.verify_environment(home)
            self.assertEqual(verification["status"], "failed")
            self.assertIn("Unsafe install parent", verification["issues"][0])
            self.assertEqual(installer.plan_environment(home)["items"][0]["status"], "conflict")

    def test_symlinked_parent_in_second_home_prevents_all_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first, second, other = (base / name for name in ("first", "second", "other"))
            second.mkdir(); other.mkdir()
            (second / "agents").symlink_to(other, target_is_directory=True)
            with contextlib.redirect_stdout(io.StringIO()):
                code = installer.main(["install", "--all", "--wsl-home", str(first), "--desktop-home", str(second)])
            self.assertEqual(code, 2)
            self.assertFalse(first.exists())
            self.assertEqual(list(other.iterdir()), [])

    def test_unmanaged_profile_overrides_prevent_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "custom.config.toml").write_text("model = 'old'\n")
            with self.assertRaisesRegex(installer.InstallError, "Unmanaged profile"):
                installer.install_environment(home)
            self.assertFalse((home / "skills").exists())
        with self.assertRaisesRegex(ValueError, "Embedded profile"):
            installer.config_with_block("[profiles.custom]\nmodel='old'\n")

    def test_unmanaged_profile_drift_is_reported_by_verify_plan_and_install(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installer.install_environment(home)
            custom = home / "custom.config.toml"
            custom.write_text("model = 'old-model'\n")
            verification = installer.verify_environment(home)
            self.assertEqual(verification["status"], "failed")
            self.assertIn("Unmanaged profile", verification["issues"][0])
            planned = installer.plan_environment(home)
            self.assertEqual(planned["items"][0]["status"], "conflict")
            with self.assertRaisesRegex(installer.InstallError, "Unmanaged profile"):
                installer.preflight_environment(home)
            custom.write_text("sandbox_mode = 'read-only'\n")
            self.assertEqual(installer.verify_environment(home)["status"], "ok")

    def test_alias_original_is_backed_up_and_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            original = "model='old'\nmodel_reasoning_effort='medium'\n"
            alias = home / "astra-medium-baseline.config.toml"
            alias.write_text(original)
            installed = installer.install_environment(home)
            self.assertEqual((Path(installed["backup"]) / alias.name).read_text(), original)
            self.assertEqual("ok", installer.verify_environment(home)["status"])
            self.assertTrue(all(item["status"] == "in-sync" for item in installer.install_environment(home)["changes"]))
            (home / "agents/worker.toml").write_text("model='old'\n")
            self.assertEqual("failed", installer.verify_environment(home)["status"])

    def test_partial_failure_reports_completed_changes_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            real_replace = installer.replace_generated
            def fail_policy(content, target, backup):
                if target.name == "model-routing.toml":
                    raise OSError("fixture write failure")
                return real_replace(content, target, backup)
            output = io.StringIO()
            with patch.object(installer, "replace_generated", side_effect=fail_policy), contextlib.redirect_stdout(output):
                code = installer.main(["install", "--wsl", "--wsl-home", str(home)])
            data = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            changes = data["data"]["partial_install"]["changes"]
            expected = {("runtime", "agent-graph-runtime")} | {
                ("skill", name) for name in installer.SKILLS
            }
            self.assertEqual({(item["kind"], item["name"]) for item in changes}, expected)
            self.assertEqual(len(changes), len(expected))
            self.assertFalse((home / "config.toml").exists())


if __name__ == "__main__":
    unittest.main()
