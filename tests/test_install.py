#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("graph_install", MODULE_PATH)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / ".codex"
        self.home.mkdir()
        (self.home / "config.toml").write_text("[agents]\nmax_threads = 6\n", encoding="utf-8")
        (self.home / "AGENTS.md").write_text("# My existing global policy\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_install_and_verify(self) -> None:
        result = installer.install_environment(self.home)
        self.assertEqual(installer.verify_environment(self.home)["status"], "ok")
        self.assertTrue((self.home / "skills" / "research" / "graph.json").is_file())
        self.assertTrue((self.home / "skills" / "agent-graph-builder" / "SKILL.md").is_file())
        dependency = self.home / "skills" / "agent-graph-builder" / "skill-dependencies.json"
        self.assertIn("skill-creator", dependency.read_text(encoding="utf-8"))
        self.assertTrue((self.home / "skills" / "project-start" / "graph.json").is_file())
        self.assertTrue((self.home / "skills" / "development-recovery" / "SKILL.md").is_file())
        self.assertFalse((self.home / "skills" / "development-recovery" / "graph.json").exists())
        self.assertIn("[agents.research_verifier]", (self.home / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("[agents.project_docs_verifier]", (self.home / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("[agents.task_result_reviewer]", (self.home / "config.toml").read_text(encoding="utf-8"))
        self.assertTrue((self.home / "skills" / "task-delivery" / "graph.json").is_file())
        global_policy = (self.home / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# My existing global policy", global_policy)
        self.assertIn(installer.POLICY_BLOCK_START, global_policy)
        self.assertIn("$development-recovery", global_policy)
        self.assertIn(installer.DISCOVERY_POLICY_BLOCK_START, global_policy)
        self.assertIn("Do not finalize a plan or specification", global_policy)
        self.assertIn("Never spawn more than two internal explorers", global_policy)
        self.assertIn("generic `explorer` and `researcher` roles", global_policy)
        self.assertFalse((self.home / "skills" / "codebase-discovery").exists())
        self.assertIsNotNone(result["backup"])

    def test_global_policy_install_is_idempotent(self) -> None:
        installer.install_environment(self.home)
        installer.install_environment(self.home)
        global_policy = (self.home / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(global_policy.count(installer.POLICY_BLOCK_START), 1)
        self.assertEqual(global_policy.count(installer.POLICY_BLOCK_END), 1)
        self.assertEqual(global_policy.count(installer.DISCOVERY_POLICY_BLOCK_START), 1)
        self.assertEqual(global_policy.count(installer.DISCOVERY_POLICY_BLOCK_END), 1)
        self.assertEqual(global_policy.count("# My existing global policy"), 1)
        self.assertEqual(installer.verify_environment(self.home)["status"], "ok")

    def test_malformed_discovery_policy_block_is_rejected(self) -> None:
        (self.home / "AGENTS.md").write_text(
            f"# Mine\n\n{installer.DISCOVERY_POLICY_BLOCK_START}\nunfinished\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(installer.InstallError, "large-codebase-discovery"):
            installer.install_environment(self.home)
        self.assertFalse((self.home / "skills").exists())

    def test_embedded_discovery_policy_marker_is_rejected(self) -> None:
        (self.home / "AGENTS.md").write_text(
            "# Mine "
            f"{installer.DISCOVERY_POLICY_BLOCK_START}\nbody\n"
            f"{installer.DISCOVERY_POLICY_BLOCK_END}\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(installer.InstallError, "embedded"):
            installer.install_environment(self.home)
        self.assertFalse((self.home / "skills").exists())

    def test_policy_source_cannot_embed_managed_markers(self) -> None:
        bad_source = Path(self.temp.name) / "bad-policy.md"
        bad_source.write_text(installer.DISCOVERY_POLICY_BLOCK_START, encoding="utf-8")
        with mock.patch.object(installer, "DISCOVERY_POLICY_SOURCE", bad_source):
            with self.assertRaisesRegex(installer.InstallError, "contains a managed marker"):
                installer.install_environment(self.home)
        self.assertFalse((self.home / "skills").exists())

    def test_global_policy_drift_is_backed_up_and_repaired(self) -> None:
        installer.install_environment(self.home)
        agents_file = self.home / "AGENTS.md"
        agents_file.write_text(
            agents_file.read_text(encoding="utf-8").replace(
                "Treat an accepted specification",
                "tampered managed policy",
            ),
            encoding="utf-8",
        )
        self.assertEqual(installer.verify_environment(self.home)["status"], "failed")
        result = installer.install_environment(self.home)
        self.assertEqual(installer.verify_environment(self.home)["status"], "ok")
        self.assertIsNotNone(result["backup"])
        backups = [
            path
            for path in (self.home / "backups" / "agent-graphs").rglob("AGENTS.md")
            if "tampered managed policy" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(len(backups), 1)

    def test_discovery_policy_drift_is_backed_up_and_repaired(self) -> None:
        installer.install_environment(self.home)
        agents_file = self.home / "AGENTS.md"
        agents_file.write_text(
            agents_file.read_text(encoding="utf-8").replace(
                "A timeout is not completion",
                "tampered discovery policy",
            ),
            encoding="utf-8",
        )
        self.assertEqual(installer.verify_environment(self.home)["status"], "failed")
        result = installer.install_environment(self.home)
        self.assertEqual(installer.verify_environment(self.home)["status"], "ok")
        self.assertIsNotNone(result["backup"])
        backups = [
            path
            for path in (self.home / "backups" / "agent-graphs").rglob("AGENTS.md")
            if "tampered discovery policy" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(len(backups), 1)

    def test_malformed_global_policy_block_is_rejected(self) -> None:
        (self.home / "AGENTS.md").write_text(
            f"# Mine\n\n{installer.POLICY_BLOCK_START}\nunfinished\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(installer.InstallError, "Malformed"):
            installer.install_environment(self.home)
        self.assertFalse((self.home / "skills").exists())

    def test_drift_is_backed_up_and_repaired(self) -> None:
        installer.install_environment(self.home)
        installed = self.home / "skills" / "research" / "SKILL.md"
        installed.write_text("local drift", encoding="utf-8")
        self.assertEqual(installer.verify_environment(self.home)["status"], "failed")
        result = installer.install_environment(self.home)
        self.assertEqual(installer.verify_environment(self.home)["status"], "ok")
        self.assertIsNotNone(result["backup"])
        backups = list((self.home / "backups" / "agent-graphs").rglob("research/SKILL.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "local drift")

    def test_unmanaged_agent_role_conflict_is_rejected(self) -> None:
        config = self.home / "config.toml"
        config.write_text("[agents.research_scout]\ndescription = 'mine'\n", encoding="utf-8")
        with self.assertRaises(installer.InstallError):
            installer.install_environment(self.home)
        self.assertFalse((self.home / "skills").exists())

    def test_legacy_research_block_is_upgraded_without_duplication(self) -> None:
        config = self.home / "config.toml"
        config.write_text(
            "[agents]\nmax_threads = 6\n\n"
            "# BEGIN codex-agent-graphs: research agents\n"
            "[agents.research_scout]\n"
            "description = 'old managed role'\n"
            "config_file = './agents/research_scout.toml'\n"
            "# END codex-agent-graphs: research agents\n",
            encoding="utf-8",
        )
        installer.install_environment(self.home)
        updated = config.read_text(encoding="utf-8")
        self.assertNotIn("research agents", updated)
        self.assertEqual(updated.count("[agents.research_scout]"), 1)
        self.assertIn("[agents.project_docs_auditor]", updated)

    def test_all_environments_are_preflighted_before_first_write(self) -> None:
        first = Path(self.temp.name) / "first"
        second = Path(self.temp.name) / "second"
        first.mkdir()
        second.mkdir()
        (first / "config.toml").write_text("[agents]\nmax_threads = 6\n", encoding="utf-8")
        (second / "config.toml").write_text(
            "[agents.research_scout]\ndescription = 'conflict'\n", encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = installer.main(
                [
                    "install",
                    "--all",
                    "--wsl-home",
                    str(first),
                    "--desktop-home",
                    str(second),
                ]
            )
        self.assertEqual(exit_code, 2)
        self.assertFalse((first / "skills").exists())

    def test_symlinked_config_is_rejected_without_replacing_link(self) -> None:
        config = self.home / "config.toml"
        config.unlink()
        shared = Path(self.temp.name) / "shared-config.toml"
        shared.write_text("[agents]\nmax_threads = 6\n", encoding="utf-8")
        config.symlink_to(shared)
        with self.assertRaisesRegex(installer.InstallError, "Symlinked config"):
            installer.install_environment(self.home)
        self.assertTrue(config.is_symlink())
        self.assertEqual("[agents]\nmax_threads = 6\n", shared.read_text(encoding="utf-8"))
        self.assertFalse((self.home / "skills").exists())


if __name__ == "__main__":
    unittest.main()
