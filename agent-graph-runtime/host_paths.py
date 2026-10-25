"""Provider-specific discovery without importing another provider's profile."""
from __future__ import annotations

import os
from pathlib import Path


def _unique(paths: list[Path]) -> list[Path]:
    result = []
    for path in paths:
        path = path.expanduser().resolve()
        if path not in result:
            result.append(path)
    return result


def located_skills(script: str | Path) -> Path | None:
    return next((parent for parent in Path(script).resolve().parents if parent.name == "skills"), None)


def located_native_home(script: str | Path) -> Path | None:
    skills = located_skills(script)
    if skills and (skills.parent / "agent-graph-runtime" / "claude-native.json").is_file():
        return skills.parent
    return None


def claude_active(script: str | Path) -> bool:
    return bool(os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_PLUGIN_ROOT") or located_native_home(script) or not (Path.home() / ".codex").is_dir())


def claude_skill_roots(script: str | Path) -> list[Path]:
    if not claude_active(script):
        return []
    native = located_native_home(script)
    if native:
        return [native / "skills"]
    roots = []
    skills = located_skills(script)
    if skills and (located_native_home(script) or not (skills.parent / "config.toml").is_file() and skills.parent.name != ".codex"):
        roots.append(skills)
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin:
        roots.append(Path(plugin) / "skills")
    configured = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    roots.append(configured / "skills")
    return _unique(roots)


def claude_homes(script: str | Path) -> list[Path]:
    return _unique([root.parent for root in claude_skill_roots(script)])
