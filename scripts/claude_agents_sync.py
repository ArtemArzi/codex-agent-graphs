#!/usr/bin/env python3
"""Проекция канона agents/*.toml в сабагентов Claude Code (agents/*.md).

Канон ролей: agents/*.toml + policies/model-routing.toml + описания install.py.
Файлы agents/*.md — машинная проекция ДЛЯ Claude Code, лежащая рядом с toml:
загрузчик плагинов CC обнаруживает агентов только конвенцией из корневого
agents/ (поля `agents` в схеме plugin.json не существует — см. ECC
PLUGIN_SCHEMA_NOTES). Для Codex эти .md невидимы: install.py копирует агентов
строго поимённо как agents/<role>.toml. Ручные правки .md не проходят гейт
--check в check_all.py.

Использование:
    claude_agents_sync.py --check   сверка: проекция байт-в-байт + чётность ролей
    claude_agents_sync.py --write   перегенерация agents/*.md

Модели Claude явно сохранены в общем manifest независимо от моделей Codex. Любое неизвестное
значение любого поля — немедленный отказ (никаких молчаливых дефолтов):
устаревший маппинг должен ломать сборку, а не тихо портить агентов.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Provider settings are explicit and independent in the routing manifest.
# Changing Codex routing must not invent an equivalence to Claude models.
EFFORT_MAP = {"medium": "medium", "high": "high", "xhigh": "xhigh", "max": "max"}
DEFAULT_WEB = "disabled"  # web_search отсутствует в 2 из 13 toml — трактуем как disabled
# Native Codex defaults that require an explicit Claude tool projection.
# The default role inherits parent write authority in Codex; Claude still
# requires an implementation assignment in its unchanged canonical prompt.
CLAUDE_NATIVE_DEFAULTS = {
    "default": {"sandbox_mode": "workspace-write"},
    "researcher": {"web_search": "live"},
    "vacancy_researcher": {"web_search": "live"},
}

KNOWN_TOML_KEYS = {
    "model",
    "model_reasoning_effort",
    "sandbox_mode",
    "web_search",
    "developer_instructions",
    # Explicit Codex-only native metadata; Claude uses canonical role IDs and
    # descriptions, but has no nickname_candidates frontmatter equivalent.
    "name", "description", "nickname_candidates",
}

# Пиновый безопасный набор инструментов. Спавн-инструмент называется Agent
# (legacy-имя Task) и НИКОГДА не включается: паритет с [agents] max_depth = 1.
READ_TOOLS = ["Read", "Grep", "Glob", "Bash"]
WRITE_TOOLS = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]
WEB_TOOLS = ["WebSearch", "WebFetch"]
WRITE_DENY = ["Write", "Edit", "NotebookEdit"]
FORBIDDEN_TOOL_NAMES = {"Agent", "Task"}

# Роли графов, у которых нет и не должно быть agents/*.toml.
GRAPH_ROLE_EXEMPT = {"root"}  # root — сама корневая сессия, отдельный агент не нужен

def _load_install_module():
    spec = importlib.util.spec_from_file_location("graph_install", ROOT / "scripts" / "install.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


def role_descriptions() -> dict[str, str]:
    """Описания ролей — из managed-блока install.py (единый источник)."""
    install = _load_install_module()
    parsed = tomllib.loads(install.managed_block())
    return {role: spec["description"] for role, spec in parsed["agents"].items()}


def canonical_roles() -> dict[str, dict]:
    roles: dict[str, dict] = {}
    policy = _load_install_module().routing.load_policy()
    for role, projection in sorted(policy["roles"].items()):
        path = ROOT / projection["template"]
        data = {**CLAUDE_NATIVE_DEFAULTS.get(role, {}),
                **tomllib.loads(path.read_text(encoding="utf-8"))}
        if "name" in data and data["name"] != role:
            raise SystemExit(f"{path.name}: native role name differs from policy ID")
        if "description" in data and (not isinstance(data["description"], str) or not data["description"].strip()):
            raise SystemExit(f"{path.name}: invalid native description")
        nicknames = data.get("nickname_candidates", [])
        if not isinstance(nicknames, list) or any(not isinstance(item, str) for item in nicknames):
            raise SystemExit(f"{path.name}: invalid Codex-only nickname metadata")
        unknown = set(data) - KNOWN_TOML_KEYS
        if unknown:
            raise SystemExit(f"{path.name}: неизвестные ключи toml {sorted(unknown)} — обнови маппинги генератора")
        routing = _load_install_module().routing
        route = routing.role_route(role)
        if "model" in data or "model_reasoning_effort" in data:
            raise SystemExit(f"{path.name}: модели должны находиться только в model-routing.toml")
        roles[role] = {**data, "model": route["model"], "model_reasoning_effort": route["effort"]}
    return roles


def claude_name(role: str) -> str:
    """Имя сабагента CC: lowercase + дефисы (подчёркивания запрещены докой)."""
    name = role.replace("_", "-")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        raise SystemExit(f"Роль {role}: имя {name} не проходит чарсет Claude Code")
    return name


def _tools_for(sandbox_mode: str, web_search: str) -> tuple[list[str], list[str]]:
    if sandbox_mode == "read-only":
        tools, deny = list(READ_TOOLS), list(WRITE_DENY)
    elif sandbox_mode == "workspace-write":
        tools, deny = list(WRITE_TOOLS), []
    else:
        raise SystemExit(f"Неизвестный sandbox_mode: {sandbox_mode!r}")
    if web_search == "live":
        tools.extend(WEB_TOOLS)
    elif web_search != "disabled":
        raise SystemExit(f"Неизвестный web_search: {web_search!r}")
    bad = FORBIDDEN_TOOL_NAMES.intersection(tools)
    if bad:
        raise SystemExit(f"Запрещённые инструменты в allowlist: {sorted(bad)}")
    return tools, deny


def render_role(role: str, spec: dict, description: str) -> str:
    routing = _load_install_module().routing
    policy = routing.load_policy()
    projection = policy["roles"].get(role, {})
    if "claude_model" not in projection:
        raise SystemExit(f"{role}: отсутствует явная независимая проекция Claude")
    route = routing.role_route(role, policy)
    if (spec["model"], spec["model_reasoning_effort"]) != (route["model"], route["effort"]):
        raise SystemExit(f"{role}: модель/effort расходятся с model-routing.toml")
    model, effort = projection["claude_model"], projection["claude_effort"]
    if model not in ("sonnet", "opus", "inherit") or effort not in EFFORT_MAP:
        raise SystemExit(f"{role}: неизвестные настройки проекции Claude")
    tools, deny = _tools_for(spec["sandbox_mode"], spec.get("web_search", DEFAULT_WEB))
    deny = list(dict.fromkeys([*deny, "Agent", "Task"]))

    lines = [
        "---",
        f"# GENERATED FROM {projection['template']} - regenerate: scripts/claude_agents_sync.py --write",
        f"# graph.json role id: {role}",
        f"name: {claude_name(role)}",
        f"description: {description}",
        f"model: {model}",
        f"effort: {effort}",
        f"tools: {', '.join(tools)}",
    ]
    if deny:
        lines.append(f"disallowedTools: {', '.join(deny)}")
    lines.append("---")
    body = (f"Claude Code projection of canonical role {role}. Use the provider model in "
            "frontmatter. Sol/Astra/Codex model names in the shared instructions describe "
            "the Codex policy, not your actual provider identity. Preserve their scope "
            "and review thresholds; never claim to be a Sol/Astra reviewer.\n\n" +
            spec["developer_instructions"].strip())
    return "\n".join(lines) + "\n\n" + body + "\n"


def render_template_roles() -> dict[str, str]:
    """Legacy API; explorer is now projected from its canonical native template."""
    return {}


def render_all() -> dict[str, str]:
    """Полная проекция: имя файла (без .md) → содержимое."""
    descriptions = role_descriptions()
    rendered: dict[str, str] = {}
    for role, spec in canonical_roles().items():
        if role not in descriptions:
            raise SystemExit(f"{role}: нет описания в managed-блоке install.py")
        rendered[claude_name(role)] = render_role(role, spec, spec.get("description", descriptions[role]))
    for role, text in render_template_roles().items():
        if role in rendered:
            raise SystemExit(f"Шаблонная роль {role} конфликтует с канонической")
        rendered[claude_name(role)] = text
    return rendered


def graph_roles() -> set[str]:
    found: set[str] = set()
    for graph_path in sorted((ROOT / "skills").glob("*/graph.json")):
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        found.update(graph.get("optional_agents", []))

        def walk(node):
            if isinstance(node, dict):
                role = node.get("role")
                if isinstance(role, str):
                    found.add(role)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(graph)
    return found


def check_parity(rendered: dict[str, str]) -> list[str]:
    errors: list[str] = []
    toml_roles = set(canonical_roles())
    template_roles = set(render_template_roles())
    install = _load_install_module()
    if set(install.AGENT_ROLES) != toml_roles:
        errors.append(
            f"install.py AGENT_ROLES != agents/*.toml: {sorted(set(install.AGENT_ROLES) ^ toml_roles)}"
        )
    for role in sorted(graph_roles() - GRAPH_ROLE_EXEMPT):
        if role not in toml_roles and role not in template_roles:
            errors.append(f"Роль {role} из graph.json не резолвится ни в agents/*.toml, ни в шаблонах")
    expected_names = {claude_name(role) for role in toml_roles | template_roles}
    if set(rendered) != expected_names:
        errors.append(f"Проекция не сходится с ожидаемым набором имён: {sorted(set(rendered) ^ expected_names)}")
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if plugin.get("skills") != ["./skills/"]:
        errors.append(f'plugin.json skills != ["./skills/"]: {plugin.get("skills")}')
    if "agents" in plugin:
        errors.append('plugin.json содержит поле "agents" — валидатор CC его отвергает; агенты открываются конвенцией из agents/')
    return errors


def cmd_check() -> int:
    rendered = render_all()
    errors = check_parity(rendered)
    out_dir = ROOT / "agents"
    on_disk = {path.stem: path for path in sorted(out_dir.glob("*.md"))} if out_dir.is_dir() else {}
    for name in sorted(set(rendered) | set(on_disk)):
        if name not in rendered:
            errors.append(f"agents/{name}.md лишний: роли в каноне нет")
        elif name not in on_disk:
            errors.append(f"agents/{name}.md отсутствует: запусти --write")
        elif on_disk[name].read_text(encoding="utf-8") != rendered[name]:
            errors.append(f"agents/{name}.md отличается от регенерации: правки руками запрещены, запусти --write")
    if errors:
        print("claude_agents_sync --check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"claude_agents_sync --check: OK ({len(rendered)} агентов в синхроне с каноном)")
    return 0


def cmd_write() -> int:
    rendered = render_all()
    errors = check_parity(rendered)
    if errors:
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    out_dir = ROOT / "agents"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.md"):
        if stale.stem not in rendered:
            stale.unlink()
            print(f"удалён лишний {stale.name}")
    for name, text in sorted(rendered.items()):
        target = out_dir / f"{name}.md"
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            target.write_text(text, encoding="utf-8")
            print(f"записан {target.relative_to(ROOT)}")
    print(f"Готово: {len(rendered)} агентов.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="сверить проекцию и чётность ролей")
    group.add_argument("--write", action="store_true", help="перегенерировать claude/agents/*.md")
    args = parser.parse_args()
    return cmd_check() if args.check else cmd_write()


if __name__ == "__main__":
    sys.exit(main())
