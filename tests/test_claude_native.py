"""Native provider isolation, transaction safety and dependency independence."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import install_claude as native

spec = importlib.util.spec_from_file_location("claude_inventory_tests", REPO / "skills/task-delivery/scripts/task_delivery_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class NativeClaudeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cag-native-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / ".claude"
        self.home.mkdir()

    def prepare(self, names=("research",), adopt=()):
        return native.prepare(self.home, names=names, adopt=adopt)

    def install(self, names=("research",), adopt=()):
        home, units, _record, rows, total = self.prepare(names, adopt)
        return native.install(home, units, rows, total, names=names)

    def test_native_fresh_repeat_and_plan_preserve_private_surfaces(self):
        sentinels = {"AGENTS.md": "personal instructions", "settings.json": '{"model":"private-model"}', "agents/private.md": "private agent", "skills/private/SKILL.md": "private skill", "plugins/installed_plugins.json": "private registry", "credentials.json": "synthetic-private-token"}
        for relative, content in sentinels.items():
            target = self.home / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        before = native.shared.manifest(self.home)
        self.prepare()
        self.assertEqual(native.shared.manifest(self.home), before)
        self.assertEqual(self.install()["status"], "installed")
        record = json.loads((self.home / "agent-graph-runtime/claude-native.json").read_text())
        self.assertEqual(len(record["roles"]), 20)
        self.assertTrue(all(value["agent_type"].startswith("cag-") for value in record["roles"].values()))
        for relative, content in sentinels.items():
            self.assertEqual((self.home / relative).read_text(), content)
        self.assertFalse((self.home / "CLAUDE.md").exists())
        self.assertIn("/research", (self.home / "skills/research/SKILL.md").read_text())
        self.assertIn(str(self.home), (self.home / "skills/research/SKILL.md").read_text())
        installed = native.shared.manifest(self.home)
        self.assertEqual(self.install()["status"], "already-installed")
        self.assertEqual(installed, native.shared.manifest(self.home))

    def test_unmanaged_adoption_then_future_private_drift_stops(self):
        path = self.home / "skills/research/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("private research")
        with self.assertRaisesRegex(native.shared.InstallError, "Unmanaged/private drift"):
            self.install()
        result = self.install(adopt=("research",))
        backup = Path(result["environments"][0]["backup"])
        self.assertEqual((backup / "skills/research/SKILL.md").read_text(), "private research")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        path.write_text(path.read_text() + "\nnew private edit\n")
        with self.assertRaisesRegex(native.shared.InstallError, "drift"):
            self.prepare()

    def test_active_lock_and_symlink_parent_refuse_changes(self):
        lock = self.home / ".skills-install.lock"
        lock.write_text("foreign writer")
        with self.assertRaisesRegex(native.shared.InstallError, "Another skill installer"):
            self.install()
        self.assertEqual(lock.read_text(), "foreign writer")
        lock.unlink()
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / "skills").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(native.shared.InstallError, "Unsafe"):
            self.prepare()
        self.assertEqual(list(outside.iterdir()), [])

    def test_late_failure_rolls_back_directories_including_roles(self):
        original = native.shared.replace_directory
        count = 0
        def fail_late(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                raise native.shared.InstallError("injected late failure")
            return original(*args, **kwargs)
        with mock.patch.object(native.shared, "replace_directory", side_effect=fail_late):
            with self.assertRaisesRegex(native.shared.InstallError, "owned writes rolled back"):
                self.install()
        self.assertFalse((self.home / "skills/research").exists())
        self.assertFalse((self.home / "agents/cag").exists())
        self.assertFalse((self.home / ".skills-install.lock").exists())

    def test_concurrent_target_edit_is_preserved(self):
        home, units, _record, rows, total = self.prepare()
        target = self.home / "skills/research"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("concurrent human change")
        with self.assertRaisesRegex(native.shared.InstallError, "Concurrent skill edit"):
            native.install(home, units, rows, total, names=("research",))
        self.assertEqual((target / "SKILL.md").read_text(), "concurrent human change")

    def test_creator_required_and_verifiable_without_codex_source_after_copy(self):
        with self.assertRaisesRegex(native.shared.InstallError, "Supply --skill-creator"):
            self.prepare(("agent-graph-builder",))
        creator = self.root / "reviewed-creator"
        creator.mkdir()
        (creator / "SKILL.md").write_text("---\nname: skill-creator\ndescription: Fixture skill creator\n---\nGeneric structure.\n")
        (creator / "license.txt").write_text("fixture licence")
        (creator / "scripts").mkdir()
        helper = creator / "scripts/helper.py"
        helper.write_text("print('fixture helper')\n")
        helper.chmod(0o755)
        home, units, _record, rows, total = native.prepare(self.home, names=("agent-graph-builder",), creator=creator)
        native.install(home, units, rows, total, names=("agent-graph-builder",), creator=creator)
        (creator / "SKILL.md").unlink()
        (creator / "license.txt").unlink()
        helper.unlink()
        (creator / "scripts").rmdir()
        creator.rmdir()
        _, _units, _record, verified, _total = self.prepare(("agent-graph-builder",))
        self.assertTrue(all(row["status"] == "in-sync" for row in verified))
        self.assertEqual((self.home / "skills/skill-creator/license.txt").read_text(), "fixture licence")
        self.assertTrue((self.home / "skills/skill-creator/scripts/helper.py").stat().st_mode & 0o100)

    def test_installed_helpers_from_other_cwd_without_plugin_or_codex(self):
        self.install(names=("project-start", "research"))
        project = self.root / "project"
        unrelated = self.root / "unrelated-cwd"
        project.mkdir()
        unrelated.mkdir()
        env = dict(os.environ)
        for key in ["CLAUDECODE", "CLAUDE_PLUGIN_ROOT", "CLAUDE_CONFIG_DIR", "CODEX_HOME"]:
            env.pop(key, None)
        script = self.home / "skills/project-start/scripts/project_start.py"
        dependencies = subprocess.run([sys.executable, "-B", str(script), "dependencies"], cwd=unrelated, env=env, capture_output=True, text=True, timeout=25)
        value = json.loads(dependencies.stdout)
        self.assertNotIn(str(Path.home() / ".codex"), dependencies.stdout)
        self.assertIn(str(self.home / "skills"), dependencies.stdout)
        graph = self.home / "skills/research/scripts/research_graph.py"
        initialized = subprocess.run([sys.executable, "-B", str(graph), "init", "--question", "Synthetic offline portability fixture", "--workspace", str(project), "--output", str(project / "report.md")], cwd=unrelated, env=env, capture_output=True, text=True, timeout=25)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        runs = list((project / ".agent-graphs/research-runs").iterdir())
        self.assertEqual(len(runs), 1)
        for _ in range(2):
            resumed = subprocess.run([sys.executable, "-B", str(graph), "ready", "--run", str(runs[0])], cwd=unrelated, env=env, capture_output=True, text=True, timeout=25)
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        incomplete = subprocess.run([sys.executable, "-B", str(graph), "complete", "--run", str(runs[0])], cwd=unrelated, env=env, capture_output=True, text=True, timeout=25)
        self.assertNotEqual(incomplete.returncode, 0, "No fabricated receipt may complete the fixture")

    def test_creator_new_skill_destination_uses_claude_and_preserves_source(self):
        creator = self.root / "creator-source"
        creator.mkdir()
        source = creator / "SKILL.md"
        original = '''---
name: skill-creator
description: Create or update a Codex skill.
---
Respect a user-specified location; otherwise create discoverable skills in `$CODEX_HOME/skills`, or `~/.codex/skills` when `CODEX_HOME` is unset.
```bash
scripts/init_skill.py my-skill --path "${CODEX_HOME:-$HOME/.codex}/skills"
scripts/init_skill.py my-skill --path "${CODEX_HOME:-$HOME/.codex}/skills" --resources references
```
'''
        source.write_text(original)
        home, units, _record, rows, total = native.prepare(self.home, names=("agent-graph-builder",), creator=creator)
        native.install(home, units, rows, total, names=("agent-graph-builder",), creator=creator)
        installed = (self.home / "skills/skill-creator/SKILL.md").read_text()
        self.assertNotIn("CODEX_HOME", installed)
        self.assertNotIn(".codex/skills", installed)
        self.assertIn(f'--path "{self.home / "skills"}"', installed)
        self.assertIn("Respect a user-specified location", installed)
        self.assertEqual(source.read_text(), original)
        _, _units, _record, verified, _total = self.prepare(("agent-graph-builder",))
        self.assertTrue(all(row["status"] == "in-sync" for row in verified))

    def test_admission_caps_do_not_create_a_new_namespace(self):
        with mock.patch.object(native, "STAGING_LIMIT", 1):
            with self.assertRaisesRegex(native.shared.InstallError, "staging exceeds"):
                self.prepare()
        home, units, _record, rows, total = self.prepare()
        with mock.patch.object(native, "BACKUP_LIMIT", -1):
            with self.assertRaisesRegex(native.shared.InstallError, "backup history"):
                native.install(home, units, rows, total, names=("research",))
        self.assertFalse((self.home / "backups").exists())
        self.assertFalse((self.home / "skills").exists())

    def test_symlinked_home_ancestor_is_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(native.shared.InstallError, "Symlinked native home ancestor"):
            native.prepare(alias / ".claude", names=("research",))
        self.assertFalse((self.home / "skills").exists())

    def test_source_guard_rejects_changed_projection_before_target_writes(self):
        home, units, record, rows, total = self.prepare()
        changed = {name: dict(files) for name, files in units.items()}
        changed["skills/research"]["SKILL.md"] += b"\nchanged source\n"
        with mock.patch.object(native.projection, "build", return_value=(changed, record)):
            with self.assertRaisesRegex(native.shared.InstallError, "Concurrent canonical"):
                native.install(home, units, rows, total, names=("research",))
        self.assertFalse((self.home / "skills/research").exists())
        self.assertFalse((self.home / "agents/cag").exists())

    def test_rollback_preserves_a_concurrent_human_edit(self):
        original = native.shared.replace_directory
        count = 0
        def concurrent_then_fail(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                raise native.shared.InstallError("injected failure after human edit")
            result = original(*args, **kwargs)
            if count == 1:
                (self.home / "skills/research/SKILL.md").write_text("new human change")
            return result
        with mock.patch.object(native.shared, "replace_directory", side_effect=concurrent_then_fail):
            with self.assertRaisesRegex(native.shared.InstallError, "rollback conflicts|readback failed"):
                self.install()
        self.assertEqual((self.home / "skills/research/SKILL.md").read_text(), "new human change")

    def test_secret_safe_claude_capabilities_include_nested_roles(self):
        marker = "SYNTHETIC-SECRET-DO-NOT-EXPORT"
        (self.home / "settings.json").write_text(json.dumps({"env": {"TOKEN": marker}, "enabledPlugins": {"active@example": True, "off@example": False}, "hooks": {"SessionStart": [{"command": marker}]}}))
        (self.root / ".claude.json").write_text(json.dumps({"mcpServers": {"context7": {"headers": {"Authorization": marker}, "args": [marker]}}, "projects": {str(self.root): {"mcpServers": {"project-only": {"env": {"KEY": marker}}}}}}))
        agent = self.home / "agents/cag/cag-researcher.md"
        agent.parent.mkdir(parents=True)
        agent.write_text("---\nname: cag-researcher\ndescription: fixture\n---\n" + marker)
        result = inventory.parse_safe_claude_config(self.home, self.root)
        self.assertEqual(result["mcp_servers"], ["context7", "project-only"])
        self.assertEqual(result["agent_keys"], ["cag-researcher"])
        self.assertEqual(result["plugins"], ["active@example"])
        self.assertNotIn(marker, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
