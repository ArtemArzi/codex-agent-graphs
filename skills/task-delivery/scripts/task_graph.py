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
MODES = {"plan", "implement", "full"}
PROFILES = {"light", "standard", "complex", "critical"}
PROFILE_RANK = {"light": 0, "standard": 1, "complex": 2, "critical": 3}
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


def validate_agents(value: Any, profile: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise GraphError("agents должен быть списком.")
    graph = graph_contract()
    if len(value) > int(graph["limits"]["max_agents_per_run"]):
        raise GraphError("Превышен общий лимит агентов Task Delivery.")
    normalized: list[dict[str, str]] = []
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
        if outcome not in {"used", "pass", "completed"}:
            raise GraphError("Agent outcome должен быть used, pass или completed.")
        receipts.add(receipt)
        normalized.append({"role": role, "phase": phase, "receipt": receipt, "outcome": outcome})
    workers = sum(item["role"] == "task_worker" for item in normalized)
    explorers = sum(item["role"] == "task_explorer" for item in normalized)
    if workers > 2 or explorers > 2:
        raise GraphError("Task Delivery допускает не более двух workers и двух explorers.")
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


def validate_tests(value: Any, mode: str) -> None:
    if not isinstance(value, list):
        raise GraphError("tests должен быть списком.")
    if mode == "plan":
        return
    if not value:
        raise GraphError("Реализация требует хотя бы одну фактически выполненную проверку.")
    for item in value:
        if not isinstance(item, dict) or item.get("status") != "passed" or item.get("exit_code") != 0:
            raise GraphError("Каждая проверка должна иметь status=passed и exit_code=0.")
        if len(str(item.get("command", "")).strip()) < 3 or len(str(item.get("purpose", "")).strip()) < 3:
            raise GraphError("Проверка требует command и purpose.")


def review_receipts(agents: list[dict[str, str]], role: str) -> list[str]:
    return [item["receipt"] for item in agents if item["role"] == role and item["outcome"] == "pass"]


def validate_work(state: dict[str, Any], artifact: dict[str, Any], outcome: str) -> dict[str, Any]:
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
    strings(artifact.get("capabilities"), "capabilities", allow_empty=False)
    agents = validate_agents(artifact.get("agents"), profile)
    validate_research(artifact.get("research"))
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
        and prior.get("plan_digest") == digest
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
    validate_tests(artifact.get("tests"), mode)
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
    if state.get("graph_version") != graph["graph_version"] or state.get("graph_sha256") != sha256_file(GRAPH_PATH):
        raise GraphError("Run связан с другой версией Task Delivery graph.")
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
) -> dict[str, Any]:
    if mode not in MODES or profile not in PROFILES:
        raise GraphError("Режим или профиль Task Delivery неизвестен.")
    if len(title.strip()) < 3 or len(outcome.strip()) < 8:
        raise GraphError("Нужны содержательные title и outcome.")
    root = root_path(root_raw)
    task_id = legacy.validate_task_id(task_id)
    graph = graph_contract()
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
        raw_id = f"{task_id}:{mode}:{profile}:{graph['graph_version']}:{run_number}"
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
        task.setdefault("runs", []).append({"run_id": run_id, "mode": mode, "profile": profile, "started_at": stamp})
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
    actions: list[str] = []
    if state["status"] == "running" and current in {"work", "verify"}:
        artifact = run_dir / (WORK_NAME if current == "work" else VERIFY_NAME)
        actions = [
            f"Создай {artifact}",
            f"{runner_command()} record --run {shlex.quote(str(run_dir))} --node {current} --outcome <outcome>",
        ]
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
                details = validate_work(state, artifact, outcome)
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


def verify_integrity(state: dict[str, Any]) -> dict[str, Any]:
    root = Path(state["root"])
    work = state["nodes"]["work"]["receipts"][-1]
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
    ready_parser = sub.add_parser("ready")
    ready_parser.add_argument("--run", required=True)
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
            payload = initialize(args.root, args.mode, args.task_id, args.title, args.outcome, args.plan, args.profile)
        elif args.command == "ready":
            payload = ready(run_path(args.run))
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
