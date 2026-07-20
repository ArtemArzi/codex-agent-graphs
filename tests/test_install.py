#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


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

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_install_and_verify(self) -> None:
        result = installer.install_environment(self.home)
        self.assertEqual(installer.verify_environment(self.home)["status"], "ok")
        self.assertTrue((self.home / "skills" / "research" / "graph.json").is_file())
        self.assertTrue((self.home / "skills" / "project-start" / "graph.json").is_file())
        self.assertIn("[agents.research_verifier]", (self.home / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("[agents.project_docs_verifier]", (self.home / "config.toml").read_text(encoding="utf-8"))
        self.assertIsNotNone(result["backup"])

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
