#!/usr/bin/env python3
"""Герметичные проверки Claude-слоя: без бинаря claude, только файлы/JSON.

Контракт (этап 3 адаптации):
- Проекция claude/agents/*.md детерминирована и байт-в-байт совпадает с
  регенерацией из agents/*.toml (single source, ручные правки запрещены).
- Имена агентов: lowercase + дефисы, без подчёркиваний (чарсет Claude Code).
- Каждый allowlist инструментов — явный, из пинового набора, без спавн-инструмента.
- Чётность ролей: все роли graph.json (кроме root) резолвятся в канон или шаблон.
- Неизвестные значения полей toml — жёсткий отказ генератора, не молчаливый дефолт.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sync = _load("claude_agents_sync_test", "scripts/claude_agents_sync.py")

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def frontmatter_fields(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    assert match, "нет YAML-frontmatter"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if line.startswith("#") or not line.strip():
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


class ClaudePackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rendered = sync.render_all()

    def test_projection_is_deterministic(self) -> None:
        self.assertEqual(self.rendered, sync.render_all())

    def test_committed_files_match_regeneration_exactly(self) -> None:
        out_dir = REPO / "agents"
        on_disk = {path.stem: path.read_text(encoding="utf-8") for path in sorted(out_dir.glob("*.md"))}
        self.assertEqual(sorted(on_disk), sorted(self.rendered))
        for name, text in self.rendered.items():
            self.assertEqual(on_disk[name], text, f"agents/{name}.md разошёлся с каноном")

    def test_md_and_toml_basenames_never_collide(self) -> None:
        toml_names = {path.stem for path in (REPO / "agents").glob("*.toml")}
        md_names = {path.stem for path in (REPO / "agents").glob("*.md")}
        self.assertFalse(toml_names & md_names, "basename-коллизия toml/md в agents/")

    def test_names_are_claude_safe(self) -> None:
        for name in self.rendered:
            self.assertRegex(name, r"^[a-z][a-z0-9-]*$")
            self.assertNotIn("_", name)

    def test_every_agent_has_explicit_pinned_tools(self) -> None:
        allowed = set(sync.WRITE_TOOLS) | set(sync.WEB_TOOLS)
        for name, text in self.rendered.items():
            fields = frontmatter_fields(text)
            self.assertIn("tools", fields, f"{name}: нет явного tools-allowlist")
            tools = [tool.strip() for tool in fields["tools"].split(",")]
            self.assertTrue(tools, name)
            for tool in tools:
                self.assertIn(tool, allowed, f"{name}: инструмент {tool} вне пинового набора")
                self.assertNotIn(tool, sync.FORBIDDEN_TOOL_NAMES, f"{name}: спавн-инструмент запрещён")
            self.assertEqual(fields["name"], name)
            self.assertIn(fields["model"], {"sonnet", "opus"})
            self.assertIn(fields["effort"], set(sync.EFFORT_MAP.values()))

    def test_read_only_roles_deny_write_tools(self) -> None:
        for role, spec in sync.canonical_roles().items():
            if spec["sandbox_mode"] != "read-only":
                continue
            fields = frontmatter_fields(self.rendered[sync.claude_name(role)])
            self.assertEqual(
                fields.get("disallowedTools"),
                ", ".join(sync.WRITE_DENY),
                f"{role}: read-only роль обязана запрещать запись",
            )
            self.assertNotIn("Edit", fields["tools"])
            self.assertNotIn("Write", fields["tools"])

    def test_generated_header_present(self) -> None:
        for name, text in self.rendered.items():
            self.assertTrue(
                "GENERATED FROM agents/" in text or "TEMPLATE ROLE" in text,
                f"{name}: нет шапки о происхождении",
            )

    def test_graph_role_parity(self) -> None:
        self.assertEqual(sync.check_parity(self.rendered), [])

    def test_graph_roles_cover_known_set(self) -> None:
        roles = sync.graph_roles()
        self.assertIn("root", roles)
        self.assertIn("explorer", roles)
        self.assertIn("task_worker", roles)

    def test_unknown_model_hard_fails(self) -> None:
        spec = {
            "model": "gpt-99-unknown",
            "model_reasoning_effort": "high",
            "sandbox_mode": "read-only",
            "developer_instructions": "x",
        }
        with self.assertRaises(SystemExit):
            sync.render_role("fake_role", spec, "desc")

    def test_unknown_effort_and_sandbox_hard_fail(self) -> None:
        base = {"model": "gpt-5.6-sol", "developer_instructions": "x"}
        with self.assertRaises(SystemExit):
            sync.render_role("fake", {**base, "model_reasoning_effort": "ultra", "sandbox_mode": "read-only"}, "d")
        with self.assertRaises(SystemExit):
            sync.render_role("fake", {**base, "model_reasoning_effort": "high", "sandbox_mode": "full"}, "d")

    def test_plugin_manifest_shape(self) -> None:
        plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["skills"], ["./skills/"])
        # Поля agents в схеме манифеста CC не существует — агенты открываются
        # конвенцией из корневого agents/ (см. ECC PLUGIN_SCHEMA_NOTES).
        self.assertNotIn("agents", plugin)
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["plugins"][0]["name"], plugin["name"])
        self.assertEqual(marketplace["plugins"][0]["source"], "./")


if __name__ == "__main__":
    unittest.main()
