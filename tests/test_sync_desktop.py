"""Portable sync preserves platform state and each home's manual root effort."""
import importlib.util
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("desktop_sync_test", ROOT / "scripts/sync_desktop.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
spec = importlib.util.spec_from_file_location("desktop_install_test", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def config(effort="max", platform="wsl"):
    return f'''model = "gpt-6.1-sol"
model_reasoning_effort = "{effort}"
suppress_unstable_features_warning = true
approvals_reviewer = "auto_review"
project_doc_fallback_filenames = [
    "AGENTS.md",
]
project_doc_max_bytes = 65536
service_tier = "priority"
personality = "pragmatic"
model_verbosity = "low"
model_reasoning_summary = "concise"
approval_policy = "on-request"
model_provider = "openai"
sandbox_mode = "workspace-write"
notify = ["{platform}-notify"]
developer_instructions = """
[agents.fake_example]
model = "preserve the example"
"""
[agents]
max_threads = 6
max_depth = 1
default_subagent_model = "gpt-6.1-sol"
default_subagent_reasoning_effort = "medium"
[features]
multi_agent = true
hooks = true
memories = true
mentions_v2 = true
prevent_idle_sleep = true
[mcp_servers.example]
command = "{platform}-command"
env = {{ TEST_TOKEN = "fixture-only-{platform}" }}
[features.multi_agent_v2]
enabled = true
usage_hint_text = "source policy"
[agents.worker]
config_file = "./agents/worker.toml"
nickname_candidates = ["FixtureWorker"]
[history]
max_bytes = 123
[agents.vacancy_researcher]
config_file = "./agents/vacancy_researcher.toml"
[desktop]
theme = "{platform}"
[plugins.example]
enabled = true
[projects."/fixture"]
trust_level = "trusted"
[shell_environment_policy]
inherit = "core"
[marketplaces.example]
source = "{platform}-local"
'''


class DesktopSyncTests(unittest.TestCase):
    def test_separated_agent_tables_and_platform_settings_are_preserved(self):
        source, target = config().encode(), config("high", "desktop").encode()
        result = sync.build_desktop_config(source, target)
        before, after = tomllib.loads(target.decode()), tomllib.loads(result.decode())
        self.assertEqual(tomllib.loads(source.decode())["agents"], after["agents"])
        self.assertIn("vacancy_researcher", after["agents"])
        self.assertEqual("high", after["model_reasoning_effort"])
        self.assertEqual(before["developer_instructions"], after["developer_instructions"])
        for key in sync.PROTECTED_KEYS:
            with self.subTest(key=key):
                self.assertEqual(before[key], after[key])
        self.assertEqual(result, sync.build_desktop_config(source, result))

    def test_install_sync_repeat_preserve_asymmetric_manual_efforts(self):
        for source_effort, target_effort in (("max", "high"), ("high", "xhigh")):
            with self.subTest(source=source_effort, target=target_effort), tempfile.TemporaryDirectory() as tmp:
                source, target = Path(tmp) / "source", Path(tmp) / "target"
                for home, effort, platform in ((source, source_effort, "wsl"), (target, target_effort, "desktop")):
                    home.mkdir()
                    (home / "config.toml").write_text(config(effort, platform))
                    installer.install_environment(home)
                before_source = (source / "config.toml").read_bytes()
                expected_target = sync.build_desktop_config(before_source, (target / "config.toml").read_bytes())
                sync.deploy_snapshot(target, expected_target, (source / "AGENTS.md").read_bytes(), source / "agents", label="fixture")
                self.assertFalse(sync.drift_report(source, target)[0])
                self.assertEqual(before_source, (source / "config.toml").read_bytes())
                self.assertEqual(target_effort, tomllib.loads((target / "config.toml").read_text())["model_reasoning_effort"])
                installer.install_environment(target)
                self.assertFalse(sync.drift_report(source, target)[0])
                self.assertEqual("ok", installer.verify_environment(target)["status"])

    def test_missing_or_former_root_uses_max_default(self):
        for target in (config("high").replace('model = "gpt-6.1-sol"', 'model = "gpt-6-astra"'),
                       config().replace('model_reasoning_effort = "max"\n', '')):
            result = tomllib.loads(sync.build_desktop_config(config("high").encode(), target.encode()).decode())
            self.assertEqual("max", result["model_reasoning_effort"])

    def test_obsolete_multiline_override_and_separated_profiles_are_removed(self):
        target = 'persistent_instructions = """\nold\n[agents.fake]\n"""\n' + config("high", "desktop")
        target += '\n[profiles.old]\nmodel="old"\n[unrelated]\nvalue=7\n[profiles.other]\nmodel="other"\n'
        result = tomllib.loads(sync.build_desktop_config(config().encode(), target.encode()).decode())
        self.assertNotIn("persistent_instructions", result)
        self.assertNotIn("profiles", result)
        self.assertEqual({"value": 7}, result["unrelated"])

    def prepare_homes(self, tmp):
        source, target = Path(tmp) / "source", Path(tmp) / "target"
        for home, effort in ((source, "max"), (target, "high")):
            home.mkdir()
            (home / "agents").mkdir()
            (home / "config.toml").write_text(config(effort))
            (home / "AGENTS.md").write_text("fixture policy\n")
            (home / "agents/worker.toml").write_text('name="worker"\ndescription="fixture"\ndeveloper_instructions="fixture instructions"\n')
        return source, target

    def test_failed_deployment_restores_owned_files_and_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = self.prepare_homes(tmp)
            before = sync.snapshot_hashes(target)
            replace = sync.os.replace
            def fail_policy(src, dst):
                if Path(dst) == target / "AGENTS.md":
                    raise OSError("fixture deployment failure")
                return replace(src, dst)
            with patch.object(sync.os, "replace", side_effect=fail_policy), self.assertRaises(OSError):
                sync.deploy_snapshot(target, config().encode(), b"new policy\n", source / "agents", label="fixture")
            self.assertEqual(before, sync.snapshot_hashes(target))
            self.assertTrue(list((target / "backups/desktop-sync").glob("*/manifest.json")))

    def test_concurrent_target_edit_during_backup_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = self.prepare_homes(tmp)
            create_backup = sync.create_backup
            def external_edit(home, label):
                backup = create_backup(home, label)
                (home / "config.toml").write_text(config("xhigh"))
                return backup
            with patch.object(sync, "create_backup", side_effect=external_edit), self.assertRaises(sync.SyncError):
                sync.deploy_snapshot(target, config().encode(), b"new policy", source / "agents", label="fixture")
            self.assertEqual("xhigh", tomllib.loads((target / "config.toml").read_text())["model_reasoning_effort"])

    def test_target_edit_after_planning_preserves_effort_and_platform_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = self.prepare_homes(tmp)
            (source / "AGENTS.md").write_text("new source policy\n")
            planned_state = sync.planned_state
            edited = False
            def external_edit(source_home, target_home):
                nonlocal edited
                plan = planned_state(source_home, target_home)
                if not edited:
                    (target / "config.toml").write_text(config("xhigh", "desktop"))
                    edited = True
                return plan
            with patch.object(sync, "planned_state", side_effect=external_edit), self.assertRaises(sync.SyncError):
                sync.run_apply(source, target)
            result = tomllib.loads((target / "config.toml").read_text())
            self.assertEqual("xhigh", result["model_reasoning_effort"])
            self.assertEqual(["desktop-notify"], result["notify"])
            self.assertEqual("fixture policy\n", (target / "AGENTS.md").read_text())
            self.assertFalse((target / "backups").exists())

    def test_source_edit_after_planning_prevents_stale_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = self.prepare_homes(tmp)
            (source / "AGENTS.md").write_text("new source policy\n")
            before = sync.snapshot_hashes(target)
            planned_state = sync.planned_state
            def external_edit(source_home, target_home):
                plan = planned_state(source_home, target_home)
                (source / "AGENTS.md").write_text("later source policy\n")
                return plan
            with patch.object(sync, "planned_state", side_effect=external_edit), self.assertRaises(sync.SyncError):
                sync.run_apply(source, target)
            self.assertEqual(before, sync.snapshot_hashes(target))

    def test_symlinked_profile_path_is_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = self.prepare_homes(tmp)
            real = target / "config.real.toml"
            (target / "config.toml").rename(real)
            (target / "config.toml").symlink_to(real)
            with self.assertRaises(sync.SyncError):
                sync.planned_state(source, target)
            self.assertFalse((target / "backups").exists())
