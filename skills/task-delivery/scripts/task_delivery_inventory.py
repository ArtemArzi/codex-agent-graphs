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
    names = {"AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", "CONTEXT.md", ".claude/AGENTS.md", ".claude/CLAUDE.md"}
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


def parse_safe_claude_config(home: Path, root: Path) -> dict[str, Any]:
    """Read metadata only. Never return JSON values, env, headers or commands."""
    result = {"path": str(home), "mcp_servers": set(), "plugins": set(),
              "feature_keys": set(), "agent_keys": set(), "hook_state_events": set()}
    paths = [home / "settings.json", home / "settings.local.json", home / ".claude.json",
             root / ".mcp.json", root / ".claude/settings.json", root / ".claude/settings.local.json"]
    if home.name == ".claude":
        paths.append(home.parent / ".claude.json")
    for path in paths:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        servers = value.get("mcpServers", {})
        if isinstance(servers, dict):
            result["mcp_servers"].update(servers)
        projects = value.get("projects", {})
        project = projects.get(str(root.resolve()), {}) if isinstance(projects, dict) else {}
        project_servers = project.get("mcpServers", {}) if isinstance(project, dict) else {}
        if isinstance(project_servers, dict):
            result["mcp_servers"].update(project_servers)
        plugins = value.get("enabledPlugins", {})
        if isinstance(plugins, dict):
            result["plugins"].update(name for name, enabled in plugins.items() if enabled is True)
        hooks = value.get("hooks", {})
        if isinstance(hooks, dict):
            result["hook_state_events"].update(hooks)
    for directory in [home / "agents", root / ".claude/agents"]:
        if directory.is_dir() and not directory.is_symlink():
            for path in directory.rglob("*.md"):
                if path.is_symlink() or path.stat().st_size > 128 * 1024:
                    continue
                match = re.search(r"(?m)^name: ([a-z][a-z0-9-]*)\s*$", path.read_text(encoding="utf-8"))
                if match:
                    result["agent_keys"].add(match.group(1))
    return _serializable(result)


def _serializable(result: dict[str, Any]) -> dict[str, Any]:
    return {key: sorted(value) if isinstance(value, set) else value for key, value in result.items()}


def _cag_host_paths():
    import importlib.util
    for parent in Path(__file__).resolve().parents:
        source = parent / "agent-graph-runtime" / "host_paths.py"
        if source.is_file():
            spec = importlib.util.spec_from_file_location("cag_host_paths", source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("CAG host runtime missing; reinstall this skill and its sibling runtime")


def _claude_host_homes(explicit_given: bool) -> list[Path]:
    return [] if explicit_given else _cag_host_paths().claude_homes(__file__)


def codex_homes(explicit: Iterable[str]) -> list[Path]:
    explicit_paths = [Path(raw).expanduser() for raw in explicit]
    candidates: list[Path] = []
    if os.environ.get("CODEX_HOME"):
        candidates.append(Path(os.environ["CODEX_HOME"]))
    candidates.append(Path.home() / ".codex")
    candidates.extend(explicit_paths)
    claude_candidates = _claude_host_homes(bool(explicit_paths))
    if claude_candidates:
        candidates = claude_candidates
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
    is_claude = _cag_host_paths().claude_active(__file__)
    locations = [root / ".claude" / "skills"] if is_claude else [root / ".agents" / "skills", root / ".codex" / "skills"]
    for home in homes:
        locations.extend([home / "skills"] if is_claude else [home / "skills", home / ".agents" / "skills"])
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
    if _cag_host_paths().claude_active(__file__):
        candidates = [root / ".claude/settings.json", root / ".claude/settings.local.json"]
        candidates.extend(home / "settings.json" for home in homes)
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
        parsed = (parse_safe_claude_config(home, root) if _cag_host_paths().claude_active(__file__)
                  else parse_safe_config(home / "config.toml"))
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
        "codex_homes": [str(home) for home in homes],  # retained legacy field
        "harness_homes": [str(home) for home in homes],
        "provider": "claude" if _cag_host_paths().claude_active(__file__) else "codex",
        "match_terms": terms,
        "filesystem_skill_candidates": discover_skills(root, homes, terms),
        "config_candidates": configs,
        "hook_manifests": discover_hook_events(root, homes),
        "actual_catalog_required": True,
        "catalog_note": "Имена и наличие — кандидаты. Выбранный MCP/app надо подтвердить безопасным read-only вызовом.",
    }
