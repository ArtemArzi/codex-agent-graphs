#!/usr/bin/env python3
"""Хост-условное обнаружение skills-root: Codex-режим байт-в-байт прежний.

Контракт (этап 1 адаптации под Claude Code):
- Без маркеров Claude-хоста и при существующем ~/.codex список кандидатов
  ИДЕНТИЧЕН историческому поведению — ни ~/.claude, ни self-located корней.
- Маркер CLAUDECODE / CLAUDE_PLUGIN_ROOT (или отсутствие ~/.codex) добавляет
  self-located корень и ~/.claude строго В ХВОСТ списка.
- Явный override (--skills-root / --codex-home / explicit) отключает добавки
  полностью — в том числе на Claude-хосте.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


inventory = _load("tdi_claude_host", "skills/task-delivery/scripts/task_delivery_inventory.py")
maintenance = _load("pm_claude_host", "skills/project-start/scripts/project_maintenance.py")
project_start = _load("ps_claude_host", "skills/project-start/scripts/project_start.py")

CLAUDE_MARKERS = ("CLAUDECODE", "CLAUDE_PLUGIN_ROOT")


class ClaudeHostDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()
        (self.home / ".codex" / "skills").mkdir(parents=True)
        (self.home / ".claude" / "skills").mkdir(parents=True)
        self.addCleanup(self.temp.cleanup)

    def _env(self, **extra: str) -> dict[str, str]:
        env = {"HOME": str(self.home), "PATH": os.environ.get("PATH", "")}
        env.update(extra)
        return env

    # --- Codex-режим: поведение байт-в-байт прежнее -------------------------

    def test_codex_host_inventory_homes_unchanged(self) -> None:
        with mock.patch.dict(os.environ, self._env(), clear=True):
            homes = inventory.codex_homes([])
        self.assertEqual(homes, [self.home / ".codex"])

    def test_codex_host_maintenance_roots_unchanged(self) -> None:
        with mock.patch.dict(os.environ, self._env(), clear=True):
            roots = maintenance.skill_roots(None)
        self.assertNotIn(self.home / ".claude" / "skills", roots)
        self.assertNotIn(REPO / "skills", roots)
        self.assertEqual(roots[0], self.home / ".codex" / "skills")

    def test_codex_host_codex_home_env_priority_kept(self) -> None:
        override = self.home / "custom-codex"
        (override / "skills").mkdir(parents=True)
        with mock.patch.dict(os.environ, self._env(CODEX_HOME=str(override)), clear=True):
            homes = inventory.codex_homes([])
            roots = maintenance.skill_roots(None)
        self.assertEqual(homes[0], override)
        self.assertEqual(roots[0], override / "skills")

    # --- Claude-режим: добавки строго в хвост -------------------------------

    def test_claude_marker_appends_extras_after_codex_candidates(self) -> None:
        with mock.patch.dict(os.environ, self._env(CLAUDECODE="1"), clear=True):
            homes = inventory.codex_homes([])
            roots = maintenance.skill_roots(None)
        self.assertEqual(homes[0], self.home / ".codex")
        self.assertIn(self.home / ".claude", homes)
        self.assertGreater(homes.index(self.home / ".claude"), homes.index(self.home / ".codex"))
        self.assertEqual(roots[0], self.home / ".codex" / "skills")
        self.assertIn(self.home / ".claude" / "skills", roots)
        self.assertIn(REPO / "skills", roots)  # self-located корень репо/кэша плагина

    def test_plugin_root_marker_works_too(self) -> None:
        with mock.patch.dict(os.environ, self._env(CLAUDE_PLUGIN_ROOT="/x"), clear=True):
            homes = inventory.codex_homes([])
        self.assertIn(self.home / ".claude", homes)

    def test_missing_codex_home_is_portable_fallback(self) -> None:
        import shutil

        shutil.rmtree(self.home / ".codex")
        with mock.patch.dict(os.environ, self._env(), clear=True):
            homes = inventory.codex_homes([])
            roots = maintenance.skill_roots(None)
        self.assertIn(self.home / ".claude", homes)
        self.assertIn(self.home / ".claude" / "skills", roots)

    # --- Явный override глушит добавки даже на Claude-хосте -----------------

    def test_explicit_override_suppresses_extras(self) -> None:
        explicit = self.home / "explicit-home"
        (explicit / "skills").mkdir(parents=True)
        with mock.patch.dict(os.environ, self._env(CLAUDECODE="1"), clear=True):
            homes = inventory.codex_homes([str(explicit)])
            roots = maintenance.skill_roots(str(explicit / "skills"))
            helper_ps = project_start.claude_host_skill_roots(True)
        self.assertNotIn(self.home / ".claude", homes)
        self.assertNotIn(self.home / ".claude" / "skills", roots)
        self.assertEqual(helper_ps, [])
        self.assertIn(explicit, homes)

    # --- Хелпер project_start согласован с maintenance ----------------------

    def test_project_start_helper_matches_contract(self) -> None:
        with mock.patch.dict(os.environ, self._env(CLAUDECODE="1"), clear=True):
            extras = project_start.claude_host_skill_roots(False)
        self.assertEqual(extras[-1], self.home / ".claude" / "skills")
        self.assertEqual(extras[0], REPO / "skills")
        with mock.patch.dict(os.environ, self._env(), clear=True):
            self.assertEqual(project_start.claude_host_skill_roots(False), [])


if __name__ == "__main__":
    unittest.main()
