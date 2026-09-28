"""One-source Codex routing, rendered without changing unrelated TOML values."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "policies" / "model-routing.toml"
POLICY_TARGET = "model-routing.toml"
POLICY_START = "<!-- BEGIN codex-model-routing -->"
POLICY_END = "<!-- END codex-model-routing -->"


def load_policy(path: Path | None = None) -> dict[str, Any]:
    path = path or POLICY_PATH
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Invalid routing policy: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not data.get("policy_id"):
        raise ValueError("Unsupported routing policy identity")
    for kind in ("root", "auxiliary", "acceptance"):
        if set(data.get(kind, {})) != {"model", "effort"}:
            raise ValueError(f"Incomplete routing class: {kind}")
        if not all(isinstance(v, str) and v for v in data[kind].values()):
            raise ValueError(f"Invalid routing class: {kind}")
    roles = data.get("roles", {})
    if not isinstance(roles, dict) or not roles:
        raise ValueError("Routing policy has no roles")
    for role, spec in roles.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", role):
            raise ValueError(f"Invalid role id: {role}")
        if spec.get("class") not in ("auxiliary", "acceptance"):
            raise ValueError(f"Unknown routing class for {role}")
        relative = Path(spec.get("template", ""))
        if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".toml":
            raise ValueError(f"Unsafe template path for {role}")
        if ("claude_model" in spec) != ("claude_effort" in spec):
            raise ValueError(f"Incomplete independent Claude projection for {role}")
    for key in ("plan_role", "result_role"):
        if roles.get(data.get(key), {}).get("class") != "acceptance":
            raise ValueError(f"{key} must name an acceptance role")
    aliases = data.get("profile_aliases", [])
    if not isinstance(aliases, list) or len(set(aliases)) != len(aliases):
        raise ValueError("Invalid profile aliases")
    if not all(isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_-]+", v) for v in aliases):
        raise ValueError("Unsafe profile alias")
    if not isinstance(data.get("instructions"), str) or not data["instructions"].strip():
        raise ValueError("Routing policy requires acceptance instructions")
    return data


def role_route(role: str, policy: dict[str, Any] | None = None) -> dict[str, str]:
    policy = policy or load_policy()
    return policy[policy["roles"][role]["class"]]


def role_template(role: str) -> Path:
    path = ROOT / load_policy()["roles"][role]["template"]
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Invalid role template: {path}")
    return path


def render_agent(role: str, description: str) -> str:
    template = role_template(role).read_text(encoding="utf-8")
    spec = tomllib.loads(template)
    if "model" in spec or "model_reasoning_effort" in spec:
        raise ValueError(f"{role}: model settings belong only in model-routing.toml")
    route = role_route(role)
    header = ["# Generated from policies/model-routing.toml and the role template."]
    if "name" not in spec:
        header.append(f"name = {json.dumps(role)}")
    if "description" not in spec:
        header.append(f"description = {json.dumps(description)}")
    header.extend((f"model = {json.dumps(route['model'])}",
                   f"model_reasoning_effort = {json.dumps(route['effort'])}", ""))
    rendered = "\n".join(header) + template
    parsed = tomllib.loads(rendered)
    if parsed.get("name") != role or not parsed.get("developer_instructions"):
        raise ValueError(f"Incomplete role template: {role}")
    return rendered


def render_policy() -> str:
    data = load_policy()
    rows = ["# Unified model routing and independent acceptance", "",
            "Generated from `policies/model-routing.toml`; change that source and run the installer.", "",
            "| Role class | Model | Reasoning |", "| --- | --- | --- |"]
    for label, kind in (("Main orchestrator", "root"), ("Auxiliary work and focused reviews", "auxiliary"),
                        ("Fresh whole-plan / whole-result acceptance", "acceptance")):
        rows.append(f"| {label} | `{data[kind]['model']}` | `{data[kind]['effort']}` |")
    rows.extend(("", f"Shared plan role: `{data['plan_role']}`. General result role: `{data['result_role']}`.",
                 "Workflow-specific acceptance roles: " + ", ".join(f"`{r}`" for r, s in data["roles"].items()
                     if s["class"] == "acceptance" and r not in (data["plan_role"], data["result_role"])) + ".",
                 "", data["instructions"].strip(), ""))
    return "\n".join(rows)


def usage_hint() -> str:
    data = load_policy()
    return ("Apply the global complex-engineering/material-risk threshold. Simple engineering gets one "
            "block_reviewer result review; ordinary non-engineering reviews also use block_reviewer, "
            "including complete bounded artifacts. Trivial chat/wording stays root-only. "
            "Bounded block reviews remain auxiliary even within complex tasks. Reserve reviewer and "
            "workflow acceptors for qualifying whole outcomes; state the concrete escalation reason. "
            "Stage/skill switches and routine corrections reuse valid acceptance and the same reviewer. "
            "Default to root-only implementation for simple "
            "tasks, known-context fixes and same-outcome refinements; no mandatory whole-plan/whole-result pair for them. "
            "Use a fresh whole-plan acceptor and different fresh whole-result acceptor for complex engineering or materially high-risk work in any domain. "
            "Honor explicit delegation/review at its requested scope; one simple worker request does not require a pair. "
            "Reassess material scope or risk changes. Add extra focused review only for a justified independent block or distinct material risk. "
            f"Use configured auxiliary roles ({data['auxiliary']['model']}, {data['auxiliary']['effort']}) "
            "only when an independent block repays handoff cost. "
            'Always set agent_type and fork_turns="none"; preserve role settings. Children are leaves. '
            "When independent acceptance is required, missing evidence is not a pass. "
            "Reuse the same reviewer only for corrections to its scope. Respect host concurrency/writer limits, "
            "avoid duplicate scopes, and return compact cited evidence.")


def _structural_lines(text: str) -> list[tuple[int, str]]:
    """Locate TOML statements outside strings; do not edit example keys in prompts."""
    result: list[tuple[int, str]] = []
    quote: str | None = None
    for n, line in enumerate(text.splitlines(keepends=True)):
        if quote is None:
            result.append((n, line))
        i = 0
        while i < len(line):
            if quote:
                if quote.startswith('"') and line[i] == "\\":
                    i += 2
                elif line.startswith(quote, i):
                    i += len(quote)
                    quote = None
                else:
                    i += 1
            elif line[i] == "#":
                break
            elif line[i] in "\"'":
                quote = line[i] * (3 if line.startswith(line[i] * 3, i) else 1)
                i += len(quote)
            else:
                i += 1
    return result


def _header_path(line: str) -> tuple[str, ...] | None:
    if not line.lstrip().startswith("["):
        return None
    probe = tomllib.loads(line + "\n__routing_probe__ = true\n")
    path: list[str] = []
    while isinstance(probe, dict) and "__routing_probe__" not in probe:
        if len(probe) != 1:
            raise ValueError("Unsupported TOML table shape")
        key, probe = next(iter(probe.items()))
        path.append(key)
        if isinstance(probe, list):
            probe = probe[-1]
    return tuple(path)


def table_spans(text: str) -> list[tuple[tuple[str, ...], int, int]]:
    lines = text.splitlines(keepends=True)
    headers = [(path, n) for n, line in _structural_lines(text)
               if (path := _header_path(line)) is not None]
    spans = [((), 0, headers[0][1] if headers else len(lines))]
    spans.extend((path, start, headers[i + 1][1] if i + 1 < len(headers) else len(lines))
                 for i, (path, start) in enumerate(headers))
    return spans


def rewrite_fields(text: str, table: tuple[str, ...], values: dict[str, Any]) -> str:
    """Set/delete selected scalar keys while retaining all other text and values."""
    tomllib.loads(text)
    lines = text.splitlines(keepends=True)
    spans = [span for span in table_spans(text) if span[0] == table]
    if len(spans) > 1:
        raise ValueError(f"Ambiguous TOML table: {table}")
    if not spans:
        if all(v is None for v in values.values()):
            return text
        text = text.rstrip() + "\n\n[" + ".".join(table) + "]\n"
        return rewrite_fields(text, table, values)
    _, start, end = spans[0]
    structural = dict(_structural_lines(text))
    removals: set[int] = set()
    for n in range(start, end):
        if n not in structural:
            continue
        line = structural[n]
        for key in values:
            if re.match(r"^\s*(?:" + re.escape(key) + r"|\"" + re.escape(key) + r"\"|'" + re.escape(key) + r"')\s*=", line):
                stop = n + 1
                while stop < end and stop not in structural:
                    stop += 1
                removals.update(range(n, stop))
                break
    additions = [f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
                 for key, value in values.items() if value is not None]
    insert = start if not table else start + 1
    result = "".join(lines[:insert] + additions + [line for n, line in enumerate(lines[insert:], insert)
                                                if n not in removals])
    tomllib.loads(result)
    return result


def config_defaults(text: str) -> str:
    data = load_policy()
    original = tomllib.loads(text)
    for name, overlay in original.get("profiles", {}).items():
        if has_routing_override(overlay):
            raise ValueError(f"Embedded profile {name} contains routing overrides; migrate explicitly")
    text = rewrite_fields(text, (), {"model": data["root"]["model"], "model_reasoning_effort": data["root"]["effort"]})
    text = rewrite_fields(text, ("features",), {"multi_agent": True})
    text = rewrite_fields(text, ("agents",), {"enabled": True,
        "default_subagent_model": data["auxiliary"]["model"],
        "default_subagent_reasoning_effort": data["auxiliary"]["effort"]})
    text = rewrite_fields(text, ("features", "multi_agent_v2"), {"usage_hint_text": usage_hint()})
    return text


def has_routing_override(data: dict[str, Any]) -> bool:
    if any(key in data for key in ("model", "model_reasoning_effort")) or data.get("developer_instructions"):
        return True
    agents = data.get("agents", {})
    if any(key in agents for key in ("default_subagent_model", "default_subagent_reasoning_effort", "enabled")):
        return True
    if any(isinstance(value, dict) and any(key in value for key in
           ("config_file", "model", "model_reasoning_effort")) for value in agents.values()):
        return True
    return "usage_hint_text" in data.get("features", {}).get("multi_agent_v2", {})


def adopt_native_registrations(text: str, native_roles: set[str]) -> tuple[str, dict[str, dict]]:
    data = tomllib.loads(text)
    lines = text.splitlines(keepends=True)
    keep: dict[str, dict] = {}
    remove: set[int] = set()
    for path, start, end in table_spans(text):
        if len(path) != 2 or path[0] != "agents" or path[1] not in native_roles:
            continue
        role = path[1]
        entry = data["agents"][role]
        normalized = str(entry.get("config_file", "")).replace("\\", "/")
        if normalized not in (f"./agents/{role}.toml", f"agents/{role}.toml"):
            raise ValueError(f"Unmanaged config already defines [agents.{role}] with an unknown config_file")
        if set(entry) - {"description", "config_file", "nickname_candidates"}:
            raise ValueError(f"Unmanaged config already defines unsupported [agents.{role}] fields")
        keep[role] = {k: v for k, v in entry.items() if k == "nickname_candidates"}
        remove.update(range(start, end))
    return "".join(line for i, line in enumerate(lines) if i not in remove), keep


def profile_candidate(original: str, name: str) -> str:
    """Known profile names become aliases; retain unrelated profile settings."""
    data = tomllib.loads(original)
    text = rewrite_fields(original, (), {"model": None, "model_reasoning_effort": None})
    instructions = data.get("developer_instructions", "")
    if "user-requested model-routing experiment" in instructions:
        text = rewrite_fields(text, (), {"developer_instructions": None})
    elif instructions:
        # Model names are open-ended. A keyword heuristic cannot prove safety.
        raise ValueError(f"Profile {name} has custom developer instructions; inspect before migration")

    preserved: dict[str, Any] = {}
    aliases: dict[str, dict] = {}
    for key, value in data.get("agents", {}).items():
        if key in ("default_subagent_model", "default_subagent_reasoning_effort", "enabled"):
            continue
        if isinstance(value, dict):
            if key not in load_policy()["roles"]:
                raise ValueError(f"Profile {name} has an unmanaged agent override: {key}")
            if set(value) - {"config_file", "description", "nickname_candidates"}:
                raise ValueError(f"Profile {name} has unsupported agent fields: {key}")
            aliases[key] = {field: item for field, item in value.items() if field != "config_file"}
        else:
            preserved[key] = value

    # Rebuild only the agents subtree. This also handles inline registrations;
    # nickname-only overlays keep inheriting the generated config_file.
    text = rewrite_fields(text, (), {"agents": None})
    lines = text.splitlines(keepends=True)
    remove: set[int] = set()
    for path, start, end in table_spans(text):
        if path and path[0] == "agents":
            remove.update(range(start, end))
    text = "".join(line for i, line in enumerate(lines) if i not in remove)
    if "agents" in tomllib.loads(text):
        raise ValueError(f"Profile {name} uses unsupported dotted agent assignments; inspect before migration")
    rows = []
    if preserved:
        rows = ["[agents]"] + [f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in preserved.items()]
    for role, fields in aliases.items():
        if fields:
            rows += ["", f"[agents.{role}]"] + [f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()]
    if rows:
        text = text.rstrip() + "\n\n" + "\n".join(rows) + "\n"
    marker = "# Managed routing alias: inherits root and agent models from config.toml."
    text = "\n".join(line for line in text.splitlines() if line != marker).strip()
    result = marker + "\n" + (text + "\n" if text else "")
    rendered = tomllib.loads(result)
    expected = {**preserved, **{role: fields for role, fields in aliases.items() if fields}}
    if rendered.get("agents", {}) != expected or has_routing_override(rendered):
        raise ValueError(f"Profile {name} retains unsupported routing overrides")
    return result
