#!/usr/bin/env python3
"""Run repository validation without third-party dependencies."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def find_skill_validator() -> Path | None:
    candidates = [
        Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py",
        Path.home() / ".agents" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py",
    ]
    windows_users = Path("/mnt/c/Users")
    if windows_users.is_dir():
        candidates.extend(
            windows_users.glob("*/.codex/skills/.system/skill-creator/scripts/quick_validate.py")
        )
    return next((path for path in candidates if path.is_file()), None)


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({' '.join(command)}):\n{completed.stdout}\n{completed.stderr}"
        )
    if completed.stdout.strip():
        print(completed.stdout.strip())


def main() -> int:
    scripts = [
        ROOT / "scripts" / "install.py",
        ROOT / "scripts" / "check_all.py",
        ROOT / "skills" / "research" / "scripts" / "research_graph.py",
    ]
    for script in scripts:
        py_compile.compile(str(script), doraise=True)
    for config in sorted((ROOT / "agents").glob("*.toml")):
        tomllib.loads(config.read_text(encoding="utf-8"))
    graph = json.loads((ROOT / "skills" / "research" / "graph.json").read_text(encoding="utf-8"))
    if set(graph["nodes"]) != {
        "intake",
        "capability_discovery",
        "plan",
        "collect",
        "evidence",
        "reconcile",
        "gap_check",
        "synthesize",
        "verify",
        "complete",
    }:
        raise RuntimeError("Research graph node contract changed unexpectedly")
    skill_validator = find_skill_validator()
    if skill_validator:
        for skill in ("project-start", "research", "task-delivery"):
            run([sys.executable, str(skill_validator), str(ROOT / "skills" / skill)])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    run([sys.executable, "-m", "unittest", "skills/research/scripts/test_research_graph.py", "-v"])
    run([sys.executable, "skills/project-start/scripts/test_project_start.py"])
    run([sys.executable, "skills/task-delivery/scripts/test_task_delivery.py"])
    print("All graph-skill checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
