#!/usr/bin/env python3
"""Secret-safe, bounded capability inventory for task-delivery."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


TABLE_RE = re.compile(r"^\s*\[([^]]+)]\s*$")
KEY_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*=")


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def discover_instructions(root: Path) -> list[str]:
    names = {"AGENTS.md", "CLAUDE.md", "CONTEXT.md"}
    found: set[Path] = set()
    current = root.resolve()
    while True:
        for name in names:
            path = current / name
            if path.is_file():
                found.add(path)
        if current.parent == current:
            break
        current = current.parent
    listed = run_git(root, "ls-files")
    if listed and listed.returncode == 0:
        for raw in listed.stdout.splitlines():
            path = root / raw
            if path.name in names:
                found.add(path)
    return sorted(str(path) for path in found)


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_safe_config(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "mcp_servers": set(),
        "plugins": set(),
        "feature_keys": set(),
        "agent_keys": set(),
        "hook_state_events": set(),
    }
    if not path.is_file():
        return _serializable(result)
    current = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        table = TABLE_RE.match(line)
        if table:
            current = table.group(1)
            if current.startswith("mcp_servers.") and ".env" not in current:
                result["mcp_servers"].add(unquote(current[len("mcp_servers.") :]))
            elif current.startswith("plugins."):
                result["plugins"].add(unquote(current[len("plugins.") :]))
            elif current.startswith("hooks.state."):
                for event in ("pre_tool_use", "post_tool_use", "pre_compact", "session_start", "user_prompt_submit", "subagent_start", "subagent_stop", "stop"):
                    if f":{event}:" in current:
                        result["hook_state_events"].add(event)
            continue
        key = KEY_RE.match(line)
        if not key:
            continue
        name = key.group(1)
        if current == "features" and name in {"hooks", "multi_agent", "memories"}:
            result["feature_keys"].add(name)
        elif current == "agents" and name in {"max_threads", "max_depth"}:
            result["agent_keys"].add(name)
    return _serializable(result)


def _serializable(result: dict[str, Any]) -> dict[str, Any]:
    return {key: sorted(value) if isinstance(value, set) else value for key, value in result.items()}


def _claude_host_homes(explicit_given: bool) -> list[Path]:
    """Дополнительные дома харнеса для запуска под Claude Code.

    Добавляются только когда (а) явных --codex-home не передано и (б) процесс
    запущен из Claude Code (маркеры CLAUDECODE / CLAUDE_PLUGIN_ROOT) либо
    ~/.codex отсутствует вовсе. Безусловное добавление подмешивало бы
    поверхности ~/.claude в инвентарь Codex-ранов на машине с двумя CLI.
    """
    if explicit_given:
        return []
    claude_marker = os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not claude_marker and (Path.home() / ".codex").is_dir():
        return []
    homes: list[Path] = []
    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == "skills":
            homes.append(ancestor.parent)
            break
    homes.append(Path.home() / ".claude")
    return homes


def codex_homes(explicit: Iterable[str]) -> list[Path]:
    explicit_paths = [Path(raw).expanduser() for raw in explicit]
    candidates: list[Path] = []
    if os.environ.get("CODEX_HOME"):
        candidates.append(Path(os.environ["CODEX_HOME"]))
    candidates.append(Path.home() / ".codex")
    candidates.extend(explicit_paths)
    candidates.extend(_claude_host_homes(bool(explicit_paths)))
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_dir() and str(resolved) not in seen:
            seen.add(str(resolved))
            unique.append(resolved)
    return unique


def _matches(names: Iterable[str], terms: list[str]) -> list[str]:
    if not terms:
        return []
    lowered = [term.lower() for term in terms]
    return sorted(name for name in names if any(term in name.lower() for term in lowered))


def discover_skills(root: Path, homes: list[Path], terms: list[str]) -> dict[str, dict[str, Any]]:
    locations = [root / ".agents" / "skills", root / ".codex" / "skills"]
    for home in homes:
        locations.extend([home / "skills", home / ".agents" / "skills"])
    result: dict[str, dict[str, Any]] = {}
    for location in locations:
        if not location.is_dir():
            continue
        names = sorted(path.parent.name for path in location.glob("*/SKILL.md"))
        if names:
            result[str(location)] = {"count": len(names), "matches": _matches(names, terms)}
    return result


def discover_hook_events(root: Path, homes: list[Path]) -> list[dict[str, Any]]:
    candidates = [root / ".codex" / "hooks.json"]
    for home in homes:
        candidates.extend(home.glob("plugins/cache/*/*/*/hooks/*.json"))
    result: list[dict[str, Any]] = []
    for path in sorted(set(candidates)):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        hooks = value.get("hooks") if isinstance(value, dict) else None
        if isinstance(hooks, dict) and hooks:
            result.append({"path": str(path), "events": sorted(hooks.keys())})
    return result[:50]


def build_inventory(root: Path, explicit_homes: list[str], terms: list[str]) -> dict[str, Any]:
    homes = codex_homes(explicit_homes)
    git_root = run_git(root, "rev-parse", "--show-toplevel")
    git_status = run_git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    dirty_count = None
    if git_status and git_status.returncode == 0:
        dirty_count = len([line for line in git_status.stdout.splitlines() if line])
    markers = [".project-start", ".planning", ".gsd", "docs/tasks", ".github", ".codex/hooks.json"]
    configs = []
    for home in homes:
        parsed = parse_safe_config(home / "config.toml")
        configs.append(
            {
                "path": parsed["path"],
                "mcp_server_count": len(parsed["mcp_servers"]),
                "mcp_matches": _matches(parsed["mcp_servers"], terms),
                "plugin_count": len(parsed["plugins"]),
                "plugin_matches": _matches(parsed["plugins"], terms),
                "feature_keys_present": parsed["feature_keys"],
                "agent_keys_present": parsed["agent_keys"],
                "hook_state_events": parsed["hook_state_events"],
            }
        )
    return {
        "root": str(root),
        "git_root": git_root.stdout.strip() if git_root and git_root.returncode == 0 else None,
        "dirty_entry_count": dirty_count,
        "instruction_files": discover_instructions(root),
        "workflow_markers": [marker for marker in markers if (root / marker).exists()],
        "codex_homes": [str(home) for home in homes],
        "match_terms": terms,
        "filesystem_skill_candidates": discover_skills(root, homes, terms),
        "config_candidates": configs,
        "hook_manifests": discover_hook_events(root, homes),
        "actual_catalog_required": True,
        "catalog_note": "Имена и наличие — кандидаты. Выбранный MCP/app надо подтвердить безопасным read-only вызовом.",
    }
