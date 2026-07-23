#!/usr/bin/env python3
"""Small deterministic control layer for model-first Project Start work."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import subprocess
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
TASK_DELIVERY_SCRIPT_DIR = SKILL_DIR.parent / "task-delivery" / "scripts"
if str(TASK_DELIVERY_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(TASK_DELIVERY_SCRIPT_DIR))

import project_maintenance as legacy_maintenance  # noqa: E402
import project_start as project_runtime  # noqa: E402
import task_delivery as task_delivery_runtime  # noqa: E402


GRAPH_PATH = SKILL_DIR / "graph.json"
RUNTIME_REL = Path(".agent-graphs/project-start-runs")
STATE_NAME = "state.json"
LOCK_NAME = ".state.lock"
WORK_NAME = "project.json"
VERIFY_NAME = "verification.json"
DOC_SUFFIXES = {".md", ".mdx", ".rst"}
IGNORED_DIRS = {
    ".agent-graphs",
    ".codex",
    ".git",
    ".mypy_cache",
    ".project-start",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "generated",
    "node_modules",
    "vendor",
}
LEGACY_BOOTSTRAP_COVERAGE = {
    "business",
    "documentation_map",
    "domain_context",
    "foundation",
    "codebase",
    "quality",
    "plan",
    "agent_context",
    "skill_contract",
}
BOOTSTRAP_COVERAGE = LEGACY_BOOTSTRAP_COVERAGE | {"engineering_standard"}
LEGACY_ACTIVE_GRAPH_IDENTITIES = {
    ("3.4.0", "658f933cb082d2b1a5070bf35cf2f452b7353dbc2cf16d501338b9797dd020a2"),
}


class GraphError(RuntimeError):
    """A safe, actionable Project Start graph error."""


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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_digest(snapshot: dict[str, str]) -> str:
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def graph_contract() -> dict[str, Any]:
    graph = load_json(GRAPH_PATH)
    if graph.get("schema_version") != 2 or graph.get("graph_id") != "project-start":
        raise GraphError("Project Start graph должен использовать schema_version 2.")
    if set(graph.get("routes", {})) != {"bootstrap", "maintenance"}:
        raise GraphError("Project Start graph должен содержать bootstrap и maintenance.")
    for mode in ("bootstrap", "maintenance"):
        route = graph["routes"][mode]
        if route.get("entry") != "work" or route.get("terminal") != "complete":
            raise GraphError(f"Некорректные entry/terminal для {mode}.")
        if set(route.get("nodes", {})) != {"work", "verify", "complete"}:
            raise GraphError(f"Маршрут {mode} должен иметь только work, verify, complete.")
    contract = graph.get("documentation_contract")
    if not isinstance(contract, dict) or set(contract.get("coverage", [])) != BOOTSTRAP_COVERAGE:
        raise GraphError("Project Start documentation contract содержит неверный coverage.")
    anchors = contract.get("anchors")
    expected_anchors = {"agent_context", "documentation_map", "domain_context", "skill_contract"}
    if not isinstance(anchors, dict) or set(anchors) != expected_anchors:
        raise GraphError("Project Start documentation contract содержит неверные anchors.")
    required_skills = contract.get("required_bootstrap_skills")
    if not isinstance(required_skills, list) or set(required_skills) != {
        "domain-modeling",
        "codebase-design",
    }:
        raise GraphError("Project Start documentation contract содержит неверные bootstrap skills.")
    providers = contract.get("skill_contract_providers")
    if not isinstance(providers, list) or set(providers) != {
        "setup-matt-pocock-skills",
        "project-start:skill-contract-fallback",
    }:
        raise GraphError("Project Start documentation contract содержит неверные skill contract providers.")
    engineering_providers = contract.get("engineering_standard_providers")
    if not isinstance(engineering_providers, list) or set(engineering_providers) != {
        "coding-standards",
        "project-start:engineering-standard-fallback",
    }:
        raise GraphError(
            "Project Start documentation contract содержит неверные engineering standard providers."
        )
    mcp_policy = graph.get("mcp_policy")
    if (
        not isinstance(mcp_policy, dict)
        or mcp_policy.get("discovery") != "when-relevant"
        or mcp_policy.get("relevant_use") != "required"
        or mcp_policy.get("receipt_prefix") != "mcp:"
        or mcp_policy.get("fallback_prefix") != "mcp:fallback:"
        or mcp_policy.get("not_applicable_prefix") != "mcp:not-applicable:"
        or not isinstance(mcp_policy.get("selection_order"), list)
    ):
        raise GraphError("Project Start graph содержит неверную conditional MCP policy.")
    if graph.get("work_policy", {}).get("fast_path") != "root-only":
        raise GraphError("Project Start graph должен сохранять root-only fast path.")
    execution = graph.get("execution_policy", {})
    if (
        execution.get("default_tier") != "tracked"
        or set(execution.get("tiers", {})) != {"tracked", "verified"}
    ):
        raise GraphError("Project Start graph содержит неверные execution tiers.")
    return graph


def supported_graph_identity(state: dict[str, Any]) -> bool:
    graph = graph_contract()
    identity = (state.get("graph_version"), state.get("graph_sha256"))
    current = (graph["graph_version"], sha256_file(GRAPH_PATH))
    return identity == current or identity in LEGACY_ACTIVE_GRAPH_IDENTITIES


def documentation_contract_for_state(state: dict[str, Any]) -> dict[str, Any]:
    contract = json.loads(json.dumps(graph_contract()["documentation_contract"]))
    if state.get("graph_version") == "3.4.0":
        contract["coverage"] = sorted(LEGACY_BOOTSTRAP_COVERAGE)
        contract.pop("engineering_standard_providers", None)
    return contract


def root_path(raw: str) -> Path:
    try:
        return project_runtime.root_path(raw)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc


def safe_path(root: Path, raw: str | Path, *, expected: str | None = None) -> Path:
    try:
        return project_runtime.safe_repo_path(root, raw, expected=expected)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc


def write_json(path: Path, value: dict[str, Any], root: Path) -> None:
    try:
        project_runtime.write_json_atomic(root, path, value)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc


def write_text(path: Path, content: str, root: Path) -> None:
    try:
        project_runtime.write_text_atomic(root, path, content)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc


def run_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_dir() or not (path / STATE_NAME).is_file():
        raise GraphError(f"Не найден Project Start run: {path}")
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
            if age > stale_seconds and not project_runtime._pid_is_alive(pid):
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


def discover_docs(root: Path) -> list[str]:
    docs: list[str] = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in IGNORED_DIRS and not (current_path / name).is_symlink()
        ]
        for name in names:
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() in DOC_SUFFIXES or name in {"AGENTS.md", "CLAUDE.md"}:
                docs.append(path.relative_to(root).as_posix())
    return sorted(set(docs))


def legacy_canonical_docs(root: Path, project: dict[str, Any]) -> list[str]:
    graph_v3 = project.get("graph_v3") if isinstance(project.get("graph_v3"), dict) else {}
    recorded = graph_v3.get("canonical_docs")
    if isinstance(recorded, list) and recorded:
        return sorted(set(item for item in recorded if isinstance(item, str) and item.strip()))
    return [path.relative_to(root).as_posix() for path in legacy_maintenance.canonical_docs(root, project)]


def changed_paths(before: dict[str, str], after: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """Return changed, created and deleted paths between two exact document snapshots."""
    relatives = sorted(set(before) | set(after))
    changed = [
        path
        for path in relatives
        if before.get(path, "missing") not in {None, "missing"}
        and after.get(path, "missing") not in {"missing", before[path]}
    ]
    created = [
        path
        for path in relatives
        if before.get(path, "missing") == "missing" and after.get(path, "missing") != "missing"
    ]
    deleted = [
        path
        for path in relatives
        if before.get(path, "missing") not in {None, "missing"} and after.get(path, "missing") == "missing"
    ]
    return changed, created, deleted


def snapshot(root: Path, relatives: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for relative in sorted(set(relatives)):
        path = safe_path(root, relative, expected="file")
        values[relative] = sha256_file(path) if path.is_file() else "missing"
    return values


def repository_entries(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        text=False,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return sorted(
            Path(item.decode("utf-8", errors="surrogateescape"))
            for item in completed.stdout.split(b"\0")
            if item
        )
    values: list[Path] = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        symlink_dirs = [name for name in directories if (current_path / name).is_symlink()]
        values.extend((current_path / name).relative_to(root) for name in symlink_dirs)
        directories[:] = [
            name
            for name in directories
            if name not in IGNORED_DIRS and name not in symlink_dirs
        ]
        values.extend((current_path / name).relative_to(root) for name in names)
    return sorted(values)


def repository_sha(root: Path, *, include_docs: bool = True) -> str:
    digest = hashlib.sha256()
    for relative in repository_entries(root):
        if not relative.parts or any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if not include_docs and (relative.suffix.lower() in DOC_SUFFIXES or relative.name in {"AGENTS.md", "CLAUDE.md"}):
            continue
        try:
            path = legacy_maintenance.repository_entry(root / relative, root)
        except legacy_maintenance.MaintenanceError as exc:
            raise GraphError(str(exc)) from exc
        digest.update(relative.as_posix().encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(f"file:{path.stat().st_mode & 0o777:o}\0".encode("ascii"))
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(b"missing\0")
        digest.update(b"\0")
    return digest.hexdigest()


def source_sha(root: Path) -> str:
    """Hash non-document repository inputs so model work cannot race code changes."""
    return repository_sha(root, include_docs=False)


def runner_command() -> str:
    return f"python3 {shlex.quote(str(Path(__file__).resolve()))}"


def project_state(root: Path) -> dict[str, Any] | None:
    path = root / project_runtime.STATE_REL
    if not path.is_file():
        return None
    try:
        return project_runtime.load_state(root)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc


def save_project(root: Path, project: dict[str, Any], expected: str | None) -> str:
    try:
        return project_runtime.save_project_state(root, project, expected_sha256=expected)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc


def commit_initial_state(
    root: Path,
    project: dict[str, Any],
    expected: str | None,
    require_absent: bool,
    run_dir: Path,
    state: dict[str, Any],
) -> str:
    """Reserve the run and write both state files under one activation lock."""
    project_path = safe_path(root, project_runtime.STATE_REL, expected="file")
    try:
        with task_delivery_runtime.admission_guard(root):
            with project_runtime.project_state_lock(root):
                current = sha256_file(project_path) if project_path.is_file() else None
                if require_absent and current is not None:
                    raise GraphError("Project Start state появился после init preview; повтори команду.")
                if expected is not None and current != expected:
                    raise GraphError("Project Start state изменился конкурентно; повтори init на свежем состоянии.")
                if run_dir.exists():
                    persisted = load_json(project_path) if project_path.is_file() else {}
                    active = persisted.get("maintenance", {}).get("active_run")
                    if isinstance(active, dict) and active.get("run_id") == run_dir.name:
                        raise GraphError("Предыдущая активация run прервалась; сначала выполни recover.")
                    if not run_dir.is_dir() or any(run_dir.iterdir()):
                        raise GraphError(f"Run directory уже занят: {run_dir}")
                    run_dir.rmdir()
                run_dir.mkdir(parents=True, exist_ok=False)
                payload = dict(project)
                payload.pop("_loaded_state_sha256", None)
                project_runtime.write_json_atomic(root, project_path, payload)
                digest = sha256_file(project_path)
                state["project_state_sha256"] = digest
                write_json(run_dir / STATE_NAME, state, root)
    except ValueError as exc:
        raise GraphError(str(exc)) from exc
    project["_loaded_state_sha256"] = digest
    return digest


def resolve_mode(requested: str, project: dict[str, Any] | None) -> str:
    if requested not in {"auto", "bootstrap", "maintenance"}:
        raise GraphError("Режим должен быть auto, bootstrap или maintenance.")
    inferred = "bootstrap" if project is None or project.get("phase") not in {"execution", "complete"} else "maintenance"
    mode = inferred if requested == "auto" else requested
    if mode == "maintenance" and (project is None or project.get("phase") not in {"execution", "complete"}):
        raise GraphError("Maintenance доступен только после Project Start execution/complete.")
    if mode == "bootstrap" and project is not None and project.get("phase") in {"execution", "complete"}:
        raise GraphError("Проект уже подготовлен; используй maintenance или auto.")
    return mode


def run_id_for(
    root: Path,
    mode: str,
    reason: str,
    receipt: dict[str, str] | None,
    version: str,
    source_sha256: str,
    trigger: str,
    cycle: str,
    restart_nonce: str,
) -> str:
    raw = json.dumps(
        {
            "root": str(root),
            "mode": mode,
            "reason": reason.strip(),
            "receipt": receipt,
            "version": version,
            "source_sha256": source_sha256,
            "trigger": trigger,
            "cycle": cycle,
            "restart_nonce": restart_nonce,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def ensure_activation_available(project: dict[str, Any], run_id: str) -> None:
    maintenance = project.setdefault("maintenance", {"history": []})
    active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
    status = maintenance.get("status")
    allowed = {
        "not-ready",
        "operational",
        "maintenance-required",
        "restart-required",
        "running",
        "blocked",
        "reopen-required",
    }
    if status not in allowed:
        raise GraphError(f"Неизвестный fail-closed maintenance status: {status!r}")
    if active:
        raise GraphError(
            f"Project Start run {active.get('run_id')} уже активен; продолжи его или выполни recover."
        )
    if status in {"running", "blocked", "reopen-required"}:
        raise GraphError(f"Maintenance status {status} потерял active_run; сначала выполни recover.")
    if status == "maintenance-required" and not isinstance(maintenance.get("maintenance_required"), dict):
        raise GraphError("maintenance-required не содержит точную Task Delivery obligation.")
    if status == "restart-required" and not isinstance(maintenance.get("pending_restart"), dict):
        raise GraphError("restart-required не содержит replacement-run obligation.")


def mark_active(
    project: dict[str, Any],
    run_id: str,
    run_dir: Path,
    mode: str,
    reason: str,
    trigger: str,
    *,
    consumed_obligation: dict[str, Any] | None = None,
    requires_verification: bool = False,
) -> None:
    stamp = now()
    ensure_activation_available(project, run_id)
    maintenance = project.setdefault("maintenance", {"history": []})
    maintenance["status"] = "running"
    maintenance["active_run"] = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "mode": mode,
        "reason": reason,
        "trigger": trigger,
        "node": "work",
        "updated_at": stamp,
    }
    if consumed_obligation is not None:
        maintenance["active_run"]["consumed_obligation"] = consumed_obligation
    if requires_verification:
        maintenance["active_run"]["requires_verification"] = True
    maintenance.pop("maintenance_required", None)
    maintenance.pop("pending_reopen", None)
    maintenance.pop("pending_drift", None)
    maintenance.pop("pending_restart", None)
    project["updated_at"] = stamp


def validate_pending_obligation(
    project: dict[str, Any] | None,
    mode: str,
    trigger: str,
    receipt: dict[str, str] | None,
) -> None:
    if project is None:
        return
    maintenance = project.get("maintenance") if isinstance(project.get("maintenance"), dict) else {}
    if maintenance.get("status") != "maintenance-required":
        return
    required = maintenance.get("maintenance_required")
    if not isinstance(required, dict):
        raise GraphError("Project Start содержит повреждённый maintenance-required obligation.")
    if mode != "maintenance" or trigger != "task-delivery" or not isinstance(receipt, dict):
        raise GraphError("Незакрытый Task Delivery obligation требует точный trigger task-delivery и HANDOFF receipt.")
    expected = {
        "path": required.get("handoff_path"),
        "sha256": required.get("handoff_sha256"),
        "task_id": required.get("task_id"),
        "task_state": required.get("task_state_path"),
        "task_state_sha256": required.get("task_state_sha256"),
    }
    actual = {
        "path": receipt.get("path"),
        "sha256": receipt.get("sha256"),
        "task_id": receipt.get("task_id"),
        "task_state": receipt.get("task_state"),
        "task_state_sha256": receipt.get("task_state_sha256"),
    }
    if receipt.get("kind") != "task-delivery" or actual != expected:
        raise GraphError("Переданный HANDOFF receipt не совпадает с maintenance-required obligation.")


def validate_pending_drift(project: dict[str, Any] | None, root: Path) -> None:
    if project is None:
        return
    maintenance = project.get("maintenance") if isinstance(project.get("maintenance"), dict) else {}
    pending = maintenance.get("pending_drift") if isinstance(maintenance.get("pending_drift"), dict) else None
    if pending is None:
        return
    baseline = pending.get("baseline")
    if not isinstance(baseline, dict) or not baseline:
        raise GraphError("Blocked document drift не содержит безопасного baseline; требуется ручное восстановление.")
    if snapshot(root, list(baseline)) != baseline:
        raise GraphError("Перед свежим init восстанови документы, изменённые в abandoned run.")


def validate_task_delivery_freshness(root: Path, receipt: dict[str, str] | None) -> None:
    if not isinstance(receipt, dict) or receipt.get("kind") != "task-delivery":
        return
    state_path = safe_path(root, receipt.get("task_state", ""), expected="file")
    task_state = load_json(state_path)
    try:
        task_delivery_runtime._MANIFEST_CACHE.clear()
        current_digest = task_delivery_runtime.implementation_repo_state(root, task_state)[1]
    except (task_delivery_runtime.TaskError, KeyError, OSError, ValueError) as exc:
        raise GraphError(f"Не удалось проверить свежесть Task Delivery implementation: {exc}") from exc
    if current_digest != receipt.get("implementation_sha256"):
        raise GraphError(
            "Репозиторий изменился после Task Delivery handoff; нужен новый Task Delivery checkpoint."
        )


def initialize(
    root_raw: str,
    requested_mode: str,
    reason: str,
    trigger: str,
    change_receipt: str | None,
    cycle_key: str | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise GraphError("Причина запуска не должна быть пустой.")
    root = root_path(root_raw)
    graph = graph_contract()
    project = project_state(root)
    mode = resolve_mode(requested_mode, project)
    if trigger not in {"manual", "task-delivery", "drift", "scheduled"}:
        raise GraphError("Неизвестный trigger.")
    try:
        receipt = legacy_maintenance.resolve_receipt(root, change_receipt, trigger)
    except legacy_maintenance.MaintenanceError as exc:
        raise GraphError(str(exc)) from exc
    validate_pending_obligation(project, mode, trigger, receipt)
    validate_pending_drift(project, root)
    validate_task_delivery_freshness(root, receipt)
    repo_sha256 = repository_sha(root)
    source_sha256 = source_sha(root)
    # Close the freshness-to-baseline window: later source drift is bound by baseline_source_sha256.
    validate_task_delivery_freshness(root, receipt)
    cycle = (cycle_key or "").strip() or (now()[:10] if trigger == "scheduled" else "")
    graph_v3 = project.get("graph_v3") if project is not None and isinstance(project.get("graph_v3"), dict) else {}
    restart_nonce = str(graph_v3.get("restart_nonce", ""))
    run_id = run_id_for(
        root,
        mode,
        reason,
        receipt,
        graph["graph_version"],
        repo_sha256,
        trigger,
        cycle,
        restart_nonce,
    )
    runtime_root = safe_path(root, RUNTIME_REL, expected="dir")
    runtime_root.mkdir(parents=True, exist_ok=True)
    ignore = safe_path(root, RUNTIME_REL.parent / ".gitignore", expected="file")
    if not ignore.exists():
        write_text(ignore, "*\n", root)
    elif "*" not in {line.strip() for line in ignore.read_text(encoding="utf-8").splitlines()}:
        write_text(ignore, ignore.read_text(encoding="utf-8").rstrip() + "\n*\n", root)
    run_dir = safe_path(root, RUNTIME_REL / run_id, expected="dir")
    state_path = run_dir / STATE_NAME
    if state_path.is_file():
        state = load_state(run_dir)
        return result(
            state["status"],
            "Продолжай существующий Project Start run.",
            artifacts=[str(run_dir)],
            data={"run": str(run_dir), "mode": state["mode"], "current": state["current"]},
        )
    if project is not None:
        ensure_activation_available(project, run_id)
    new_project = project is None
    if new_project:
        project = project_runtime.new_state("docs/project", None, None)
        expected = None
    else:
        expected = project.pop("_loaded_state_sha256", None)
    baseline_docs = discover_docs(root)
    baseline_canonical: list[str] = []
    operational_docs: dict[str, str] = {}
    operational_baseline_known = False
    maintenance_before = project.get("maintenance") if isinstance(project.get("maintenance"), dict) else {}
    consumed_obligation = (
        dict(maintenance_before["maintenance_required"])
        if maintenance_before.get("status") == "maintenance-required"
        and isinstance(maintenance_before.get("maintenance_required"), dict)
        else None
    )
    pending_restart = (
        dict(maintenance_before["pending_restart"])
        if isinstance(maintenance_before.get("pending_restart"), dict)
        else None
    )
    if mode == "maintenance":
        inherited = legacy_canonical_docs(root, project)
        baseline_docs = sorted(set(baseline_docs) | set(inherited))
        baseline_canonical = sorted(set(inherited))
        graph_v3 = project.get("graph_v3") if isinstance(project.get("graph_v3"), dict) else {}
        canonical_hashes = graph_v3.get("canonical_doc_hashes")
        agent_hashes = graph_v3.get("agent_instruction_doc_hashes")
        if isinstance(canonical_hashes, dict) and isinstance(agent_hashes, dict) and all(
            isinstance(path, str) and isinstance(digest, str)
            for path, digest in {**canonical_hashes, **agent_hashes}.items()
        ):
            operational_docs = {**canonical_hashes, **agent_hashes}
            operational_baseline_known = True
        else:
            authority = sorted(
                set(baseline_canonical)
                | {
                    path
                    for path in baseline_docs
                    if path == "AGENTS.md" or path.endswith("/AGENTS.md")
                }
            )
            operational_docs = snapshot(root, authority)
    baseline_snapshot = snapshot(root, baseline_docs)
    current_agent_docs = {
        path for path in baseline_docs if path == "AGENTS.md" or path.endswith("/AGENTS.md")
    }
    comparison_paths = sorted(set(operational_docs) | current_agent_docs)
    current_operational_view = snapshot(root, comparison_paths)
    preexisting_changed, preexisting_created, preexisting_deleted = changed_paths(
        operational_docs, current_operational_view
    ) if mode == "maintenance" and operational_baseline_known else ([], [], [])
    mark_active(
        project,
        run_id,
        run_dir,
        mode,
        reason.strip(),
        trigger,
        consumed_obligation=consumed_obligation,
        requires_verification=bool(pending_restart and pending_restart.get("requires_verification")),
    )
    nodes = {name: {"status": "pending", "attempts": 0, "receipts": []} for name in ("work", "verify", "complete")}
    nodes["work"]["status"] = "ready"
    stamp = now()
    state = {
        "schema_version": 3,
        "graph_id": "project-start",
        "graph_version": graph["graph_version"],
        "graph_sha256": sha256_file(GRAPH_PATH),
        "run_id": run_id,
        "root": str(root),
        "mode": mode,
        "reason": reason.strip(),
        "trigger": trigger,
        "cycle": cycle,
        "change_receipt": receipt,
        "consumed_obligation": consumed_obligation,
        "status": "running",
        "current": "work",
        "baseline_docs": baseline_snapshot,
        "baseline_canonical": sorted(set(baseline_canonical)),
        "operational_docs": operational_docs,
        "operational_baseline_known": operational_baseline_known,
        "preexisting_drift": {
            "changed": preexisting_changed,
            "created": preexisting_created,
            "deleted": preexisting_deleted,
        },
        "baseline_repo_sha256": repo_sha256,
        "baseline_source_sha256": source_sha256,
        "project_state_sha256": "pending",
        "verification_required": bool(pending_restart and pending_restart.get("requires_verification")),
        "verification_repairs": 0,
        "node_retries": {name: 0 for name in nodes},
        "decisions": [],
        "nodes": nodes,
        "created_at": stamp,
        "updated_at": stamp,
        "events": [{"at": stamp, "event": "run_initialized", "node": "work"}],
    }
    project_sha = commit_initial_state(root, project, expected, new_project, run_dir, state)
    return result(
        "running",
        f"Project Start {mode} готов к одному рабочему проходу.",
        next_actions=[f"{runner_command()} ready --run {shlex.quote(str(run_dir))}"],
        artifacts=[str(run_dir)],
        data={"run": str(run_dir), "mode": mode, "current": "work"},
    )


def load_state(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    if state.get("schema_version") != 3 or state.get("graph_id") != "project-start":
        raise GraphError("Run использует неподдерживаемый контракт.")
    if not supported_graph_identity(state):
        raise GraphError("Run связан с неподдерживаемой версией Project Start graph.")
    root = root_path(state.get("root", ""))
    expected_dir = safe_path(root, RUNTIME_REL / state.get("run_id", ""), expected="dir")
    if expected_dir != run_dir.resolve():
        raise GraphError("Run directory не соответствует root/run_id.")
    receipt = state.get("change_receipt")
    if isinstance(receipt, dict):
        path = safe_path(root, receipt.get("path", ""), expected="file")
        if not path.is_file() or sha256_file(path) != receipt.get("sha256"):
            raise GraphError("Change receipt изменился или исчез.")
        task_state = receipt.get("task_state")
        if task_state:
            task_path = safe_path(root, task_state, expected="file")
            if not task_path.is_file() or sha256_file(task_path) != receipt.get("task_state_sha256"):
                raise GraphError("Task Delivery state изменился или исчез после init.")
    project_file = root / project_runtime.STATE_REL
    if not project_file.is_file():
        raise GraphError(".project-start/state.json исчез.")
    if state.get("status") not in {"completed", "superseded"} and sha256_file(project_file) != state.get("project_state_sha256"):
        raise GraphError(".project-start/state.json изменился конкурентно.")
    return state


def save_state(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    write_json(run_dir / STATE_NAME, state, Path(state["root"]))


def preserve_artifact(run_dir: Path, node: str, attempt: int, source: Path, root: Path) -> tuple[Path, str]:
    digest = sha256_file(source)
    destination = run_dir / "receipts" / f"{node}-{attempt:02d}-{digest[:12]}.json"
    write_text(destination, source.read_text(encoding="utf-8"), root)
    if sha256_file(destination) != digest:
        raise GraphError(f"Не удалось сохранить точную квитанцию {node}.")
    return destination, digest


def ready(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    current = state["current"]
    if state["status"] == "decision-required":
        return result("decision-required", "Нужен только зафиксированный ответ на существенное решение.", data={"decision": state["decisions"][-1]})
    if state["status"] == "blocked":
        return result("blocked", "Run заблокирован; исправь причину и используй retry.")
    if state["status"] == "completed":
        return result("completed", "Project Start run уже завершён.", artifacts=[str(run_dir)])
    if state["status"] != "running":
        return result(state["status"], "Project Start run больше не активен.", artifacts=[str(run_dir)])
    artifact = WORK_NAME if current == "work" else VERIFY_NAME if current == "verify" else None
    actions: list[str] = []
    if artifact:
        actions.append(f"Заполни {run_dir / artifact} по references/control-artifact.md")
        actions.append(f"{runner_command()} record --run {shlex.quote(str(run_dir))} --node {current} --outcome <...>")
    else:
        actions.append(f"{runner_command()} complete --run {shlex.quote(str(run_dir))}")
    data: dict[str, Any] = {"mode": state["mode"], "node": current}
    if current == "work":
        contract = graph_contract()
        data["documentation_contract"] = documentation_contract_for_state(state)
        data["mcp_policy"] = contract["mcp_policy"]
        data["execution_policy"] = contract["execution_policy"]
    return result("ready", f"Готов узел {current}.", next_actions=actions, data=data)


def strings(value: Any, field: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise GraphError(f"{field} должен быть массивом непустых строк.")
    if not allow_empty and not value:
        raise GraphError(f"{field} не должен быть пустым.")
    if len(value) != len(set(value)):
        raise GraphError(f"{field} содержит дубликаты.")
    return value


def validate_mcp_capabilities(capabilities: list[str]) -> None:
    policy = graph_contract()["mcp_policy"]
    prefix = policy["receipt_prefix"]
    fallback_prefix = policy["fallback_prefix"]
    not_applicable_prefix = policy["not_applicable_prefix"]
    receipts = [item for item in capabilities if item.startswith(prefix)]
    if not receipts:
        raise GraphError(
            "capabilities требует MCP receipt: mcp:<server>, mcp:fallback:<reason> "
            "либо mcp:not-applicable:<reason>."
        )
    used: list[str] = []
    fallbacks: list[str] = []
    not_applicable: list[str] = []
    for receipt in receipts:
        if receipt.startswith(not_applicable_prefix):
            reason = receipt[len(not_applicable_prefix) :]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,}", reason):
                raise GraphError(
                    "MCP not-applicable требует содержательный machine-readable reason."
                )
            not_applicable.append(receipt)
            continue
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
    if sum(bool(group) for group in (used, fallbacks, not_applicable)) != 1:
        raise GraphError(
            "MCP receipt должен быть ровно одного типа: used, fallback или not-applicable."
        )


def validate_root_agents(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if re.search(r"(?i)\b(?:PENDING|TODO|TBD)\b|__REQUIRED__", text):
        raise GraphError("Новый AGENTS.md содержит placeholder.")
    for heading in ("Scope|Область", "Map|Карта", "Commands|Команды", "Boundaries|Границы"):
        match = re.search(rf"(?ims)^##\s+(?:{heading})\s*$\n(?P<body>.*?)(?=^##\s+|\Z)", text)
        if not match or len(" ".join(match.group("body").split())) < 8:
            raise GraphError("Новый AGENTS.md требует заполненные Scope, Map, Commands и Boundaries.")
    if not re.search(r"(?im)^##\s+(?:Agent skills|Навыки агентов)\s*$", text):
        raise GraphError("Корневой AGENTS.md требует раздел Agent skills.")
    for required in ("docs/README.md", "docs/agents/domain.md", "docs/agents/issue-tracker.md"):
        if required not in text:
            raise GraphError(f"Корневой AGENTS.md должен направлять к {required}.")


def markdown_mentions(source_relative: str, text: str, target_relative: str) -> bool:
    source_parent = Path(source_relative).parent
    target = Path(target_relative)
    relative = os.path.relpath(target, source_parent).replace(os.sep, "/")
    candidates = {target.as_posix(), relative, f"./{relative}"}
    return any(candidate in text for candidate in candidates)


def validate_documentation_contract(
    root: Path,
    canonical: list[str],
    coverage: dict[str, str],
    contract: dict[str, Any],
) -> None:
    anchors = contract["anchors"]
    if coverage["agent_context"] != anchors["agent_context"]:
        raise GraphError("coverage.agent_context должен ссылаться на корневой AGENTS.md.")
    if coverage["documentation_map"] != anchors["documentation_map"]:
        raise GraphError("coverage.documentation_map должен ссылаться на docs/README.md.")
    if coverage["domain_context"] not in anchors["domain_context"]:
        raise GraphError("coverage.domain_context должен ссылаться на CONTEXT.md или CONTEXT-MAP.md.")
    if coverage["skill_contract"] != anchors["skill_contract"][0]:
        raise GraphError("coverage.skill_contract должен ссылаться на docs/agents/domain.md.")

    canonical_set = set(canonical)
    required_contract_docs = set(anchors["skill_contract"])
    if not required_contract_docs.issubset(canonical_set):
        missing = sorted(required_contract_docs - canonical_set)
        raise GraphError("Skill contract отсутствует в canonical_docs: " + ", ".join(missing))

    map_relative = anchors["documentation_map"]
    map_text = (root / map_relative).read_text(encoding="utf-8")
    targets = set(coverage.values()) | required_contract_docs
    for target in sorted(targets - {map_relative}):
        if not markdown_mentions(map_relative, map_text, target):
            raise GraphError(f"docs/README.md не отображает каноническую роль на {target}.")

    domain_relative = coverage["domain_context"]
    domain_text = (root / domain_relative).read_text(encoding="utf-8")
    if re.search(r"(?i)\b(?:PENDING|TODO|TBD)\b|__REQUIRED__", domain_text):
        raise GraphError(f"{domain_relative} содержит placeholder.")
    if domain_relative == "CONTEXT.md":
        if not re.search(r"(?im)^##\s+(?:Language|Язык)\s*$", domain_text):
            raise GraphError("CONTEXT.md должен содержать раздел Language и оставаться доменным словарём.")
    elif not re.search(r"(?im)^##\s+(?:Contexts|Контексты)\s*$", domain_text) or "CONTEXT.md" not in domain_text:
        raise GraphError("CONTEXT-MAP.md должен перечислять контексты и ссылки на их CONTEXT.md.")


def validate_skill_usage(
    state: dict[str, Any],
    capabilities: list[str],
    coverage: dict[str, str],
    changed_docs: set[str],
    contract: dict[str, Any],
) -> None:
    required: set[str] = set()
    requires_skill_contract_provider = False
    requires_engineering_provider = False
    if state["mode"] == "bootstrap":
        required.update(contract["required_bootstrap_skills"])
        requires_skill_contract_provider = True
        requires_engineering_provider = "engineering_standard" in coverage
    else:
        setup_paths = {"AGENTS.md", "docs/README.md", *contract["anchors"]["skill_contract"]}
        if changed_docs.intersection(setup_paths):
            requires_skill_contract_provider = True
        if coverage["domain_context"] in changed_docs:
            required.add("domain-modeling")
        if changed_docs.intersection({coverage["foundation"], coverage["codebase"]}):
            required.add("codebase-design")
        if (
            "engineering_standard" in coverage
            and coverage["engineering_standard"] in changed_docs
        ):
            requires_engineering_provider = True
    missing = sorted(required - set(capabilities))
    if missing:
        raise GraphError("Не применены обязательные documentation skills: " + ", ".join(missing))
    providers = set(contract["skill_contract_providers"])
    if requires_skill_contract_provider and not providers.intersection(capabilities):
        raise GraphError(
            "Не применён provider skill contract: setup-matt-pocock-skills либо "
            "project-start:skill-contract-fallback."
        )
    engineering_providers = set(contract.get("engineering_standard_providers", []))
    if (
        requires_engineering_provider
        and not engineering_providers.intersection(capabilities)
    ):
        raise GraphError(
            "Не применён provider engineering standard: coding-standards либо "
            "project-start:engineering-standard-fallback."
        )


def validate_work(
    state: dict[str, Any], artifact: dict[str, Any], outcome: str
) -> tuple[dict[str, str], list[str], list[str], dict[str, str]]:
    root = Path(state["root"])
    if source_sha(root) != state.get("baseline_source_sha256"):
        raise GraphError("Исходный код или конфигурация изменились после init; выполни abandon и свежий init.")
    required = {
        "schema_version", "mode", "summary", "classification", "capabilities", "agents",
        "canonical_docs", "changed_docs", "created_docs", "evidence", "coverage",
        "verification", "confidence", "gaps", "decision",
    }
    missing = sorted(required - set(artifact))
    if missing:
        raise GraphError("project.json не содержит поля: " + ", ".join(missing))
    if artifact["schema_version"] != 3 or artifact["mode"] != state["mode"]:
        raise GraphError("project.json использует неверную schema_version или mode.")
    if not isinstance(artifact["summary"], str) or len(artifact["summary"].strip()) < 8:
        raise GraphError("summary слишком краткий.")
    capabilities = strings(artifact["capabilities"], "capabilities")
    agents = strings(artifact["agents"], "agents")
    if len(agents) > graph_contract()["limits"][state["mode"]]["max_parallel_explorers"]:
        raise GraphError("Превышен лимит explorer-агентов.")
    if any(not re.fullmatch(r"explorer(?::[A-Za-z0-9._-]+)?", item) for item in agents):
        raise GraphError("Project Start разрешает только read-only explorer-агентов.")
    canonical = strings(
        artifact["canonical_docs"], "canonical_docs", allow_empty=outcome == "decision"
    )
    declared_changed = strings(artifact["changed_docs"], "changed_docs")
    declared_created = strings(artifact["created_docs"], "created_docs")
    evidence = strings(artifact["evidence"], "evidence", allow_empty=outcome == "decision")
    for relative in canonical + declared_changed + declared_created + evidence:
        path = safe_path(root, relative, expected="file")
        if relative in canonical + evidence and (path.is_symlink() or not path.is_file()):
            raise GraphError(f"Обязательный артефакт отсутствует: {relative}")
    current_docs = discover_docs(root)
    comparison = (
        state.get("operational_docs", {})
        if state["mode"] == "maintenance" and state.get("operational_baseline_known")
        else state["baseline_docs"]
    )
    all_relatives = sorted(set(state["baseline_docs"]) | set(current_docs))
    current = snapshot(root, all_relatives)
    current_agent_docs = {
        path for path in current_docs if path == "AGENTS.md" or path.endswith("/AGENTS.md")
    }
    authority_paths = sorted(set(comparison) | set(canonical) | current_agent_docs)
    current_authority = snapshot(root, authority_paths)
    authority_changed, authority_created, authority_deleted = changed_paths(comparison, current_authority)
    run_changed, run_created, run_deleted = changed_paths(state["baseline_docs"], current)
    actual_changed = sorted(set(authority_changed) | set(run_changed))
    actual_created = sorted(set(authority_created) | set(run_created))
    actual_deleted = sorted(set(authority_deleted) | set(run_deleted))
    if actual_deleted:
        raise GraphError("Project Start не удаляет канонические документы автоматически: " + ", ".join(actual_deleted))
    if declared_created != actual_created or declared_changed != actual_changed:
        raise GraphError(f"Фактическая document delta не совпадает: changed={actual_changed}, created={actual_created}")
    changed_set = set(actual_changed) | set(actual_created)
    if outcome == "decision" and (run_changed or run_created or run_deleted):
        raise GraphError("Существенное решение запрашивается до изменения документов.")
    if not changed_set.issubset(set(canonical)):
        raise GraphError("Все изменённые документы должны входить в canonical_docs.")
    if state["mode"] == "bootstrap" and outcome != "decision":
        discovered_agents = {
            path for path in current_docs if path == "AGENTS.md" or path.endswith("/AGENTS.md")
        }
        if not discovered_agents.issubset(set(canonical)):
            raise GraphError("Bootstrap обязан включить все обнаруженные AGENTS.md в canonical_docs.")
    agents_to_validate = {
        relative
        for relative in canonical
        if relative == "AGENTS.md" or relative.endswith("/AGENTS.md")
    }
    for relative in sorted(agents_to_validate):
        if relative.endswith("/AGENTS.md") or relative == "AGENTS.md":
            if relative == "AGENTS.md":
                validate_root_agents(root / relative)
            else:
                try:
                    legacy_maintenance.validate_new_agent_doc_path(root, relative, must_exist=True)
                except legacy_maintenance.MaintenanceError as exc:
                    raise GraphError(str(exc)) from exc
    classification = artifact["classification"]
    coverage = artifact["coverage"]
    if outcome == "decision":
        if coverage not in ({}, None):
            raise GraphError("Decision до правок использует пустой coverage.")
    if state["mode"] == "bootstrap":
        if classification != "bootstrap-ready":
            raise GraphError("Bootstrap требует classification=bootstrap-ready.")
    else:
        inherited = set(state.get("baseline_canonical", []))
        if not inherited.issubset(set(canonical)):
            raise GraphError("Maintenance не может молча исключить ранее канонический документ.")
        if classification not in {"no-change", "factual", "semantic"}:
            raise GraphError("Maintenance classification должен быть no-change, factual или semantic.")
        if classification == "no-change" and changed_set:
            raise GraphError("no-change не может содержать document delta.")
        if classification in {"factual", "semantic"} and not changed_set and outcome != "decision":
            raise GraphError(f"{classification} требует фактическую document delta.")
        if classification == "semantic":
            decision = artifact["decision"]
            if outcome == "decision":
                if not isinstance(decision, dict):
                    raise GraphError("Существенное решение требует decision payload.")
            else:
                resolved = state["decisions"][-1] if state["decisions"] else None
                if not isinstance(decision, dict) or not resolved or decision.get("id") != resolved.get("id") or not resolved.get("answer"):
                    raise GraphError("Semantic update должен ссылаться на resolved decision id.")
    decision = artifact["decision"]
    if outcome == "decision":
        if state["decisions"]:
            raise GraphError("Один run поддерживает одно объединённое существенное решение.")
        if not isinstance(decision, dict) or not all(
            isinstance(decision.get(key), str) and decision[key].strip()
            for key in ("question", "recommended")
        ):
            raise GraphError("decision требует question и recommended.")
        scope = strings(decision.get("scope"), "decision.scope", allow_empty=False)
        for relative in scope:
            if Path(relative).is_absolute() or any(part in IGNORED_DIRS for part in Path(relative).parts):
                raise GraphError(f"decision.scope содержит недопустимый путь: {relative}")
            safe_path(root, relative, expected="file")
    elif state["decisions"]:
        resolved = state["decisions"][-1]
        if not isinstance(decision, dict) or decision.get("id") != resolved.get("id") or not resolved.get("answer"):
            raise GraphError("Итоговая работа должна ссылаться на resolved decision id.")
        decision_before = resolved.get("docs") if isinstance(resolved.get("docs"), dict) else {}
        after_keys = sorted(set(decision_before) | set(current))
        after = snapshot(root, after_keys)
        post_decision_delta = {
            relative
            for relative in after_keys
            if decision_before.get(relative, "missing") != after.get(relative, "missing")
        }
        if not post_decision_delta.issubset(set(resolved.get("scope", []))):
            raise GraphError("Document delta после ответа выходит за пределы resolved decision scope.")
        if not changed_set.issubset(set(resolved.get("scope", []))):
            raise GraphError("Полная document delta выходит за пределы resolved decision scope.")
    if outcome != "decision":
        contract = documentation_contract_for_state(state)
        expected_coverage = set(contract["coverage"])
        if not isinstance(coverage, dict) or set(coverage) != expected_coverage:
            raise GraphError(
                "Project Start coverage должен закрыть business/documentation_map/domain_context/"
                "foundation/engineering_standard/codebase/quality/plan/agent_context/"
                "skill_contract для текущей версии graph."
            )
        for key, relative in coverage.items():
            if not isinstance(relative, str) or relative not in canonical:
                raise GraphError(f"coverage.{key} должен ссылаться на canonical_docs.")
        validate_documentation_contract(root, canonical, coverage, contract)
        validate_skill_usage(state, capabilities, coverage, changed_set, contract)
    validate_mcp_capabilities(capabilities)
    if artifact["verification"] not in {"self", "independent"}:
        raise GraphError("verification должен быть self или independent.")
    if outcome == "verify" and artifact["verification"] != "independent":
        raise GraphError("Outcome verify требует independent verification.")
    if outcome == "succeeded" and artifact["verification"] != "self":
        raise GraphError("Outcome succeeded требует self verification.")
    if outcome == "decision" and artifact["decision"] is None:
        raise GraphError("Outcome decision требует decision payload.")
    if artifact["confidence"] not in {"high", "medium", "low"}:
        raise GraphError("confidence должен быть high, medium или low.")
    gaps = strings(artifact["gaps"], "gaps")
    if artifact["confidence"] == "low" and not gaps:
        raise GraphError("Low confidence требует явные gaps.")
    if outcome != "decision" and (
        artifact["confidence"] == "low"
        or (state["mode"] == "maintenance" and classification == "semantic")
        or bool(state["decisions"])
        or bool(state.get("preexisting_drift", {}).get("changed"))
        or bool(state.get("preexisting_drift", {}).get("created"))
        or bool(state.get("preexisting_drift", {}).get("deleted"))
        or (state["mode"] == "maintenance" and not state.get("operational_baseline_known"))
    ) and outcome != "verify":
        raise GraphError("Semantic или low-confidence результат требует independent verify.")
    return snapshot(root, canonical), canonical, capabilities, current


def validate_verification(state: dict[str, Any], artifact: dict[str, Any], outcome: str) -> None:
    if artifact.get("schema_version") != 3 or artifact.get("verdict") not in {"pass", "reject"}:
        raise GraphError("verification.json требует schema_version 3 и verdict pass|reject.")
    work_receipt = state["nodes"]["work"]["receipts"][-1]
    if artifact.get("work_sha256") != work_receipt["sha256"]:
        raise GraphError("Verifier проверил не текущий project.json.")
    checked = strings(artifact.get("checked_docs"), "checked_docs")
    if checked != work_receipt["canonical_docs"]:
        raise GraphError("Verifier обязан проверить точный canonical_docs set.")
    root = Path(state["root"])
    current = snapshot(root, checked)
    if artifact.get("docs_sha256") != snapshot_digest(current) or current != work_receipt["docs"]:
        raise GraphError("Документы изменились после work или verifier указал неверный digest.")
    strings(artifact.get("residual_risks"), "residual_risks")
    repairs = strings(artifact.get("repair_list"), "repair_list")
    if outcome == "succeeded" and artifact["verdict"] != "pass":
        raise GraphError("Verifier outcome succeeded требует verdict=pass.")
    if outcome == "failed" and (artifact["verdict"] != "reject" or not repairs):
        raise GraphError("Rejected verification требует непустой repair_list.")


def record(run_dir: Path, node: str, outcome: str) -> dict[str, Any]:
    if node not in {"work", "verify"} or outcome not in {"succeeded", "verify", "decision", "failed"}:
        raise GraphError("Некорректные node/outcome.")
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] != "running" or state["current"] != node or state["nodes"][node]["status"] != "ready":
            raise GraphError(f"Узел {node} сейчас не готов.")
        if node == "work" and outcome == "failed":
            state["nodes"][node]["attempts"] += 1
            state["status"] = "blocked"
            state["nodes"][node]["status"] = "failed"
            mark_project_status(state, "blocked", node=node)
            state["events"].append({"at": now(), "event": "node_failed", "node": node})
            save_state(run_dir, state)
            return result("blocked", "Work остановлен; retry доступен один раз.")
        artifact_path = run_dir / (WORK_NAME if node == "work" else VERIFY_NAME)
        artifact = load_json(artifact_path)
        if node == "work":
            if outcome not in {"succeeded", "verify", "decision"}:
                raise GraphError("Work outcome должен быть succeeded, verify, decision или failed.")
            if state["verification_required"] and outcome == "succeeded":
                raise GraphError("После verifier reject исправленная работа обязана снова пройти independent verify.")
            docs, canonical, capabilities, observed_docs = validate_work(state, artifact, outcome)
            attempt = state["nodes"][node]["attempts"] + 1
            preserved, artifact_sha = preserve_artifact(run_dir, node, attempt, artifact_path, Path(state["root"]))
            receipt = {
                "path": str(preserved),
                "source_path": str(artifact_path),
                "sha256": artifact_sha,
                "docs": docs,
                "docs_sha256": snapshot_digest(docs),
                "observed_docs": observed_docs,
                "canonical_docs": canonical,
                "capabilities": capabilities,
                "agents": artifact["agents"],
                "classification": artifact["classification"],
                "coverage": artifact["coverage"],
                "outcome": outcome,
                "at": now(),
            }
            state["nodes"][node]["attempts"] += 1
            state["nodes"][node]["receipts"].append(receipt)
            state["nodes"][node]["status"] = "completed"
            if outcome == "decision":
                decision = dict(artifact["decision"])
                decision["id"] = hashlib.sha256((receipt["sha256"] + decision["question"]).encode("utf-8")).hexdigest()[:12]
                decision["docs"] = observed_docs
                decision["requested_at"] = now()
                state["decisions"].append(decision)
                state["status"] = "decision-required"
                mark_project_status(state, "reopen-required", pending=decision)
            elif outcome == "verify":
                state["verification_required"] = True
                state["current"] = "verify"
                state["nodes"]["verify"]["status"] = "ready"
                mark_project_status(state, "running", node="verify")
            else:
                state["current"] = "complete"
                state["nodes"]["complete"]["status"] = "ready"
                mark_project_status(state, "running", node="complete")
        else:
            if outcome not in {"succeeded", "failed"}:
                raise GraphError("Verify outcome должен быть succeeded или failed.")
            validate_verification(state, artifact, outcome)
            attempt = state["nodes"][node]["attempts"] + 1
            preserved, artifact_sha = preserve_artifact(run_dir, node, attempt, artifact_path, Path(state["root"]))
            receipt = {
                "path": str(preserved),
                "source_path": str(artifact_path),
                "sha256": artifact_sha,
                "work_sha256": state["nodes"]["work"]["receipts"][-1]["sha256"],
                "outcome": outcome,
                "at": now(),
            }
            state["nodes"][node]["attempts"] += 1
            state["nodes"][node]["receipts"].append(receipt)
            if outcome == "succeeded":
                state["nodes"][node]["status"] = "completed"
                state["current"] = "complete"
                state["nodes"]["complete"]["status"] = "ready"
                mark_project_status(state, "running", node="complete")
            else:
                state["verification_repairs"] += 1
                if state["verification_repairs"] > graph_contract()["limits"]["max_verification_repairs"]:
                    state["status"] = "blocked"
                    state["nodes"][node]["status"] = "failed"
                    mark_project_status(state, "blocked", node="verify")
                else:
                    state["nodes"][node]["status"] = "pending"
                    state["nodes"]["work"]["status"] = "ready"
                    state["current"] = "work"
                    mark_project_status(state, "running", node="work")
        state["events"].append({"at": now(), "event": f"{node}_{outcome}", "node": node})
        save_state(run_dir, state)
    return ready(run_dir)


def mark_project_status(state: dict[str, Any], status: str, *, node: str | None = None, pending: dict[str, Any] | None = None) -> None:
    root = Path(state["root"])
    project = project_state(root)
    if project is None:
        raise GraphError("Project Start state исчез.")
    expected = state["project_state_sha256"]
    project.pop("_loaded_state_sha256", None)
    maintenance = project.setdefault("maintenance", {"history": []})
    maintenance["status"] = status
    active = maintenance.setdefault("active_run", {})
    active.update({"run_id": state["run_id"], "run_dir": str(root / RUNTIME_REL / state["run_id"]), "mode": state["mode"], "node": node or state["current"], "updated_at": now()})
    if pending is not None:
        maintenance["pending_reopen"] = {"run_id": state["run_id"], "decision_id": pending["id"], "stage": "documentation", "rationale": pending["question"], "recommended": pending["recommended"]}
    elif status != "reopen-required":
        maintenance.pop("pending_reopen", None)
    project["updated_at"] = now()
    state["project_state_sha256"] = save_project(root, project, expected)


def decide(run_dir: Path, answer: str) -> dict[str, Any]:
    if not answer.strip():
        raise GraphError("Ответ на решение не должен быть пустым.")
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] != "decision-required" or not state["decisions"]:
            raise GraphError("Run не ожидает решения.")
        decision = state["decisions"][-1]
        decision["answer"] = answer.strip()
        decision["resolved_at"] = now()
        state["status"] = "running"
        state["current"] = "work"
        state["nodes"]["work"]["status"] = "ready"
        mark_project_status(state, "running", node="work")
        state["events"].append({"at": now(), "event": "decision_resolved", "decision_id": decision["id"]})
        save_state(run_dir, state)
    return ready(run_dir)


def retry(run_dir: Path, node: str) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] != "blocked" or state["nodes"].get(node, {}).get("status") != "failed":
            raise GraphError("Указанный узел не находится в failed состоянии.")
        limit = graph_contract()["limits"]["max_node_retries"]
        if node == "verify" and state["verification_repairs"] > graph_contract()["limits"]["max_verification_repairs"]:
            raise GraphError("Verification repair limit исчерпан; требуется новый запуск или решение человека.")
        if state["node_retries"][node] >= limit:
            raise GraphError(f"Retry limit исчерпан для {node}.")
        state["node_retries"][node] += 1
        state["status"] = "running"
        state["current"] = node
        state["nodes"][node]["status"] = "ready"
        mark_project_status(state, "running", node=node)
        state["events"].append({"at": now(), "event": "node_retried", "node": node})
        save_state(run_dir, state)
    return ready(run_dir)


def abandon(run_dir: Path, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise GraphError("Причина abandon не должна быть пустой.")
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] == "completed":
            raise GraphError("Завершённый run нельзя abandon.")
        if state["status"] == "superseded":
            return result("superseded", "Run уже закрыт как superseded.", artifacts=[str(run_dir)])
        if state["status"] == "decision-required":
            raise GraphError("Нельзя abandon незакрытое существенное решение; сначала выполни decide.")
        root = Path(state["root"])
        project = project_state(root)
        if project is None:
            raise GraphError("Project Start state исчез.")
        expected = state["project_state_sha256"]
        project.pop("_loaded_state_sha256", None)
        maintenance = project.setdefault("maintenance", {"history": []})
        active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
        if active.get("run_id") != state["run_id"]:
            raise GraphError("Run больше не владеет Project Start state.")
        obligation = state.get("consumed_obligation")
        current_relatives = sorted(set(state["baseline_docs"]) | set(discover_docs(root)))
        current_docs = snapshot(root, current_relatives)
        baseline_docs = state["baseline_docs"]
        drifted_docs = sorted(
            relative
            for relative in set(current_docs) | set(baseline_docs)
            if current_docs.get(relative, "missing") != baseline_docs.get(relative, "missing")
        )
        if isinstance(obligation, dict):
            maintenance["status"] = "maintenance-required"
            maintenance["maintenance_required"] = obligation
        else:
            maintenance["status"] = (
                "not-ready"
                if state["mode"] == "bootstrap" and project.get("phase") not in {"execution", "complete"}
                else "restart-required"
            )
            maintenance.pop("maintenance_required", None)
            maintenance["pending_restart"] = {
                "run_id": state["run_id"],
                "reason": reason.strip(),
                "requires_verification": bool(state.get("verification_required")),
                "created_at": now(),
            }
            if not drifted_docs:
                maintenance.pop("pending_drift", None)
        if state.get("verification_required"):
            maintenance["pending_restart"] = {
                "run_id": state["run_id"],
                "reason": reason.strip(),
                "requires_verification": True,
                "created_at": now(),
            }
        if drifted_docs:
            maintenance["pending_drift"] = {
                "run_id": state["run_id"],
                "reason": reason.strip(),
                "changed_docs": drifted_docs,
                "baseline": {
                    relative: baseline_docs.get(relative, "missing") for relative in drifted_docs
                },
                "created_at": now(),
            }
        maintenance.pop("active_run", None)
        maintenance.pop("pending_reopen", None)
        stamp = now()
        graph_v3 = project.setdefault("graph_v3", {})
        graph_v3["restart_nonce"] = hashlib.sha256(
            f"{state['run_id']}:{stamp}:{reason.strip()}".encode("utf-8")
        ).hexdigest()[:16]
        maintenance.setdefault("history", []).append({"at": stamp, "event": "project-graph-superseded", "run_id": state["run_id"], "reason": reason.strip()})
        project["updated_at"] = stamp
        state["project_state_sha256"] = save_project(root, project, expected)
        state["status"] = "superseded"
        state["events"].append({"at": stamp, "event": "run_superseded", "reason": reason.strip()})
        save_state(run_dir, state)
    return result("superseded", "Run безопасно закрыт; теперь можно выполнить свежий init.", artifacts=[str(run_dir)])


def check_integrity(state: dict[str, Any]) -> None:
    root = Path(state["root"])
    if source_sha(root) != state.get("baseline_source_sha256"):
        raise GraphError("Исходный код или конфигурация изменились после work receipt.")
    work_receipts = state["nodes"]["work"]["receipts"]
    if work_receipts:
        receipt = work_receipts[-1]
        path = Path(receipt["path"])
        if not path.is_file() or sha256_file(path) != receipt["sha256"]:
            raise GraphError("Квитанция project.json изменилась после record.")
        source = Path(receipt.get("source_path", ""))
        if not source.is_file() or sha256_file(source) != receipt["sha256"]:
            raise GraphError("project.json изменился после record.")
        if snapshot(root, receipt["canonical_docs"]) != receipt["docs"]:
            raise GraphError("Канонические документы изменились после record.")
        observed = receipt.get("observed_docs") if isinstance(receipt.get("observed_docs"), dict) else {}
        current_relatives = sorted(set(observed) | set(discover_docs(root)))
        if snapshot(root, current_relatives) != observed:
            raise GraphError("Набор или содержимое документов изменились после work receipt.")
    if state["verification_required"]:
        if state["nodes"]["verify"]["status"] != "completed":
            raise GraphError("Обязательная independent verification не завершена.")
        if not work_receipts or work_receipts[-1].get("outcome") != "verify":
            raise GraphError("Последняя исправленная работа не была направлена на independent verify.")
        receipt = state["nodes"]["verify"]["receipts"][-1]
        if receipt.get("outcome") != "succeeded" or receipt.get("work_sha256") != work_receipts[-1]["sha256"]:
            raise GraphError("Verifier PASS не связан с последней work receipt.")
        path = Path(receipt["path"])
        if not path.is_file() or sha256_file(path) != receipt["sha256"]:
            raise GraphError("Квитанция verification.json изменилась после record.")
        source = Path(receipt.get("source_path", ""))
        if not source.is_file() or sha256_file(source) != receipt["sha256"]:
            raise GraphError("verification.json изменился после record.")


def check_historical_receipts(state: dict[str, Any]) -> None:
    for node in ("work", "verify"):
        for receipt in state["nodes"][node]["receipts"]:
            path = Path(receipt["path"])
            if not path.is_file() or sha256_file(path) != receipt["sha256"]:
                raise GraphError(f"Историческая квитанция {node} повреждена.")


def raw_run_state(root: Path, run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    if state.get("schema_version") != 3 or state.get("graph_id") != "project-start":
        raise GraphError(f"Recover обнаружил неподдерживаемый run: {run_dir}")
    if state.get("root") != str(root) or state.get("run_id") != run_dir.name:
        raise GraphError(f"Recover отклонил run с неверной identity: {run_dir}")
    if not supported_graph_identity(state):
        raise GraphError("Recover не мигрирует неподдерживаемый run автоматически.")
    return state


def recovery_nonce(run_id: str, reason: str) -> str:
    return hashlib.sha256(f"{run_id}:{reason}:{now()}".encode("utf-8")).hexdigest()[:16]


def recover(root_raw: str) -> dict[str, Any]:
    """Reconcile a crash between shared project-state and per-run state writes."""
    root = root_path(root_raw)
    project = project_state(root)
    if project is None:
        return result("clean", "Project Start state ещё не создан; восстанавливать нечего.")
    expected = project.pop("_loaded_state_sha256", None)
    maintenance = project.setdefault("maintenance", {"history": []})
    active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else None
    if active is not None:
        run_id = active.get("run_id")
        run_dir_raw = active.get("run_dir")
        if not isinstance(run_id, str) or not isinstance(run_dir_raw, str):
            raise GraphError("Active Project Start run повреждён; автоматический recover небезопасен.")
        run_dir = safe_path(root, run_dir_raw, expected="dir")
        expected_run_dir = safe_path(root, RUNTIME_REL / run_id, expected="dir")
        if run_dir != expected_run_dir or not run_dir.is_dir():
            raise GraphError("Active Project Start run указывает на неверный каталог.")
        state_path = run_dir / STATE_NAME
        if not state_path.is_file():
            with state_lock(run_dir):
                try:
                    with project_runtime.project_state_lock(root):
                        if state_path.is_file():
                            return result(
                                "clean",
                                "Инициализация завершилась конкурентно; run согласован.",
                                artifacts=[str(run_dir)],
                            )
                        latest = project_runtime.load_state(root)
                        latest.pop("_loaded_state_sha256", None)
                        latest_maintenance = latest.setdefault("maintenance", {"history": []})
                        latest_active = (
                            latest_maintenance.get("active_run")
                            if isinstance(latest_maintenance.get("active_run"), dict)
                            else {}
                        )
                        if latest_active.get("run_id") != run_id:
                            raise GraphError("Active run сменился во время recover; повтори проверку.")
                        obligation = latest_active.get("consumed_obligation")
                        if isinstance(obligation, dict):
                            latest_maintenance["status"] = "maintenance-required"
                            latest_maintenance["maintenance_required"] = obligation
                            if latest_active.get("requires_verification"):
                                latest_maintenance["pending_restart"] = {
                                    "run_id": run_id,
                                    "reason": "Interrupted verification-required initialization",
                                    "requires_verification": True,
                                    "created_at": now(),
                                }
                        else:
                            latest_maintenance["status"] = (
                                "not-ready"
                                if latest_active.get("mode") == "bootstrap"
                                and latest.get("phase") not in {"execution", "complete"}
                                else "restart-required"
                            )
                            latest_maintenance["pending_restart"] = {
                                "run_id": run_id,
                                "reason": "Interrupted initialization",
                                "requires_verification": bool(latest_active.get("requires_verification")),
                                "created_at": now(),
                            }
                        latest_maintenance.pop("active_run", None)
                        latest_maintenance.pop("pending_reopen", None)
                        latest.setdefault("graph_v3", {})["restart_nonce"] = recovery_nonce(
                            run_id, "missing-run-state"
                        )
                        stamp = now()
                        latest_maintenance.setdefault("history", []).append(
                            {
                                "at": stamp,
                                "event": "project-graph-recovered",
                                "run_id": run_id,
                                "action": "released-uninitialized",
                            }
                        )
                        latest["updated_at"] = stamp
                        project_runtime.write_json_atomic(root, root / project_runtime.STATE_REL, latest)
                except ValueError as exc:
                    raise GraphError(str(exc)) from exc
            return result("recovered", "Незавершённая активация снята; можно выполнить свежий init.")
        with state_lock(run_dir):
            state = raw_run_state(root, run_dir)
            current_project_sha = sha256_file(root / project_runtime.STATE_REL)
            if state.get("project_state_sha256") == current_project_sha:
                return result(
                    "clean",
                    "Active run согласован; восстановление не требуется.",
                    artifacts=[str(run_dir)],
                )
            status = state.get("status")
            if status not in {"running", "blocked", "decision-required"}:
                raise GraphError("Active run имеет неоднозначный статус; автоматический recover остановлен.")
            if status == "decision-required":
                maintenance["status"] = "reopen-required"
                decision = state["decisions"][-1] if state.get("decisions") else None
                if not isinstance(decision, dict):
                    raise GraphError("Decision-required run не содержит решения.")
                maintenance["pending_reopen"] = {
                    "run_id": run_id,
                    "decision_id": decision.get("id"),
                    "stage": "documentation",
                    "rationale": decision.get("question"),
                    "recommended": decision.get("recommended"),
                }
            else:
                maintenance["status"] = status
                maintenance.pop("pending_reopen", None)
            active.update({"node": state.get("current"), "updated_at": now()})
            project["updated_at"] = now()
            project_sha = save_project(root, project, expected)
            state["project_state_sha256"] = project_sha
            state.setdefault("events", []).append(
                {"at": now(), "event": "run_recovered", "action": "rolled-back-shared-transition"}
            )
            save_state(run_dir, state)
        return result(
            "recovered",
            "Shared state возвращён к последней целой run-квитанции.",
            artifacts=[str(run_dir)],
        )

    runtime_root = safe_path(root, RUNTIME_REL, expected="dir")
    if runtime_root.is_dir():
        history = maintenance.get("history") if isinstance(maintenance.get("history"), list) else []
        superseded_ids = {
            item.get("run_id")
            for item in history
            if isinstance(item, dict) and item.get("event") == "project-graph-superseded"
        }
        last_run = (
            project.get("graph_v3", {}).get("last_run")
            if isinstance(project.get("graph_v3"), dict)
            else None
        )
        candidates: list[tuple[Path, str]] = []
        for run_dir in sorted(runtime_root.iterdir()):
            if not run_dir.is_dir() or not (run_dir / STATE_NAME).is_file():
                continue
            state = raw_run_state(root, run_dir)
            if state.get("status") in {"completed", "superseded"}:
                continue
            if state.get("run_id") == last_run and state.get("current") == "complete":
                candidates.append((run_dir, "completed"))
            elif state.get("run_id") in superseded_ids:
                candidates.append((run_dir, "superseded"))
        if len(candidates) > 1:
            raise GraphError("Recover нашёл несколько неоднозначных незавершённых run.")
        if candidates:
            run_dir, terminal = candidates[0]
            with state_lock(run_dir):
                state = raw_run_state(root, run_dir)
                if terminal == "completed":
                    check_historical_receipts(state)
                    work = state["nodes"]["work"]["receipts"][-1]
                    graph_v3 = project.get("graph_v3") if isinstance(project.get("graph_v3"), dict) else {}
                    if (
                        graph_v3.get("last_run") != state["run_id"]
                        or graph_v3.get("canonical_doc_hashes") != work.get("docs")
                        or graph_v3.get("docs_sha256") != work.get("docs_sha256")
                    ):
                        raise GraphError("Shared completion marker не совпадает с immutable work receipt.")
                    if state.get("verification_required"):
                        verifies = state["nodes"]["verify"]["receipts"]
                        if not verifies or verifies[-1].get("outcome") != "succeeded" or verifies[-1].get("work_sha256") != work.get("sha256"):
                            raise GraphError("Shared completion не имеет связанной verifier PASS receipt.")
                    state["nodes"]["complete"]["status"] = "completed"
                state["status"] = terminal
                state["project_state_sha256"] = sha256_file(root / project_runtime.STATE_REL)
                state.setdefault("events", []).append(
                    {"at": now(), "event": "run_recovered", "action": f"finalized-{terminal}"}
                )
                save_state(run_dir, state)
            return result(
                "recovered",
                f"Run-квитанция доведена до durable terminal status: {terminal}.",
                artifacts=[str(run_dir)],
            )
    return result("clean", "Несогласованных Project Start транзакций не найдено.")


def complete(run_dir: Path) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] == "completed":
            return result("completed", "Project Start run уже завершён.", artifacts=[str(run_dir)])
        if state["status"] != "running" or state["current"] != "complete" or state["nodes"]["complete"]["status"] != "ready":
            raise GraphError("Complete ещё не готов.")
        check_integrity(state)
        work = state["nodes"]["work"]["receipts"][-1]
        root = Path(state["root"])
        project = project_state(root)
        if project is None:
            raise GraphError("Project Start state исчез.")
        expected = state["project_state_sha256"]
        project.pop("_loaded_state_sha256", None)
        stamp = now()
        if state["mode"] == "bootstrap":
            project["phase"] = "execution"
        project["graph_version"] = state["graph_version"]
        project["graph_sha256"] = state["graph_sha256"]
        previous_graph_v3 = project.get("graph_v3") if isinstance(project.get("graph_v3"), dict) else {}
        project["graph_v3"] = {
            "status": "operational",
            "last_run": state["run_id"],
            "mode": state["mode"],
            "canonical_docs": work["canonical_docs"],
            "coverage": work["coverage"],
            "docs_sha256": work["docs_sha256"],
            "canonical_doc_hashes": work["docs"],
            "observed_doc_hashes": work["observed_docs"],
            "agent_instruction_doc_hashes": {
                path: digest
                for path, digest in work["observed_docs"].items()
                if path == "AGENTS.md" or path.endswith("/AGENTS.md")
            },
            "restart_nonce": str(previous_graph_v3.get("restart_nonce", "")),
            "updated_at": stamp,
        }
        maintenance = project.setdefault("maintenance", {"history": []})
        maintenance["status"] = "operational"
        maintenance["canonical_docs"] = work["canonical_docs"]
        maintenance["agent_instruction_docs"] = [path for path in work["canonical_docs"] if path == "AGENTS.md" or path.endswith("/AGENTS.md")]
        obligation = state.get("consumed_obligation")
        if isinstance(obligation, dict):
            processed = maintenance.setdefault("processed_handoffs", [])
            entry = {
                "task_id": obligation.get("task_id"),
                "handoff_path": obligation.get("handoff_path"),
                "handoff_sha256": obligation.get("handoff_sha256"),
                "task_state_path": obligation.get("task_state_path"),
                "task_state_sha256": obligation.get("task_state_sha256"),
                "run_id": state["run_id"],
                "processed_at": stamp,
            }
            if not any(
                isinstance(item, dict)
                and item.get("task_id") == entry["task_id"]
                and item.get("handoff_sha256") == entry["handoff_sha256"]
                and item.get("task_state_sha256") == entry["task_state_sha256"]
                for item in processed
            ):
                processed.append(entry)
        maintenance.pop("active_run", None)
        maintenance.pop("pending_reopen", None)
        maintenance.pop("maintenance_required", None)
        maintenance.pop("pending_drift", None)
        maintenance.pop("pending_restart", None)
        history = maintenance.setdefault("history", [])
        history.append({"at": stamp, "event": "project-graph-completed", "run_id": state["run_id"], "mode": state["mode"], "classification": work["classification"]})
        project.setdefault("history", []).append({"at": stamp, "event": "project-graph-completed", "phase": project["phase"], "run_id": state["run_id"], "mode": state["mode"]})
        project["updated_at"] = stamp
        state["project_state_sha256"] = save_project(root, project, expected)
        state["status"] = "completed"
        state["nodes"]["complete"]["status"] = "completed"
        state["events"].append({"at": stamp, "event": "run_completed", "node": "complete"})
        save_state(run_dir, state)
    return result("completed", "Project Start завершён; документация и состояние связаны точными digest.", artifacts=[str(run_dir), str(Path(state["root"]) / project_runtime.STATE_REL)], data={"mode": state["mode"], "canonical_docs": work["canonical_docs"]})


def status(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    if state["status"] in {"completed", "superseded"}:
        check_historical_receipts(state)
    return result(state["status"], f"Project Start {state['mode']}: {state['current']}.", artifacts=[str(run_dir)], data={"current": state["current"], "mode": state["mode"], "retries": state["node_retries"], "verification_repairs": state["verification_repairs"]})


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--mode", choices=("auto", "bootstrap", "maintenance"), default="auto")
    init.add_argument("--reason", required=True)
    init.add_argument("--trigger", choices=("manual", "task-delivery", "drift", "scheduled"), default="manual")
    init.add_argument("--change-receipt")
    init.add_argument("--cycle", help="Ключ scheduled-прохода; по умолчанию UTC-день")
    for name in ("ready", "status", "complete"):
        item = sub.add_parser(name)
        item.add_argument("--run", required=True)
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
    abandon_parser = sub.add_parser("abandon")
    abandon_parser.add_argument("--run", required=True)
    abandon_parser.add_argument("--reason", required=True)
    recover_parser = sub.add_parser("recover")
    recover_parser.add_argument("--root", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            payload = initialize(args.root, args.mode, args.reason, args.trigger, args.change_receipt, args.cycle)
        elif args.command == "recover":
            payload = recover(args.root)
        else:
            run_dir = run_path(args.run)
            if args.command == "ready":
                payload = ready(run_dir)
            elif args.command == "status":
                payload = status(run_dir)
            elif args.command == "record":
                payload = record(run_dir, args.node, args.outcome)
            elif args.command == "decide":
                payload = decide(run_dir, args.answer)
            elif args.command == "retry":
                payload = retry(run_dir, args.node)
            elif args.command == "abandon":
                payload = abandon(run_dir, args.reason)
            else:
                payload = complete(run_dir)
    except (GraphError, OSError) as exc:
        payload = result("error", str(exc))
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
