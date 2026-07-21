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
        ROOT / "skills" / "agent-graph-builder" / "scripts" / "graph_contract.py",
        ROOT / "skills" / "research" / "scripts" / "research_graph.py",
        ROOT / "skills" / "project-start" / "scripts" / "project_graph.py",
        ROOT / "skills" / "project-start" / "scripts" / "project_start.py",
        ROOT / "skills" / "project-start" / "scripts" / "project_maintenance.py",
        ROOT / "skills" / "task-delivery" / "scripts" / "task_graph.py",
    ]
    for script in scripts:
        py_compile.compile(str(script), doraise=True)
    for config in sorted((ROOT / "agents").glob("*.toml")):
        tomllib.loads(config.read_text(encoding="utf-8"))
    dependencies = json.loads(
        (ROOT / "skills" / "agent-graph-builder" / "skill-dependencies.json").read_text(encoding="utf-8")
    )
    if dependencies != {
        "schema_version": 1,
        "required_skills": [
            {
                "name": "skill-creator",
                "phase": "scaffold-and-validate",
                "reason": "Owns generic skill structure, metadata generation, progressive disclosure and base validation.",
            }
        ],
    }:
        raise RuntimeError("Agent Graph Builder must retain its exact skill-creator dependency contract")
    graph = json.loads((ROOT / "skills" / "research" / "graph.json").read_text(encoding="utf-8"))
    if graph.get("schema_version") != 2 or set(graph["nodes"]) != {"work", "verify", "complete"}:
        raise RuntimeError("Research graph node contract changed unexpectedly")
    if graph.get("default_depth") != "auto" or graph["limits"]["fast"]["max_parallel_scouts"] != 0:
        raise RuntimeError("Research fast path must remain native and single-agent by default")
    project_graph = json.loads((ROOT / "skills" / "project-start" / "graph.json").read_text(encoding="utf-8"))
    if set(project_graph["routes"]) != {"bootstrap", "maintenance"}:
        raise RuntimeError("Project Start must expose exactly bootstrap and maintenance routes")
    if project_graph.get("schema_version") != 2 or project_graph.get("default_mode") != "auto":
        raise RuntimeError("Project Start v3 must use schema 2 and auto mode")
    if project_graph["legacy_v2_bootstrap"]["phases"] != [
        "discovery", "foundation", "planning", "tickets", "execution", "complete"
    ]:
        raise RuntimeError("Project Start compatibility phases changed unexpectedly")
    if set(project_graph["legacy_v2_bootstrap"]["events"]) != {"foundation", "tickets", "completion"}:
        raise RuntimeError("Project Start compatibility events changed unexpectedly")
    for mode in ("bootstrap", "maintenance"):
        route = project_graph["routes"][mode]
        if route.get("entry") != "work" or route.get("terminal") != "complete":
            raise RuntimeError(f"Project Start {mode} entry/terminal changed unexpectedly")
        if set(route["nodes"]) != {"work", "verify", "complete"}:
            raise RuntimeError(f"Project Start {mode} must remain a three-node control graph")
    if project_graph["limits"]["maintenance"]["max_parallel_explorers"] > 2:
        raise RuntimeError("Project Start maintenance explorer bound is too high")
    verifier_prompt = (ROOT / "agents" / "project_docs_verifier.toml").read_text(encoding="utf-8")
    if "schema_version 1" not in verifier_prompt or "schema_version 3" not in verifier_prompt:
        raise RuntimeError("Project Start verifier must remain dual-compatible with active v2 and new v3 runs")
    if not (ROOT / "skills" / "project-start" / "references" / "legacy-v2-resume.md").is_file():
        raise RuntimeError("Project Start active-v2 resume instructions are missing")
    task_graph = json.loads((ROOT / "skills" / "task-delivery" / "graph.json").read_text(encoding="utf-8"))
    if task_graph.get("schema_version") != 2 or task_graph.get("default_mode") != "full":
        raise RuntimeError("Task Delivery v3 must use schema 2 and full default mode")
    if set(task_graph.get("routes", {})) != {"plan", "implement", "full"}:
        raise RuntimeError("Task Delivery must expose plan, implement and full routes")
    for mode in ("plan", "implement", "full"):
        if set(task_graph["routes"][mode]["nodes"]) != {"work", "verify", "complete"}:
            raise RuntimeError(f"Task Delivery {mode} must remain a three-node control graph")
    if set(task_graph.get("profiles", {})) != {"light", "standard", "complex", "critical"}:
        raise RuntimeError("Task Delivery risk profiles changed unexpectedly")
    limits = task_graph["limits"]
    if limits["max_agents_per_run"] > 5 or limits["max_parallel_agents"] > 2:
        raise RuntimeError("Task Delivery agent bounds are too high")
    for role in ("task_plan_reviewer", "task_result_reviewer", "task_risk_reviewer"):
        prompt = (ROOT / "agents" / f"{role}.toml").read_text(encoding="utf-8")
        if "spawn descendants" not in prompt or "commit" not in prompt:
            raise RuntimeError(f"Task Delivery role {role} must remain leaf-only and non-committing")
    recovery_root = ROOT / "skills" / "development-recovery"
    if (recovery_root / "graph.json").exists():
        raise RuntimeError("Development Recovery must remain independent of graph runtime")
    recovery_skill = (recovery_root / "SKILL.md").read_text(encoding="utf-8")
    for required in ("first false assumption", "rebuild-from-checkpoint", "repair-forward"):
        if required not in recovery_skill:
            raise RuntimeError(f"Development Recovery contract is missing: {required}")
    recovery_policy = (ROOT / "policies" / "development-recovery.md").read_text(encoding="utf-8")
    if "$development-recovery" not in recovery_policy or "regardless of which graph" not in recovery_policy:
        raise RuntimeError("Global Development Recovery trigger is missing or graph-coupled")
    discovery_policy = (ROOT / "policies" / "large-codebase-discovery.md").read_text(encoding="utf-8")
    for required in (
        "Do not finalize a plan or specification",
        "Never spawn more than two internal explorers",
        "A third child is permitted only",
        "generic `explorer` and `researcher` roles",
        "A timeout is not completion",
        "compact summary alone",
    ):
        if required not in discovery_policy:
            raise RuntimeError(f"Large-codebase discovery policy is missing: {required}")
    if (ROOT / "skills" / "codebase-discovery").exists():
        raise RuntimeError("Large-codebase discovery must reuse existing roles instead of adding a skill")
    graph_validator = ROOT / "skills" / "agent-graph-builder" / "scripts" / "graph_contract.py"
    for skill in ("project-start", "research", "task-delivery"):
        run([sys.executable, str(graph_validator), "validate", "--skill-dir", str(ROOT / "skills" / skill)])
    skill_validator = find_skill_validator()
    if skill_validator:
        for skill in ("agent-graph-builder", "development-recovery", "project-start", "research", "task-delivery"):
            run([sys.executable, str(skill_validator), str(ROOT / "skills" / skill)])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    run([sys.executable, "-m", "unittest", "skills/research/scripts/test_research_graph.py", "-v"])
    run([sys.executable, "-m", "unittest", "skills/agent-graph-builder/scripts/test_graph_contract.py", "-v"])
    run([sys.executable, "skills/project-start/scripts/test_project_start.py"])
    run([sys.executable, "skills/project-start/scripts/test_project_maintenance.py"])
    run([sys.executable, "-m", "unittest", "skills/project-start/scripts/test_project_graph.py", "-v"])
    run([sys.executable, "skills/task-delivery/scripts/test_task_delivery.py"])
    run([sys.executable, "-m", "unittest", "skills/task-delivery/scripts/test_task_graph.py", "-v"])
    print("All workflow checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
