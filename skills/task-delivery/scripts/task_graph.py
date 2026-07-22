#!/usr/bin/env python3
"""Small deterministic control layer for model-first Task Delivery work."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import task_delivery as legacy  # noqa: E402
import task_delivery_snapshot as snapshots  # noqa: E402


GRAPH_PATH = SKILL_DIR / "graph.json"
RUNS_REL = Path(".agent-graphs/task-delivery-runs")
HANDOFFS_REL = Path(".agent-graphs/task-delivery-handoffs")
STATE_NAME = "state.json"
WORK_NAME = "task.json"
VERIFY_NAME = "verification.json"
LOCK_NAME = ".state.lock"
SLICES_DIR = "slices"
SLICE_PACKET_NAME = "packet.json"
SLICE_BASELINE_NAME = "baseline.json"
SLICE_ACCEPTANCE_NAME = "root-acceptance.json"
CONTEXT_CHECKPOINT_NAME = "context-checkpoint.json"
SCOPE_AMENDMENTS_DIR = "scope-amendments"
MODES = {"plan", "implement", "full"}
PROFILES = {"light", "standard", "complex", "critical"}
PROFILE_RANK = {"light": 0, "standard": 1, "complex": 2, "critical": 3}
IMPLEMENTATION_STRATEGIES = {"root-only", "delegated-sequential", "delegated-parallel"}
IMPLEMENTATION_STRATEGY_REQUESTS = {"auto", "root-only", "delegated-sequential"}
WORKER_STATUSES = {"done", "done_with_concerns", "needs_context", "blocked"}
ALLOWED_ROLES = {
    "task_explorer",
    "task_worker",
    "task_plan_reviewer",
    "task_result_reviewer",
    "task_risk_reviewer",
    "research_planner",
    "research_scout",
    "research_synthesizer",
    "research_verifier",
}
LEGACY_ACTIVE_GRAPH_IDENTITIES = {
    ("3.0.0", "b2a735ff751a88a21175ea7fcfd0f9d0960f53abe540373360180a5ca14fdf3a"),
    ("3.1.0", "a9d10724ff236fe787540d4f8c0e3dcb18f66e989e4d57bfc0a0683bff999d46"),
    ("3.2.0", "4317362f02d843470cfa3bc063cb861577bec09c9b98bd78126dd12bb8bb2bb1"),
    ("3.3.0", "07b19482bca36d54ace9a3cc470e76e421b2b1c14f0ee123c90a7792af79b7e8"),
}
SLICE_CONTRACT_VERSIONS = {"3.3.0", "3.4.0"}


class GraphError(RuntimeError):
    """A safe, actionable Task Delivery graph error."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def result(
    status: str,
    summary: str,
    *,
    next_actions: list[str] | None = None,
    artifacts: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "summary": summary,
        "next_actions": next_actions or [],
        "artifacts": artifacts or [],
        "data": data or {},
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GraphError(f"Файл не найден: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GraphError(f"Некорректный JSON в {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GraphError(f"Ожидался JSON-объект: {path}")
    return value


def sha256_file(path: Path) -> str:
    return snapshots.hash_file(path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def graph_contract() -> dict[str, Any]:
    graph = load_json(GRAPH_PATH)
    if graph.get("schema_version") != 2 or graph.get("graph_id") != "task-delivery":
        raise GraphError("Task Delivery graph должен использовать schema_version 2.")
    if set(graph.get("routes", {})) != MODES:
        raise GraphError("Task Delivery graph должен содержать plan, implement и full.")
    if set(graph.get("profiles", {})) != PROFILES:
        raise GraphError("Task Delivery graph должен содержать четыре профиля риска.")
    for mode in MODES:
        route = graph["routes"][mode]
        if route.get("entry") != "work" or route.get("terminal") != "complete":
            raise GraphError(f"Некорректные entry/terminal для {mode}.")
        if set(route.get("nodes", {})) != {"work", "verify", "complete"}:
            raise GraphError(f"Маршрут {mode} должен иметь только work, verify, complete.")
    mcp_policy = graph.get("mcp_policy")
    if (
        not isinstance(mcp_policy, dict)
        or mcp_policy.get("discovery") != "required"
        or mcp_policy.get("relevant_use") != "required"
        or mcp_policy.get("receipt_prefix") != "mcp:"
        or mcp_policy.get("fallback_prefix") != "mcp:fallback:"
        or not isinstance(mcp_policy.get("selection_order"), list)
    ):
        raise GraphError("Task Delivery graph содержит неверную MCP-first policy.")
    delegation = graph.get("delegation_policy")
    limits = graph.get("limits", {})
    if (
        not isinstance(delegation, dict)
        or delegation.get("default_strategy") != "adaptive"
        or delegation.get("profile_preference")
        != {
            "light": "root-only",
            "standard": "delegated-sequential",
            "complex": "delegated-sequential",
            "critical": "delegated-sequential",
        }
        or delegation.get("explicit_slice_request") != "required"
        or set(delegation.get("strategies", [])) != IMPLEMENTATION_STRATEGIES
        or set(delegation.get("worker_statuses", [])) != WORKER_STATUSES
        or delegation.get("parallel_write_isolation") != "worktree-required"
        or delegation.get("parallel_write_enabled") is not False
        or not isinstance(limits.get("max_slices_per_run"), int)
        or limits["max_slices_per_run"] < 1
        or limits.get("max_verification_repair_slices") != 1
        or not isinstance(limits.get("max_selected_skills_per_slice"), int)
        or limits["max_selected_skills_per_slice"] < 1
    ):
        raise GraphError("Task Delivery graph содержит неверную delegation policy.")
    context_policy = graph.get("context_policy")
    if context_policy != {
        "checkpoint_schema_version": 1,
        "checkpoint_after": "slice-accept",
        "rehydrate_before": "next-slice",
        "host_compact": "optional",
        "global_hook_required": False,
    }:
        raise GraphError("Task Delivery graph содержит неверную context policy.")
    test_policy = graph.get("test_policy")
    if (
        not isinstance(test_policy, dict)
        or test_policy.get("packet_schema_version") != 2
        or test_policy.get("check_identity") != "sha256-command-purpose"
        or set(test_policy.get("impact_actions", []))
        != {"reuse", "update", "add", "not-applicable"}
        or set(test_policy.get("impact_levels", []))
        != {"unit", "integration", "e2e", "static", "other"}
        or set(test_policy.get("required_impact_levels", [])) != {"unit", "integration", "e2e"}
        or test_policy.get("root_replay_minimum_per_slice") != 1
        or test_policy.get("deferred_final_checks") != "exact-union-by-check-id"
    ):
        raise GraphError("Task Delivery graph содержит неверную staged-test policy.")
    amendment = graph.get("scope_amendment_policy")
    if (
        not isinstance(amendment, dict)
        or amendment.get("allowed_authority") != "root-technical"
        or amendment.get("review_effect") != "preserve-reviewed-base-through-digest-chain"
        or not isinstance(amendment.get("protected_prefixes"), list)
        or not isinstance(amendment.get("protected_names"), list)
        or limits.get("max_root_technical_amendments") != 2
        or limits.get("max_paths_per_scope_amendment") != 2
    ):
        raise GraphError("Task Delivery graph содержит неверную scope-amendment policy.")
    return graph


def root_path(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise GraphError(f"Корень проекта не найден: {root}")
    return root


def relative_path(root: Path, raw: str | Path) -> str:
    candidate = Path(raw).expanduser()
    path = candidate.resolve(strict=False) if candidate.is_absolute() else (root / candidate).resolve(strict=False)
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise GraphError(f"Путь выходит за корень проекта: {raw}") from exc
    try:
        snapshots.safe_join_no_symlinks(root, relative)
    except snapshots.SnapshotError as exc:
        raise GraphError(str(exc)) from exc
    return relative


def task_state_path(root: Path, task_id: str) -> Path:
    try:
        return legacy.state_file(root, legacy.validate_task_id(task_id))
    except legacy.TaskError as exc:
        raise GraphError(str(exc)) from exc


def run_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_dir() or not (path / STATE_NAME).is_file():
        raise GraphError(f"Не найден Task Delivery run: {path}")
    return path


@contextlib.contextmanager
def state_lock(run_dir: Path, wait_seconds: float = 5.0, stale_seconds: int = 120) -> Iterator[None]:
    lock = run_dir / LOCK_NAME
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            try:
                raw = lock.read_text(encoding="utf-8")
                match = re.search(r"pid=(\d+)", raw)
                pid = int(match.group(1)) if match else -1
                age = time.time() - lock.stat().st_mtime
            except (FileNotFoundError, OSError, ValueError):
                continue
            if age > stale_seconds and not legacy.process_alive(pid):
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise GraphError(f"Run занят другим процессом: {run_dir}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} at={now()}\n".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def runner_command() -> str:
    return f"python3 {shlex.quote(str(Path(__file__).resolve()))}"


def plan_relative(root: Path, raw: str | None, task_id: str, mode: str) -> str:
    if raw:
        relative = relative_path(root, raw)
    else:
        relative = f"docs/tasks/{task_id}/PLAN.md"
    if Path(relative).suffix.lower() != ".md":
        raise GraphError("План должен быть Markdown-файлом внутри проекта.")
    path = snapshots.safe_join_no_symlinks(root, relative)
    if mode == "implement" and not path.is_file():
        raise GraphError("Режим implement требует точный существующий --plan.")
    return relative


def plan_template(task_id: str, title: str, outcome: str) -> str:
    return f"""# {title}

Status: DRAFT
Task ID: {task_id}

<!-- task-delivery:plan:start -->
## Outcome

{outcome}

## Research basis

- Internal: PENDING
- External: PENDING or NOT NEEDED with reason

## Acceptance

- PENDING

## Implementation plan

1. PENDING

## Tests

- PENDING

## Stop conditions

- PENDING

## Scope

<!-- task-delivery:scope
PENDING
-->
<!-- task-delivery:plan:end -->

## Plan review

PENDING

## Delivery result

PENDING
"""


def plan_contract_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = "<!-- task-delivery:plan:start -->"
    end = "<!-- task-delivery:plan:end -->"
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
            raise GraphError("Некорректные границы task-delivery:plan в плане.")
        return text[text.index(start) + len(start) : text.index(end)]
    return text


def plan_digest(path: Path) -> str:
    return hashlib.sha256(plan_contract_text(path).encode("utf-8")).hexdigest()


def validate_plan(path: Path) -> tuple[str, list[str]]:
    if path.is_symlink() or not path.is_file():
        raise GraphError(f"План должен быть обычным существующим файлом: {path}")
    contract = plan_contract_text(path)
    placeholders = [token for token in ("PENDING", "TODO", "{{") if token in contract]
    if placeholders:
        raise GraphError("Контракт плана содержит незаполненные маркеры: " + ", ".join(placeholders))
    try:
        scope = snapshots.parse_scope(path.read_text(encoding="utf-8"))
    except snapshots.SnapshotError as exc:
        raise GraphError(str(exc)) from exc
    return plan_digest(path), scope


def exclusions(plan: str) -> list[str]:
    return [
        plan,
        ".agent-graphs",
        ".codex/task-delivery",
        ".project-start/state.json",
        ".project-start/.state.lock",
    ]


def manifest(root: Path, plan: str) -> dict[str, dict[str, Any]]:
    return snapshots.repo_manifest(root, exclusions(plan))


def profile_requires_verify(mode: str, profile: str, confidence: str = "high") -> bool:
    if confidence == "low":
        return True
    if mode == "plan":
        return profile in {"complex", "critical"}
    return profile in {"standard", "complex", "critical"}


def strings(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise GraphError(f"{name} должен быть списком непустых строк.")
    if not allow_empty and not value:
        raise GraphError(f"{name} не должен быть пустым.")
    return value


def objects(value: Any, name: str, *, allow_empty: bool = True) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise GraphError(f"{name} должен быть списком объектов.")
    if not allow_empty and not value:
        raise GraphError(f"{name} не должен быть пустым.")
    return value


def meaningful(value: Any, name: str, minimum: int = 8) -> str:
    text = str(value or "").strip()
    if len(text) < minimum:
        raise GraphError(f"{name} должен быть содержательным.")
    return text


def hex_digest(value: Any, name: str) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise GraphError(f"{name} должен быть SHA-256.")
    return text


def normalize_repo_paths(
    root: Path,
    value: Any,
    name: str,
    *,
    allow_empty: bool = True,
    require_files: bool = False,
) -> list[str]:
    raw_paths = strings(value, name, allow_empty=allow_empty)
    normalized: list[str] = []
    for raw in raw_paths:
        try:
            relative = snapshots.safe_relative(raw).as_posix().rstrip("/")
            path = snapshots.safe_join_no_symlinks(root, relative)
        except snapshots.SnapshotError as exc:
            raise GraphError(str(exc)) from exc
        if relative in {"", "."}:
            raise GraphError(f"{name} не может содержать корень репозитория.")
        if require_files and (path.is_symlink() or not path.is_file()):
            raise GraphError(f"{name} ссылается не на обычный файл: {relative}")
        normalized.append(relative)
    if len(set(normalized)) != len(normalized):
        raise GraphError(f"{name} не должен содержать дубликаты.")
    return normalized


def path_allowed(path: str, allowed: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in allowed)


def paths_overlap(left: str, right: str) -> bool:
    return path_allowed(left, [right]) or path_allowed(right, [left])


def slice_id(value: Any) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", text):
        raise GraphError("slice_id должен содержать 2-64 строчные буквы, цифры или дефисы.")
    return text


def slice_directory(run_dir: Path, identifier: str) -> Path:
    return run_dir / SLICES_DIR / slice_id(identifier)


def check_identity(command: str, purpose: str) -> str:
    canonical = json.dumps(
        {"command": command.strip(), "purpose": purpose.strip()},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_checks(value: Any, name: str, *, allow_empty: bool = True) -> list[dict[str, str]]:
    raw = objects(value, name, allow_empty=allow_empty)
    normalized: list[dict[str, str]] = []
    identities: set[str] = set()
    for item in raw:
        command = meaningful(item.get("command"), f"{name}.command", 3)
        purpose = meaningful(item.get("purpose"), f"{name}.purpose", 3)
        identifier = check_identity(command, purpose)
        supplied = item.get("check_id")
        if supplied is not None and supplied != identifier:
            raise GraphError(f"{name}.check_id не совпадает с canonical command/purpose.")
        if identifier in identities:
            raise GraphError(f"{name} не должен содержать повторный check_id.")
        identities.add(identifier)
        normalized.append({"check_id": identifier, "command": command, "purpose": purpose})
    return normalized


def normalize_legacy_checks(value: Any, name: str, *, allow_empty: bool = True) -> list[dict[str, str]]:
    raw = objects(value, name, allow_empty=allow_empty)
    return [
        {
            "command": meaningful(item.get("command"), f"{name}.command", 3),
            "purpose": meaningful(item.get("purpose"), f"{name}.purpose", 3),
        }
        for item in raw
    ]


def validate_test_impact(root: Path, value: Any, owned: list[str]) -> list[dict[str, Any]]:
    policy = graph_contract()["test_policy"]
    raw = objects(value, "test_impact", allow_empty=False)
    normalized: list[dict[str, Any]] = []
    levels_seen: set[str] = set()
    for item in raw:
        level = item.get("level")
        action = item.get("action")
        if level not in policy["impact_levels"] or action not in policy["impact_actions"]:
            raise GraphError("test_impact требует допустимые level и action.")
        if level in levels_seen:
            raise GraphError("test_impact допускает одну классификацию на test level.")
        levels_seen.add(level)
        reason = meaningful(item.get("reason"), f"test_impact {level}.reason")
        paths = normalize_repo_paths(root, item.get("paths", []), f"test_impact {level}.paths")
        if action == "not-applicable":
            if paths:
                raise GraphError("not-applicable test impact не должен содержать paths.")
        else:
            if not paths:
                raise GraphError(f"test_impact {level}:{action} требует test paths.")
            outside = snapshots.outside_scope(paths, owned)
            if outside:
                raise GraphError("Test paths должны входить в slice ownership: " + ", ".join(outside))
            if action in {"reuse", "update"}:
                for relative in paths:
                    path = snapshots.safe_join_no_symlinks(root, relative)
                    if path.is_symlink() or not path.is_file():
                        raise GraphError(f"test_impact {action} требует существующий файл: {relative}")
            if action == "add":
                for relative in paths:
                    path = snapshots.safe_join_no_symlinks(root, relative)
                    if path.exists() or path.is_symlink():
                        raise GraphError(f"test_impact add требует новый отсутствующий путь: {relative}")
        normalized.append({"level": level, "action": action, "paths": paths, "reason": reason})
    missing = set(policy["required_impact_levels"]).difference(levels_seen)
    if missing:
        raise GraphError("test_impact должен классифицировать unit, integration и e2e: " + ", ".join(sorted(missing)))
    return normalized


def validate_test_records(
    value: Any,
    name: str,
    *,
    require_pass: bool,
    include_check_id: bool = True,
) -> list[dict[str, Any]]:
    records = objects(value, name)
    normalized: list[dict[str, Any]] = []
    identities: set[str] = set()
    for item in records:
        command = meaningful(item.get("command"), f"{name}.command", 3)
        purpose = meaningful(item.get("purpose"), f"{name}.purpose", 3)
        status = item.get("status")
        exit_code = item.get("exit_code")
        if status not in {"passed", "failed", "not-run"} or not isinstance(exit_code, int):
            raise GraphError(f"{name} требует status passed|failed|not-run и целый exit_code.")
        if require_pass and (status != "passed" or exit_code != 0):
            raise GraphError(f"{name} должен содержать только прошедшие проверки.")
        identifier = check_identity(command, purpose)
        supplied = item.get("check_id")
        if include_check_id:
            if supplied is not None and supplied != identifier:
                raise GraphError(f"{name}.check_id не совпадает с canonical command/purpose.")
            if identifier in identities:
                raise GraphError(f"{name} не должен содержать повторный check_id.")
            identities.add(identifier)
        record = {
            "command": command,
            "purpose": purpose,
            "status": status,
            "exit_code": exit_code,
        }
        if include_check_id:
            record["check_id"] = identifier
        normalized.append(record)
    return normalized


def validate_capability_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GraphError("capability_context должен быть объектом.")
    limit = int(graph_contract()["limits"]["max_selected_skills_per_slice"])
    skills = objects(value.get("skills", []), "capability_context.skills")
    if len(skills) > limit:
        raise GraphError(f"Slice допускает не более {limit} выбранных skills.")
    normalized_skills: list[dict[str, Any]] = []
    names: set[str] = set()
    for item in skills:
        name = str(item.get("name") or "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", name) or name in names:
            raise GraphError("Каждый selected skill требует уникальное переносимое имя.")
        reason = meaningful(item.get("reason"), f"skill {name}.reason")
        required = item.get("required")
        if not isinstance(required, bool):
            raise GraphError(f"skill {name}.required должен быть boolean.")
        names.add(name)
        normalized_skills.append({"name": name, "reason": reason, "required": required})
    mcp = objects(value.get("mcp", []), "capability_context.mcp")
    normalized_mcp: list[dict[str, str]] = []
    receipts: set[str] = set()
    for item in mcp:
        receipt = str(item.get("receipt") or "")
        mode = item.get("mode")
        if (
            not receipt.startswith("mcp:")
            or receipt.startswith("mcp:fallback:")
            or len(receipt) < 6
            or receipt in receipts
        ):
            raise GraphError("MCP context требует уникальный receipt mcp:<server>.")
        if mode not in {"provided", "call-required"}:
            raise GraphError("MCP context mode должен быть provided или call-required.")
        if mode == "call-required" and receipt.startswith("mcp:fallback:"):
            raise GraphError("MCP fallback нельзя требовать как worker call.")
        receipts.add(receipt)
        normalized_mcp.append(
            {"receipt": receipt, "mode": mode, "purpose": meaningful(item.get("purpose"), "mcp purpose")}
        )
    return {"skills": normalized_skills, "mcp": normalized_mcp}


def validate_worker_capabilities(packet: dict[str, Any], receipt: dict[str, Any], status: str) -> list[dict[str, str]]:
    used = objects(receipt.get("capabilities_used", []), "capabilities_used")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in used:
        kind = item.get("kind")
        name = str(item.get("name") or "")
        state = item.get("status")
        if kind not in {"skill", "mcp"} or not name or (kind, name) in seen:
            raise GraphError("capabilities_used требует уникальные kind/name.")
        allowed = {"applied", "unavailable", "skipped"} if kind == "skill" else {"consumed", "called", "unavailable"}
        if state not in allowed:
            raise GraphError(f"Некорректный capability status для {kind}:{name}.")
        seen.add((kind, name))
        normalized.append(
            {"kind": kind, "name": name, "status": state, "evidence": meaningful(item.get("evidence"), "capability evidence")}
        )
    by_key = {(item["kind"], item["name"]): item["status"] for item in normalized}
    for skill in packet["capability_context"]["skills"]:
        if ("skill", skill["name"]) not in by_key:
            raise GraphError(f"Worker не отчитался о selected skill: {skill['name']}")
    for mcp in packet["capability_context"]["mcp"]:
        if ("mcp", mcp["receipt"]) not in by_key:
            raise GraphError(f"Worker не отчитался о MCP context: {mcp['receipt']}")
    if status in {"done", "done_with_concerns"}:
        for skill in packet["capability_context"]["skills"]:
            if skill["required"] and by_key.get(("skill", skill["name"])) != "applied":
                raise GraphError(f"Worker не применил обязательный skill: {skill['name']}")
        for mcp in packet["capability_context"]["mcp"]:
            actual = by_key.get(("mcp", mcp["receipt"]))
            expected = {"called"} if mcp["mode"] == "call-required" else {"called", "consumed"}
            if actual not in expected:
                raise GraphError(f"Worker не использовал обязательный MCP context: {mcp['receipt']}")
    return normalized


def validate_amendment_chain(
    state: dict[str, Any], run_dir: Path, *, current_digest: str | None = None
) -> dict[str, Any]:
    records = state.get("scope_amendments", [])
    if not isinstance(records, list):
        raise GraphError("Scope amendment registry повреждён.")
    if not records:
        digest = current_digest or plan_digest(snapshots.safe_join_no_symlinks(Path(state["root"]), state["plan_path"]))
        return {"base_digest": digest, "effective_digest": digest, "receipts": []}
    cursor: str | None = None
    validated: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise GraphError("Scope amendment registry содержит не объект.")
        expected_path = run_dir / SCOPE_AMENDMENTS_DIR / f"{index:02d}.json"
        path = Path(str(record.get("path", "")))
        if path.resolve(strict=False) != expected_path.resolve(strict=False):
            raise GraphError("Scope amendment receipt имеет неожиданный путь.")
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise GraphError("Scope amendment receipt изменился после record.")
        artifact = load_json(path)
        if artifact.get("schema_version") != 1 or artifact.get("authority") != "root-technical":
            raise GraphError("Scope amendment receipt имеет неподдерживаемый contract.")
        meaningful(artifact.get("plan_review_receipt"), "amendment.plan_review_receipt", 6)
        before = hex_digest(artifact.get("before_digest"), "amendment.before_digest")
        after = hex_digest(artifact.get("after_digest"), "amendment.after_digest")
        if cursor is not None and before != cursor:
            raise GraphError("Scope amendment digest chain разорван.")
        if record.get("before_digest") != before or record.get("after_digest") != after:
            raise GraphError("Scope amendment registry не совпадает с receipt.")
        cursor = after
        validated.append(artifact)
    effective = current_digest or plan_digest(
        snapshots.safe_join_no_symlinks(Path(state["root"]), state["plan_path"])
    )
    if cursor != effective:
        raise GraphError("Текущий план не совпадает с effective scope-amendment digest.")
    return {
        "base_digest": validated[0]["before_digest"],
        "effective_digest": effective,
        "receipts": validated,
    }


def reviewed_digest_is_effective(
    state: dict[str, Any], run_dir: Path, reviewed_digest: Any, current_digest: str
) -> bool:
    if reviewed_digest == current_digest:
        return True
    chain = validate_amendment_chain(state, run_dir, current_digest=current_digest)
    return chain["base_digest"] == reviewed_digest and chain["effective_digest"] == current_digest


def verification_repair_work_sha(state: dict[str, Any]) -> str | None:
    if state.get("current") != "work" or state.get("status") != "running":
        return None
    receipts = state.get("nodes", {}).get("verify", {}).get("receipts", [])
    if not isinstance(receipts, list) or not receipts:
        return None
    latest = receipts[-1]
    if not isinstance(latest, dict) or latest.get("outcome") != "failed":
        return None
    return hex_digest(latest.get("work_sha256"), "verification repair work_sha256")


def load_context_checkpoint(state: dict[str, Any], run_dir: Path) -> tuple[dict[str, Any], str]:
    context = state.get("context")
    if not isinstance(context, dict):
        raise GraphError("Run context registry повреждён.")
    path = run_dir / CONTEXT_CHECKPOINT_NAME
    expected = context.get("latest_checkpoint_sha256")
    if not isinstance(expected, str) or not path.is_file() or sha256_file(path) != expected:
        raise GraphError("Latest context checkpoint отсутствует или изменился.")
    checkpoint = load_json(path)
    if (
        checkpoint.get("schema_version") != graph_contract()["context_policy"]["checkpoint_schema_version"]
        or checkpoint.get("run_id") != state["run_id"]
        or checkpoint.get("task_id") != state["task_id"]
        or checkpoint.get("graph_version") != state["graph_version"]
    ):
        raise GraphError("Context checkpoint связан с другим Task Delivery run.")
    current_plan = snapshots.safe_join_no_symlinks(Path(state["root"]), state["plan_path"])
    current_plan_digest = plan_digest(current_plan)
    if checkpoint.get("plan_digest") != current_plan_digest:
        raise GraphError("Context checkpoint связан с другим plan digest.")
    validate_amendment_chain(state, run_dir, current_digest=current_plan_digest)
    expected_amendments = [item["sha256"] for item in state.get("scope_amendments", [])]
    if checkpoint.get("scope_amendment_receipts") != expected_amendments:
        raise GraphError("Context checkpoint не совпадает с immutable scope amendment chain.")
    current_repository_digest = snapshots.manifest_digest(
        manifest(Path(state["root"]), state["plan_path"])
    )
    if checkpoint.get("repository_digest") != current_repository_digest:
        raise GraphError("Repository изменился после accepted context checkpoint.")
    return checkpoint, expected


def register_slice(run_dir: Path, draft_path: Path) -> dict[str, Any]:
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            current_contract = state.get("graph_version") == graph_contract()["graph_version"]
            if not current_contract and state.get("graph_version") != "3.3.0":
                raise GraphError("Slice delegation недоступен для этой legacy Task Delivery версии.")
            if state["status"] != "running" or state["current"] != "work":
                raise GraphError("Slice можно зарегистрировать только внутри готового work.")
            if state["mode"] == "plan":
                raise GraphError("Режим plan не запускает implementation workers.")
            if state["profile"] == "light":
                raise GraphError("Профиль light использует root-only implementation.")
            if state.get("implementation_strategy_request") == "root-only":
                raise GraphError("Run явно закреплён за root-only implementation.")
            if current_contract:
                accepted = [item for item in state.get("slices", {}).values() if item.get("status") == "accepted"]
                if accepted:
                    _, checkpoint_sha = load_context_checkpoint(state, run_dir)
                    if state.get("context", {}).get("rehydrated_checkpoint_sha256") != checkpoint_sha:
                        raise GraphError("Перед следующим slice выполни context-rehydrate для latest checkpoint.")
            draft = load_json(draft_path.resolve())
            expected_schema = graph_contract()["test_policy"]["packet_schema_version"] if current_contract else 1
            if draft.get("schema_version") != expected_schema:
                raise GraphError(f"Slice draft требует schema_version {expected_schema}.")
            identifier = slice_id(draft.get("slice_id"))
            strategy = draft.get("strategy")
            if strategy not in {"delegated-sequential", "delegated-parallel"}:
                raise GraphError("Slice strategy должна быть delegated-sequential или delegated-parallel.")
            policy = graph_contract()["delegation_policy"]
            if strategy == "delegated-parallel" and not policy["parallel_write_enabled"]:
                raise GraphError("Parallel write slices отключены до проверяемой worktree isolation.")
            records = state.setdefault("slices", {})
            if identifier in records:
                raise GraphError(f"Slice уже зарегистрирован: {identifier}")
            successful_unaccepted = [
                name
                for name, item in records.items()
                if item.get("worker_status") in {"done", "done_with_concerns"}
                and item.get("status") != "accepted"
            ]
            if current_contract and successful_unaccepted:
                raise GraphError(
                    "Перед следующим slice root обязан выполнить slice-accept: "
                    + ", ".join(sorted(successful_unaccepted))
                )
            repair_work_sha = verification_repair_work_sha(state) if current_contract else None
            repair_for = draft.get("repair_for_work_sha256")
            repair_records = [
                item for item in records.values() if item.get("repair_for_work_sha256") is not None
            ]
            normal_records = [
                item for item in records.values() if item.get("repair_for_work_sha256") is None
            ]
            if repair_work_sha is not None:
                if state.get("implementation_strategy") != "delegated-sequential":
                    raise GraphError("Verifier repair slice допустим только для уже delegated candidate.")
                if repair_for != repair_work_sha:
                    raise GraphError(
                        "Verifier repair slice требует exact repair_for_work_sha256 rejected candidate."
                    )
                if len(repair_records) >= int(
                    graph_contract()["limits"]["max_verification_repair_slices"]
                ):
                    raise GraphError("Превышен отдельный лимит verifier repair slices.")
            else:
                if repair_for is not None:
                    raise GraphError("repair_for_work_sha256 допустим только после verifier reject.")
                unresolved = [
                    name
                    for name, item in records.items()
                    if item.get("worker_status") in {"needs_context", "blocked"}
                    and not any(
                        Path(str(successor.get("packet_path", ""))).is_file()
                        and load_json(Path(successor["packet_path"])).get("supersedes") == name
                        for successor in records.values()
                    )
                ]
                if current_contract and unresolved and draft.get("supersedes") != unresolved[-1]:
                    raise GraphError(
                        "Следующий normal slice обязан supersedes exact unresolved slice: "
                        + unresolved[-1]
                    )
                if len(normal_records) >= int(graph_contract()["limits"]["max_slices_per_run"]):
                    raise GraphError("Превышен лимит normal slice packets для одного run.")
            current_strategy = state.get("implementation_strategy", "root-only")
            if current_strategy not in {"root-only", strategy}:
                raise GraphError("Нельзя смешивать implementation strategies внутри одного run.")
            if strategy == "delegated-sequential" and any(item.get("status") == "ready" for item in records.values()):
                raise GraphError("Delegated-sequential допускает только один активный slice.")
            plan_path = snapshots.safe_join_no_symlinks(root, state["plan_path"])
            digest, scope = validate_plan(plan_path)
            if state["mode"] == "implement":
                prior = state.get("task_state_snapshot", {}).get("checkpoints", {}).get("plan-review")
                if (
                    not isinstance(prior, dict)
                    or not reviewed_digest_is_effective(state, run_dir, prior.get("plan_digest"), digest)
                    or prior.get("verdict") != "pass"
                ):
                    raise GraphError("Implement slice требует точный сохранённый plan review.")
                plan_review = {"mode": "reused", "receipt": "task-state:plan-review"}
            else:
                raw_review = draft.get("plan_review")
                if not isinstance(raw_review, dict):
                    raise GraphError("Full slice draft требует plan_review до делегации.")
                review_mode = raw_review.get("mode")
                review_receipt = meaningful(raw_review.get("receipt"), "plan_review.receipt", 6)
                allowed_review_modes = {"self", "independent"}
                if review_mode not in allowed_review_modes:
                    raise GraphError("Full slice plan_review mode должен быть self или independent.")
                if state["profile"] in {"complex", "critical"} and review_mode != "independent":
                    raise GraphError("Complex/critical slice требует independent plan review до worker.")
                plan_review = {"mode": review_mode, "receipt": review_receipt}
            root_only_amendment_receipts: list[str] = []
            for amendment in state.get("scope_amendments", []):
                amendment_path = Path(str(amendment.get("path", "")))
                if not amendment_path.is_file() or sha256_file(amendment_path) != amendment.get("sha256"):
                    raise GraphError("Scope amendment receipt изменился перед slice-create.")
                amendment_artifact = load_json(amendment_path)
                if amendment_artifact.get("review_source") == "root-only-full":
                    root_only_amendment_receipts.append(
                        meaningful(
                            amendment_artifact.get("plan_review_receipt"),
                            "root-only amendment review receipt",
                            6,
                        )
                    )
            if any(receipt != plan_review["receipt"] for receipt in root_only_amendment_receipts):
                raise GraphError(
                    "Delegated packet должен сохранить exact review receipt root-only scope amendment."
                )
            owned = normalize_repo_paths(root, draft.get("owned_paths"), "owned_paths", allow_empty=False)
            outside_plan = snapshots.outside_scope(owned, scope)
            if outside_plan:
                raise GraphError("Slice ownership выходит за scope плана: " + ", ".join(outside_plan))
            excluded = normalize_repo_paths(root, draft.get("excluded_paths", []), "excluded_paths")
            overlap = sorted({f"{left} ↔ {right}" for left in owned for right in excluded if paths_overlap(left, right)})
            if overlap:
                raise GraphError("owned_paths пересекаются с excluded_paths: " + ", ".join(overlap))
            must_read = normalize_repo_paths(root, draft.get("must_read"), "must_read", allow_empty=False, require_files=True)
            snapshots_read = [
                {"path": relative, "sha256": sha256_file(snapshots.safe_join_no_symlinks(root, relative))}
                for relative in must_read
            ]
            known_facts = objects(draft.get("known_facts", []), "known_facts")
            normalized_facts: list[dict[str, str]] = []
            for fact in known_facts:
                source = normalize_repo_paths(root, [fact.get("source")], "known_facts.source", require_files=True)[0]
                normalized_facts.append(
                    {"fact": meaningful(fact.get("fact"), "known fact"), "source": source}
                )
            stop_questions = strings(draft.get("stop_questions", []), "stop_questions")
            acceptance = strings(draft.get("acceptance"), "acceptance", allow_empty=False)
            if current_contract:
                test_impact = validate_test_impact(root, draft.get("test_impact"), owned)
                slice_checks = normalize_checks(draft.get("slice_checks"), "slice_checks", allow_empty=False)
                deferred_final_checks = normalize_checks(
                    draft.get("deferred_final_checks", []), "deferred_final_checks"
                )
                e2e_impact = next(item for item in test_impact if item["level"] == "e2e")
                if e2e_impact["action"] != "not-applicable" and not deferred_final_checks:
                    raise GraphError(
                        "Applicable E2E impact требует хотя бы один deferred_final_check для финального flow."
                    )
            else:
                test_impact = []
                slice_checks = normalize_legacy_checks(
                    draft.get("verification_commands"), "verification_commands", allow_empty=False
                )
                deferred_final_checks = []
            objective = meaningful(draft.get("objective"), "slice objective", 12)
            capability_context = validate_capability_context(draft.get("capability_context", {}))
            supersedes = draft.get("supersedes")
            if supersedes is not None:
                supersedes = slice_id(supersedes)
                previous = records.get(supersedes)
                if not previous or previous.get("worker_status") not in {"needs_context", "blocked"}:
                    raise GraphError("supersedes должен ссылаться на needs_context или blocked slice.")
            baseline = manifest(root, state["plan_path"])
            target_dir = slice_directory(run_dir, identifier)
            baseline_path = target_dir / SLICE_BASELINE_NAME
            packet = {
                "schema_version": expected_schema,
                "slice_id": identifier,
                "strategy": strategy,
                "plan_digest": digest,
                "base_repo_digest": snapshots.manifest_digest(baseline),
                "objective": objective,
                "plan_review": plan_review,
                "owned_paths": owned,
                "excluded_paths": excluded,
                "must_read": snapshots_read,
                "known_facts": normalized_facts,
                "stop_questions": stop_questions,
                "acceptance": acceptance,
                **(
                    {
                        "test_impact": test_impact,
                        "slice_checks": slice_checks,
                        "deferred_final_checks": deferred_final_checks,
                        "context_checkpoint": (
                            {
                                "path": str(run_dir / CONTEXT_CHECKPOINT_NAME),
                                "sha256": state.get("context", {}).get("latest_checkpoint_sha256"),
                            }
                            if state.get("context", {}).get("latest_checkpoint_sha256")
                            else None
                        ),
                    }
                    if current_contract
                    else {"verification_commands": slice_checks}
                ),
                "capability_context": capability_context,
                "supersedes": supersedes,
                **({"repair_for_work_sha256": repair_work_sha} if repair_work_sha else {}),
                "created_at": now(),
            }
            packet_path = target_dir / SLICE_PACKET_NAME
            try:
                target_dir.mkdir(parents=True, exist_ok=False)
                atomic_json(baseline_path, baseline)
                atomic_json(packet_path, packet)
                packet_sha = sha256_file(packet_path)
                record = {
                    "slice_id": identifier,
                    "strategy": strategy,
                    "status": "ready",
                    "packet_path": str(packet_path),
                    "packet_sha256": packet_sha,
                    "baseline_path": str(baseline_path),
                    "base_repo_digest": packet["base_repo_digest"],
                    "worker_status": None,
                    "receipt_path": None,
                    "receipt_sha256": None,
                    "repair_for_work_sha256": repair_work_sha,
                    "created_at": packet["created_at"],
                }
                records[identifier] = record
                state["implementation_strategy"] = strategy
                save_run(run_dir, state)
            except Exception:
                records.pop(identifier, None)
                packet_path.unlink(missing_ok=True)
                baseline_path.unlink(missing_ok=True)
                with contextlib.suppress(OSError):
                    target_dir.rmdir()
                raise
    return result(
        "ready",
        "Slice packet зафиксирован; передай worker точный path и SHA-256.",
        artifacts=[str(packet_path), str(baseline_path)],
        data={"slice_id": identifier, "packet": str(packet_path), "packet_sha256": packet_sha},
    )


def validate_worker_test_changes(
    root: Path,
    packet: dict[str, Any],
    receipt: dict[str, Any],
    changed: list[str],
    status: str,
) -> list[dict[str, Any]]:
    raw = objects(receipt.get("test_changes"), "test_changes", allow_empty=False)
    by_level: dict[str, dict[str, Any]] = {}
    for item in raw:
        level = item.get("level")
        action = item.get("action")
        if not isinstance(level, str) or level in by_level:
            raise GraphError("test_changes требует уникальный test level.")
        paths = normalize_repo_paths(root, item.get("paths", []), f"test_changes {level}.paths")
        by_level[level] = {"level": level, "action": action, "paths": paths}
    expected = {item["level"]: item for item in packet["test_impact"]}
    if set(by_level) != set(expected):
        raise GraphError("Worker test_changes должен покрыть точный test_impact packet.")
    normalized: list[dict[str, Any]] = []
    for level, impact in expected.items():
        actual = by_level[level]
        if actual["action"] != impact["action"] or actual["paths"] != impact["paths"]:
            raise GraphError(f"Worker test_changes не совпадает с packet для {level}.")
        if (
            status in {"done", "done_with_concerns"}
            and impact["action"] in {"add", "update"}
            and any(path not in changed for path in impact["paths"])
        ):
            raise GraphError(f"Worker обязан изменить объявленные {level} tests для action {impact['action']}.")
        if (
            status in {"done", "done_with_concerns"}
            and impact["action"] == "reuse"
            and any(path in changed for path in impact["paths"])
        ):
            raise GraphError(f"Worker изменил {level} test, объявленный reuse; используй action update.")
        normalized.append(actual)
    return normalized


def record_slice(run_dir: Path, identifier: str, receipt_path: Path) -> dict[str, Any]:
    identifier = slice_id(identifier)
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            current_contract = state.get("graph_version") == graph_contract()["graph_version"]
            if not current_contract and state.get("graph_version") != "3.3.0":
                raise GraphError("Worker receipts недоступны для этой legacy Task Delivery версии.")
            if state["status"] != "running" or state["current"] != "work":
                raise GraphError("Worker receipt можно записать только внутри work.")
            record = state.get("slices", {}).get(identifier)
            if not record or record.get("status") != "ready":
                raise GraphError("Slice не найден или уже имеет receipt.")
            packet_path = Path(record["packet_path"])
            baseline_path = Path(record["baseline_path"])
            if sha256_file(packet_path) != record["packet_sha256"]:
                raise GraphError("Slice packet изменился после регистрации.")
            packet = load_json(packet_path)
            baseline = snapshots.load_manifest(baseline_path)
            if snapshots.manifest_digest(baseline) != record["base_repo_digest"]:
                raise GraphError("Slice baseline изменился после регистрации.")
            current_plan = snapshots.safe_join_no_symlinks(root, state["plan_path"])
            if plan_digest(current_plan) != packet["plan_digest"]:
                raise GraphError("План изменился после выдачи slice packet; создай новый packet.")
            receipt = load_json(receipt_path.resolve())
            expected_schema = graph_contract()["test_policy"]["packet_schema_version"] if current_contract else 1
            if receipt.get("schema_version") != expected_schema or slice_id(receipt.get("slice_id")) != identifier:
                raise GraphError(f"Worker receipt требует schema_version {expected_schema} и точный slice_id.")
            if receipt.get("packet_sha256") != record["packet_sha256"]:
                raise GraphError("Worker receipt связан с другим slice packet.")
            worker_receipt = meaningful(receipt.get("worker_receipt"), "worker_receipt", 6)
            status = receipt.get("status")
            if status not in WORKER_STATUSES:
                raise GraphError("Worker status должен быть done|done_with_concerns|needs_context|blocked.")
            changed = snapshots.changed_paths(baseline, manifest(root, state["plan_path"]))
            declared = normalize_repo_paths(root, receipt.get("changed_paths", []), "changed_paths")
            if sorted(declared) != changed:
                raise GraphError("Worker changed_paths не совпадает с дельтой slice baseline.")
            outside = snapshots.outside_scope(changed, packet["owned_paths"])
            if outside:
                raise GraphError("Worker изменил пути вне slice ownership: " + ", ".join(outside[:20]))
            if status in {"done", "done_with_concerns"} and not changed:
                raise GraphError("Завершённый implementation slice требует фактическую дельту.")
            if current_contract and status in {"needs_context", "blocked"} and changed:
                raise GraphError(
                    "needs_context/blocked slice не может оставлять непринятую дельту; "
                    "worker должен откатить только собственные edits по pre-edit patch, сохранив user baseline."
                )
            tests = validate_test_records(
                receipt.get("tests", []),
                "worker tests",
                require_pass=status in {"done", "done_with_concerns"},
                include_check_id=current_contract,
            )
            if status in {"done", "done_with_concerns"}:
                assigned = packet["slice_checks"] if current_contract else packet["verification_commands"]
                if current_contract:
                    expected = {item["check_id"] for item in assigned}
                    actual = {item["check_id"] for item in tests if item["status"] == "passed"}
                else:
                    expected = {(item["command"], item["purpose"]) for item in assigned}
                    actual = {
                        (item["command"], item["purpose"])
                        for item in tests
                        if item["status"] == "passed"
                    }
                missing = expected - actual
                if missing:
                    raise GraphError("Worker не выполнил назначенные slice checks.")
            concerns = strings(receipt.get("concerns", []), "concerns")
            risks = strings(receipt.get("residual_risks", []), "residual_risks")
            if status == "done" and concerns:
                raise GraphError("Статус done не должен скрывать concerns; используй done_with_concerns.")
            if status == "done_with_concerns" and not concerns:
                raise GraphError("done_with_concerns требует непустой concerns.")
            context_request = str(receipt.get("context_request") or "").strip()
            blocker = str(receipt.get("blocker") or "").strip()
            if status == "needs_context" and len(context_request) < 8:
                raise GraphError("needs_context требует содержательный context_request.")
            if status == "blocked" and len(blocker) < 8:
                raise GraphError("blocked требует содержательный blocker.")
            artifacts = normalize_repo_paths(root, receipt.get("artifacts", []), "artifacts")
            for relative in artifacts:
                if not snapshots.safe_join_no_symlinks(root, relative).exists():
                    raise GraphError(f"Worker artifact не существует: {relative}")
            discoveries = objects(receipt.get("discoveries", []), "discoveries")
            normalized_discoveries: list[dict[str, str]] = []
            for discovery in discoveries:
                source = normalize_repo_paths(
                    root, [discovery.get("source")], "discoveries.source", require_files=True
                )[0]
                normalized_discoveries.append(
                    {"fact": meaningful(discovery.get("fact"), "discovery fact"), "source": source}
                )
            test_changes = (
                validate_worker_test_changes(root, packet, receipt, changed, status) if current_contract else []
            )
            deferred = (
                normalize_checks(receipt.get("deferred_final_checks", []), "worker deferred_final_checks")
                if current_contract
                else []
            )
            if current_contract and deferred != packet["deferred_final_checks"]:
                raise GraphError("Worker deferred_final_checks не совпадают с packet.")
            canonical = {
                "schema_version": expected_schema,
                "slice_id": identifier,
                "packet_sha256": record["packet_sha256"],
                "worker_receipt": worker_receipt,
                "status": status,
                "summary": meaningful(receipt.get("summary"), "worker summary", 12),
                "changed_paths": changed,
                "tests": tests,
                **(
                    {"test_changes": test_changes, "deferred_final_checks": deferred}
                    if current_contract
                    else {}
                ),
                "artifacts": artifacts,
                "capabilities_used": validate_worker_capabilities(packet, receipt, status),
                "concerns": concerns,
                "residual_risks": risks,
                "discoveries": normalized_discoveries,
                "context_request": context_request or None,
                "blocker": blocker or None,
                "recorded_at": now(),
            }
            target = slice_directory(run_dir, identifier) / "worker-receipt.json"
            atomic_json(target, canonical)
            record.update(
                {
                    "status": "recorded",
                    "worker_status": status,
                    "worker_receipt": worker_receipt,
                    "receipt_path": str(target),
                    "receipt_sha256": sha256_file(target),
                    "changed_paths": changed,
                    "recorded_at": canonical["recorded_at"],
                }
            )
            terminal_unsuccessful = False
            if current_contract and status in {"needs_context", "blocked"}:
                normal_count = sum(
                    item.get("repair_for_work_sha256") is None
                    for item in state.get("slices", {}).values()
                )
                terminal_unsuccessful = (
                    record.get("repair_for_work_sha256") is not None
                    or normal_count >= int(graph_contract()["limits"]["max_slices_per_run"])
                )
                if terminal_unsuccessful:
                    state["status"] = "blocked"
                    state["nodes"]["work"]["status"] = "failed"
                    state["node_retries"]["work"] = graph_contract()["limits"]["max_node_retries"]
            save_run(run_dir, state)
    if terminal_unsuccessful:
        return result(
            "blocked",
            "Последний допустимый slice завершился без принятой дельты; нужен новый reviewed run, а не скрытый обход лимита.",
            artifacts=[str(target)],
            data={
                "slice_id": identifier,
                "status": status,
                "packet_sha256": record["packet_sha256"],
                "receipt_sha256": record["receipt_sha256"],
            },
        )
    return result(
        "recorded",
        f"Worker receipt зафиксирован со статусом {status}; root обязан проверить реальный diff.",
        artifacts=[str(target)],
        data={
            "slice_id": identifier,
            "status": status,
            "packet_sha256": record["packet_sha256"],
            "receipt_sha256": record["receipt_sha256"],
        },
    )

def write_context_checkpoint(state: dict[str, Any], run_dir: Path, *, next_objective: str) -> tuple[Path, str]:
    root = Path(state["root"])
    plan_path = snapshots.safe_join_no_symlinks(root, state["plan_path"])
    digest, scope = validate_plan(plan_path)
    accepted: list[dict[str, Any]] = []
    deferred_by_id: dict[str, dict[str, str]] = {}
    verified_discoveries: list[dict[str, str]] = []
    for identifier, record in sorted(state.get("slices", {}).items()):
        if record.get("status") != "accepted":
            continue
        packet_path = Path(record["packet_path"])
        receipt_path = Path(record["receipt_path"])
        acceptance_path = Path(record["acceptance_path"])
        if (
            not packet_path.is_file()
            or sha256_file(packet_path) != record["packet_sha256"]
            or not receipt_path.is_file()
            or sha256_file(receipt_path) != record["receipt_sha256"]
            or not acceptance_path.is_file()
            or sha256_file(acceptance_path) != record["acceptance_sha256"]
        ):
            raise GraphError(f"Accepted slice artifacts изменились: {identifier}")
        packet = load_json(packet_path)
        acceptance = load_json(acceptance_path)
        for check in packet.get("deferred_final_checks", []):
            existing = deferred_by_id.get(check["check_id"])
            if existing is not None and existing != check:
                raise GraphError("Deferred final check identity conflict.")
            deferred_by_id[check["check_id"]] = check
        verified_discoveries.extend(acceptance.get("verified_discoveries", []))
        accepted.append(
            {
                "slice_id": identifier,
                "packet_sha256": record["packet_sha256"],
                "receipt_sha256": record["receipt_sha256"],
                "acceptance_sha256": record["acceptance_sha256"],
                "changed_paths": record.get("changed_paths", []),
                "root_tests": acceptance["tests"],
            }
        )
    if not accepted:
        raise GraphError("Context checkpoint требует хотя бы один accepted slice.")
    chain = validate_amendment_chain(state, run_dir, current_digest=digest)
    accepted_paths = {path for item in accepted for path in item["changed_paths"]}
    checkpoint = {
        "schema_version": graph_contract()["context_policy"]["checkpoint_schema_version"],
        "run_id": state["run_id"],
        "task_id": state["task_id"],
        "graph_version": state["graph_version"],
        "plan_path": state["plan_path"],
        "plan_digest": digest,
        "reviewed_base_digest": chain["base_digest"],
        "baseline_repo_digest": state["baseline_repo_digest"],
        "repository_digest": snapshots.manifest_digest(manifest(root, state["plan_path"])),
        "accepted_slices": accepted,
        "accepted_changed_paths": sorted(accepted_paths),
        "plan_scope": sorted(scope),
        "verified_discoveries": verified_discoveries,
        "deferred_final_checks": [deferred_by_id[key] for key in sorted(deferred_by_id)],
        "next_objective": meaningful(next_objective, "next_objective", 12),
        "scope_amendment_receipts": [item["sha256"] for item in state.get("scope_amendments", [])],
        "created_at": now(),
    }
    path = run_dir / CONTEXT_CHECKPOINT_NAME
    atomic_json(path, checkpoint)
    digest_value = sha256_file(path)
    state["context"] = {
        "latest_checkpoint_path": str(path),
        "latest_checkpoint_sha256": digest_value,
        "rehydrated_checkpoint_sha256": None,
        "rehydrated_at": None,
    }
    return path, digest_value


def accept_slice(run_dir: Path, identifier: str, acceptance_path: Path) -> dict[str, Any]:
    identifier = slice_id(identifier)
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state.get("graph_version") != graph_contract()["graph_version"]:
                raise GraphError("slice-accept доступен только для Task Delivery 3.4 runs.")
            if state["status"] != "running" or state["current"] != "work":
                raise GraphError("Slice acceptance можно записать только внутри work.")
            record = state.get("slices", {}).get(identifier)
            if not record or record.get("status") != "recorded":
                raise GraphError("Slice не имеет готового immutable worker receipt.")
            if record.get("worker_status") not in {"done", "done_with_concerns"}:
                raise GraphError("Root может принять только done или done_with_concerns slice.")
            packet = load_json(Path(record["packet_path"]))
            receipt = load_json(Path(record["receipt_path"]))
            current_plan = snapshots.safe_join_no_symlinks(root, state["plan_path"])
            if packet.get("plan_digest") != plan_digest(current_plan):
                raise GraphError("План изменился после выдачи slice packet; создай новый packet.")
            draft = load_json(acceptance_path.resolve())
            if draft.get("schema_version") != 1 or slice_id(draft.get("slice_id")) != identifier:
                raise GraphError("Root acceptance требует schema_version 1 и точный slice_id.")
            if (
                draft.get("packet_sha256") != record["packet_sha256"]
                or draft.get("receipt_sha256") != record["receipt_sha256"]
            ):
                raise GraphError("Root acceptance связан с другим packet или worker receipt.")
            expected_verdict = (
                "accepted_with_concerns"
                if record["worker_status"] == "done_with_concerns"
                else "accepted"
            )
            if draft.get("verdict") != expected_verdict:
                raise GraphError("Root acceptance verdict не соответствует worker status.")
            verified_paths = normalize_repo_paths(
                root,
                draft.get("verified_changed_paths"),
                "verified_changed_paths",
                allow_empty=False,
            )
            if sorted(verified_paths) != sorted(record.get("changed_paths", [])):
                raise GraphError("Root acceptance должен проверить точные worker changed_paths.")
            tests = validate_test_records(draft.get("tests"), "root acceptance tests", require_pass=True)
            assigned_ids = {item["check_id"] for item in packet["slice_checks"]}
            replayed = {item["check_id"] for item in tests}.intersection(assigned_ids)
            if len(replayed) < graph_contract()["test_policy"]["root_replay_minimum_per_slice"]:
                raise GraphError("Root acceptance должен повторить хотя бы один exact slice check.")
            resolution = strings(draft.get("concerns_resolution", []), "concerns_resolution")
            if record["worker_status"] == "done_with_concerns" and not resolution:
                raise GraphError("Принятие concerns требует явное concerns_resolution.")
            discoveries = objects(draft.get("verified_discoveries", []), "verified_discoveries")
            available = receipt.get("discoveries", [])
            normalized_discoveries: list[dict[str, str]] = []
            for discovery in discoveries:
                candidate = {
                    "fact": meaningful(discovery.get("fact"), "verified discovery fact"),
                    "source": normalize_repo_paths(
                        root,
                        [discovery.get("source")],
                        "verified discovery source",
                        require_files=True,
                    )[0],
                }
                if candidate not in available:
                    raise GraphError("Root acceptance может подтвердить только worker discovery из receipt.")
                normalized_discoveries.append(candidate)
            canonical = {
                "schema_version": 1,
                "slice_id": identifier,
                "packet_sha256": record["packet_sha256"],
                "receipt_sha256": record["receipt_sha256"],
                "verdict": expected_verdict,
                "verified_changed_paths": verified_paths,
                "tests": tests,
                "verified_discoveries": normalized_discoveries,
                "concerns_resolution": resolution,
                "next_objective": meaningful(draft.get("next_objective"), "next_objective", 12),
                "accepted_at": now(),
            }
            target = slice_directory(run_dir, identifier) / SLICE_ACCEPTANCE_NAME
            checkpoint_file = run_dir / CONTEXT_CHECKPOINT_NAME
            old_checkpoint_text = (
                checkpoint_file.read_text(encoding="utf-8") if checkpoint_file.is_file() else None
            )
            old_record = json.loads(json.dumps(record))
            old_context = json.loads(json.dumps(state.get("context", {})))
            try:
                atomic_json(target, canonical)
                record.update(
                    {
                        "status": "accepted",
                        "acceptance_path": str(target),
                        "acceptance_sha256": sha256_file(target),
                        "accepted_at": canonical["accepted_at"],
                    }
                )
                checkpoint_path, checkpoint_sha = write_context_checkpoint(
                    state, run_dir, next_objective=canonical["next_objective"]
                )
                save_run(run_dir, state)
            except Exception:
                state["slices"][identifier] = old_record
                state["context"] = old_context
                target.unlink(missing_ok=True)
                if old_checkpoint_text is None:
                    checkpoint_file.unlink(missing_ok=True)
                else:
                    atomic_text(checkpoint_file, old_checkpoint_text)
                raise
    return result(
        "accepted",
        "Slice принят root; context checkpoint зафиксирован и требует rehydrate перед следующим slice.",
        artifacts=[str(target), str(checkpoint_path)],
        data={
            "slice_id": identifier,
            "acceptance_sha256": record["acceptance_sha256"],
            "checkpoint_sha256": checkpoint_sha,
        },
    )


def rehydrate_context(run_dir: Path) -> dict[str, Any]:
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state.get("graph_version") != graph_contract()["graph_version"]:
                raise GraphError("context-rehydrate доступен только для Task Delivery 3.4 runs.")
            if state["status"] != "running" or state["current"] != "work":
                raise GraphError("Context можно rehydrate только внутри work.")
            checkpoint, digest_value = load_context_checkpoint(state, run_dir)
            state["context"]["rehydrated_checkpoint_sha256"] = digest_value
            state["context"]["rehydrated_at"] = now()
            save_run(run_dir, state)
    return result(
        "rehydrated",
        "Verified Task Delivery checkpoint загружен для следующего slice.",
        artifacts=[str(run_dir / CONTEXT_CHECKPOINT_NAME)],
        data={
            "checkpoint_sha256": digest_value,
            "plan_digest": checkpoint["plan_digest"],
            "accepted_slices": checkpoint["accepted_slices"],
            "verified_discoveries": checkpoint["verified_discoveries"],
            "deferred_final_checks": checkpoint["deferred_final_checks"],
            "next_objective": checkpoint["next_objective"],
        },
    )


def amend_scope(run_dir: Path, draft_path: Path) -> dict[str, Any]:
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state.get("graph_version") != graph_contract()["graph_version"]:
                raise GraphError("scope-amend доступен только для Task Delivery 3.4 runs.")
            if state["status"] != "running" or state["current"] != "work" or state["mode"] == "plan":
                raise GraphError("Technical scope amendment доступен только внутри implementation work.")
            if any(
                item.get("status") == "ready"
                or (
                    item.get("status") == "recorded"
                    and item.get("worker_status") in {"done", "done_with_concerns"}
                )
                for item in state.get("slices", {}).values()
            ):
                raise GraphError("Нельзя менять scope при активном незавершённом slice packet.")
            records = state.setdefault("scope_amendments", [])
            limit = int(graph_contract()["limits"]["max_root_technical_amendments"])
            if len(records) >= limit:
                raise GraphError("Превышен лимит root-technical scope amendments.")
            draft = load_json(draft_path.resolve())
            if draft.get("schema_version") != 1 or draft.get("authority") != "root-technical":
                raise GraphError("scope-amend требует schema_version 1 и authority root-technical.")
            impacts = draft.get("impacts")
            required_impacts = {
                "outcome_changed",
                "acceptance_changed",
                "public_contract_changed",
                "data_or_security_changed",
                "external_state_changed",
                "risk_profile_changed",
            }
            if (
                not isinstance(impacts, dict)
                or set(impacts) != required_impacts
                or any(value is not False for value in impacts.values())
            ):
                raise GraphError("Consequential scope amendment требует user decision и новый reviewed plan run.")
            added = normalize_repo_paths(root, draft.get("added_paths"), "added_paths", allow_empty=False)
            if len(added) > int(graph_contract()["limits"]["max_paths_per_scope_amendment"]):
                raise GraphError("Technical scope amendment допускает не более двух bounded paths.")
            policy = graph_contract()["scope_amendment_policy"]
            protected_prefixes = policy["protected_prefixes"]
            protected_names = {name.casefold() for name in policy["protected_names"]}
            for relative in added:
                parts = Path(relative).parts
                basename = Path(relative).name
                folded_parts = tuple(part.casefold() for part in parts)
                folded_relative = relative.casefold()
                candidate = snapshots.safe_join_no_symlinks(root, relative)
                if (
                    path_allowed(folded_relative, [prefix.casefold() for prefix in protected_prefixes])
                    or any(
                        part in {
                            ".git",
                            ".codex",
                            ".agent-graphs",
                            "migrate",
                            "migration",
                            "migrations",
                            "secrets",
                        }
                        for part in folded_parts
                    )
                    or any(
                        left == ".github" and right == "workflows"
                        for left, right in zip(folded_parts, folded_parts[1:])
                    )
                    or basename.casefold() in protected_names
                    or basename.casefold().startswith(".env.")
                ):
                    raise GraphError(f"Protected path требует user decision и новый reviewed plan: {relative}")
                if candidate.exists() and (candidate.is_symlink() or not candidate.is_file()):
                    raise GraphError(f"Technical scope amendment допускает только exact file paths: {relative}")
                if not candidate.exists() and (not candidate.parent.is_dir() or "." not in basename):
                    raise GraphError(f"Новый technical scope path должен быть bounded file внутри существующего parent: {relative}")
            evidence = normalize_repo_paths(
                root,
                draft.get("evidence_paths"),
                "evidence_paths",
                allow_empty=False,
                require_files=True,
            )
            reason = meaningful(draft.get("reason"), "scope amendment reason", 16)
            plan_path = snapshots.safe_join_no_symlinks(root, state["plan_path"])
            text_value = plan_path.read_text(encoding="utf-8")
            before_digest, before_scope = validate_plan(plan_path)
            review_receipt = meaningful(
                draft.get("plan_review_receipt"), "scope amendment plan_review_receipt", 6
            )
            review_bound = False
            review_source: str | None = None
            if state["mode"] == "implement":
                prior_review = state.get("task_state_snapshot", {}).get("checkpoints", {}).get("plan-review")
                review_bound = (
                    isinstance(prior_review, dict)
                    and prior_review.get("plan_digest") == before_digest
                    and prior_review.get("verdict") == "pass"
                    and review_receipt == "task-state:plan-review"
                )
                if review_bound:
                    review_source = "task-state"
            elif (
                state["mode"] == "full"
                and state.get("implementation_strategy", "root-only") == "root-only"
                and not state.get("slices")
            ):
                review_bound = (
                    review_receipt == "root:self-review"
                    if state["profile"] in {"light", "standard"}
                    else review_receipt.startswith("/")
                )
                if review_bound:
                    review_source = "root-only-full"
            if not review_bound:
                for item in state.get("slices", {}).values():
                    packet_path = Path(str(item.get("packet_path", "")))
                    if not packet_path.is_file() or sha256_file(packet_path) != item.get("packet_sha256"):
                        continue
                    packet = load_json(packet_path)
                    packet_review = packet.get("plan_review", {})
                    if (
                        packet.get("plan_digest") == before_digest
                        and packet_review.get("receipt") == review_receipt
                    ):
                        review_bound = True
                        review_source = "slice-packet"
                        break
            if not review_bound:
                raise GraphError(
                    "Technical scope amendment требует exact reviewed base receipt; иначе нужен новый plan review."
                )
            redundant = [path for path in added if path_allowed(path, before_scope)]
            if redundant:
                raise GraphError("added_paths уже входят в plan scope: " + ", ".join(redundant))
            broad = [path for path in added if any(path_allowed(existing, [path]) for existing in before_scope)]
            if broad:
                raise GraphError("Technical scope amendment не может расширять reviewed file до parent tree: " + ", ".join(broad))
            match = re.search(r"(<!--\s*task-delivery:scope\s*\n)(.*?)(\n\s*-->)", text_value, flags=re.DOTALL)
            if not match:
                raise GraphError("PLAN.md не содержит машинный scope block.")
            after_scope = sorted(set(before_scope).union(added))
            replacement = match.group(1) + "\n".join(after_scope) + match.group(3)
            updated = text_value[: match.start()] + replacement + text_value[match.end() :]
            descriptor, temporary = tempfile.mkstemp(prefix=".scope-amend.", dir=plan_path.parent)
            temporary_path = Path(temporary)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(updated)
                after_digest, verified_scope = validate_plan(temporary_path)
            finally:
                temporary_path.unlink(missing_ok=True)
            if verified_scope != after_scope or after_digest == before_digest:
                raise GraphError("Scope amendment не создал ожидаемый plan identity.")
            artifact = {
                "schema_version": 1,
                "authority": "root-technical",
                "review_effect": "preserved",
                "before_digest": before_digest,
                "after_digest": after_digest,
                "before_scope": before_scope,
                "after_scope": after_scope,
                "plan_review_receipt": review_receipt,
                "review_source": review_source,
                "added_paths": added,
                "reason": reason,
                "evidence": [
                    {
                        "path": relative,
                        "sha256": sha256_file(snapshots.safe_join_no_symlinks(root, relative)),
                    }
                    for relative in evidence
                ],
                "impacts": impacts,
                "recorded_at": now(),
            }
            target = run_dir / SCOPE_AMENDMENTS_DIR / f"{len(records) + 1:02d}.json"
            has_accepted = any(item.get("status") == "accepted" for item in state.get("slices", {}).values())
            checkpoint_file = run_dir / CONTEXT_CHECKPOINT_NAME
            old_checkpoint_text: str | None = None
            previous_objective: str | None = None
            if has_accepted:
                previous, _ = load_context_checkpoint(state, run_dir)
                previous_objective = previous["next_objective"]
                old_checkpoint_text = checkpoint_file.read_text(encoding="utf-8")
            appended = False
            try:
                atomic_text(plan_path, updated)
                actual_digest, actual_scope = validate_plan(plan_path)
                if actual_digest != after_digest or actual_scope != after_scope:
                    raise GraphError("Scope amendment plan write не совпал с validated draft.")
                atomic_json(target, artifact)
                records.append(
                    {
                        "path": str(target),
                        "sha256": sha256_file(target),
                        "before_digest": before_digest,
                        "after_digest": after_digest,
                    }
                )
                appended = True
                validate_amendment_chain(state, run_dir, current_digest=after_digest)
                if has_accepted:
                    checkpoint_path, checkpoint_sha = write_context_checkpoint(
                        state, run_dir, next_objective=str(previous_objective)
                    )
                else:
                    checkpoint_path = None
                    checkpoint_sha = None
                save_run(run_dir, state)
            except Exception:
                if appended:
                    records.pop()
                atomic_text(plan_path, text_value)
                target.unlink(missing_ok=True)
                if old_checkpoint_text is not None:
                    atomic_text(checkpoint_file, old_checkpoint_text)
                raise
    artifacts = [str(target), str(plan_path)]
    if checkpoint_path is not None:
        artifacts.append(str(checkpoint_path))
    return result(
        "amended",
        "Safe technical scope amendment recorded without a user approval prompt.",
        artifacts=artifacts,
        data={
            "before_digest": before_digest,
            "after_digest": after_digest,
            "added_paths": added,
            "checkpoint_sha256": checkpoint_sha,
        },
    )


def validate_mcp_capabilities(capabilities: list[str]) -> None:
    policy = graph_contract()["mcp_policy"]
    prefix = policy["receipt_prefix"]
    fallback_prefix = policy["fallback_prefix"]
    receipts = [item for item in capabilities if item.startswith(prefix)]
    if not receipts:
        raise GraphError(
            "capabilities требует MCP receipt: mcp:<server> либо mcp:fallback:<reason>."
        )
    used: list[str] = []
    fallbacks: list[str] = []
    for receipt in receipts:
        if receipt.startswith(fallback_prefix):
            reason = receipt[len(fallback_prefix) :]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,}", reason):
                raise GraphError("MCP fallback требует содержательный machine-readable reason.")
            fallbacks.append(receipt)
            continue
        server = receipt[len(prefix) :]
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", server)
            or server in {"fallback", "discovery", "none", "not-needed"}
        ):
            raise GraphError(f"Некорректный MCP server receipt: {receipt}")
        used.append(receipt)
    if used and fallbacks:
        raise GraphError("MCP fallback нельзя записывать вместе с успешным MCP server receipt.")


def validate_agents(value: Any, profile: str, *, slice_contract: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise GraphError("agents должен быть списком.")
    graph = graph_contract()
    if len(value) > int(graph["limits"]["max_agents_per_run"]):
        raise GraphError("Превышен общий лимит агентов Task Delivery.")
    normalized: list[dict[str, Any]] = []
    receipts: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise GraphError("Каждый agent receipt должен быть объектом.")
        role = item.get("role")
        phase = item.get("phase")
        receipt = item.get("receipt")
        outcome = item.get("outcome")
        if role not in ALLOWED_ROLES or phase not in {"research", "plan-review", "implementation", "result-review"}:
            raise GraphError("Agent receipt содержит неизвестную роль или фазу.")
        if not isinstance(receipt, str) or len(receipt.strip()) < 6 or receipt in receipts:
            raise GraphError("Agent receipt должен быть уникальным и содержательным.")
        if role == "task_worker" and slice_contract:
            if phase != "implementation" or outcome not in WORKER_STATUSES:
                raise GraphError("task_worker требует phase=implementation и точный worker status.")
            worker_fields = {
                "slice_id": slice_id(item.get("slice_id")),
                "packet_sha256": hex_digest(item.get("packet_sha256"), "agent.packet_sha256"),
                "receipt_sha256": hex_digest(item.get("receipt_sha256"), "agent.receipt_sha256"),
            }
        else:
            if outcome not in {"used", "pass", "completed"}:
                raise GraphError("Agent outcome должен быть used, pass или completed.")
            worker_fields = {}
        receipts.add(receipt)
        normalized.append(
            {"role": role, "phase": phase, "receipt": receipt, "outcome": outcome, **worker_fields}
        )
    workers = sum(item["role"] == "task_worker" for item in normalized)
    explorers = sum(item["role"] == "task_explorer" for item in normalized)
    worker_limit = int(graph["limits"]["max_slices_per_run"]) + int(
        graph["limits"]["max_verification_repair_slices"]
    )
    if workers > worker_limit or explorers > 2:
        raise GraphError(
            "Task Delivery допускает не более двух normal workers, одного verifier-repair worker и двух explorers."
        )
    required = set()
    if profile in {"complex", "critical"}:
        required.add("task_plan_reviewer")
    if profile == "critical":
        required.add("task_risk_reviewer")
    return normalized


def validate_research(value: Any) -> None:
    if not isinstance(value, dict):
        raise GraphError("research должен быть объектом.")
    strings(value.get("internal"), "research.internal", allow_empty=False)
    external = value.get("external")
    if not isinstance(external, dict) or external.get("status") not in {"not-needed", "used"}:
        raise GraphError("research.external требует status not-needed|used.")
    if external["status"] == "used" and len(str(external.get("receipt", "")).strip()) < 6:
        raise GraphError("Использованный внешний research требует receipt.")
    if external["status"] == "not-needed" and len(str(external.get("reason", "")).strip()) < 8:
        raise GraphError("Отказ от внешнего research требует причину.")


def validate_tests(value: Any, mode: str, *, staged_contract: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise GraphError("tests должен быть списком.")
    if mode == "plan":
        if staged_contract and value:
            raise GraphError("Plan mode не должен объявлять выполненные implementation tests.")
        return []
    if not value:
        raise GraphError("Реализация требует хотя бы одну фактически выполненную проверку.")
    return validate_test_records(
        value,
        "tests",
        require_pass=True,
        include_check_id=staged_contract,
    )


def review_receipts(agents: list[dict[str, Any]], role: str) -> list[str]:
    return [item["receipt"] for item in agents if item["role"] == role and item["outcome"] == "pass"]


def validate_slice_acceptance(
    state: dict[str, Any],
    run_dir: Path,
    implementation: dict[str, Any],
    agents: list[dict[str, Any]],
    changed: list[str],
    task_tests: list[dict[str, Any]],
) -> dict[str, Any]:
    strategy = implementation.get("strategy")
    if strategy not in IMPLEMENTATION_STRATEGIES:
        raise GraphError("implementation.strategy должен быть root-only|delegated-sequential|delegated-parallel.")
    declared_slices = objects(implementation.get("slices", []), "implementation.slices")
    records = state.get("slices", {})
    if not isinstance(records, dict):
        raise GraphError("Run slice registry повреждён.")
    workers = [item for item in agents if item["role"] == "task_worker"]
    if state["mode"] == "plan":
        if strategy != "root-only" or declared_slices or records or workers:
            raise GraphError("Режим plan не допускает implementation slices или task_worker.")
        return {"strategy": strategy, "accepted_slices": []}
    if strategy == "root-only":
        if declared_slices or records or workers:
            raise GraphError("root-only implementation не должен содержать slice artifacts или task_worker.")
        request = state.get("implementation_strategy_request", "auto")
        preferred = state.get("implementation_strategy_preferred", "root-only")
        if request == "delegated-sequential":
            raise GraphError("Явный запрос на реализацию слайсами запрещает root-only completion.")
        if request == "auto" and preferred == "delegated-sequential":
            meaningful(
                implementation.get("delegation_reason"),
                "implementation.delegation_reason для adaptive root-only",
                12,
            )
        return {"strategy": strategy, "accepted_slices": []}
    if state.get("implementation_strategy_request") == "root-only":
        raise GraphError("Run явно закреплён за root-only implementation.")
    if strategy == "delegated-parallel":
        raise GraphError("delegated-parallel остаётся fail-closed до проверяемой worktree isolation.")
    if state.get("implementation_strategy") != strategy:
        raise GraphError("task.json strategy не совпадает с зарегистрированной strategy run.")
    current_contract = state.get("graph_version") == graph_contract()["graph_version"]
    allowed_record_statuses = {"recorded", "accepted"} if current_contract else {"recorded"}
    if any(item.get("status") not in allowed_record_statuses for item in records.values()):
        raise GraphError("Все зарегистрированные slices должны иметь immutable worker receipt.")
    if current_contract and any(
        item.get("worker_status") in {"done", "done_with_concerns"}
        and item.get("status") != "accepted"
        for item in records.values()
    ):
        raise GraphError("Каждый successful 3.4 slice требует immutable root acceptance до final work.")
    by_slice = {item["slice_id"]: item for item in workers}
    if len(by_slice) != len(workers):
        raise GraphError("Каждый task_worker должен ссылаться на уникальный slice_id.")
    if set(by_slice) != set(records):
        raise GraphError("Agent receipts должны покрывать все и только зарегистрированные slices.")
    for identifier, record in records.items():
        worker = by_slice[identifier]
        if (
            worker["receipt"] != record.get("worker_receipt")
            or worker["outcome"] != record.get("worker_status")
            or worker["packet_sha256"] != record.get("packet_sha256")
            or worker["receipt_sha256"] != record.get("receipt_sha256")
        ):
            raise GraphError(f"Agent receipt не совпадает с immutable slice record: {identifier}")
        packet_path = Path(record["packet_path"])
        receipt_path = Path(record["receipt_path"])
        if (
            not packet_path.is_file()
            or sha256_file(packet_path) != record["packet_sha256"]
            or not receipt_path.is_file()
            or sha256_file(receipt_path) != record["receipt_sha256"]
        ):
            raise GraphError(f"Slice artifacts изменились после record: {identifier}")
        packet = load_json(packet_path)
        packet_review = packet.get("plan_review", {})
        if packet_review.get("mode") == "independent" and packet_review.get("receipt") not in review_receipts(
            agents, "task_plan_reviewer"
        ):
            raise GraphError(f"Slice plan-review receipt отсутствует в task.json agents: {identifier}")
    if current_contract:
        for identifier, record in records.items():
            if record.get("worker_status") not in {"needs_context", "blocked"}:
                continue
            resolved = False
            for successor_id, successor in records.items():
                if successor_id == identifier or successor.get("status") != "accepted":
                    continue
                successor_packet = load_json(Path(successor["packet_path"]))
                if successor_packet.get("supersedes") == identifier:
                    resolved = True
                    break
            if not resolved:
                raise GraphError(
                    f"Unsuccessful slice {identifier} должен быть разрешён accepted superseding slice."
                )
    accepted: list[dict[str, Any]] = []
    accepted_ids: set[str] = set()
    deferred_by_id: dict[str, dict[str, str]] = {}
    for item in declared_slices:
        identifier = slice_id(item.get("slice_id"))
        if identifier in accepted_ids or identifier not in records:
            raise GraphError("implementation.slices содержит неизвестный или повторный slice_id.")
        record = records[identifier]
        if record.get("worker_status") not in {"done", "done_with_concerns"}:
            raise GraphError("Root может принять только done или done_with_concerns slice.")
        if item.get("packet_sha256") != record["packet_sha256"] or item.get("receipt_sha256") != record["receipt_sha256"]:
            raise GraphError("Root acceptance связан с другим packet или worker receipt.")
        if current_contract:
            if record.get("status") != "accepted":
                raise GraphError("Task Delivery 3.4 требует отдельный slice-accept до итогового task.json.")
            if item.get("acceptance_sha256") != record.get("acceptance_sha256"):
                raise GraphError("task.json связан с другим root acceptance receipt.")
            acceptance_path = Path(str(record.get("acceptance_path", "")))
            expected_path = slice_directory(run_dir, identifier) / SLICE_ACCEPTANCE_NAME
            if acceptance_path.resolve(strict=False) != expected_path.resolve(strict=False):
                raise GraphError("Root acceptance имеет неожиданный путь.")
            if not acceptance_path.is_file() or sha256_file(acceptance_path) != record.get("acceptance_sha256"):
                raise GraphError("Root acceptance изменился после slice-accept.")
            acceptance = load_json(acceptance_path)
        else:
            acceptance = item.get("root_acceptance")
        if not isinstance(acceptance, dict):
            raise GraphError("Каждый принятый slice требует root_acceptance.")
        verdict = acceptance.get("verdict")
        expected_verdict = "accepted_with_concerns" if record["worker_status"] == "done_with_concerns" else "accepted"
        if verdict != expected_verdict:
            raise GraphError(f"Root acceptance verdict не соответствует worker status: {identifier}")
        verified_paths = normalize_repo_paths(
            Path(state["root"]), acceptance.get("verified_changed_paths"), "verified_changed_paths", allow_empty=False
        )
        if sorted(verified_paths) != sorted(record.get("changed_paths", [])):
            raise GraphError("Root acceptance должен проверить точные worker changed_paths.")
        if any(path not in changed for path in verified_paths):
            raise GraphError("Принятый slice ссылается на путь вне итоговой реализации.")
        root_tests = validate_test_records(
            acceptance.get("tests"),
            "root acceptance tests",
            require_pass=True,
            include_check_id=current_contract,
        )
        if not root_tests:
            raise GraphError("Root acceptance требует хотя бы одну независимо проверенную команду.")
        if current_contract:
            packet = load_json(Path(record["packet_path"]))
            assigned_ids = {check["check_id"] for check in packet["slice_checks"]}
            if not assigned_ids.intersection(check["check_id"] for check in root_tests):
                raise GraphError("Root acceptance должен повторить хотя бы один exact slice check.")
            for check in packet["deferred_final_checks"]:
                existing = deferred_by_id.get(check["check_id"])
                if existing is not None and existing != check:
                    raise GraphError("Deferred final check identity conflict.")
                deferred_by_id[check["check_id"]] = check
        resolution = strings(acceptance.get("concerns_resolution", []), "concerns_resolution")
        if record["worker_status"] == "done_with_concerns" and not resolution:
            raise GraphError("Принятие concerns требует явное concerns_resolution.")
        accepted_ids.add(identifier)
        accepted.append(
            {
                "slice_id": identifier,
                "packet_sha256": record["packet_sha256"],
                "receipt_sha256": record["receipt_sha256"],
                **({"acceptance_sha256": record["acceptance_sha256"]} if current_contract else {}),
                "root_acceptance": {
                    "verdict": verdict,
                    "verified_changed_paths": verified_paths,
                    "tests": root_tests,
                    "concerns_resolution": resolution,
                },
            }
        )
    expected_accepted = {
        identifier
        for identifier, record in records.items()
        if record.get("status") == ("accepted" if current_contract else "recorded")
        and record.get("worker_status") in {"done", "done_with_concerns"}
    }
    if accepted_ids != expected_accepted:
        raise GraphError("implementation.slices должен покрывать все и только root-accepted slices.")
    if not accepted_ids:
        raise GraphError("Delegated implementation требует хотя бы один root-accepted slice.")
    if current_contract:
        accepted_path_union = {
            path
            for item in accepted
            for path in item["root_acceptance"]["verified_changed_paths"]
        }
        if set(changed) != accepted_path_union:
            raise GraphError("Итоговая delegated delta должна иметь только root-accepted path provenance.")
        passed_ids = {item["check_id"] for item in task_tests}
        missing = set(deferred_by_id).difference(passed_ids)
        if missing:
            raise GraphError("Итоговые tests не выполнили все deferred_final_checks accepted slices.")
        checkpoint, checkpoint_sha = load_context_checkpoint(state, run_dir)
        checkpoint_ids = {item["slice_id"] for item in checkpoint["accepted_slices"]}
        if checkpoint_ids != accepted_ids:
            raise GraphError("Latest context checkpoint не покрывает точный набор accepted slices.")
    else:
        checkpoint_sha = None
    return {
        "strategy": strategy,
        "accepted_slices": accepted,
        "context_checkpoint_sha256": checkpoint_sha,
        "deferred_final_check_ids": sorted(deferred_by_id),
    }


def validate_work(state: dict[str, Any], artifact: dict[str, Any], outcome: str, run_dir: Path) -> dict[str, Any]:
    root = Path(state["root"])
    mode = state["mode"]
    profile = state["profile"]
    if artifact.get("schema_version") != 3 or artifact.get("task_id") != state["task_id"]:
        raise GraphError("task.json требует schema_version 3 и точный task_id.")
    if artifact.get("mode") != mode or artifact.get("profile") != profile:
        raise GraphError("task.json не совпадает с режимом или профилем run.")
    summary = str(artifact.get("summary", "")).strip()
    if len(summary) < 12:
        raise GraphError("task.json требует содержательный summary.")
    confidence = artifact.get("confidence")
    if confidence not in {"high", "medium", "low"}:
        raise GraphError("confidence должен быть high, medium или low.")
    capabilities = strings(artifact.get("capabilities"), "capabilities", allow_empty=False)
    current_contract = state.get("graph_version") == graph_contract()["graph_version"]
    slice_contract = state.get("graph_version") in SLICE_CONTRACT_VERSIONS
    agents = validate_agents(artifact.get("agents"), profile, slice_contract=slice_contract)
    validate_research(artifact.get("research"))
    if state.get("graph_version") in {"3.3.0", graph_contract()["graph_version"]}:
        validate_mcp_capabilities(capabilities)
    plan_path = snapshots.safe_join_no_symlinks(root, state["plan_path"])
    digest, scope = validate_plan(plan_path)
    plan = artifact.get("plan")
    if not isinstance(plan, dict) or plan.get("path") != state["plan_path"] or plan.get("digest") != digest:
        raise GraphError("task.json должен быть связан с точным путём и digest плана.")
    plan_review = plan.get("review")
    if not isinstance(plan_review, dict) or plan_review.get("verdict") != "pass":
        raise GraphError("План должен иметь review.verdict=pass.")
    review_mode = plan_review.get("mode")
    if review_mode not in {"self", "independent", "reused"}:
        raise GraphError("Plan review mode должен быть self, independent или reused.")
    independent_plan = bool(review_receipts(agents, "task_plan_reviewer"))
    task_snapshot = state.get("task_state_snapshot") if isinstance(state.get("task_state_snapshot"), dict) else {}
    prior = task_snapshot.get("checkpoints", {}).get("plan-review")
    prior = prior if isinstance(prior, dict) else {}
    prior_reusable = (
        review_mode == "reused"
        and reviewed_digest_is_effective(state, run_dir, prior.get("plan_digest"), digest)
        and prior.get("verdict") == "pass"
        and prior.get("mode") in {"self", "independent"}
    )
    if review_mode == "reused" and not prior_reusable:
        raise GraphError("Reuse plan review требует свежую точную квитанцию прошлого plan run.")
    if profile in {"complex", "critical"} and mode != "plan" and not (independent_plan or prior_reusable):
        raise GraphError("Complex/critical реализация требует отдельный plan review или свежую reuse-квитанцию.")
    if profile in {"complex", "critical"} and mode != "plan" and prior_reusable and prior.get("mode") != "independent":
        raise GraphError("Complex/critical нельзя переиспользовать self-review лёгкого плана.")
    if review_mode == "independent" and not independent_plan:
        raise GraphError("Independent plan review требует task_plan_reviewer receipt.")
    if current_contract and state.get("scope_amendments"):
        amendment_review_receipts: list[str] = []
        for item in state["scope_amendments"]:
            amendment_path = Path(str(item.get("path", "")))
            if not amendment_path.is_file() or sha256_file(amendment_path) != item.get("sha256"):
                raise GraphError("Scope amendment receipt изменился перед final work validation.")
            amendment_artifact = load_json(amendment_path)
            if amendment_artifact.get("review_source") == "root-only-full":
                amendment_review_receipts.append(
                    meaningful(
                        amendment_artifact.get("plan_review_receipt"),
                        "scope amendment review receipt",
                        6,
                    )
                )
        if review_mode == "independent":
            available = set(review_receipts(agents, "task_plan_reviewer"))
            if any(receipt not in available for receipt in amendment_review_receipts):
                raise GraphError("Root-only scope amendment не связан с exact independent plan reviewer receipt.")
        elif any(receipt != "root:self-review" for receipt in amendment_review_receipts):
            raise GraphError("Self-reviewed root-only scope amendment требует root:self-review receipt.")
    decision = artifact.get("decision")
    if outcome == "decision":
        if not isinstance(decision, dict) or len(str(decision.get("question", "")).strip()) < 12:
            raise GraphError("Outcome decision требует содержательный decision.question.")
    elif decision is not None:
        raise GraphError("Обычный результат не должен содержать незакрытое решение.")
    baseline = snapshots.load_manifest(snapshots.safe_join_no_symlinks(root, state["baseline_manifest"]))
    if snapshots.manifest_digest(baseline) != state["baseline_repo_digest"]:
        raise GraphError("Baseline manifest повреждён.")
    current = manifest(root, state["plan_path"])
    changed = snapshots.changed_paths(baseline, current)
    implementation = artifact.get("implementation")
    if not isinstance(implementation, dict):
        raise GraphError("implementation должен быть объектом.")
    if mode == "plan":
        if implementation.get("status") != "not-run" or changed:
            raise GraphError("Plan mode не должен менять производственный код.")
    else:
        if implementation.get("status") != "complete" or not changed:
            raise GraphError("Implement/full требует завершённую фактическую дельту.")
        declared = strings(implementation.get("changed_paths"), "implementation.changed_paths", allow_empty=False)
        if sorted(set(declared)) != changed:
            raise GraphError("implementation.changed_paths не совпадает с фактической дельтой.")
        outside = snapshots.outside_scope(changed, scope)
        if outside:
            raise GraphError("Изменения вышли за область плана: " + ", ".join(outside[:20]))
    task_tests = validate_tests(artifact.get("tests"), mode, staged_contract=current_contract)
    delegation = (
        validate_slice_acceptance(state, run_dir, implementation, agents, changed, task_tests)
        if slice_contract
        else {"strategy": implementation.get("strategy", "root-only"), "accepted_slices": []}
    )
    if len(str(artifact.get("documentation_impact", "")).strip()) < 8:
        raise GraphError("documentation_impact должен быть содержательным.")
    if len(str(artifact.get("rollback", "")).strip()) < 8:
        raise GraphError("rollback должен быть содержательным.")
    strings(artifact.get("residual_risks"), "residual_risks")
    if profile == "critical" and mode != "plan" and not review_receipts(agents, "task_risk_reviewer"):
        raise GraphError("Critical реализация требует отдельный task_risk_reviewer receipt.")
    required_verify = profile_requires_verify(mode, profile, confidence)
    if outcome == "verify" and not required_verify:
        required_verify = True
    if outcome == "succeeded" and required_verify:
        raise GraphError("Этот профиль требует независимый verify.")
    if outcome == "verify" and not profile_requires_verify(mode, profile, confidence):
        # Root may escalate a risky light path; this is intentionally allowed.
        required_verify = True
    if outcome not in {"succeeded", "verify", "decision"}:
        raise GraphError("Work outcome должен быть succeeded, verify или decision.")
    if state.get("verification_required") and outcome == "succeeded":
        raise GraphError("После verifier reject исправление обязано снова пройти verify.")
    scope_snapshot = snapshots.scope_manifest(root, scope)
    legacy_state = dict(state["task_state_snapshot"])
    legacy_state["baseline_manifest"] = state["baseline_manifest"]
    legacy_state["baseline_repo_digest"] = state["baseline_repo_digest"]
    legacy_state["artifacts"] = {"plan": state["plan_path"]}
    legacy_state["checkpoints"] = {"plan-review": {"review_scope_manifest": scope_snapshot}}
    legacy._MANIFEST_CACHE.clear()
    implementation_digest = legacy.implementation_repo_state(root, legacy_state)[1]
    return {
        "plan_digest": digest,
        "scope": scope,
        "scope_manifest": scope_snapshot,
        "changed_paths": changed,
        "implementation_digest": implementation_digest,
        "agents": agents,
        "implementation_strategy": delegation["strategy"],
        "accepted_slices": delegation["accepted_slices"],
        "context_checkpoint_sha256": delegation.get("context_checkpoint_sha256"),
        "deferred_final_check_ids": delegation.get("deferred_final_check_ids", []),
        "scope_amendments": [item["sha256"] for item in state.get("scope_amendments", [])],
        "confidence": confidence,
        "verification_required": required_verify,
        "summary": summary,
    }


def validate_verification(state: dict[str, Any], artifact: dict[str, Any], outcome: str) -> None:
    if artifact.get("schema_version") != 3 or artifact.get("task_id") != state["task_id"]:
        raise GraphError("verification.json требует schema_version 3 и точный task_id.")
    if artifact.get("mode") != state["mode"]:
        raise GraphError("Verifier проверил другой режим.")
    work = state["nodes"]["work"]["receipts"][-1]
    if artifact.get("work_sha256") != work["sha256"]:
        raise GraphError("Verifier проверил не текущий task.json.")
    if artifact.get("plan_digest") != work["plan_digest"]:
        raise GraphError("Verifier проверил не текущий план.")
    if artifact.get("implementation_digest") != work["implementation_digest"]:
        raise GraphError("Verifier проверил не текущий снимок реализации.")
    verdict = artifact.get("verdict")
    if verdict not in {"pass", "reject"}:
        raise GraphError("Verifier verdict должен быть pass или reject.")
    strings(artifact.get("checked_claims"), "checked_claims", allow_empty=False)
    strings(artifact.get("residual_risks"), "residual_risks")
    repairs = strings(artifact.get("repair_list"), "repair_list")
    expected_role = "task_plan_reviewer" if state["mode"] == "plan" else "task_result_reviewer"
    if artifact.get("reviewer_role") != expected_role or len(str(artifact.get("reviewer_receipt", ""))) < 6:
        raise GraphError(f"Verifier требует роль {expected_role} и reviewer_receipt.")
    if outcome == "succeeded" and verdict != "pass":
        raise GraphError("Verify succeeded требует verdict=pass.")
    if outcome == "failed" and (verdict != "reject" or not repairs):
        raise GraphError("Verify failed требует verdict=reject и repair_list.")


def load_run_state(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    if state.get("schema_version") != 3 or state.get("graph_id") != "task-delivery":
        raise GraphError("Run не является Task Delivery v3.")
    graph = graph_contract()
    identity = (state.get("graph_version"), state.get("graph_sha256"))
    current_identity = (graph["graph_version"], sha256_file(GRAPH_PATH))
    if identity != current_identity and identity not in LEGACY_ACTIVE_GRAPH_IDENTITIES:
        raise GraphError("Run связан с неподдерживаемой версией Task Delivery graph.")
    root = root_path(str(state.get("root", "")))
    task_id = legacy.validate_task_id(str(state.get("task_id", "")))
    run_id = str(state.get("run_id", ""))
    if not re.fullmatch(r"[0-9a-f]{16}", run_id):
        raise GraphError("Run id повреждён.")
    expected = snapshots.safe_join_no_symlinks(root, RUNS_REL / run_id).resolve()
    if run_dir.resolve() != expected:
        raise GraphError("Run directory не совпадает с root/run_id из состояния.")
    if state.get("mode") not in MODES or state.get("profile") not in PROFILES:
        raise GraphError("Run содержит неизвестный mode/profile.")
    plan = relative_path(root, str(state.get("plan_path", "")))
    if plan != state.get("plan_path"):
        raise GraphError("Run содержит неканонический путь плана.")
    expected_baseline = f".codex/task-delivery/{task_id}/baseline-{run_id}.json"
    if state.get("baseline_manifest") != expected_baseline:
        raise GraphError("Run содержит неожиданный baseline manifest.")
    return state


def save_run(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    atomic_json(run_dir / STATE_NAME, state)


def load_task_state(root: Path, task_id: str) -> tuple[Path, dict[str, Any]]:
    path = task_state_path(root, task_id)
    state = load_json(path)
    if state.get("schema_version") == 2:
        raise GraphError("Это активная v2-задача; продолжи её через legacy task_delivery.py.")
    if state.get("schema_version") != 3 or state.get("task_id") != task_id:
        raise GraphError("Task Delivery state повреждён или имеет неизвестную версию.")
    return path, state


def save_task(path: Path, state: dict[str, Any]) -> None:
    state["revision"] = int(state.get("revision", 0)) + 1
    state["updated_at"] = now()
    atomic_json(path, state)


def initialize(
    root_raw: str,
    mode: str,
    task_id: str,
    title: str,
    outcome: str,
    plan_raw: str | None,
    profile: str,
    implementation_strategy: str = "auto",
) -> dict[str, Any]:
    if mode not in MODES or profile not in PROFILES:
        raise GraphError("Режим или профиль Task Delivery неизвестен.")
    if implementation_strategy not in IMPLEMENTATION_STRATEGY_REQUESTS:
        raise GraphError("Implementation strategy должна быть auto, root-only или delegated-sequential.")
    if mode == "plan" and implementation_strategy == "delegated-sequential":
        raise GraphError("Режим plan не реализует код и не может требовать implementation slices.")
    if len(title.strip()) < 3 or len(outcome.strip()) < 8:
        raise GraphError("Нужны содержательные title и outcome.")
    root = root_path(root_raw)
    task_id = legacy.validate_task_id(task_id)
    graph = graph_contract()
    policy = graph["delegation_policy"]
    strategy_request = "root-only" if mode == "plan" else implementation_strategy
    strategy_preferred = (
        policy["profile_preference"][profile]
        if strategy_request == "auto"
        else strategy_request
    )
    plan = plan_relative(root, plan_raw, task_id, mode)
    task_path = task_state_path(root, task_id)
    with legacy.mutation_guard(root, task_id, True):
        existing: dict[str, Any] | None = None
        if task_path.is_file():
            existing = load_json(task_path)
            if existing.get("schema_version") == 2:
                raise GraphError("Task-id принадлежит v2; продолжи его через legacy task_delivery.py.")
            if existing.get("schema_version") != 3:
                raise GraphError("Неизвестная версия Task Delivery state.")
            if mode != "implement" or existing.get("phase") != "awaiting_implementation":
                raise GraphError("Существующую v3-задачу можно продолжить только implement после plan mode.")
            if existing.get("artifacts", {}).get("plan") != plan:
                raise GraphError("Implement должен открыть точный ранее проверенный план.")
            plan_path = snapshots.safe_join_no_symlinks(root, plan)
            digest, scope = validate_plan(plan_path)
            review = existing.get("checkpoints", {}).get("plan-review")
            if not isinstance(review, dict) or review.get("plan_digest") != digest:
                raise GraphError("План изменился после review; нужен новый plan run.")
            if review.get("review_scope_manifest") != snapshots.scope_manifest(root, scope):
                raise GraphError("Область реализации изменилась после plan review; нужен новый план.")
            if PROFILE_RANK[profile] < PROFILE_RANK[existing["profile"]]:
                raise GraphError("Implement не может понизить уже выбранный профиль риска.")
        plan_path = snapshots.safe_join_no_symlinks(root, plan)
        if not plan_path.exists():
            atomic_text(plan_path, plan_template(task_id, title.strip(), outcome.strip()))
        baseline = manifest(root, plan)
        run_number = len(existing.get("runs", [])) + 1 if existing else 1
        raw_id = f"{task_id}:{mode}:{profile}:{strategy_request}:{graph['graph_version']}:{run_number}"
        run_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
        run_dir = snapshots.safe_join_no_symlinks(root, RUNS_REL / run_id)
        if run_dir.exists():
            state = load_run_state(run_dir)
            return ready(run_dir) if state["status"] != "completed" else result(
                "completed", "Run уже завершён.", artifacts=[str(run_dir)], data={"run": str(run_dir)}
            )
        run_dir.mkdir(parents=True, exist_ok=False)
        baseline_rel = f".codex/task-delivery/{task_id}/baseline-{run_id}.json"
        baseline_path = snapshots.safe_join_no_symlinks(root, baseline_rel)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        snapshots.write_manifest(baseline_path, baseline)
        stamp = now()
        task = existing or {
            "schema_version": 3,
            "task_id": task_id,
            "title": title.strip(),
            "outcome": outcome.strip(),
            "phase": "running",
            "profile": profile,
            "artifacts": {"plan": plan},
            "checkpoints": {},
            "runs": [],
            "revision": 0,
            "created_at": stamp,
            "completed_at": None,
        }
        task["phase"] = "running"
        task["profile"] = profile
        task["baseline_manifest"] = baseline_rel
        task["baseline_repo_digest"] = snapshots.manifest_digest(baseline)
        task["current_run"] = run_id
        task.setdefault("runs", []).append(
            {
                "run_id": run_id,
                "mode": mode,
                "profile": profile,
                "implementation_strategy_request": strategy_request,
                "started_at": stamp,
            }
        )
        task_snapshot = json.loads(json.dumps(task))
        nodes = {name: {"status": "pending", "attempts": 0, "receipts": []} for name in ("work", "verify", "complete")}
        nodes["work"]["status"] = "ready"
        run = {
            "schema_version": 3,
            "graph_id": "task-delivery",
            "graph_version": graph["graph_version"],
            "graph_sha256": sha256_file(GRAPH_PATH),
            "run_id": run_id,
            "root": str(root),
            "task_id": task_id,
            "mode": mode,
            "profile": profile,
            "plan_path": plan,
            "baseline_manifest": baseline_rel,
            "baseline_repo_digest": snapshots.manifest_digest(baseline),
            "task_state_snapshot": task_snapshot,
            "status": "running",
            "current": "work",
            "verification_required": False,
            "verification_repairs": 0,
            "implementation_strategy": "root-only",
            "implementation_strategy_request": strategy_request,
            "implementation_strategy_preferred": strategy_preferred,
            "slices": {},
            "context": {
                "latest_checkpoint_path": None,
                "latest_checkpoint_sha256": None,
                "rehydrated_checkpoint_sha256": None,
                "rehydrated_at": None,
            },
            "scope_amendments": [],
            "node_retries": {"work": 0, "verify": 0},
            "decisions": [],
            "nodes": nodes,
            "created_at": stamp,
            "updated_at": stamp,
        }
        save_task(task_path, task)
        save_run(run_dir, run)
    return ready(run_dir)


def ready(run_dir: Path) -> dict[str, Any]:
    state = load_run_state(run_dir)
    current = state["current"]
    current_contract = state.get("graph_version") == graph_contract()["graph_version"]
    rejected_work_sha = verification_repair_work_sha(state) if current_contract else None
    delegated_repair_sha = (
        rejected_work_sha
        if state.get("implementation_strategy") == "delegated-sequential"
        else None
    )
    actions: list[str] = []
    if state["status"] == "running" and current in {"work", "verify"}:
        artifact = run_dir / (WORK_NAME if current == "work" else VERIFY_NAME)
        actions = [
            f"Создай {artifact}",
            f"{runner_command()} record --run {shlex.quote(str(run_dir))} --node {current} --outcome <outcome>",
        ]
        records = state.get("slices", {}) if current == "work" else {}
        successful_unaccepted = sorted(
            name
            for name, item in records.items()
            if item.get("worker_status") in {"done", "done_with_concerns"}
            and item.get("status") != "accepted"
        )
        superseded: set[str] = set()
        for item in records.values():
            packet_path = Path(str(item.get("packet_path", "")))
            if packet_path.is_file():
                predecessor = load_json(packet_path).get("supersedes")
                if isinstance(predecessor, str):
                    superseded.add(predecessor)
        unresolved = sorted(
            name
            for name, item in records.items()
            if item.get("worker_status") in {"needs_context", "blocked"}
            and item.get("repair_for_work_sha256") is None
            and name not in superseded
        )
        matching_repairs = [
            item
            for item in records.values()
            if item.get("repair_for_work_sha256") == delegated_repair_sha
        ]
        if current_contract and current == "work" and successful_unaccepted:
            identifier = successful_unaccepted[0]
            actions = [
                "Проверь exact diff и хотя бы один assigned slice check, затем выполни: "
                f"{runner_command()} slice-accept --run {shlex.quote(str(run_dir))} "
                f"--slice-id {shlex.quote(identifier)} --acceptance <acceptance.json>"
            ]
        elif current_contract and current == "work" and unresolved:
            identifier = unresolved[-1]
            actions = [
                "Создай bounded successor slice с "
                f"supersedes={identifier}; если нужен новый technical file path, "
                "снача выполни bounded scope-amend."
            ]
        elif current_contract and current == "work" and delegated_repair_sha and not matching_repairs:
            actions = [
                "Создай ровно один verifier repair slice с "
                f"repair_for_work_sha256={delegated_repair_sha} и снова проведи root acceptance."
            ]
        elif current_contract and current == "work" and rejected_work_sha and not delegated_repair_sha:
            actions.insert(0, "Исправь отклонённый root-owned candidate и снова запиши task.json для verify.")
        elif (
            current == "work"
            and state["mode"] != "plan"
            and state.get("implementation_strategy_preferred") == "delegated-sequential"
            and not records
            and rejected_work_sha is None
        ):
            actions.insert(0, "Выдели bounded implementation slice и выполни slice-create до запуска task_worker.")
        context = state.get("context", {})
        checkpoint_sha = context.get("latest_checkpoint_sha256") if isinstance(context, dict) else None
        if (
            current_contract
            and current == "work"
            and checkpoint_sha
            and context.get("rehydrated_checkpoint_sha256") != checkpoint_sha
        ):
            actions.insert(
                0,
                "Только если нужен следующий slice: "
                f"{runner_command()} context-rehydrate --run {shlex.quote(str(run_dir))}",
            )
    elif state["status"] == "running" and current == "complete":
        actions = [f"{runner_command()} complete --run {shlex.quote(str(run_dir))}"]
    return result(
        state["status"],
        f"Task Delivery готов: {current}.",
        next_actions=actions,
        artifacts=[str(run_dir), str(Path(state["root"]) / state["plan_path"])],
        data={
            "run": str(run_dir),
            "task_id": state["task_id"],
            "mode": state["mode"],
            "profile": state["profile"],
            "current": current,
            "artifact": str(run_dir / (WORK_NAME if current == "work" else VERIFY_NAME)) if current in {"work", "verify"} else None,
            "mcp_policy": graph_contract()["mcp_policy"] if current == "work" else None,
            "implementation_strategy": state.get("implementation_strategy", "root-only"),
            "implementation_strategy_request": state.get("implementation_strategy_request", "auto"),
            "implementation_strategy_preferred": state.get("implementation_strategy_preferred", "root-only"),
            "context": state.get("context", {}),
            "scope_amendment_count": len(state.get("scope_amendments", [])),
            "verification_repair_work_sha256": delegated_repair_sha,
            "slices": [
                {
                    "slice_id": identifier,
                    "status": item.get("status"),
                    "worker_status": item.get("worker_status"),
                    "packet": item.get("packet_path"),
                    "packet_sha256": item.get("packet_sha256"),
                    "receipt": item.get("receipt_path"),
                    "receipt_sha256": item.get("receipt_sha256"),
                    "acceptance": item.get("acceptance_path"),
                    "acceptance_sha256": item.get("acceptance_sha256"),
                }
                for identifier, item in sorted(state.get("slices", {}).items())
            ],
        },
    )


def preserve_artifact(run_dir: Path, node: str, attempt: int, source: Path) -> tuple[Path, str]:
    digest = sha256_file(source)
    target = run_dir / "receipts" / f"{node}-{attempt}.json"
    atomic_text(target, source.read_text(encoding="utf-8"))
    if sha256_file(target) != digest:
        raise GraphError("Не удалось сохранить immutable receipt.")
    return target, digest


def record(run_dir: Path, node: str, outcome: str) -> dict[str, Any]:
    if node not in {"work", "verify"}:
        raise GraphError("Record допускает только work или verify.")
    root: Path
    task_id: str
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state["status"] != "running" or state["current"] != node or state["nodes"][node]["status"] != "ready":
                raise GraphError(f"Узел {node} сейчас не готов.")
            artifact_path = run_dir / (WORK_NAME if node == "work" else VERIFY_NAME)
            artifact = load_json(artifact_path)
            if node == "work":
                if outcome == "failed":
                    state["nodes"][node]["status"] = "failed"
                    state["nodes"][node]["attempts"] += 1
                    state["status"] = "blocked"
                    save_run(run_dir, state)
                    return result("blocked", "Work остановлен; доступен один retry.", artifacts=[str(run_dir)])
                details = validate_work(state, artifact, outcome, run_dir)
                attempt = state["nodes"][node]["attempts"] + 1
                preserved, digest = preserve_artifact(run_dir, node, attempt, artifact_path)
                receipt = {"path": str(preserved), "source": str(artifact_path), "sha256": digest, "outcome": outcome, "at": now(), **details}
                state["nodes"][node]["attempts"] = attempt
                state["nodes"][node]["receipts"].append(receipt)
                state["nodes"][node]["status"] = "completed"
                if outcome == "decision":
                    decision = dict(artifact["decision"])
                    decision["id"] = hashlib.sha256((digest + decision["question"]).encode("utf-8")).hexdigest()[:12]
                    decision["requested_at"] = now()
                    state["decisions"].append(decision)
                    state["status"] = "decision-required"
                elif outcome == "verify":
                    state["verification_required"] = True
                    state["current"] = "verify"
                    state["nodes"]["verify"]["status"] = "ready"
                else:
                    state["current"] = "complete"
                    state["nodes"]["complete"]["status"] = "ready"
            else:
                if outcome not in {"succeeded", "failed"}:
                    raise GraphError("Verify outcome должен быть succeeded или failed.")
                validate_verification(state, artifact, outcome)
                attempt = state["nodes"][node]["attempts"] + 1
                preserved, digest = preserve_artifact(run_dir, node, attempt, artifact_path)
                receipt = {
                    "path": str(preserved),
                    "source": str(artifact_path),
                    "sha256": digest,
                    "work_sha256": state["nodes"]["work"]["receipts"][-1]["sha256"],
                    "outcome": outcome,
                    "at": now(),
                }
                state["nodes"][node]["attempts"] = attempt
                state["nodes"][node]["receipts"].append(receipt)
                if outcome == "succeeded":
                    state["nodes"][node]["status"] = "completed"
                    state["current"] = "complete"
                    state["nodes"]["complete"]["status"] = "ready"
                else:
                    state["verification_repairs"] += 1
                    if state["verification_repairs"] > graph_contract()["limits"]["max_verification_repairs"]:
                        state["nodes"][node]["status"] = "failed"
                        state["status"] = "blocked"
                    else:
                        state["nodes"][node]["status"] = "pending"
                        state["nodes"]["work"]["status"] = "ready"
                        state["current"] = "work"
            save_run(run_dir, state)
    return ready(run_dir)


def decide(run_dir: Path, answer: str) -> dict[str, Any]:
    if len(answer.strip()) < 3:
        raise GraphError("Ответ на решение не должен быть пустым.")
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    with legacy.mutation_guard(root, initial["task_id"], True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state["status"] != "decision-required" or not state["decisions"]:
                raise GraphError("Run не ожидает решения.")
            state["decisions"][-1]["answer"] = answer.strip()
            state["decisions"][-1]["resolved_at"] = now()
            state["status"] = "running"
            state["current"] = "work"
            state["nodes"]["work"]["status"] = "ready"
            save_run(run_dir, state)
    return ready(run_dir)


def retry(run_dir: Path, node: str) -> dict[str, Any]:
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    with legacy.mutation_guard(root, initial["task_id"], True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state["status"] != "blocked" or state["nodes"].get(node, {}).get("status") != "failed":
                raise GraphError("Указанный узел не находится в failed состоянии.")
            if node == "verify" and state["verification_repairs"] > graph_contract()["limits"]["max_verification_repairs"]:
                raise GraphError("Verification repair limit исчерпан; второй reject терминален для этого run.")
            if state["node_retries"].get(node, 0) >= graph_contract()["limits"]["max_node_retries"]:
                raise GraphError("Retry limit исчерпан.")
            state["node_retries"][node] += 1
            state["status"] = "running"
            state["current"] = node
            state["nodes"][node]["status"] = "ready"
            save_run(run_dir, state)
    return ready(run_dir)


def verify_slices_integrity(state: dict[str, Any], run_dir: Path) -> None:
    if state.get("graph_version") not in SLICE_CONTRACT_VERSIONS:
        return
    current_contract = state.get("graph_version") == graph_contract()["graph_version"]
    records = state.get("slices", {})
    if not isinstance(records, dict):
        raise GraphError("Run slice registry повреждён.")
    for identifier, record in records.items():
        expected = slice_directory(run_dir, identifier)
        packet = Path(str(record.get("packet_path", "")))
        baseline = Path(str(record.get("baseline_path", "")))
        if packet.resolve(strict=False) != (expected / SLICE_PACKET_NAME).resolve(strict=False):
            raise GraphError(f"Slice packet имеет неожиданный путь: {identifier}")
        if baseline.resolve(strict=False) != (expected / SLICE_BASELINE_NAME).resolve(strict=False):
            raise GraphError(f"Slice baseline имеет неожиданный путь: {identifier}")
        if not packet.is_file() or sha256_file(packet) != record.get("packet_sha256"):
            raise GraphError(f"Slice packet изменился: {identifier}")
        baseline_value = snapshots.load_manifest(baseline)
        if snapshots.manifest_digest(baseline_value) != record.get("base_repo_digest"):
            raise GraphError(f"Slice baseline изменился: {identifier}")
        receipt_value = record.get("receipt_path")
        if record.get("status") in {"recorded", "accepted"}:
            receipt = Path(str(receipt_value or ""))
            if receipt.resolve(strict=False) != (expected / "worker-receipt.json").resolve(strict=False):
                raise GraphError(f"Worker receipt имеет неожиданный путь: {identifier}")
            if not receipt.is_file() or sha256_file(receipt) != record.get("receipt_sha256"):
                raise GraphError(f"Worker receipt изменился: {identifier}")
        if current_contract and record.get("status") == "accepted":
            acceptance = Path(str(record.get("acceptance_path", "")))
            if acceptance.resolve(strict=False) != (expected / SLICE_ACCEPTANCE_NAME).resolve(strict=False):
                raise GraphError(f"Root acceptance имеет неожиданный путь: {identifier}")
            if not acceptance.is_file() or sha256_file(acceptance) != record.get("acceptance_sha256"):
                raise GraphError(f"Root acceptance изменился: {identifier}")
    if current_contract:
        validate_amendment_chain(state, run_dir)
        accepted_ids = {
            identifier for identifier, record in records.items() if record.get("status") == "accepted"
        }
        if accepted_ids:
            checkpoint, _ = load_context_checkpoint(state, run_dir)
            if {item["slice_id"] for item in checkpoint["accepted_slices"]} != accepted_ids:
                raise GraphError("Latest context checkpoint не покрывает exact accepted slices.")


def verify_integrity(state: dict[str, Any]) -> dict[str, Any]:
    root = Path(state["root"])
    work = state["nodes"]["work"]["receipts"][-1]
    run_dir = Path(work["path"]).parent.parent
    verify_slices_integrity(state, run_dir)
    for key in ("path", "source"):
        path = Path(work[key])
        if not path.is_file() or sha256_file(path) != work["sha256"]:
            raise GraphError("task.json изменился после record.")
    plan = snapshots.safe_join_no_symlinks(root, state["plan_path"])
    if plan_digest(plan) != work["plan_digest"]:
        raise GraphError("План изменился после record.")
    if state["verification_required"]:
        verifier = state["nodes"]["verify"]
        if verifier["status"] != "completed" or not verifier["receipts"]:
            raise GraphError("Обязательный verify не завершён.")
        receipt = verifier["receipts"][-1]
        if receipt["outcome"] != "succeeded" or receipt["work_sha256"] != work["sha256"]:
            raise GraphError("Verifier PASS не связан с текущим task.json.")
        for key in ("path", "source"):
            path = Path(receipt[key])
            if not path.is_file() or sha256_file(path) != receipt["sha256"]:
                raise GraphError("verification.json изменился после record.")
    baseline = snapshots.load_manifest(snapshots.safe_join_no_symlinks(root, state["baseline_manifest"]))
    changed = snapshots.changed_paths(baseline, manifest(root, state["plan_path"]))
    if changed != work["changed_paths"]:
        raise GraphError("Реализация изменилась после work receipt.")
    legacy._MANIFEST_CACHE.clear()
    task = load_json(task_state_path(root, state["task_id"]))
    task["checkpoints"]["plan-review"] = {
        "plan_digest": work["plan_digest"],
        "verdict": "pass",
        "review_scope_manifest": work["scope_manifest"],
        "reviewed_at": now(),
    }
    current_digest = legacy.implementation_repo_state(root, task)[1]
    if current_digest != work["implementation_digest"]:
        raise GraphError("Implementation digest изменился после work receipt.")
    return {"task": task, "work": work, "implementation_digest": current_digest}


def complete(run_dir: Path) -> dict[str, Any]:
    initial = load_run_state(run_dir)
    root = Path(initial["root"])
    task_id = initial["task_id"]
    with legacy.mutation_guard(root, task_id, True, allow_project_obligation=True):
        with state_lock(run_dir):
            state = load_run_state(run_dir)
            if state["status"] == "completed":
                return result("completed", "Task Delivery run уже завершён.", artifacts=[str(run_dir)])
            if state["status"] != "running" or state["current"] != "complete":
                raise GraphError("Run ещё не готов к complete.")
            task_path = task_state_path(root, task_id)
            persisted_task = load_json(task_path)
            if persisted_task.get("schema_version") == 3 and persisted_task.get("phase") == "completed":
                last_run = persisted_task.get("runs", [])[-1] if persisted_task.get("runs") else {}
                if last_run.get("run_id") != state["run_id"]:
                    raise GraphError("Completed task state принадлежит другому run.")
                recovered_integrity = verify_integrity(state)
                handoff_checkpoint = persisted_task.get("checkpoints", {}).get("handoff")
                if not isinstance(handoff_checkpoint, dict):
                    raise GraphError("Completed task state не содержит handoff checkpoint.")
                handoff_path = snapshots.safe_join_no_symlinks(root, str(handoff_checkpoint.get("path", "")))
                if (
                    not handoff_path.is_file()
                    or sha256_file(handoff_path) != handoff_checkpoint.get("sha256")
                    or recovered_integrity["implementation_digest"] != handoff_checkpoint.get("implementation_repo_digest")
                ):
                    raise GraphError("Прерванное завершение имеет дрейф реализации или handoff; сначала восстанови точный receipt.")
                try:
                    legacy.mark_project_start_maintenance_required(root, task_path, persisted_task)
                except legacy.TaskError as exc:
                    raise GraphError(str(exc)) from exc
                legacy.obligation_marker(root, task_id).unlink(missing_ok=True)
                state["nodes"]["complete"]["status"] = "completed"
                state["status"] = "completed"
                save_run(run_dir, state)
                return result(
                    "completed",
                    "Прерванное завершение согласовано без изменения Task Delivery receipt.",
                    artifacts=[str(root / HANDOFFS_REL / task_id / "HANDOFF.md"), str(run_dir)],
                    data={"phase": "completed", "task_id": task_id},
                )
            integrity = verify_integrity(state)
            task = integrity["task"]
            work = integrity["work"]
            task["checkpoints"]["plan-review"] = {
                "plan_digest": work["plan_digest"],
                "verdict": "pass",
                "mode": "independent" if state["verification_required"] and state["mode"] == "plan" else load_json(Path(work["source"]))["plan"]["review"]["mode"],
                "profile": state["profile"],
                "review_scope_manifest": work["scope_manifest"],
                "reviewed_at": now(),
            }
            task["plan_review"] = dict(task["checkpoints"]["plan-review"])
            task["last_work_receipt"] = work["path"]
            if state["mode"] == "plan":
                task["phase"] = "awaiting_implementation"
                task["current_run"] = None
                task["runs"][-1]["completed_at"] = now()
                task["runs"][-1]["status"] = "awaiting_implementation"
                save_task(task_path, task)
                state["nodes"]["complete"]["status"] = "completed"
                state["status"] = "completed"
                save_run(run_dir, state)
                return result(
                    "completed",
                    "План проверен; реализация не запускалась.",
                    next_actions=[f"Запусти implement с task-id {task_id} и тем же --plan."],
                    artifacts=[str(root / state["plan_path"]), str(run_dir)],
                    data={"phase": "awaiting_implementation", "task_id": task_id},
                )
            task["phase"] = "ready_to_complete"
            task["current_run"] = None
            task["runs"][-1]["completed_at"] = now()
            task["runs"][-1]["status"] = "completed"
            task["completed_at"] = now()
            task["checkpoints"]["result-review"] = {
                "work_sha256": work["sha256"],
                "implementation_repo_digest": integrity["implementation_digest"],
                "verified": bool(state["verification_required"]),
                "completed_at": now(),
            }
            task["baseline_manifest"] = state["baseline_manifest"]
            task["baseline_repo_digest"] = state["baseline_repo_digest"]
            task["artifacts"] = {"plan": state["plan_path"]}
            canonical_files, canonical_prefixes = legacy.project_start_canonical_contract(root)
            changed_docs = sorted(
                path
                for path in work["changed_paths"]
                if path in canonical_files or any(path.startswith(prefix) for prefix in canonical_prefixes)
            )
            if changed_docs:
                raise GraphError("Task Delivery не должен менять канонические Project Start документы: " + ", ".join(changed_docs[:20]))
            work_artifact = load_json(Path(work["source"]))
            handoff_rel = (HANDOFFS_REL / task_id / "HANDOFF.md").as_posix()
            handoff = snapshots.safe_join_no_symlinks(root, handoff_rel)
            proposal = str(work_artifact["documentation_impact"]).strip()
            risks = work_artifact["residual_risks"] or ["No known residual risks after the recorded checks."]
            handoff_text = (
                f"# Task Delivery handoff: {task_id}\n\n"
                "Status: READY\n"
                "Criteria passed: YES\n"
                "Rollback documented: YES\n"
                "Residual risks documented: YES\n"
                "Canonical docs changed: NO\n"
                f"Implementation SHA-256: {integrity['implementation_digest']}\n"
                f"Proposed documentation maintenance: {proposal}\n\n"
                f"## Summary\n\n{work_artifact['summary']}\n\n"
                f"## Rollback\n\n{work_artifact['rollback']}\n\n"
                "## Residual risks\n\n" + "\n".join(f"- {item}" for item in risks) + "\n"
            )
            atomic_text(handoff, handoff_text)
            task["checkpoints"]["handoff"] = {
                "path": handoff_rel,
                "sha256": sha256_file(handoff),
                "implementation_repo_digest": integrity["implementation_digest"],
                "recorded_at": now(),
            }
            marker = legacy.obligation_marker(root, task_id)
            atomic_json(marker, {"schema_version": 1, "task_id": task_id, "handoff_path": handoff_rel, "handoff_sha256": sha256_file(handoff), "created_at": now()})
            task["phase"] = "completed"
            save_task(task_path, task)
            try:
                legacy.mark_project_start_maintenance_required(root, task_path, task)
            except legacy.TaskError as exc:
                raise GraphError(str(exc)) from exc
            marker.unlink(missing_ok=True)
            state["nodes"]["complete"]["status"] = "completed"
            state["status"] = "completed"
            save_run(run_dir, state)
    return result(
        "completed",
        "Реализация, тесты и проверка завершены; handoff создан автоматически.",
        artifacts=[str(root / HANDOFFS_REL / task_id / "HANDOFF.md"), str(run_dir)],
        data={"phase": "completed", "task_id": task_id},
    )


def status(run_dir: Path) -> dict[str, Any]:
    state = load_run_state(run_dir)
    repair_work_sha = (
        verification_repair_work_sha(state)
        if (
            state.get("graph_version") == graph_contract()["graph_version"]
            and state.get("implementation_strategy") == "delegated-sequential"
        )
        else None
    )
    return result(
        state["status"],
        "Состояние Task Delivery прочитано без изменений.",
        artifacts=[str(run_dir / STATE_NAME)],
        data={
            "task_id": state["task_id"],
            "mode": state["mode"],
            "profile": state["profile"],
            "current": state["current"],
            "status": state["status"],
            "verification_repairs": state["verification_repairs"],
            "implementation_strategy": state.get("implementation_strategy", "root-only"),
            "implementation_strategy_request": state.get("implementation_strategy_request", "auto"),
            "implementation_strategy_preferred": state.get("implementation_strategy_preferred", "root-only"),
            "context": state.get("context", {}),
            "scope_amendment_count": len(state.get("scope_amendments", [])),
            "verification_repair_work_sha256": repair_work_sha,
            "slices": [
                {
                    "slice_id": identifier,
                    "status": item.get("status"),
                    "worker_status": item.get("worker_status"),
                }
                for identifier, item in sorted(state.get("slices", {}).items())
            ],
        },
    )


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--mode", choices=sorted(MODES), default="full")
    init.add_argument("--task-id", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--outcome", required=True)
    init.add_argument("--plan")
    init.add_argument("--profile", choices=sorted(PROFILES), default="standard")
    init.add_argument(
        "--implementation-strategy",
        choices=sorted(IMPLEMENTATION_STRATEGY_REQUESTS),
        default="auto",
    )
    ready_parser = sub.add_parser("ready")
    ready_parser.add_argument("--run", required=True)
    slice_create = sub.add_parser("slice-create")
    slice_create.add_argument("--run", required=True)
    slice_create.add_argument("--packet", required=True)
    slice_record = sub.add_parser("slice-record")
    slice_record.add_argument("--run", required=True)
    slice_record.add_argument("--slice-id", required=True)
    slice_record.add_argument("--receipt", required=True)
    slice_accept = sub.add_parser("slice-accept")
    slice_accept.add_argument("--run", required=True)
    slice_accept.add_argument("--slice-id", required=True)
    slice_accept.add_argument("--acceptance", required=True)
    context_rehydrate = sub.add_parser("context-rehydrate")
    context_rehydrate.add_argument("--run", required=True)
    scope_amend = sub.add_parser("scope-amend")
    scope_amend.add_argument("--run", required=True)
    scope_amend.add_argument("--amendment", required=True)
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--run", required=True)
    record_parser.add_argument("--node", choices=("work", "verify"), required=True)
    record_parser.add_argument("--outcome", choices=("succeeded", "verify", "decision", "failed"), required=True)
    decide_parser = sub.add_parser("decide")
    decide_parser.add_argument("--run", required=True)
    decide_parser.add_argument("--answer", required=True)
    retry_parser = sub.add_parser("retry")
    retry_parser.add_argument("--run", required=True)
    retry_parser.add_argument("--node", choices=("work", "verify"), required=True)
    complete_parser = sub.add_parser("complete")
    complete_parser.add_argument("--run", required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--run", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            payload = initialize(
                args.root,
                args.mode,
                args.task_id,
                args.title,
                args.outcome,
                args.plan,
                args.profile,
                args.implementation_strategy,
            )
        elif args.command == "ready":
            payload = ready(run_path(args.run))
        elif args.command == "slice-create":
            payload = register_slice(run_path(args.run), Path(args.packet))
        elif args.command == "slice-record":
            payload = record_slice(run_path(args.run), args.slice_id, Path(args.receipt))
        elif args.command == "slice-accept":
            payload = accept_slice(run_path(args.run), args.slice_id, Path(args.acceptance))
        elif args.command == "context-rehydrate":
            payload = rehydrate_context(run_path(args.run))
        elif args.command == "scope-amend":
            payload = amend_scope(run_path(args.run), Path(args.amendment))
        elif args.command == "record":
            payload = record(run_path(args.run), args.node, args.outcome)
        elif args.command == "decide":
            payload = decide(run_path(args.run), args.answer)
        elif args.command == "retry":
            payload = retry(run_path(args.run), args.node)
        elif args.command == "complete":
            payload = complete(run_path(args.run))
        else:
            payload = status(run_path(args.run))
    except (GraphError, legacy.TaskError, snapshots.SnapshotError, OSError, KeyError, ValueError) as exc:
        payload = result("failed", str(exc), next_actions=["Исправь указанное условие и повтори ту же команду."])
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] not in {"failed", "blocked"} else 2


if __name__ == "__main__":
    sys.exit(main())
