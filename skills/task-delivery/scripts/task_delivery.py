#!/usr/bin/env python3
"""Evidence gates and resumable state for task-delivery."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from task_delivery_inventory import build_inventory
from task_delivery_snapshot import (
    SnapshotError,
    changed_paths,
    hash_file,
    load_manifest,
    looks_like_test_path,
    manifest_digest,
    outside_scope,
    parse_scope,
    repo_manifest,
    safe_join,
    safe_join_no_symlinks,
    safe_relative,
    scope_fingerprint,
    scope_manifest,
    write_manifest,
)


SCHEMA_VERSION = 2
EVENTS = [
    "capabilities",
    "internal-research",
    "external-research",
    "plan",
    "plan-review",
    "verification",
    "code-review",
    "handoff",
]
ARTIFACTS = {
    "capabilities": "CAPABILITIES.md",
    "internal-research": "INTERNAL-RESEARCH.md",
    "external-research": "EXTERNAL-RESEARCH.md",
    "plan": "PLAN.md",
    "plan-review": "PLAN-REVIEW.md",
    "verification": "VERIFICATION.md",
    "code-review": "CODE-REVIEW.md",
    "handoff": "HANDOFF.md",
    "progress": "PROGRESS.md",
}
DEPENDENCIES = {
    "capabilities": [],
    "internal-research": ["capabilities"],
    "external-research": ["capabilities"],
    "plan": ["internal-research", "external-research"],
    "plan-review": ["plan"],
    "verification": ["plan-review"],
    "code-review": ["verification"],
    "handoff": ["code-review"],
}
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
RECEIPTS = {
    "subagent": re.compile(r"^/[A-Za-z0-9._/-]{7,}$"),
    "codex-review": re.compile(r"^codex-review:[A-Za-z0-9._/-]{6,}$"),
    "human": re.compile(r"^human:.+@\d{4}-\d{2}-\d{2}$"),
}
_MANIFEST_CACHE: dict[str, tuple[dict[str, dict[str, Any]], str]] = {}
STALE_LOCK_SECONDS = 30
CANONICAL_RECEIPT_MAX_AGE_SECONDS = 24 * 60 * 60
PROJECT_START_OBLIGATION_MARKER = "project-start-obligation.pending.json"


class TaskError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp_is_fresh(raw: str) -> bool:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        return -300 <= age <= CANONICAL_RECEIPT_MAX_AGE_SECONDS
    except (TypeError, ValueError):
        return False


def emit(status: str, summary: str, **data: Any) -> None:
    payload = {"status": status, "summary": summary, "next_actions": data.pop("next_actions", []), "data": data}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def fail(summary: str, *actions: str) -> None:
    raise TaskError(json.dumps({"summary": summary, "next_actions": list(actions)}, ensure_ascii=False))


def parse_failure(exc: TaskError) -> tuple[str, list[str]]:
    try:
        value = json.loads(str(exc))
        return value["summary"], value.get("next_actions", [])
    except (json.JSONDecodeError, KeyError, TypeError):
        return str(exc), []


def root_path(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        fail(f"Корень репозитория не найден: {root}", "Передайте существующий каталог через --root.")
    return root


def validate_task_id(task_id: str) -> str:
    if not TASK_ID_RE.fullmatch(task_id):
        fail("Недопустимый task-id.", "Используйте 1-80 латинских букв, цифр, точек, дефисов или подчёркиваний без слешей.")
    return task_id


def state_file(root: Path, task_id: str) -> Path:
    return safe_join_no_symlinks(root, Path(".codex") / "task-delivery" / validate_task_id(task_id) / "state.json")


def machine_dir(root: Path, task_id: str) -> Path:
    return state_file(root, task_id).parent


def lock_path(root: Path, task_id: str) -> Path:
    return safe_join_no_symlinks(root, Path(".codex") / "task-delivery" / f"{validate_task_id(task_id)}.lock")


def process_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True


def inspect_lock(lock: Path) -> dict[str, Any]:
    if not lock.is_dir():
        fail(f"Lock задачи не найден: {lock}")
    owner_path = lock / "owner.json"
    if owner_path.is_symlink():
        fail("owner.json является симлинком; автоматическое восстановление небезопасно.")
    owner: dict[str, Any] = {}
    if owner_path.is_file():
        try:
            value = json.loads(owner_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                owner = value
        except (OSError, json.JSONDecodeError):
            owner = {}
    pid = owner.get("pid")
    age_seconds = max(0.0, time.time() - lock.stat().st_mtime)
    alive = process_alive(pid)
    return {
        "path": str(lock),
        "pid": pid if isinstance(pid, int) else None,
        "started_at": owner.get("started_at") if isinstance(owner.get("started_at"), str) else None,
        "owner_alive": alive,
        "age_seconds": round(age_seconds, 3),
        "recoverable": not alive and age_seconds >= STALE_LOCK_SECONDS,
    }


@contextmanager
def admission_guard(root: Path, wait_seconds: float = 5.0) -> Iterator[None]:
    parent = safe_join_no_symlinks(root, Path(".codex") / "task-delivery")
    parent.mkdir(parents=True, exist_ok=True)
    lock = parent / ".admission.lock"
    deadline = time.monotonic() + wait_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                raw = lock.read_text(encoding="utf-8")
                match = re.search(r"pid=(\d+)", raw)
                pid = int(match.group(1)) if match else -1
                age = time.time() - lock.stat().st_mtime
            except (FileNotFoundError, OSError, ValueError):
                continue
            if age >= STALE_LOCK_SECONDS and not process_alive(pid):
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                fail("Другой Task Delivery процесс удерживает repo-wide admission lock.")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} at={now()}\n".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


@contextmanager
def mutation_guard(
    root: Path,
    task_id: str,
    enabled: bool,
    *,
    allow_project_obligation: bool = False,
    skip_project_reopen: bool = False,
) -> Iterator[None]:
    if not enabled:
        yield
        return
    parent = safe_join_no_symlinks(root, Path(".codex") / "task-delivery")
    parent.mkdir(parents=True, exist_ok=True)
    with admission_guard(root):
        lock = lock_path(root, task_id)
        try:
            lock.mkdir()
        except FileExistsError:
            fail(
                f"Задачу уже изменяет другой процесс: {lock}",
                f"Проверьте владельца командой recover-lock --root {root} --task-id {task_id}; не удаляйте lock вслепую.",
            )
        owner = lock / "owner.json"
        try:
            owner.write_text(json.dumps({"pid": os.getpid(), "started_at": now()}) + "\n", encoding="utf-8")
            if not skip_project_reopen:
                reject_pending_project_reopen(
                    root, allow_task_id=task_id if allow_project_obligation else None
                )
            yield
        finally:
            try:
                owner.unlink(missing_ok=True)
                lock.rmdir()
            except OSError:
                pass


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="state-", suffix=".json.tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def save_state(path: Path, state: dict[str, Any]) -> None:
    state["revision"] = int(state.get("revision", 0)) + 1
    state["updated_at"] = now()
    atomic_json(path, state)


def load_state(root: Path, task_id: str) -> tuple[Path, dict[str, Any]]:
    path = state_file(root, task_id)
    if not path.is_file():
        fail(f"Состояние задачи {task_id} не найдено.", "Для plan/full выполните bootstrap; implement открывает прежний task-id.")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Состояние задачи не читается: {exc}", "Не переписывайте его вслепую.")
    if state.get("schema_version") != SCHEMA_VERSION:
        fail(f"Неподдерживаемая версия состояния: {state.get('schema_version')}")
    return path, state


def artifact_path(root: Path, state: dict[str, Any], name: str) -> Path:
    relative = state.get("artifacts", {}).get(name)
    if not relative:
        fail(f"В состоянии отсутствует артефакт {name}.")
    return safe_join(root, relative)


def state_exclusions(state: dict[str, Any]) -> list[str]:
    artifact_dir = Path(state["artifacts"]["plan"]).parent.as_posix()
    return [
        artifact_dir,
        ".agent-graphs",
        ".codex/task-delivery",
        ".project-start/state.json",
        ".project-start/.state.lock",
    ]


def current_repo_state(root: Path, state: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str]:
    key = f"{root}:{'|'.join(state_exclusions(state))}"
    if key not in _MANIFEST_CACHE:
        manifest = repo_manifest(root, state_exclusions(state))
        _MANIFEST_CACHE[key] = (manifest, manifest_digest(manifest))
    return _MANIFEST_CACHE[key]


def baseline_manifest(root: Path, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = load_manifest(safe_join_no_symlinks(root, state["baseline_manifest"]))
    if manifest_digest(manifest) != state.get("baseline_repo_digest"):
        fail("Baseline manifest повреждён или подменён; сохранённый digest не совпадает.", "Не продолжайте по этому состоянию до осознанного восстановления baseline.")
    return manifest


def reviewed_scope_manifest(root: Path, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    value = state.get("checkpoints", {}).get("plan-review", {}).get("review_scope_manifest")
    if not isinstance(value, dict):
        fail("В plan-review отсутствует снимок области реализации.")
    return value


def implementation_baseline(root: Path, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    combined = dict(baseline_manifest(root, state))
    combined.update(reviewed_scope_manifest(root, state))
    return combined


def implementation_repo_state(root: Path, state: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str]:
    manifest = dict(current_repo_state(root, state)[0])
    plan = artifact_path(root, state, "plan")
    manifest.update(scope_manifest(root, parse_scope(plan.read_text(encoding="utf-8"))))
    return manifest, manifest_digest(manifest)


def checkpoint_fresh(root: Path, state: dict[str, Any], event: str) -> bool:
    checkpoint = state.get("checkpoints", {}).get(event)
    if not checkpoint:
        return False
    path = artifact_path(root, state, event)
    if not path.is_file() or hash_file(path) != checkpoint.get("sha256"):
        return False
    implementation = checkpoint.get("implementation_repo_digest")
    return not implementation or implementation_repo_state(root, state)[1] == implementation


def gate_fresh(root: Path, state: dict[str, Any], event: str, seen: set[str] | None = None) -> bool:
    seen = set() if seen is None else seen
    if event in seen:
        return False
    seen.add(event)
    return checkpoint_fresh(root, state, event) and all(
        gate_fresh(root, state, dependency, seen.copy()) for dependency in DEPENDENCIES[event]
    )


def progress_fresh(root: Path, state: dict[str, Any]) -> bool:
    progress = state.get("progress")
    if not progress:
        return False
    path = artifact_path(root, state, "progress")
    return path.is_file() and hash_file(path) == progress.get("sha256") and implementation_repo_state(root, state)[1] == progress.get("implementation_repo_digest")


def assert_dependencies(root: Path, state: dict[str, Any], event: str) -> None:
    stale = [item for item in DEPENDENCIES[event] if not gate_fresh(root, state, item)]
    if stale:
        fail(f"Не готовы или устарели зависимости {event}: {', '.join(stale)}.", "Обновите доказательства по порядку.")


def field(text: str, label: str) -> str | None:
    match = re.search(rf"(?mi)^{re.escape(label)}:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else None


def json_block(text: str, name: str) -> Any:
    match = re.search(rf"<!--\s*task-delivery:{re.escape(name)}\s*\n(.*?)\n\s*-->", text, flags=re.DOTALL)
    if not match:
        fail(f"Не найден машинный JSON-блок task-delivery:{name}.")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        fail(f"Некорректный JSON-блок {name}: {exc}")


def ensure_complete(text: str, event: str) -> None:
    if len(text.strip()) < 100:
        fail(f"Артефакт {event} слишком короткий.")
    markers = [token for token in ("PENDING", "{{", "TODO") if token in text]
    if markers:
        fail(f"Артефакт {event} содержит незаполненные маркеры: {', '.join(markers)}.")


def validate_receipt(text: str) -> tuple[str, str]:
    if field(text, "Independent review") != "YES":
        fail("Требуется фактический отдельный обзор: `Independent review: YES`.")
    origin = field(text, "Review origin") or ""
    receipt = field(text, "Reviewer receipt") or ""
    pattern = RECEIPTS.get(origin)
    if not pattern or not pattern.fullmatch(receipt):
        fail("Reviewer receipt не соответствует origin: subagent=/root/..., codex-review=codex-review:..., human=human:name@YYYY-MM-DD.")
    return origin, receipt


def validate_receipt_pair(origin: str, receipt: str) -> None:
    pattern = RECEIPTS.get(origin)
    if not pattern or not pattern.fullmatch(receipt):
        fail("Reviewer receipt не соответствует origin: subagent=/root/..., codex-review=codex-review:..., human=human:name@YYYY-MM-DD.")


def validate_capabilities(text: str) -> dict[str, Any]:
    data = json_block(text, "capabilities")
    selected = data.get("selected") if isinstance(data, dict) else None
    if not isinstance(selected, list) or not selected:
        fail("В capabilities JSON нужен непустой selected.")
    names: list[str] = []
    external = 0
    for item in selected:
        if not isinstance(item, dict):
            fail("Каждая selected capability должна быть объектом.")
        name, kind, status, receipt = (item.get(key) for key in ("name", "kind", "status", "receipt"))
        if not all(isinstance(value, str) and value.strip() for value in (name, kind, status, receipt)):
            fail("Capability требует name/kind/status/receipt.")
        if kind not in {"skill", "mcp", "app", "browser", "local", "cli"}:
            fail(f"Неизвестный kind capability: {kind}")
        if kind in {"mcp", "app", "browser"}:
            external += 1
            if status != "verified-callable":
                fail(f"Выбранный {kind} {name} требует status=verified-callable после безопасного read-only вызова.")
        elif status not in {"advertised", "verified-callable"}:
            fail(f"Недопустимый status у {name}: {status}")
        if len(receipt) < 8:
            fail(f"Слишком короткая capability receipt у {name}.")
        access = item.get("access")
        if access not in {"local", "read-only", "read-write"}:
            fail(f"Capability {name} требует access=local|read-only|read-write.")
        if kind in {"mcp", "app", "browser"} and access == "local":
            fail(f"Внешняя capability {name} не может иметь access=local.")
        if kind in {"mcp", "app", "browser"} and access == "read-write":
            authorization = item.get("authorization")
            if not isinstance(authorization, dict):
                fail(f"Внешняя запись через {name} требует authorization.")
            for key in ("source", "scope", "receipt"):
                if len(str(authorization.get(key, "")).strip()) < 8:
                    fail(f"Authorization для {name} требует содержательный {key}.")
        names.append(name)
    hooks = data.get("hooks", [])
    if not isinstance(hooks, list):
        fail("capabilities.hooks должен быть списком.")
    for hook in hooks:
        if not isinstance(hook, dict) or hook.get("status") not in {"observed", "configured-only", "absent"}:
            fail("Hook требует status observed|configured-only|absent.")
        if hook.get("status") == "observed" and len(str(hook.get("receipt", ""))) < 8:
            fail("Наблюдавшийся hook требует receipt.")
    external_names = [item["name"] for item in selected if item.get("kind") in {"mcp", "app", "browser"}]
    return {"selected_capabilities": names, "verified_external_capabilities": external, "verified_external_names": external_names}


def validate_result_reviewers(text: str, state: dict[str, Any], header_origin: str, header_receipt: str) -> list[dict[str, str]]:
    data = json_block(text, "reviewers")
    reviewers = data.get("reviewers") if isinstance(data, dict) else None
    if not isinstance(reviewers, list) or not reviewers:
        fail("CODE-REVIEW.md требует непустой reviewers JSON.")
    normalized: list[dict[str, str]] = []
    receipts: set[str] = set()
    plan_receipt = state.get("checkpoints", {}).get("plan-review", {}).get("reviewer_receipt")
    for reviewer in reviewers:
        if not isinstance(reviewer, dict):
            fail("Каждый result reviewer должен быть объектом.")
        role = str(reviewer.get("role", ""))
        origin = str(reviewer.get("origin", ""))
        receipt = str(reviewer.get("receipt", ""))
        if role not in {"whole-system", "risk-block", "root-cause"} or reviewer.get("verdict") != "PASS":
            fail("Reviewer требует role=whole-system|risk-block|root-cause и verdict=PASS.")
        validate_receipt_pair(origin, receipt)
        if receipt in receipts or receipt == plan_receipt:
            fail("Квитанции независимых обзоров должны быть уникальны и отличаться от обзора плана.")
        receipts.add(receipt)
        normalized.append({"role": role, "origin": origin, "receipt": receipt})
    if not any(item["origin"] == header_origin and item["receipt"] == header_receipt for item in normalized):
        fail("Заголовочная квитанция CODE-REVIEW.md отсутствует в reviewers JSON.")
    required_roles = {"whole-system"}
    if state["priority"] == "P1":
        required_roles.add("risk-block")
    elif state["priority"] == "P0":
        required_roles.add("root-cause")
    missing = required_roles - {item["role"] for item in normalized}
    if missing:
        fail(f"Для {state['priority']} не хватает ролей обзора: {', '.join(sorted(missing))}.")
    return normalized


def project_start_canonical_contract(root: Path) -> tuple[set[str], list[str]]:
    state_path = root / ".project-start/state.json"
    if not state_path.is_file():
        return set(), []
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Project Start state не читается перед handoff: {exc}")
    artifacts = value.get("artifacts")
    if value.get("schema_version") != 2 or not isinstance(artifacts, dict):
        fail("Project Start state имеет неподдерживаемый контракт перед handoff.")
    files: set[str] = set()
    prefixes: list[str] = []
    for key, raw in artifacts.items():
        if not isinstance(raw, str) or not raw.strip():
            continue
        relative = safe_relative(raw).as_posix()
        if key == "adr_dir":
            prefixes.append(relative.rstrip("/") + "/")
        else:
            files.add(relative)
    graph_v3 = value.get("graph_v3") if isinstance(value.get("graph_v3"), dict) else {}
    for raw in graph_v3.get("canonical_docs", []):
        if isinstance(raw, str) and raw.strip():
            files.add(safe_relative(raw).as_posix())
    ignored = {".agent-graphs", ".codex", ".git", ".project-start", ".venv", "build", "dist", "generated", "node_modules", "vendor"}
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in ignored and not (current_path / name).is_symlink()
        ]
        if "AGENTS.md" not in names:
            continue
        path = current_path / "AGENTS.md"
        relative = path.relative_to(root)
        if path.is_symlink() or not path.is_file():
            fail(f"Project Start AGENTS.md должен быть обычным файлом: {relative.as_posix()}")
        files.add(relative.as_posix())
    return files, prefixes


def obligation_marker(root: Path, task_id: str) -> Path:
    return safe_join_no_symlinks(
        root, Path(".codex/task-delivery") / validate_task_id(task_id) / PROJECT_START_OBLIGATION_MARKER
    )


def pending_obligation_markers(root: Path) -> list[Path]:
    machine_root = root / ".codex/task-delivery"
    if not machine_root.is_dir():
        return []
    return sorted(
        path
        for path in machine_root.glob(f"*/{PROJECT_START_OBLIGATION_MARKER}")
        if path.is_file() and not path.is_symlink()
    )


def reject_pending_project_reopen(root: Path, allow_task_id: str | None = None) -> None:
    allowed = validate_task_id(allow_task_id) if allow_task_id is not None else None
    markers = [path for path in pending_obligation_markers(root) if path.parent.name != allowed]
    if markers:
        fail(
            "Новая Task Delivery заблокирована: завершение предыдущей задачи не успело durable записать "
            "Project Start obligation: " + ", ".join(path.parent.name for path in markers)
        )
    state_path = root / ".project-start/state.json"
    if not state_path.is_file():
        return
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Project Start state не читается: {exc}")
    graph_v3 = value.get("graph_v3") if isinstance(value.get("graph_v3"), dict) else None
    if graph_v3 is not None and graph_v3.get("status") == "operational":
        runtime = load_project_start_runtime()
        try:
            loaded = runtime.load_state(root)
            integrity = runtime.v3_integrity_issues(root, loaded)
        except (OSError, ValueError) as exc:
            fail(f"Project Start v3 authority не прошёл загрузку: {exc}")
        if integrity:
            fail(
                "Новая Task Delivery заблокирована: Project Start v3 authority drift: "
                + "; ".join(item.get("message", "unknown") for item in integrity[:5])
            )
        value = loaded
    maintenance = value.get("maintenance") if isinstance(value.get("maintenance"), dict) else {}
    status = maintenance.get("status")
    pending = maintenance.get("pending_reopen") if isinstance(maintenance.get("pending_reopen"), dict) else {}
    active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
    required = maintenance.get("maintenance_required") if isinstance(maintenance.get("maintenance_required"), dict) else {}
    if status == "reopen-required":
        fail(
            f"Новая Task Delivery заблокирована: Project Start требует reopen {pending.get('stage')}: "
            f"{pending.get('rationale')}"
        )
    if status == "maintenance-required":
        if allowed is not None and required.get("task_id") == allowed:
            return
        fail(
            "Новая Task Delivery заблокирована: сначала обработай maintenance receipt задачи "
            f"{required.get('task_id')} через Project Start."
        )
    if status in {"running", "blocked"}:
        fail(
            f"Новая Task Delivery заблокирована: Project Start maintenance run {active.get('run_id')} "
            f"имеет статус {status}."
        )
    if status == "restart-required":
        restart = maintenance.get("pending_restart") if isinstance(maintenance.get("pending_restart"), dict) else {}
        drift = maintenance.get("pending_drift")
        if (
            not isinstance(drift, dict)
            and restart.get("requires_verification") is False
            and value.get("phase") in {"execution", "complete"}
        ):
            return
        fail(
            "Новая Task Delivery заблокирована: Project Start требует свежий replacement run после "
            f"{restart.get('run_id')}: {restart.get('reason')}"
        )
    if value.get("phase") not in {"execution", "complete"}:
        fail(
            "Task Delivery закрыт: Project Start ещё не открыл фазу execution; "
            f"текущая фаза {value.get('phase')}."
        )
    if status == "not-ready" and graph_v3 is None:
        return
    if status != "operational":
        fail(f"Новая Task Delivery заблокирована: неизвестный fail-closed maintenance status {status!r}.")


def load_project_start_runtime() -> Any:
    path = Path(__file__).resolve().parents[2] / "project-start" / "scripts" / "project_start.py"
    if not path.is_file():
        fail(f"Не найден runtime Project Start для maintenance obligation: {path}")
    spec = importlib.util.spec_from_file_location("task_delivery_project_start_runtime", path)
    if spec is None or spec.loader is None:
        fail("Не удалось загрузить runtime Project Start.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mark_project_start_maintenance_required(root: Path, state_path: Path, state: dict[str, Any]) -> None:
    project_path = root / ".project-start/state.json"
    if not project_path.is_file():
        return
    runtime = load_project_start_runtime()
    try:
        project = runtime.load_state(root)
    except ValueError as exc:
        fail(f"Project Start state не прошёл проверку перед maintenance obligation: {exc}")
    if project.get("phase") not in {"execution", "complete"}:
        fail(
            "Maintenance obligation нельзя создать до фазы Project Start execution; "
            f"текущая фаза {project.get('phase')}."
        )
    checkpoint = state.get("checkpoints", {}).get("handoff")
    if not isinstance(checkpoint, dict):
        fail("Завершённая задача не содержит handoff checkpoint для Project Start.")
    obligation = {
        "task_id": state["task_id"],
        "handoff_path": checkpoint["path"],
        "handoff_sha256": checkpoint["sha256"],
        "task_state_path": state_path.relative_to(root).as_posix(),
        "task_state_sha256": hash_file(state_path),
        "created_at": now(),
    }
    maintenance = project.setdefault("maintenance", {"history": []})
    processed = maintenance.get("processed_handoffs") if isinstance(maintenance.get("processed_handoffs"), list) else []
    if any(
        isinstance(item, dict)
        and item.get("task_id") == obligation["task_id"]
        and item.get("handoff_sha256") == obligation["handoff_sha256"]
        and item.get("task_state_sha256") == obligation["task_state_sha256"]
        for item in processed
    ):
        return
    existing = maintenance.get("maintenance_required") if isinstance(maintenance.get("maintenance_required"), dict) else None
    if maintenance.get("status") == "maintenance-required" and isinstance(existing, dict):
        comparable = {key: existing.get(key) for key in obligation if key != "created_at"}
        expected = {key: value for key, value in obligation.items() if key != "created_at"}
        if comparable == expected:
            return
        fail("Project Start уже содержит другой незакрытый Task Delivery handoff.")
    if maintenance.get("status") != "operational":
        fail(
            "Project Start maintenance obligation создаётся только из operational; "
            f"текущий fail-closed статус {maintenance.get('status')!r}."
        )
    maintenance["status"] = "maintenance-required"
    maintenance["maintenance_required"] = obligation
    maintenance.pop("active_run", None)
    project["updated_at"] = obligation["created_at"]
    if not any(
        isinstance(item, dict)
        and item.get("event") == "task-maintenance-required"
        and item.get("task_id") == state["task_id"]
        and item.get("handoff_sha256") == checkpoint["sha256"]
        for item in project.setdefault("history", [])
    ):
        project["history"].append(
            {
                "at": obligation["created_at"],
                "event": "task-maintenance-required",
                "phase": project.get("phase"),
                "task_id": state["task_id"],
                "handoff_path": checkpoint["path"],
                "handoff_sha256": checkpoint["sha256"],
            }
        )
    try:
        runtime.save_project_state(root, project)
    except ValueError as exc:
        fail(f"Не удалось зафиксировать maintenance obligation: {exc}")


def canonical_doc_changes(root: Path, state: dict[str, Any]) -> list[str]:
    files, prefixes = project_start_canonical_contract(root)
    if not files and not prefixes:
        return []
    baseline = implementation_baseline(root, state)
    current = implementation_repo_state(root, state)[0]
    changed = changed_paths(baseline, current)
    return sorted(
        path for path in changed if path in files or any(path.startswith(prefix) for prefix in prefixes)
    )


def validate_canonical_attestation(
    state: dict[str, Any],
    reference: str,
    revision: str,
    source: str,
    receipt: str,
    checked_at: str,
) -> None:
    if min(len(reference), len(revision), len(source), len(receipt)) < 6:
        fail("Каноническая revision требует reference/revision/source/receipt.")
    external_names = state.get("checkpoints", {}).get("capabilities", {}).get("verified_external_names", [])
    if source != "local-repository" and source not in external_names:
        fail("Источник канонической revision не подтверждён как verified-callable capability.")
    if not timestamp_is_fresh(checked_at):
        fail("Квитанция канонической revision отсутствует, некорректна или старше 24 часов.")


def validate_plan_review_canonical(root: Path, state: dict[str, Any], review_text: str) -> dict[str, str]:
    plan_text = artifact_path(root, state, "plan").read_text(encoding="utf-8")
    plan_source = field(plan_text, "Plan source")
    checked_revision = field(review_text, "Canonical revision checked") or ""
    source = field(review_text, "Canonical revision source") or ""
    receipt = field(review_text, "Canonical revision receipt") or ""
    checked_at = field(review_text, "Canonical checked at") or ""
    if plan_source == "LOCAL":
        if (checked_revision, source, receipt, checked_at) != ("N/A", "N/A", "N/A", "N/A"):
            fail("LOCAL plan требует N/A во всех полях канонической revision.")
        return {"canonical_revision": "N/A", "canonical_revision_source": "N/A", "canonical_checked_at": "N/A"}
    reference = field(plan_text, "Canonical reference") or ""
    revision = field(plan_text, "Canonical revision") or ""
    if checked_revision != revision:
        fail("Проверенная canonical revision не совпадает с PLAN.md.")
    validate_canonical_attestation(state, reference, revision, source, receipt, checked_at)
    return {"canonical_revision": revision, "canonical_revision_source": source, "canonical_checked_at": checked_at}


def validate_verification_block(data: Any, priority: str) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("commands"), list) or not data["commands"]:
        fail("Verification JSON требует непустой commands.")
    positive_success = 0
    for command in data["commands"]:
        if not isinstance(command, dict) or not isinstance(command.get("exit_code"), int):
            fail("Каждая команда требует command/cwd/exit_code/expected_exit_codes/expectation_met/result/criterion; exit_code — число.")
        for key in ("command", "cwd", "result", "criterion"):
            if len(str(command.get(key, "")).strip()) < 2:
                fail(f"Команда verification не содержит {key}.")
        expected = command.get("expected_exit_codes")
        if not isinstance(expected, list) or not expected or not all(isinstance(code, int) for code in expected):
            fail("Команда verification требует непустой expected_exit_codes из чисел.")
        if command["exit_code"] not in expected or command.get("expectation_met") is not True:
            fail("Наблюдаемый exit_code команды не совпал с ожидаемым результатом.")
        if command["exit_code"] in {126, 127}:
            fail("Команда не была исполнима (exit 126/127); такой результат нельзя считать проверкой.")
        purpose = command.get("purpose")
        if purpose not in {"positive", "negative", "baseline", "diagnostic"}:
            fail("Команда verification требует purpose=positive|negative|baseline|diagnostic.")
        if purpose == "positive" and command["exit_code"] == 0:
            positive_success += 1
        if purpose in {"positive", "diagnostic"} and command["exit_code"] != 0:
            fail(f"Ненулевой код допустим только для ожидаемого baseline/negative, не для {purpose}.")
    if positive_success == 0:
        fail("Verification требует хотя бы один исполненный положительный оракул с exit_code=0.")
    for key in ("baseline", "test_sanity"):
        item = data.get(key)
        if not isinstance(item, dict) or item.get("status") not in {"PASS", "N/A"}:
            fail(f"{key} требует status PASS|N/A.")
        required = "evidence" if item["status"] == "PASS" else "reason"
        if len(str(item.get(required, "")).strip()) < 12:
            fail(f"{key} требует содержательный {required}.")
        if priority in {"P0", "P1"} and item["status"] == "N/A":
            fail(f"Для {priority} {key}=N/A недопустим.")
    verifier = data.get("active_verifier")
    if not isinstance(verifier, dict) or verifier.get("status") != "PASS":
        fail("active_verifier требует status=PASS.")
    if len(str(verifier.get("case", ""))) < 8 or len(str(verifier.get("result", ""))) < 8:
        fail("active_verifier требует конкретные case и result.")


def validate_evidence(root: Path, state: dict[str, Any], event: str, path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    ensure_complete(text, event)
    details: dict[str, Any] = {}
    if event in {"capabilities", "internal-research", "external-research", "plan"} and field(text, "Status") != "READY":
        fail(f"{ARTIFACTS[event]} должен содержать `Status: READY`.")
    if event == "capabilities":
        details.update(validate_capabilities(text))
    if event == "external-research":
        applicability = field(text, "Applicability")
        if applicability not in {"REQUIRED", "N/A"}:
            fail("Applicability должен быть REQUIRED или N/A.")
        if applicability == "N/A" and len(field(text, "Reason") or "") < 12:
            fail("Для N/A требуется содержательный Reason.")
    if event == "plan":
        scope = parse_scope(text)
        for allowed in scope:
            normalized = Path(allowed).as_posix().rstrip("/")
            for excluded in state_exclusions(state):
                blocked = Path(excluded).as_posix().rstrip("/")
                if normalized == blocked or normalized.startswith(blocked + "/") or blocked.startswith(normalized + "/"):
                    fail(f"Область плана пересекает служебный или исключённый путь: {allowed} ↔ {excluded}")
        source = field(text, "Plan source")
        reference, revision = field(text, "Canonical reference"), field(text, "Canonical revision")
        if source not in {"LOCAL", "CANONICAL"}:
            fail("Plan source должен быть LOCAL или CANONICAL.")
        if source != state.get("plan_source", "LOCAL"):
            fail("Plan source не совпадает с выбранным при bootstrap; не меняйте владельца плана скрыто.")
        if source == "CANONICAL" and (len(reference or "") < 6 or len(revision or "") < 6):
            fail("CANONICAL plan требует reference и revision/digest.")
        if source == "LOCAL" and (reference != "N/A" or revision != "N/A"):
            fail("LOCAL plan требует Canonical reference/revision: N/A.")
        details["plan_scope_fingerprint"] = scope_fingerprint(root, path)
    if event == "plan-review":
        if field(text, "Verdict") != "PASS" or field(text, "Critical open") != "0" or field(text, "High open") != "0":
            fail("План не прошёл PASS с нулём Critical/High.")
        origin, receipt = validate_receipt(text)
        plan = artifact_path(root, state, "plan")
        expected = hash_file(plan)
        if field(text, "Reviewed plan SHA-256") != expected:
            fail("SHA-256 обзора не совпадает с PLAN.md.")
        plan_text = plan.read_text(encoding="utf-8")
        canonical_details = validate_plan_review_canonical(root, state, text)
        expected_revision = canonical_details["canonical_revision"]
        current_scope_fingerprint = scope_fingerprint(root, plan)
        recorded_scope_fingerprint = state.get("checkpoints", {}).get("plan", {}).get("plan_scope_fingerprint")
        if current_scope_fingerprint != recorded_scope_fingerprint:
            fail("Область реализации изменилась после фиксации PLAN.md.")
        baseline = baseline_manifest(root, state)
        current, current_digest = current_repo_state(root, state)
        changed = changed_paths(baseline, current)
        if changed:
            fail("До plan-review изменены файлы репозитория: " + ", ".join(changed[:20]))
        details.update({
            "reviewed_plan_sha256": expected,
            "scope_fingerprint": current_scope_fingerprint,
            "review_scope_manifest": scope_manifest(root, parse_scope(plan_text)),
            "review_repo_digest": current_digest,
            "review_origin": origin,
            "reviewer_receipt": receipt,
            **canonical_details,
        })
    if event == "verification":
        if field(text, "Verdict") != "PASS" or field(text, "Real commands") != "YES":
            fail("VERIFICATION.md требует Verdict: PASS и Real commands: YES.")
        data = json_block(text, "verification")
        validate_verification_block(data, state["priority"])
        canonical = data.get("canonical_revision") if isinstance(data, dict) else None
        plan_text = artifact_path(root, state, "plan").read_text(encoding="utf-8")
        if not isinstance(canonical, dict):
            fail("Verification JSON требует canonical_revision.")
        if field(plan_text, "Plan source") == "LOCAL":
            values = tuple(canonical.get(key) for key in ("status", "reference", "revision", "source", "receipt", "checked_at"))
            if values != ("N/A", "N/A", "N/A", "N/A", "N/A", "N/A"):
                fail("LOCAL plan требует N/A во всех полях canonical_revision verification.")
        else:
            reference = field(plan_text, "Canonical reference") or ""
            revision = field(plan_text, "Canonical revision") or ""
            if canonical.get("status") != "PASS" or canonical.get("reference") != reference or canonical.get("revision") != revision:
                fail("Verification не подтверждает точные reference/revision канонического плана.")
            validate_canonical_attestation(
                state,
                reference,
                revision,
                str(canonical.get("source", "")),
                str(canonical.get("receipt", "")),
                str(canonical.get("checked_at", "")),
            )
        if field(text, "Baseline checked") != data["baseline"]["status"] or field(text, "Test sanity") != data["test_sanity"]["status"]:
            fail("Поля Baseline/Test sanity расходятся с JSON-блоком.")
        baseline = implementation_baseline(root, state)
        current, digest = implementation_repo_state(root, state)
        changed = changed_paths(baseline, current)
        if not changed:
            fail("В реализации нет изменений относительно исходного снимка.")
        scope = parse_scope(artifact_path(root, state, "plan").read_text(encoding="utf-8"))
        outside = outside_scope(changed, scope)
        if outside:
            fail("Изменения вне области плана: " + ", ".join(outside[:20]))
        if data["test_sanity"]["status"] == "N/A" and any(looks_like_test_path(path) for path in changed):
            fail("Test sanity: N/A недопустим, когда изменён путь теста.")
        details.update({"implementation_repo_digest": digest, "changed_paths": changed})
    if event == "code-review":
        required = {"Verdict": "PASS", "Critical open": "0", "High open": "0", "Active verifier": "YES"}
        wrong = [name for name, value in required.items() if field(text, name) != value]
        if wrong:
            fail("CODE-REVIEW.md не прошёл поля: " + ", ".join(wrong))
        origin, receipt = validate_receipt(text)
        plan_receipt = state.get("checkpoints", {}).get("plan-review", {}).get("reviewer_receipt")
        if receipt == plan_receipt:
            fail("Проверка результата требует отдельного запуска и другой квитанции, чем проверка плана.")
        reviewers = validate_result_reviewers(text, state, origin, receipt)
        current_digest = implementation_repo_state(root, state)[1]
        verification = artifact_path(root, state, "verification")
        if field(text, "Reviewed implementation SHA-256") != current_digest:
            fail("Обзор не связан с текущим снимком реализации.")
        if field(text, "Reviewed verification SHA-256") != hash_file(verification):
            fail("Обзор не связан с текущим VERIFICATION.md.")
        details.update({"implementation_repo_digest": current_digest, "review_origin": origin, "reviewer_receipt": receipt, "reviewers": reviewers})
    if event == "handoff":
        required = {"Status": "READY", "Criteria passed": "YES", "Rollback documented": "YES", "Residual risks documented": "YES"}
        wrong = [name for name, value in required.items() if field(text, name) != value]
        if wrong:
            fail("HANDOFF.md не прошёл поля: " + ", ".join(wrong))
        current_digest = implementation_repo_state(root, state)[1]
        if field(text, "Implementation SHA-256") != current_digest:
            fail("HANDOFF.md не связан с текущей реализацией.")
        if (root / ".project-start/state.json").is_file():
            if field(text, "Canonical docs changed") != "NO":
                fail("Project Start handoff требует поле Canonical docs changed: NO.")
            proposal = field(text, "Proposed documentation maintenance") or ""
            if len(proposal) < 8 or proposal == "PENDING":
                fail("Project Start handoff требует содержательное Proposed documentation maintenance.")
            changed_docs = canonical_doc_changes(root, state)
            if changed_docs:
                fail(
                    "Task Delivery не должен менять канонические документы Project Start до maintenance: "
                    + ", ".join(changed_docs[:20])
                )
        details["implementation_repo_digest"] = current_digest
    return details


def approval_valid(root: Path, state: dict[str, Any]) -> bool:
    approval = state.get("approval")
    return bool(
        approval
        and gate_fresh(root, state, "plan-review")
        and approval.get("plan_sha256") == hash_file(artifact_path(root, state, "plan"))
        and approval.get("plan_review_sha256") == hash_file(artifact_path(root, state, "plan-review"))
    )


def template_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "templates"


def cmd_inventory(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    data = build_inventory(root, args.codex_home or [], args.match or [])
    emit("ok", "Безопасный ограниченный осмотр завершён; значения config, команды MCP и журналы не читались.", **data, next_actions=["Сверьте matches с реальным каталогом и выполните read-only preflight выбранного MCP/app."])


def cmd_bootstrap(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    reject_pending_project_reopen(root)
    task_id = validate_task_id(args.task_id)
    if args.mode not in {"plan", "full"}:
        fail("bootstrap поддерживает plan/full; implement открывает существующий план.")
    if len(args.outcome.strip()) < 12:
        fail("Нужен один наблюдаемый outcome длиной не менее 12 символов.")
    artifact_root = safe_relative(args.artifact_root)
    artifact_dir = safe_join(root, artifact_root / task_id)
    target_machine = machine_dir(root, task_id)
    targets = {name: artifact_dir / filename for name, filename in ARTIFACTS.items()}
    preview = {"task_id": task_id, "mode": args.mode, "priority": args.priority, "plan_source": args.plan_source, "outcome": args.outcome, "state": str(target_machine / "state.json"), "artifacts": {name: str(path) for name, path in targets.items()}}
    if not args.apply:
        conflicts = [str(path) for path in [artifact_dir, target_machine] if path.exists()]
        if conflicts:
            fail("bootstrap не перезаписывает существующее: " + ", ".join(conflicts))
        emit("preview", "Будут созданы новые артефакты; изменений пока нет.", **preview, next_actions=["Проверьте одну связанную цель и пути, затем повторите с --apply."])
        return
    with mutation_guard(root, task_id, True):
        if artifact_dir.exists() or target_machine.exists():
            fail("bootstrap не перезаписывает существующую задачу.")
        templates = template_dir()
        rendered: dict[str, str] = {}
        substitutions = {"{{TASK_ID}}": task_id, "{{TITLE}}": args.title, "{{MODE}}": args.mode, "{{PRIORITY}}": args.priority, "{{OUTCOME}}": args.outcome}
        for name, filename in ARTIFACTS.items():
            template_name = "PLAN-CANONICAL.md" if name == "plan" and args.plan_source == "CANONICAL" else filename
            content = (templates / template_name).read_text(encoding="utf-8")
            for old, new in substitutions.items():
                content = content.replace(old, new)
            rendered[name] = content
        exclusions = [
            (artifact_root / task_id).as_posix(),
            ".codex/task-delivery",
            ".project-start/state.json",
            ".project-start/.state.lock",
        ]
        baseline = repo_manifest(root, exclusions)
        artifact_dir.parent.mkdir(parents=True, exist_ok=True)
        target_machine.parent.mkdir(parents=True, exist_ok=True)
        stage_art = Path(tempfile.mkdtemp(prefix=f".{task_id}-art-", dir=artifact_dir.parent))
        stage_machine = Path(tempfile.mkdtemp(prefix=f".{task_id}-state-", dir=target_machine.parent))
        artifact_published = False
        try:
            for name, filename in ARTIFACTS.items():
                (stage_art / filename).write_text(rendered[name], encoding="utf-8")
            write_manifest(stage_machine / "baseline-manifest.json", baseline)
            state = {
                "schema_version": SCHEMA_VERSION,
                "revision": 1,
                "task_id": task_id,
                "title": args.title,
                "outcome": args.outcome,
                "mode": args.mode,
                "plan_source": args.plan_source,
                "priority": args.priority,
                "phase": "planning",
                "created_at": now(),
                "updated_at": now(),
                "artifacts": {name: path.relative_to(root).as_posix() for name, path in targets.items()},
                "baseline_manifest": (Path(".codex") / "task-delivery" / task_id / "baseline-manifest.json").as_posix(),
                "baseline_repo_digest": manifest_digest(baseline),
                "checkpoints": {},
                "implementation_intent": None,
                "approval": None,
                "full_authorization_consumed": False,
                "progress": None,
                "completed_at": None,
            }
            (stage_machine / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(stage_art, artifact_dir)
            artifact_published = True
            os.replace(stage_machine, target_machine)
        except Exception:
            if artifact_published and not target_machine.exists():
                shutil.rmtree(artifact_dir, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(stage_art, ignore_errors=True)
            shutil.rmtree(stage_machine, ignore_errors=True)
    emit("ok", "Задача создана транзакционно без изменения промышленного кода.", **preview, next_actions=["Заполните CAPABILITIES.md."])


def resolve_evidence(root: Path, state: dict[str, Any], event: str, raw: str) -> Path:
    supplied = Path(raw).expanduser()
    supplied = supplied.resolve() if supplied.is_absolute() else safe_join(root, supplied)
    expected = artifact_path(root, state, event)
    if supplied != expected or not supplied.is_file():
        fail(f"Для {event} ожидается существующий {expected}.")
    return supplied


def cmd_record(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    with mutation_guard(root, args.task_id, args.apply):
        state_path, state = load_state(root, args.task_id)
        event = args.event
        assert_dependencies(root, state, event)
        if event == "verification":
            if not approval_valid(root, state):
                fail("Нет свежего одобрения текущего плана.")
            if not progress_fresh(root, state):
                fail("Перед verification нужен свежий PROGRESS checkpoint точного снимка кода.")
            if state.get("progress", {}).get("status") != "COMPLETE" or state.get("phase") == "blocked":
                fail("Verification разрешён только после свежего PROGRESS со Status: COMPLETE.")
        evidence = resolve_evidence(root, state, event, args.evidence)
        details = validate_evidence(root, state, event, evidence)
        digest = hash_file(evidence)
        preview = {"event": event, "evidence": str(evidence), "sha256": digest, **details}
        if not args.apply:
            emit("preview", f"Событие {event} прошло форматные и отпечаточные проверки.", **preview, next_actions=["Повторите с --apply."])
            return
        index = EVENTS.index(event)
        checkpoints = state.setdefault("checkpoints", {})
        for later in EVENTS[index + 1 :]:
            checkpoints.pop(later, None)
        state["completed_at"] = None
        if index <= EVENTS.index("plan-review"):
            state["approval"] = None
            state["progress"] = None
            intent = state.get("implementation_intent")
            plan = artifact_path(root, state, "plan")
            if intent and (not plan.is_file() or intent.get("plan_sha256") != hash_file(plan)):
                state["implementation_intent"] = None
        checkpoints[event] = {"path": evidence.relative_to(root).as_posix(), "sha256": digest, "recorded_at": now(), "note": args.note or "", **details}
        if event == "plan-review":
            state["phase"] = "ready_to_implement" if state["mode"] == "full" and not state.get("full_authorization_consumed") else "awaiting_approval"
        elif event == "verification":
            state["phase"] = "reviewing"
        elif event == "handoff":
            state["phase"] = "ready_to_complete"
        elif event == "code-review":
            state["phase"] = "reviewing"
        else:
            state["phase"] = "planning"
        save_state(state_path, state)
        emit("ok", f"Событие {event} зафиксировано.", **preview, phase=state["phase"], revision=state["revision"])


def cmd_begin_implement(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    reject_pending_project_reopen(root)
    with mutation_guard(root, args.task_id, args.apply):
        state_path, state = load_state(root, args.task_id)
        if state.get("phase") not in {"awaiting_approval", "ready_to_implement"} or not gate_fresh(root, state, "plan-review"):
            fail("Текущий проверенный план не готов принять новый запрос implement.")
        if len(args.note.strip()) < 12:
            fail("begin-implement требует квитанцию нового пользовательского запроса в --note.", "Укажите источник/ход и точный смысл без секретов; не создавайте разрешение от имени старого сообщения.")
        intent = {"plan_sha256": hash_file(artifact_path(root, state, "plan")), "plan_review_sha256": hash_file(artifact_path(root, state, "plan-review")), "requested_at": now(), "note": args.note or ""}
        if not args.apply:
            emit("preview", "Новый запрос будет привязан к текущему SHA плана.", implementation_intent=intent, next_actions=["Повторите с --apply до любых изменений плана."])
            return
        state["implementation_intent"] = intent
        state["phase"] = "awaiting_approval"
        save_state(state_path, state)
        emit("ok", "Запрос implement привязан к текущему плану; изменение PLAN.md потребует нового запроса.", implementation_intent=intent)


def cmd_approve(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    reject_pending_project_reopen(root)
    with mutation_guard(root, args.task_id, args.apply):
        state_path, state = load_state(root, args.task_id)
        if state.get("phase") not in {"awaiting_approval", "ready_to_implement"} or not gate_fresh(root, state, "plan-review"):
            fail(f"Фаза не допускает одобрение: {state.get('phase')}")
        plan = artifact_path(root, state, "plan")
        review = artifact_path(root, state, "plan-review")
        validate_plan_review_canonical(root, state, review.read_text(encoding="utf-8"))
        if args.source == "full-mode-request":
            if state.get("mode") != "full" or state.get("full_authorization_consumed"):
                fail("Первоначальное full-разрешение отсутствует или уже использовано.")
        else:
            intent = state.get("implementation_intent")
            if not intent or intent.get("plan_sha256") != hash_file(plan) or intent.get("plan_review_sha256") != hash_file(review):
                fail("Нет begin-implement, привязанного к текущему SHA плана и обзора.")
        checkpoint = state["checkpoints"]["plan-review"]
        current_digest = current_repo_state(root, state)[1]
        if current_digest != checkpoint.get("review_repo_digest") or scope_fingerprint(root, plan) != checkpoint.get("scope_fingerprint"):
            fail("Репозиторий изменился после plan-review.", "Повторно исследуйте и проверьте тот же план; изменение PLAN.md потребует нового запроса пользователя.")
        approval = {"source": args.source, "note": args.note or "", "approved_at": now(), "plan_sha256": hash_file(plan), "plan_review_sha256": hash_file(review), "review_repo_digest": current_digest}
        if not args.apply:
            emit("preview", "Текущий SHA готов к одобрению.", approval=approval, next_actions=["Повторите с --apply."])
            return
        state["approval"] = approval
        state["phase"] = "implementing"
        state["progress"] = None
        if state["mode"] == "plan":
            state["mode"] = "implement"
        if state["mode"] == "full":
            state["full_authorization_consumed"] = True
        save_state(state_path, state)
        emit("ok", "Одобрена только текущая проверенная версия плана.", approval=approval, phase="implementing")


def cmd_checkpoint(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    with mutation_guard(root, args.task_id, args.apply):
        state_path, state = load_state(root, args.task_id)
        if not approval_valid(root, state):
            fail("Нет свежего одобрения плана для checkpoint.")
        path = artifact_path(root, state, "progress")
        text = path.read_text(encoding="utf-8")
        ensure_complete(text, "progress")
        status = field(text, "Status")
        if status not in {"ACTIVE", "BLOCKED", "COMPLETE"}:
            fail("PROGRESS.md требует Status: ACTIVE|BLOCKED|COMPLETE.")
        for label in ("Last completed slice", "Best-known checks", "Next action", "Resume command"):
            if len(field(text, label) or "") < 4:
                fail(f"PROGRESS.md требует {label}.")
        baseline = implementation_baseline(root, state)
        current, digest = implementation_repo_state(root, state)
        changed = changed_paths(baseline, current)
        scope = parse_scope(artifact_path(root, state, "plan").read_text(encoding="utf-8"))
        outside = outside_scope(changed, scope)
        if outside:
            fail("Checkpoint содержит изменения вне плана: " + ", ".join(outside[:20]))
        progress = {"status": status, "sha256": hash_file(path), "implementation_repo_digest": digest, "changed_paths": changed, "recorded_at": now(), "note": args.note or ""}
        if not args.apply:
            emit("preview", "PROGRESS checkpoint согласован с текущим кодом.", progress=progress, next_actions=["Повторите с --apply."])
            return
        state["progress"] = progress
        state["phase"] = "blocked" if status == "BLOCKED" else "implementing"
        save_state(state_path, state)
        emit("ok", "Лучшее известное состояние реализации сохранено.", progress=progress, phase=state["phase"])


def cmd_recover_lock(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    lock = lock_path(root, args.task_id)
    info = inspect_lock(lock)
    if info["owner_alive"]:
        fail("Lock принадлежит живому процессу; восстановление запрещено.", "Дождитесь процесса или остановите его штатно.")
    if not info["recoverable"]:
        fail(
            f"Lock ещё не считается аварийно оставшимся; нужен возраст не менее {STALE_LOCK_SECONDS} секунд.",
            "Повторите проверку позже; не удаляйте свежий lock.",
        )
    if not args.apply:
        emit("preview", "Обнаружен старый lock без живого владельца; удаление ещё не выполнено.", lock=info, next_actions=["Повторите recover-lock с --apply."])
        return
    owner_path = lock / "owner.json"
    try:
        owner_path.unlink(missing_ok=True)
        lock.rmdir()
    except OSError as exc:
        fail(f"Lock не удалось безопасно удалить: {exc}", "Не используйте рекурсивное удаление; проверьте содержимое и владельца вручную.")
    emit("ok", "Старый lock без живого владельца удалён.", lock=info)


def cmd_complete(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    with mutation_guard(
        root, args.task_id, args.apply, allow_project_obligation=True
    ):
        reject_pending_project_reopen(root, allow_task_id=args.task_id)
        state_path, state = load_state(root, args.task_id)
        if state.get("phase") == "completed":
            missing = [
                event
                for event in ("verification", "code-review", "handoff")
                if not gate_fresh(root, state, event)
            ]
            if not approval_valid(root, state) or missing:
                fail(
                    "Завершённая задача изменилась; maintenance obligation нельзя восстановить по несвежему снимку: "
                    + ", ".join(missing or ["plan approval"])
                )
            if args.apply:
                mark_project_start_maintenance_required(root, state_path, state)
                obligation_marker(root, args.task_id).unlink(missing_ok=True)
            emit(
                "ok" if args.apply else "preview",
                "Задача уже завершена; Project Start maintenance obligation проверен."
                if args.apply
                else "Задача уже завершена; будет проверен Project Start maintenance obligation.",
                phase="completed",
                completed_at=state.get("completed_at"),
            )
            return
        if not approval_valid(root, state):
            fail("Одобрение плана отсутствует или устарело.")
        missing = [event for event in ("verification", "code-review", "handoff") if not gate_fresh(root, state, event)]
        if missing or state.get("phase") != "ready_to_complete":
            fail("Нельзя завершить задачу: несвежие рубежи " + ", ".join(missing or [str(state.get('phase'))]))
        if not args.apply:
            emit("preview", "Точный снимок кода и доказательств готов к завершению.", next_actions=["Повторите с --apply."])
            return
        marker = obligation_marker(root, args.task_id)
        checkpoint = state.get("checkpoints", {}).get("handoff")
        if not isinstance(checkpoint, dict):
            fail("Handoff checkpoint исчез до durable completion.")
        atomic_json(
            marker,
            {
                "schema_version": 1,
                "task_id": args.task_id,
                "handoff_path": checkpoint.get("path"),
                "handoff_sha256": checkpoint.get("sha256"),
                "created_at": now(),
            },
        )
        state["phase"] = "completed"
        state["completed_at"] = now()
        save_state(state_path, state)
        mark_project_start_maintenance_required(root, state_path, state)
        marker.unlink(missing_ok=True)
        emit(
            "ok",
            "Задача завершена; Project Start получил обязательную maintenance receipt до следующей задачи.",
            phase="completed",
            completed_at=state["completed_at"],
        )


def status_data(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    checkpoints = state.get("checkpoints", {})
    stale = [event for event in checkpoints if not checkpoint_fresh(root, state, event)]
    invalid = [event for event in checkpoints if not gate_fresh(root, state, event)]
    missing_files = [name for name in ARTIFACTS if not artifact_path(root, state, name).is_file()]
    next_event = next((event for event in EVENTS if event not in checkpoints or event in invalid), None)
    effective = state["phase"]
    if state["phase"] == "completed" and (stale or invalid):
        effective = "completed_with_drift"
    elif state["phase"] in {"implementing", "reviewing", "ready_to_complete"} and not approval_valid(root, state):
        effective = "awaiting_revalidation"
    return {
        "task_id": state["task_id"], "title": state["title"], "outcome": state["outcome"],
        "mode": state["mode"], "priority": state["priority"], "plan_source": state.get("plan_source", "LOCAL"), "phase": state["phase"], "effective_phase": effective,
        "approval_valid": approval_valid(root, state), "implementation_intent": state.get("implementation_intent"),
        "progress": state.get("progress"), "recorded_events": [event for event in EVENTS if event in checkpoints],
        "stale_events": stale, "invalid_events": invalid, "missing_artifacts": missing_files, "next_event": next_event,
        "artifacts": state["artifacts"], "revision": state["revision"], "updated_at": state["updated_at"],
    }


def cmd_status(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    _, state = load_state(root, args.task_id)
    data = status_data(root, state)
    phase = data["effective_phase"]
    if phase == "awaiting_approval":
        actions = ["На новом явном запросе implement сначала выполните begin-implement; затем approve-plan."]
    elif phase == "ready_to_implement":
        actions = ["Для исходного full выполните approve-plan --source full-mode-request."]
    elif phase in {"implementing", "blocked"}:
        actions = ["Обновите PROGRESS.md и checkpoint; перед verification checkpoint должен быть свежим."]
    elif phase == "ready_to_complete":
        actions = ["Выполните complete --apply."]
    elif phase == "completed_with_drift":
        actions = ["Не считайте задачу завершённой: восстановите точный снимок или повторите verification/review/handoff."]
    elif data["next_event"]:
        actions = [f"Следующий рубеж: {data['next_event']}."]
    else:
        actions = []
    emit("ok", "Состояние прочитано без изменений.", **data, next_actions=actions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence gates for task-delivery")
    sub = parser.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser("inventory")
    inventory.add_argument("--root", required=True); inventory.add_argument("--codex-home", action="append", default=[]); inventory.add_argument("--match", action="append", default=[]); inventory.set_defaults(handler=cmd_inventory)
    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--root", required=True); bootstrap.add_argument("--task-id", required=True); bootstrap.add_argument("--title", required=True); bootstrap.add_argument("--outcome", required=True)
    bootstrap.add_argument("--mode", choices=["plan", "full", "implement"], required=True); bootstrap.add_argument("--priority", choices=["P0", "P1", "P2", "P3"], default="P2"); bootstrap.add_argument("--plan-source", choices=["LOCAL", "CANONICAL"], default="LOCAL"); bootstrap.add_argument("--artifact-root", default="docs/tasks"); bootstrap.add_argument("--apply", action="store_true"); bootstrap.set_defaults(handler=cmd_bootstrap)
    status = sub.add_parser("status"); status.add_argument("--root", required=True); status.add_argument("--task-id", required=True); status.set_defaults(handler=cmd_status)
    record = sub.add_parser("record"); record.add_argument("--root", required=True); record.add_argument("--task-id", required=True); record.add_argument("--event", choices=EVENTS, required=True); record.add_argument("--evidence", required=True); record.add_argument("--note", default=""); record.add_argument("--apply", action="store_true"); record.set_defaults(handler=cmd_record)
    begin = sub.add_parser("begin-implement"); begin.add_argument("--root", required=True); begin.add_argument("--task-id", required=True); begin.add_argument("--note", required=True); begin.add_argument("--apply", action="store_true"); begin.set_defaults(handler=cmd_begin_implement)
    approve = sub.add_parser("approve-plan"); approve.add_argument("--root", required=True); approve.add_argument("--task-id", required=True); approve.add_argument("--source", choices=["full-mode-request", "user-invocation"], required=True); approve.add_argument("--note", default=""); approve.add_argument("--apply", action="store_true"); approve.set_defaults(handler=cmd_approve)
    checkpoint = sub.add_parser("checkpoint"); checkpoint.add_argument("--root", required=True); checkpoint.add_argument("--task-id", required=True); checkpoint.add_argument("--note", default=""); checkpoint.add_argument("--apply", action="store_true"); checkpoint.set_defaults(handler=cmd_checkpoint)
    recover = sub.add_parser("recover-lock"); recover.add_argument("--root", required=True); recover.add_argument("--task-id", required=True); recover.add_argument("--apply", action="store_true"); recover.set_defaults(handler=cmd_recover_lock)
    complete = sub.add_parser("complete"); complete.add_argument("--root", required=True); complete.add_argument("--task-id", required=True); complete.add_argument("--apply", action="store_true"); complete.set_defaults(handler=cmd_complete)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
        return 0
    except (TaskError, SnapshotError) as exc:
        if isinstance(exc, TaskError):
            summary, actions = parse_failure(exc)
        else:
            summary, actions = str(exc), []
        emit("error", summary, next_actions=actions)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        emit("error", f"Ошибка файловой системы или данных: {exc}", next_actions=["Проверьте пути и состояние; не повторяйте разрушительное действие."])
        return 2


if __name__ == "__main__":
    sys.exit(main())
