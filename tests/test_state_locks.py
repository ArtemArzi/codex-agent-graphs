#!/usr/bin/env python3
"""Контракт .state.lock, единый для всех пяти контроллеров графов.

Закрывает найденный дрейф:
- research: протухший лок ЖИВОГО процесса нельзя красть (до фикса крался
  по одному лишь возрасту, без проверки PID);
- continuous-improvement: протухший лок МЁРТВОГО процесса обязан
  забираться (до фикса SIGKILL владельца навсегда блокировал run-dir).

Эталон поведения — task-delivery: takeover только при (возраст > порога)
И (PID мёртв). Сообщения об ошибках каждого контроллера сохранены как есть.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).parents[1]


def _load(alias: str, relative: str):
    path = REPO / relative
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(alias, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


# (метка, путь, имя класса ошибки, kwarg ожидания, kwarg порога протухания)
SPECS = [
    ("task-delivery", "skills/task-delivery/scripts/task_graph.py", "GraphError", "wait_seconds", "stale_seconds"),
    ("project-start/graph", "skills/project-start/scripts/project_graph.py", "GraphError", "wait_seconds", "stale_seconds"),
    ("project-start/maintenance", "skills/project-start/scripts/project_maintenance.py", "MaintenanceError", "wait_seconds", "stale_seconds"),
    ("research", "skills/research/scripts/research_graph.py", "GraphError", "wait_seconds", "stale_after_seconds"),
    ("continuous-improvement", "skills/continuous-improvement/scripts/continuous_improvement_graph.py", "GraphError", "wait_seconds", "stale_seconds"),
]

MODULES = {
    label: (_load(f"lock_test_{label.replace('/', '_').replace('-', '_')}", rel), err, wait_kw, stale_kw)
    for label, rel, err, wait_kw, stale_kw in SPECS
}


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


class StateLockContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def _run_dir(self, label: str) -> Path:
        run_dir = Path(self.temp.name) / label.replace("/", "_")
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _plant_lock(self, module, run_dir: Path, pid: int, age_seconds: float = 0.0) -> Path:
        lock = run_dir / module.LOCK_NAME
        lock.write_text(f"pid={pid} at=test\n", encoding="utf-8")
        if age_seconds:
            stamp = time.time() - age_seconds
            os.utime(lock, (stamp, stamp))
        return lock

    def test_fresh_lock_contention_raises_and_preserves_lock(self) -> None:
        for label, (module, err_name, wait_kw, stale_kw) in MODULES.items():
            with self.subTest(controller=label):
                run_dir = self._run_dir(label)
                lock = self._plant_lock(module, run_dir, pid=os.getpid())
                error_type = getattr(module, err_name)
                kwargs = {wait_kw: 0.2, stale_kw: 120}
                with self.assertRaises(error_type):
                    with module.state_lock(run_dir, **kwargs):
                        self.fail("свежий чужой лок не должен был отдаться")
                self.assertTrue(lock.exists(), "чужой лок нельзя удалять при отказе")
                self.assertIn(f"pid={os.getpid()}", lock.read_text(encoding="utf-8"))

    def test_stale_lock_of_live_process_is_not_stolen(self) -> None:
        for label, (module, err_name, wait_kw, stale_kw) in MODULES.items():
            with self.subTest(controller=label):
                run_dir = self._run_dir(label)
                lock = self._plant_lock(module, run_dir, pid=os.getpid(), age_seconds=10_000)
                error_type = getattr(module, err_name)
                kwargs = {wait_kw: 0.2, stale_kw: 120}
                with self.assertRaises(error_type):
                    with module.state_lock(run_dir, **kwargs):
                        self.fail("протухший лок живого процесса украден")
                self.assertTrue(lock.exists())

    def test_stale_lock_of_dead_process_is_reclaimed(self) -> None:
        dead = _dead_pid()
        for label, (module, _err, wait_kw, stale_kw) in MODULES.items():
            with self.subTest(controller=label):
                run_dir = self._run_dir(label)
                lock = self._plant_lock(module, run_dir, pid=dead, age_seconds=10_000)
                kwargs = {wait_kw: 0.5, stale_kw: 120}
                with module.state_lock(run_dir, **kwargs):
                    self.assertTrue(lock.exists())
                    self.assertIn(f"pid={os.getpid()}", lock.read_text(encoding="utf-8"))
                self.assertFalse(lock.exists(), "лок обязан сниматься при выходе")

    def test_lock_released_on_exit_and_reacquirable(self) -> None:
        for label, (module, _err, wait_kw, stale_kw) in MODULES.items():
            with self.subTest(controller=label):
                run_dir = self._run_dir(label)
                lock = run_dir / module.LOCK_NAME
                kwargs = {wait_kw: 0.5, stale_kw: 120}
                with module.state_lock(run_dir, **kwargs):
                    self.assertTrue(lock.exists())
                self.assertFalse(lock.exists())
                with module.state_lock(run_dir, **kwargs):
                    self.assertTrue(lock.exists())
                self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
