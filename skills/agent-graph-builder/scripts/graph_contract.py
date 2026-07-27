#!/usr/bin/env python3
"""Scaffold and validate the shared Codex-native agent graph contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
WORK_POLICY_VALUES = {
    "fast_path": "root-only",
    "capability_discovery": "need-based",
    "agent_admission": "independent-work-only",
    "review_admission": "risk-or-uncertainty-only",
    "progress_updates": "state-change-only",
    "documentation_followup": "impact-gated",
    "explicit_user_override": "bounded",
}
WORK_POLICY_BUDGETS = {
    "max_agent_starts": (0, 8),
    "max_review_starts": (0, 4),
    "max_repair_cycles": (0, 2),
    "max_no_new_evidence_iterations": (1, 2),
    "max_artifacts_per_work_unit": (1, 5),
}
WORK_POLICY_LOOP_GUARDS = {
    "duplicate_agent_scope": "forbidden",
    "same_scope_retry": "new-evidence-required",
    "repair_start": "first-false-assumption-required",
    "no_new_evidence": "stop-at-budget",
}
EXECUTION_TIERS = {
    "skill-only": {"controller": False, "verification": "self"},
    "tracked": {"controller": True, "verification": "conditional"},
    "verified": {"controller": True, "verification": "required"},
}
EXECUTION_ADMISSION = {
    "controller": "resumability-or-durable-evidence",
    "verification": "risk-or-uncertainty",
}


class ContractError(RuntimeError):
    """Raised when a graph skill violates the shared contract."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot read valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    return value


def skill_name(skill_dir: Path) -> str:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        raise ContractError(f"Missing SKILL.md: {skill_file}")
    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ContractError("SKILL.md must start with YAML frontmatter.")
    name_match = re.search(r"(?m)^name:\s*([^\s]+)\s*$", match.group(1))
    if not name_match:
        raise ContractError("SKILL.md frontmatter must contain name.")
    name = name_match.group(1).strip("\"'")
    if not NAME_RE.fullmatch(name) or skill_dir.name != name:
        raise ContractError("Skill name must be lowercase hyphen-case and match its directory.")
    if "TODO" in text or "[TODO" in text:
        raise ContractError(
            "Finish the $skill-creator template before graph scaffold; SKILL.md contains an unfinished TODO."
        )
    return name


def normalized_routes(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = graph.get("routes")
    if routes is None:
        routes = {
            "default": {
                "entry": graph.get("entry"),
                "terminal": graph.get("terminal"),
                "nodes": graph.get("nodes"),
            }
        }
    if not isinstance(routes, dict) or not routes:
        raise ContractError("graph.json requires at least one route.")
    normalized: dict[str, dict[str, Any]] = {}
    for mode, route in routes.items():
        if not isinstance(mode, str) or not mode or not isinstance(route, dict):
            raise ContractError("Each graph route requires a non-empty name and object value.")
        normalized[mode] = route
    return normalized


def find_forbidden_model_key(value: Any, path: str = "graph") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {"model", "models", "model_name"}:
                return child_path
            found = find_forbidden_model_key(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_model_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def validate_work_policy(graph: dict[str, Any], *, required: bool) -> str:
    policy = graph.get("work_policy")
    if policy is None:
        if required:
            raise ContractError(
                "graph.json requires work_policy for the current efficiency contract."
            )
        return "legacy"
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise ContractError("work_policy must be an object with schema_version 1.")
    for key, expected in WORK_POLICY_VALUES.items():
        if policy.get(key) != expected:
            raise ContractError(f"work_policy.{key} must be {expected!r}.")

    budgets = policy.get("budgets")
    if not isinstance(budgets, dict) or set(budgets) != set(WORK_POLICY_BUDGETS):
        raise ContractError(
            "work_policy.budgets must contain exactly the shared efficiency budgets."
        )
    for key, (minimum, maximum) in WORK_POLICY_BUDGETS.items():
        value = budgets.get(key)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not minimum <= value <= maximum
        ):
            raise ContractError(
                f"work_policy.budgets.{key} must be an integer from {minimum} to {maximum}."
            )
    if budgets["max_review_starts"] > budgets["max_agent_starts"]:
        raise ContractError(
            "work_policy max_review_starts cannot exceed max_agent_starts."
        )

    loop_guards = policy.get("loop_guards")
    if not isinstance(loop_guards, dict) or set(loop_guards) != set(
        WORK_POLICY_LOOP_GUARDS
    ):
        raise ContractError(
            "work_policy.loop_guards must contain exactly the shared loop guards."
        )
    for key, expected in WORK_POLICY_LOOP_GUARDS.items():
        if loop_guards.get(key) != expected:
            raise ContractError(f"work_policy.loop_guards.{key} must be {expected!r}.")
    return "current"


def validate_execution_policy(graph: dict[str, Any], *, required: bool) -> str:
    policy = graph.get("execution_policy")
    if policy is None:
        if required:
            raise ContractError(
                "graph.json requires execution_policy for adaptive execution tiers."
            )
        return "legacy"
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise ContractError("execution_policy must be an object with schema_version 1.")
    tiers = policy.get("tiers")
    if not isinstance(tiers, dict) or not tiers:
        raise ContractError("execution_policy.tiers must be a non-empty object.")
    if not {"tracked", "verified"}.issubset(tiers):
        raise ContractError("execution_policy must expose tracked and verified tiers.")
    unknown = set(tiers).difference(EXECUTION_TIERS)
    if unknown:
        raise ContractError(
            "execution_policy contains unknown tiers: " + ", ".join(sorted(unknown))
        )
    for name, value in tiers.items():
        if value != EXECUTION_TIERS[name]:
            raise ContractError(
                f"execution_policy.tiers.{name} must equal the shared tier contract."
            )
    default = policy.get("default_tier")
    if default not in tiers:
        raise ContractError("execution_policy.default_tier must name an exposed tier.")
    admission = policy.get("admission")
    if admission != EXECUTION_ADMISSION:
        raise ContractError(
            "execution_policy.admission must use the shared controller and verification signals."
        )
    return "current"


def validate_graph_skill(
    skill_dir_raw: str | Path, *, require_work_policy: bool = False
) -> dict[str, Any]:
    skill_dir = Path(skill_dir_raw).expanduser().resolve()
    if not skill_dir.is_dir():
        raise ContractError(f"Graph skill directory not found: {skill_dir}")
    name = skill_name(skill_dir)

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.is_file():
        raise ContractError("Missing agents/openai.yaml generated by skill-creator.")
    openai_text = openai_yaml.read_text(encoding="utf-8")
    if f"${name}" not in openai_text or "default_prompt:" not in openai_text:
        raise ContractError("agents/openai.yaml default_prompt must explicitly invoke the skill.")

    graph_path = skill_dir / "graph.json"
    graph = load_json(graph_path)
    if graph.get("schema_version") != 2:
        raise ContractError("graph.json must use schema_version 2.")
    if graph.get("graph_id") != name:
        raise ContractError("graph_id must match the skill name.")
    if not isinstance(graph.get("graph_version"), str) or not SEMVER_RE.fullmatch(graph["graph_version"]):
        raise ContractError("graph_version must be semantic x.y.z.")
    forbidden = find_forbidden_model_key(graph)
    if forbidden:
        raise ContractError(f"Do not hard-code model selection in graph.json: {forbidden}")

    limits = graph.get("limits")
    if not isinstance(limits, dict):
        raise ContractError("graph.json requires limits.")
    for key in ("max_node_retries", "max_verification_repairs"):
        value = limits.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 2:
            raise ContractError(f"{key} must be an integer from 0 to 2.")

    work_policy = validate_work_policy(graph, required=require_work_policy)
    execution_policy = validate_execution_policy(
        graph, required=require_work_policy
    )

    control_plane = graph.get("control_plane_policy")
    if control_plane is not None and (
        control_plane.get("schema_version") != 1
        or control_plane.get("task_priority") not in {"domain-first", "code-first"}
        or control_plane.get("controller_role") != "checkpoint-and-completion-boundary"
        or control_plane.get("protocol_failure") != "degrade-control-not-task"
        or control_plane.get("max_protocol_repairs_before_degrade") != 1
        or control_plane.get("human_interrupt")
        not in {"authority-semantic-or-high-risk-only", "authority-or-high-risk-only"}
        or control_plane.get("project_context_before_controller_detail") is not True
        or control_plane.get("multiple_unfinished_tasks") != "independent-per-task"
        or control_plane.get("verified_completion_requires_healthy_control") is not True
        or len(control_plane) != 9
    ):
        raise ContractError("control_plane_policy must preserve the code-first shared contract.")

    mcp = graph.get("mcp_policy")
    if not isinstance(mcp, dict):
        raise ContractError("graph.json requires the shared conditional MCP policy.")
    mcp_discovery = mcp.get("discovery")
    if mcp_discovery not in {"required", "when-relevant"}:
        raise ContractError("mcp_policy.discovery must be required or when-relevant.")
    if (
        mcp.get("relevant_use") != "required"
        or mcp.get("receipt_prefix") != "mcp:"
        or mcp.get("fallback_prefix") != "mcp:fallback:"
        or not isinstance(mcp.get("selection_order"), list)
        or not mcp["selection_order"]
    ):
        raise ContractError("graph.json requires the shared conditional MCP receipt policy.")
    if mcp_discovery == "when-relevant" and mcp.get("not_applicable_prefix") != "mcp:not-applicable:":
        raise ContractError(
            "Conditional MCP discovery requires not_applicable_prefix mcp:not-applicable:."
        )
    if work_policy == "current" and mcp_discovery != "when-relevant":
        raise ContractError(
            "The current work_policy requires need-based MCP discovery."
        )

    optional_agents = graph.get("optional_agents", [])
    if not isinstance(optional_agents, list) or any(not isinstance(item, str) or not item for item in optional_agents):
        raise ContractError("optional_agents must be a list of role names.")

    routes = normalized_routes(graph)
    for mode, route in routes.items():
        if route.get("entry") != "work" or route.get("terminal") != "complete":
            raise ContractError(f"Route {mode} must enter work and terminate at complete.")
        nodes = route.get("nodes")
        if not isinstance(nodes, dict) or set(nodes) != {"work", "verify", "complete"}:
            raise ContractError(f"Route {mode} must contain exactly work, verify and complete.")
        work = nodes["work"]
        verify = nodes["verify"]
        complete = nodes["complete"]
        if not isinstance(work, dict) or work.get("role") != "root" or work.get("on_success") != "complete":
            raise ContractError(f"Route {mode} work node must be root and succeed to complete.")
        if work.get("on_verify") != "verify" or not isinstance(work.get("artifact"), str):
            raise ContractError(f"Route {mode} work node requires artifact and optional verify transition.")
        if (
            not isinstance(verify, dict)
            or verify.get("role") in {None, "", "root"}
            or verify.get("on_success") != "complete"
            or verify.get("on_rejected") != "work"
            or not isinstance(verify.get("artifact"), str)
        ):
            raise ContractError(f"Route {mode} verify node must be independent and reject to work.")
        if not isinstance(complete, dict) or complete.get("role") != "root" or not isinstance(complete.get("artifact"), str):
            raise ContractError(f"Route {mode} complete node must be root with a durable artifact.")

    scripts_dir = skill_dir / "scripts"
    controllers = sorted(
        path for path in scripts_dir.glob("*_graph.py") if not path.name.startswith("test_")
    )
    tests = sorted(scripts_dir.glob("test_*_graph.py"))
    if len(controllers) != 1:
        raise ContractError("Graph skill must contain exactly one scripts/*_graph.py controller.")
    if not tests:
        raise ContractError("Graph skill must contain at least one scripts/test_*_graph.py.")
    controller_text = controllers[0].read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*#\s*(?:TODO|FIXME)\b", controller_text) or re.search(
        r"(?m)^\s*raise\s+NotImplementedError\b", controller_text
    ):
        raise ContractError("Graph controller contains unfinished implementation markers.")
    if not (skill_dir / "references" / "control-artifact.md").is_file():
        raise ContractError("Graph skill requires references/control-artifact.md.")

    return {
        "status": "ok",
        "skill": name,
        "graph_version": graph["graph_version"],
        "work_policy": work_policy,
        "execution_policy": execution_policy,
        "routes": sorted(routes),
        "controller": str(controllers[0]),
        "tests": [str(path) for path in tests],
    }


def render_template(path: Path, replacements: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"__{key}__", value)
    leftovers = sorted(set(re.findall(r"__[A-Z0-9_]+__", text)))
    if leftovers:
        raise ContractError("Unresolved scaffold placeholders: " + ", ".join(leftovers))
    return text


def write_new(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise ContractError(f"Refusing to overwrite existing scaffold target: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold(
    skill_dir_raw: str | Path,
    mode: str,
    work_artifact: str,
    complete_artifact: str,
    verifier_role: str,
) -> dict[str, Any]:
    skill_dir = Path(skill_dir_raw).expanduser().resolve()
    if not skill_dir.is_dir():
        raise ContractError(f"Skill directory not found: {skill_dir}")
    name = skill_name(skill_dir)
    if not (skill_dir / "agents" / "openai.yaml").is_file():
        raise ContractError("Run $skill-creator init_skill.py before graph scaffold.")
    for label, value in {
        "mode": mode,
        "work artifact": work_artifact,
        "complete artifact": complete_artifact,
        "verifier role": verifier_role,
    }.items():
        if not value or ".." in value or any(char in value for char in "\r\n\0"):
            raise ContractError(f"Invalid {label}.")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", mode):
        raise ContractError("Mode must be lowercase hyphen-case.")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", verifier_role):
        raise ContractError("Verifier role must be lowercase snake_case.")

    replacements = {
        "GRAPH_ID": name,
        "MODE": mode,
        "WORK_ARTIFACT": work_artifact,
        "COMPLETE_ARTIFACT": complete_artifact,
        "VERIFIER_ROLE": verifier_role,
    }
    graph_target = skill_dir / "graph.json"
    control_target = skill_dir / "references" / "control-artifact.md"
    graph_text = render_template(ASSETS / "graph.template.json", replacements)
    control_text = render_template(ASSETS / "control-artifact.template.md", replacements)
    write_new(graph_target, graph_text)
    try:
        write_new(control_target, control_text)
    except Exception:
        graph_target.unlink(missing_ok=True)
        raise
    snake = name.replace("-", "_")
    return {
        "status": "scaffolded",
        "skill": name,
        "artifacts": [str(graph_target), str(control_target)],
        "next_actions": [
            f"Implement scripts/{snake}_graph.py with durable state and integrity checks.",
            f"Implement scripts/test_{snake}_graph.py from references/evaluation.md.",
            "Run graph_contract.py validate after replacing domain-specific contracts.",
        ],
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--skill-dir", required=True)
    validate.add_argument("--require-work-policy", action="store_true")
    create = sub.add_parser("scaffold")
    create.add_argument("--skill-dir", required=True)
    create.add_argument("--mode", default="full")
    create.add_argument("--work-artifact", default="work.json")
    create.add_argument("--complete-artifact", default="result.md")
    create.add_argument("--verifier-role", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate":
            result = validate_graph_skill(
                args.skill_dir, require_work_policy=args.require_work_policy
            )
        else:
            result = scaffold(
                args.skill_dir,
                args.mode,
                args.work_artifact,
                args.complete_artifact,
                args.verifier_role,
            )
    except (ContractError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
