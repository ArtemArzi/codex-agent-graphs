#!/usr/bin/env python3
"""Legacy v2 runtime kept only for already active Project Start maintenance runs."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
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
import project_start as project_start_runtime  # noqa: E402

GRAPH_PATH = SKILL_DIR / "assets" / "legacy-graph-v2.json"
LEGACY_GRAPH_SHA256 = "b30d1ef1fe6c7871f127cd02ab4bfde87f6806e53c4b195b64789730e0b87dd6"
BUNDLED_LEGACY_GRAPH_SHA256 = "24007098f6ccd59a9dabf84b3ca06314214b7931193042eb95aba128379f10d1"
PROJECT_STATE_REL = Path(".project-start/state.json")
RUNTIME_REL = Path(".agent-graphs/project-start-maintenance")
STATE_NAME = "state.json"
LOCK_NAME = ".state.lock"
ALLOWED_PROJECT_PHASES = {"execution", "complete"}
EXCLUDED_ARTIFACT_KEYS = {"adr_dir"}
PROTECTED_ARTIFACT_KEYS = {"verification"}
IGNORED_CONTEXT_DIRS = {
    ".agent-graphs",
    ".codex",
    ".git",
    ".project-start",
    ".venv",
    "build",
    "dist",
    "generated",
    "node_modules",
    "vendor",
}


class MaintenanceError(RuntimeError):
    """A safe, user-actionable maintenance-graph error."""


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
        raise MaintenanceError(f"Файл не найден: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MaintenanceError(f"Некорректный JSON в {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MaintenanceError(f"Ожидался JSON-объект: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_within(path: Path, root: Path, label: str) -> Path:
    root = root.resolve()
    lexical = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise MaintenanceError(f"{label} выходит за пределы {root}: {lexical}") from exc
    current = root
    if current.is_symlink():
        raise MaintenanceError(f"Корень не должен быть символической ссылкой: {current}")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise MaintenanceError(f"Символическая ссылка запрещена в {label}: {current}")
    resolved = lexical.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise MaintenanceError(f"{label} проходит через ссылку за пределы {root}: {lexical}") from exc
    return lexical


def repository_entry(path: Path, root: Path) -> Path:
    """Validate containment while allowing the final component itself to be a symlink."""
    root = root.resolve()
    lexical = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise MaintenanceError(f"Repository input выходит за пределы {root}: {lexical}") from exc
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise MaintenanceError(f"Символическая ссылка запрещена в родительском пути: {current}")
    if not lexical.is_symlink():
        ensure_within(lexical, root, "Repository input")
    return lexical


def graph_contract() -> dict[str, Any]:
    if sha256_file(GRAPH_PATH) != BUNDLED_LEGACY_GRAPH_SHA256:
        raise MaintenanceError("Bundled legacy graph v2 изменился; безопасное возобновление запрещено.")
    graph = load_json(GRAPH_PATH)
    if graph.get("graph_id") != "project-start":
        raise MaintenanceError("graph.json принадлежит другому графу.")
    routes = graph.get("routes")
    if not isinstance(routes, dict) or not isinstance(routes.get("maintenance"), dict):
        raise MaintenanceError("graph.json не содержит maintenance route.")
    route = routes["maintenance"]
    nodes = route.get("nodes")
    if not isinstance(nodes, dict) or route.get("entry") not in nodes or route.get("terminal") not in nodes:
        raise MaintenanceError("Некорректные entry/terminal maintenance route.")
    registry = graph.get("capability_registry")
    if not isinstance(registry, dict) or not isinstance(registry.get("skills"), list):
        raise MaintenanceError("graph.json не содержит capability registry.")
    return graph


def maintenance_route() -> dict[str, Any]:
    return graph_contract()["routes"]["maintenance"]


def repository(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise MaintenanceError(f"Репозиторий не существует: {root}")
    return root


def project_state(root: Path) -> dict[str, Any]:
    path = ensure_within(root / PROJECT_STATE_REL, root, "Project Start state")
    state = load_json(path)
    if state.get("schema_version") != 2:
        raise MaintenanceError("Поддержка документации требует Project Start state schema_version 2.")
    if state.get("phase") not in ALLOWED_PROJECT_PHASES:
        raise MaintenanceError(
            "Поддержка документации доступна в execution/complete; текущая фаза: "
            f"{state.get('phase')}"
        )
    if not isinstance(state.get("artifacts"), dict):
        raise MaintenanceError("Project Start state не содержит artifacts.")
    return state


def canonical_docs(root: Path, state: dict[str, Any]) -> list[Path]:
    docs: list[Path] = []
    for key, raw in state["artifacts"].items():
        if key in EXCLUDED_ARTIFACT_KEYS or not isinstance(raw, str):
            continue
        path = ensure_within(root / raw, root, f"Артефакт {key}")
        if path.exists():
            if not path.is_file():
                raise MaintenanceError(f"Канонический артефакт не является файлом: {path}")
        docs.append(path)
    adr_dir_raw = state["artifacts"].get("adr_dir")
    if isinstance(adr_dir_raw, str):
        adr_dir = ensure_within(root / adr_dir_raw, root, "ADR directory")
        if adr_dir.is_dir():
            for path in sorted(adr_dir.rglob("*.md")):
                ensure_within(path, root, "ADR")
                if path.is_symlink() or not path.is_file():
                    raise MaintenanceError(f"ADR должен быть обычным файлом: {path}")
                docs.append(path)
    docs.extend(existing_agent_instruction_docs(root))
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    for raw in maintenance.get("canonical_docs", []):
        if isinstance(raw, str):
            docs.append(ensure_within(root / raw, root, "Recorded canonical document"))
    for raw in maintenance.get("agent_instruction_docs", []):
        if isinstance(raw, str):
            docs.append(ensure_within(root / raw, root, "Recorded AGENTS.md"))
    unique = sorted(set(docs))
    if not unique:
        raise MaintenanceError("Не найдено ни одного канонического документа для сопровождения.")
    return unique


def existing_agent_instruction_docs(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in IGNORED_CONTEXT_DIRS and not (current_path / name).is_symlink()
        ]
        if "AGENTS.md" in names:
            candidates.append(current_path / "AGENTS.md")
    docs: list[Path] = []
    for path in candidates:
        relative = path.relative_to(root)
        if any(part in IGNORED_CONTEXT_DIRS for part in relative.parts[:-1]):
            continue
        checked = ensure_within(path, root, "Nested AGENTS.md")
        if checked.is_symlink() or not checked.is_file():
            raise MaintenanceError(f"AGENTS.md должен быть обычным файлом: {checked}")
        docs.append(checked)
    return sorted(set(docs))


def validate_new_agent_doc_path(root: Path, relative: str, *, must_exist: bool) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or raw.name != "AGENTS.md" or len(raw.parts) < 2:
        raise MaintenanceError(f"Новый вложенный контекст обязан быть <module>/AGENTS.md: {relative}")
    if any(part in IGNORED_CONTEXT_DIRS for part in raw.parts[:-1]):
        raise MaintenanceError(f"AGENTS.md запрещён в служебном/generated каталоге: {relative}")
    parent = ensure_within(root / raw.parent, root, "AGENTS.md parent")
    if not parent.is_dir():
        raise MaintenanceError(f"Родитель нового AGENTS.md не существует: {raw.parent.as_posix()}")
    path = ensure_within(root / raw, root, "Nested AGENTS.md")
    if must_exist:
        if path.is_symlink() or not path.is_file():
            raise MaintenanceError(f"Новый AGENTS.md не создан как обычный файл: {relative}")
        text = path.read_text(encoding="utf-8")
        required = ("Scope|Область", "Map|Карта", "Commands|Команды", "Boundaries|Границы")
        placeholder = re.search(r"(?i)\b(?:PENDING|TODO|TBD)\b|__REQUIRED__", text)
        sections: list[str] = []
        for heading in required:
            match = re.search(
                rf"(?ims)^##\s+(?:{heading})\s*$\n(?P<body>.*?)(?=^##\s+|\Z)", text
            )
            if not match:
                sections.append("")
                continue
            visible = re.sub(r"<!--.*?-->", "", match.group("body"), flags=re.DOTALL)
            visible = re.sub(r"[`#>*_\-|]", " ", visible)
            sections.append(" ".join(visible.split()))
        if placeholder or any(len(section) < 8 for section in sections):
            raise MaintenanceError(
                f"Новый {relative} требует заполненные Scope/Область, Map/Карта, Commands/Команды и Boundaries/Границы."
            )
    elif path.exists():
        raise MaintenanceError(f"AGENTS.md уже существовал на старте и не является created_doc: {relative}")
    return path


def managed_doc_relatives(state: dict[str, Any]) -> list[str]:
    return sorted(set(state["baseline_docs"]) | set(state.get("created_docs", [])))


def snapshot_relatives(root: Path, relatives: list[str]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for relative in relatives:
        path = ensure_within(root / relative, root, "Managed document")
        if path.is_symlink():
            raise MaintenanceError(f"Managed document не может быть симлинком: {relative}")
        snapshot[relative] = sha256_file(path) if path.is_file() else "missing"
    return snapshot


def doc_snapshot(root: Path, docs: list[Path]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in docs:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise MaintenanceError(f"Канонический документ не может быть симлинком: {relative}")
        snapshot[relative] = sha256_file(path) if path.is_file() else "missing"
    return snapshot


def snapshot_digest(snapshot: dict[str, str]) -> str:
    value = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def repository_fingerprint(root: Path, excluded: set[str] | None = None) -> str:
    """Hash tracked/untracked non-ignored repository inputs without following symlinks."""
    excluded = excluded or set()
    completed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        text=False,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        relatives = sorted(
            Path(item.decode("utf-8", errors="surrogateescape"))
            for item in completed.stdout.split(b"\0")
            if item
        )
    else:
        relatives = sorted(path.relative_to(root) for path in root.rglob("*") if path.is_file() or path.is_symlink())
    digest = hashlib.sha256()
    for relative in relatives:
        if not relative.parts or relative.parts[0] in {".git", ".agent-graphs"}:
            continue
        if relative == PROJECT_STATE_REL:
            continue
        if relative.as_posix() in excluded:
            continue
        path = repository_entry(root / relative, root)
        digest.update(relative.as_posix().encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif not path.exists():
            digest.update(b"missing\0")
        elif path.is_file():
            digest.update(f"file:{path.stat().st_mode & 0o777:o}\0".encode("ascii"))
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def markdown_field(text: str, name: str) -> str | None:
    match = re.search(rf"(?im)^{re.escape(name)}:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else None


def validate_task_delivery_receipt(root: Path, receipt: dict[str, str]) -> dict[str, str]:
    handoff = ensure_within(root / receipt["path"], root, "Task Delivery handoff")
    text = handoff.read_text(encoding="utf-8")
    required = {
        "Status": "READY",
        "Criteria passed": "YES",
        "Rollback documented": "YES",
        "Residual risks documented": "YES",
        "Canonical docs changed": "NO",
    }
    wrong = [name for name, expected in required.items() if markdown_field(text, name) != expected]
    if wrong:
        raise MaintenanceError("Task Delivery handoff не прошёл поля: " + ", ".join(wrong))
    implementation = markdown_field(text, "Implementation SHA-256") or ""
    if not re.fullmatch(r"[0-9a-f]{64}", implementation):
        raise MaintenanceError("Task Delivery handoff содержит некорректный Implementation SHA-256.")
    proposal = markdown_field(text, "Proposed documentation maintenance") or ""
    if len(proposal) < 8 or proposal == "PENDING":
        raise MaintenanceError("Task Delivery handoff не содержит Proposed documentation maintenance.")
    task_id = handoff.parent.name
    state_path = ensure_within(root / ".codex/task-delivery" / task_id / "state.json", root, "Task Delivery state")
    task = load_json(state_path)
    checkpoint = task.get("checkpoints", {}).get("handoff")
    if task.get("phase") != "completed" or not task.get("completed_at") or not isinstance(checkpoint, dict):
        raise MaintenanceError(f"Task Delivery {task_id} ещё не завершён со свежим handoff checkpoint.")
    if checkpoint.get("path") != receipt["path"] or checkpoint.get("sha256") != receipt["sha256"]:
        raise MaintenanceError("Task Delivery state не связан с точным handoff receipt.")
    if checkpoint.get("implementation_repo_digest") != implementation:
        raise MaintenanceError("Implementation SHA-256 расходится между handoff и Task Delivery state.")
    return {
        **receipt,
        "kind": "task-delivery",
        "task_id": task_id,
        "task_state": state_path.relative_to(root).as_posix(),
        "task_state_sha256": sha256_file(state_path),
        "implementation_sha256": implementation,
    }


def resolve_receipt(root: Path, raw: str | None, trigger: str) -> dict[str, str] | None:
    if trigger == "task-delivery" and not raw:
        raise MaintenanceError("Trigger task-delivery требует --change-receipt с завершённым HANDOFF.md.")
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    path = candidate if candidate.is_absolute() else root / candidate
    path = ensure_within(path, root, "Change receipt")
    if path.is_symlink() or not path.is_file():
        raise MaintenanceError(f"Change receipt должен быть обычным файлом: {path}")
    receipt = {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}
    return validate_task_delivery_receipt(root, receipt) if trigger == "task-delivery" else receipt


def skill_roots(explicit: str | None = None) -> list[Path]:
    roots: list[Path] = []
    if explicit:
        roots.append(Path(explicit).expanduser())
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    roots.append(Path.home() / ".codex" / "skills")
    desktop = Path("/mnt/c/Users")
    if desktop.is_dir():
        roots.extend(desktop.glob("*/.codex/skills"))
    unique: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def capability_inventory(graph: dict[str, Any], explicit_root: str | None = None) -> dict[str, Any]:
    route_nodes = graph["routes"]["bootstrap"]["nodes"] | graph["routes"]["maintenance"]["nodes"]
    rows: dict[str, Any] = {}
    roots = skill_roots(explicit_root)
    for name in graph["capability_registry"]["skills"]:
        found: Path | None = None
        for root in roots:
            candidate = root / name / "SKILL.md"
            if candidate.is_file() and not candidate.is_symlink():
                found = candidate.parent
                break
        nodes = sorted(node for node, spec in route_nodes.items() if name in spec.get("skills", []))
        rows[name] = {
            "available": found is not None,
            "path": str(found) if found else None,
            "route_nodes": nodes,
        }
    return {
        "schema_version": 1,
        "checked_at": now(),
        "skills": rows,
        "backend": {
            "selected": graph["capability_registry"]["default_backend"],
            "optional": graph["capability_registry"].get("optional_backends", []),
            "rule": "One orchestrator per run; Sandcastle is optional execution infrastructure, not a nested graph owner.",
        },
    }


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
            if age > stale_seconds and not project_start_runtime._pid_is_alive(pid):
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise MaintenanceError(f"Maintenance run занят другим процессом: {run_dir}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} at={now()}\n".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def save_project_state(root: Path, project: dict[str, Any], expected_sha256: str) -> str:
    try:
        return project_start_runtime.save_project_state(
            root, project, expected_sha256=expected_sha256
        )
    except ValueError as exc:
        raise MaintenanceError(str(exc)) from exc


def persist_run_status(
    state: dict[str, Any],
    status: str,
    *,
    node: str | None = None,
    summary: str | None = None,
) -> None:
    """Persist the maintenance obligation in shared Project Start state."""
    root = Path(state["root"])
    project = project_state(root)
    expected = state["project_state_sha256"]
    if sha256_file(root / PROJECT_STATE_REL) != expected:
        raise MaintenanceError("Project Start state изменился; maintenance run обязан перечитать вход.")
    maintenance = project.setdefault("maintenance", {"history": []})
    current = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
    if current and current.get("run_id") != state["run_id"]:
        raise MaintenanceError("Другой maintenance run владеет Project Start state.")
    active = {
        "run_id": state["run_id"],
        "run_dir": str(Path(state["root"]) / RUNTIME_REL / state["run_id"]),
        "trigger": state["trigger"],
        "reason": state["reason"],
        "cycle": state["cycle"],
        "change_receipt": state["change_receipt"],
        "node": node or state["current"],
        "updated_at": now(),
    }
    if summary:
        active["summary"] = summary
    maintenance["status"] = status
    maintenance["active_run"] = active
    maintenance.pop("maintenance_required", None)
    project["updated_at"] = active["updated_at"]
    state["project_state_sha256"] = save_project_state(root, project, expected)


def persist_pending_reopen(state: dict[str, Any], classification: dict[str, Any], artifact: Path) -> None:
    root = Path(state["root"])
    project = project_state(root)
    if sha256_file(root / PROJECT_STATE_REL) != state["project_state_sha256"]:
        raise MaintenanceError("Project Start state изменился до записи pending reopen; требуется новый audit.")
    maintenance = project.setdefault("maintenance", {"history": []})
    active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
    if maintenance.get("status") != "running" or active.get("run_id") != state["run_id"]:
        raise MaintenanceError("Semantic terminal не владеет активным maintenance obligation.")
    stamp = now()
    pending = {
        "run_id": state["run_id"],
        "at": stamp,
        "stage": classification["reopen_stage"],
        "rationale": classification["rationale"],
        "affected_docs": classification["affected_docs"],
        "classification_sha256": sha256_file(artifact),
    }
    maintenance["status"] = "reopen-required"
    maintenance["pending_reopen"] = pending
    maintenance.pop("active_run", None)
    maintenance.pop("maintenance_required", None)
    if not any(
        isinstance(item, dict) and item.get("run_id") == state["run_id"]
        for item in maintenance.setdefault("history", [])
    ):
        maintenance["history"].append({"classification": "semantic", **pending})
    project["updated_at"] = stamp
    if not any(
        isinstance(item, dict)
        and item.get("event") == "documentation-reopen-required"
        and item.get("run_id") == state["run_id"]
        for item in project.setdefault("history", [])
    ):
        project["history"].append(
            {"event": "documentation-reopen-required", "phase": project["phase"], **pending}
        )
    state["project_state_sha256"] = save_project_state(
        root, project, state["project_state_sha256"]
    )


def run_directory(raw: str) -> Path:
    run_dir = Path(raw).expanduser().resolve()
    if not run_dir.is_dir() or not (run_dir / STATE_NAME).is_file():
        raise MaintenanceError(f"Не найден maintenance run: {run_dir}")
    return run_dir


def initialize(
    root_value: str,
    reason: str,
    trigger: str,
    receipt_value: str | None = None,
    skills_root: str | None = None,
    cycle: str | None = None,
    *,
    allow_new: bool = False,
) -> dict[str, Any]:
    if not reason.strip():
        raise MaintenanceError("Причина запуска не может быть пустой.")
    root = repository(root_value)
    project = project_state(root)
    project_state_sha256 = sha256_file(root / PROJECT_STATE_REL)
    receipt = resolve_receipt(root, receipt_value, trigger)
    cycle_key = (cycle or "").strip() or (now()[:10] if trigger == "scheduled" else "")
    maintenance = project.get("maintenance") if isinstance(project.get("maintenance"), dict) else {}
    maintenance_status = maintenance.get("status")
    if maintenance_status == "reopen-required":
        pending = maintenance.get("pending_reopen") if isinstance(maintenance.get("pending_reopen"), dict) else {}
        raise MaintenanceError(
            f"Новый maintenance run запрещён: сначала reopen {pending.get('stage')} для run {pending.get('run_id')}."
        )
    if maintenance_status in {"running", "blocked"}:
        active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
        active_dir = Path(str(active.get("run_dir", "")))
        same_request = (
            active.get("trigger") == trigger
            and active.get("reason") == reason.strip()
            and active.get("cycle", "") == cycle_key
            and active.get("change_receipt") == receipt
        )
        if same_request and active_dir.is_dir() and (active_dir / STATE_NAME).is_file():
            active_state = load_state(active_dir)
            return result(
                "ok",
                "Существующий maintenance run возобновлён.",
                next_actions=[f"Проверить текущий узел: ready --run {active_dir}"],
                artifacts=[str(active_dir / STATE_NAME)],
                data={
                    "run_dir": str(active_dir),
                    "current": active_state["current"],
                    "status": active_state["status"],
                },
            )
        raise MaintenanceError(
            f"Project Start уже имеет {maintenance_status} maintenance run {active.get('run_id')}; "
            "новый run нельзя открыть до завершения или retry."
        )
    if maintenance_status == "maintenance-required":
        obligation = maintenance.get("maintenance_required") if isinstance(maintenance.get("maintenance_required"), dict) else {}
        if trigger != "task-delivery" or not receipt:
            raise MaintenanceError("Незакрытый Task Delivery handoff требует trigger=task-delivery и точную change receipt.")
        if (
            obligation.get("handoff_path") != receipt.get("path")
            or obligation.get("handoff_sha256") != receipt.get("sha256")
            or obligation.get("task_state_sha256") != receipt.get("task_state_sha256")
        ):
            raise MaintenanceError("Change receipt не совпадает с обязательным Task Delivery handoff.")
    if not allow_new:
        raise MaintenanceError(
            "Legacy v2 runner работает только для уже активного run; новый запуск выполняй через project_graph.py."
        )
    graph = graph_contract()
    route = graph["routes"]["maintenance"]
    docs = canonical_docs(root, project)
    baseline = doc_snapshot(root, docs)
    source_sha256 = repository_fingerprint(root, set(baseline))
    seed = {
        "root": str(root),
        "reason": reason.strip(),
        "trigger": trigger,
        "receipt": receipt,
        "baseline": snapshot_digest(baseline),
        "source_sha256": source_sha256,
        "cycle": cycle_key,
        "project_state_sha256": project_state_sha256,
    }
    run_id = hashlib.sha256(
        json.dumps(seed, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    runtime = ensure_within(root / RUNTIME_REL.parent, root, "Agent graph runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    ignore = ensure_within(runtime / ".gitignore", runtime, "Runtime gitignore")
    if not ignore.exists():
        write_text_atomic(ignore, "*\n")
    elif ignore.is_symlink() or not ignore.is_file():
        raise MaintenanceError(f"Некорректный runtime .gitignore: {ignore}")
    elif "*" not in {line.strip() for line in ignore.read_text(encoding="utf-8").splitlines()}:
        write_text_atomic(ignore, ignore.read_text(encoding="utf-8").rstrip() + "\n*\n")
    runs = ensure_within(root / RUNTIME_REL, root, "Maintenance runs")
    run_dir = ensure_within(runs / run_id, runs, "Maintenance run")
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / STATE_NAME
    with state_lock(run_dir):
        if state_path.exists():
            state = load_state(run_dir)
            persist_run_status(state, "blocked" if state["status"] == "blocked" else "running")
            write_json_atomic(state_path, state)
            return result(
                "ok",
                "Существующий maintenance run возобновлён.",
                next_actions=[f"Проверить текущий узел: ready --run {run_dir}"],
                artifacts=[str(state_path)],
                data={"run_dir": str(run_dir), "current": state["current"], "status": state["status"]},
            )
        nodes = {
            name: {"status": "pending", "attempts": 0, "receipts": []}
            for name in route["nodes"]
        }
        nodes[route["entry"]]["status"] = "ready"
        stamp = now()
        state = {
            "schema_version": 1,
            "graph_id": graph["graph_id"],
            "graph_version": graph["graph_version"],
            # Keep the historical digest so an active v2 run remains resumable
            # after graph.json becomes the v3 model-first contract.
            "graph_sha256": LEGACY_GRAPH_SHA256,
            "run_id": run_id,
            "root": str(root),
            "project_phase": project["phase"],
            "project_state_sha256": project_state_sha256,
            "reason": reason.strip(),
            "trigger": trigger,
            "change_receipt": receipt,
            "source_sha256": source_sha256,
            "cycle": cycle_key,
            "baseline_docs": baseline,
            "created_docs": [],
            "protected_docs": sorted(
                project["artifacts"][key]
                for key in PROTECTED_ARTIFACT_KEYS
                if isinstance(project["artifacts"].get(key), str)
            ),
            "classification": None,
            "status": "running",
            "current": route["entry"],
            "update_repairs": 0,
            "node_retries": {name: 0 for name in route["nodes"]},
            "created_at": stamp,
            "updated_at": stamp,
            "nodes": nodes,
            "events": [{"at": stamp, "event": "maintenance_initialized", "node": route["entry"]}],
        }
        write_json_atomic(run_dir / "capabilities.json", capability_inventory(graph, skills_root))
        write_json_atomic(state_path, state)
        persist_run_status(state, "running", node=route["entry"])
        write_json_atomic(state_path, state)
    return result(
        "ok",
        "Maintenance route инициализирован.",
        next_actions=[f"Выполнить узел {route['entry']}."],
        artifacts=[str(state_path), str(run_dir / "capabilities.json")],
        data={
            "run_dir": str(run_dir),
            "current": route["entry"],
            "canonical_docs": sorted(baseline),
            "source_sha256": source_sha256,
            "cycle": cycle_key,
        },
    )


def load_state(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    graph = graph_contract()
    if state.get("graph_id") != graph["graph_id"]:
        raise MaintenanceError("Run принадлежит другому графу.")
    if state.get("graph_version") != graph["graph_version"]:
        raise MaintenanceError("Версия graph.json изменилась после старта run.")
    if state.get("graph_sha256") not in {LEGACY_GRAPH_SHA256, sha256_file(GRAPH_PATH)}:
        raise MaintenanceError("Контракт graph.json изменился после старта run.")
    receipt = state.get("change_receipt")
    if receipt:
        root = Path(state["root"])
        path = ensure_within(root / receipt["path"], root, "Change receipt")
        if not path.is_file() or sha256_file(path) != receipt["sha256"]:
            raise MaintenanceError("Change receipt изменился или исчез после старта run.")
        task_state = receipt.get("task_state")
        if task_state:
            task_path = ensure_within(root / task_state, root, "Task Delivery state")
            if not task_path.is_file() or sha256_file(task_path) != receipt.get("task_state_sha256"):
                raise MaintenanceError("Task Delivery state изменился после старта maintenance run.")
    return state


def status(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    return result(
        "ok",
        f"Maintenance run: {state['status']} на узле {state['current']}.",
        next_actions=[] if state["status"] != "running" else [f"Выполнить узел {state['current']}."],
        artifacts=[str(run_dir / STATE_NAME)],
        data={
            "run_id": state["run_id"],
            "status": state["status"],
            "current": state["current"],
            "classification": state["classification"],
            "update_repairs": state["update_repairs"],
        },
    )


def ready(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    if state["status"] != "running":
        raise MaintenanceError(f"Run не активен: {state['status']}")
    route = maintenance_route()
    node_name = state["current"]
    node_state = state["nodes"][node_name]
    if node_state["status"] != "ready":
        raise MaintenanceError(f"Текущий узел не готов: {node_name}")
    node = route["nodes"][node_name]
    artifact = run_dir / node["artifact"]
    return result(
        "ok",
        f"Узел {node_name} готов.",
        next_actions=[f"Роль {node['role']} должна создать {artifact.name}."],
        artifacts=[str(artifact)],
        data={
            "node": node_name,
            "role": node["role"],
            "skills": node.get("skills", []),
            "expected_artifact": str(artifact),
            "attempt": node_state["attempts"] + 1,
        },
    )


def nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MaintenanceError(f"{label} должен быть непустой строкой.")
    return value.strip()


def string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise MaintenanceError(f"{label} должен быть массивом непустых строк.")
    if not allow_empty and not value:
        raise MaintenanceError(f"{label} не может быть пустым.")
    return [item.strip() for item in value]


def validate_artifact(run_dir: Path, node: str, path: Path, outcome: str) -> dict[str, Any]:
    value = load_json(path)
    if value.get("schema_version") != 1:
        raise MaintenanceError(f"{path.name}: schema_version должен быть 1.")
    if outcome == "failed":
        nonempty_string(value.get("error"), f"{node}.error")
        return value
    if node == "maintenance-intake":
        nonempty_string(value.get("reason"), "intake.reason")
        if value.get("trigger") not in {"manual", "task-delivery", "scheduled", "repository-change"}:
            raise MaintenanceError("intake.trigger имеет недопустимое значение.")
        run_state = load_state(run_dir)
        if value.get("reason") != run_state["reason"] or value.get("trigger") != run_state["trigger"]:
            raise MaintenanceError("intake reason/trigger не совпадают с неизменяемым входом run.")
        docs = string_list(value.get("canonical_docs"), "intake.canonical_docs", allow_empty=False)
        if sorted(docs) != sorted(run_state["baseline_docs"]):
            raise MaintenanceError("intake.canonical_docs не совпадает с каноническими документами run.")
    elif node == "capability-discovery":
        expected = set(graph_contract()["capability_registry"]["skills"])
        skills = value.get("skills")
        if not isinstance(skills, dict) or set(skills) != expected:
            raise MaintenanceError("capabilities.skills должен учитывать каждый навык capability registry.")
        for name, item in skills.items():
            if not isinstance(item, dict) or not isinstance(item.get("available"), bool):
                raise MaintenanceError(f"capabilities.skills.{name} имеет неверную структуру.")
            if not isinstance(item.get("route_nodes"), list) or not item["route_nodes"]:
                raise MaintenanceError(f"Навык {name} не привязан ни к одному узлу графа.")
    elif node == "drift-audit":
        docs = string_list(value.get("checked_docs"), "drift.checked_docs", allow_empty=False)
        if sorted(docs) != sorted(load_state(run_dir)["baseline_docs"]):
            raise MaintenanceError("drift.checked_docs не покрывает точный набор канонических документов.")
        findings = value.get("findings")
        if not isinstance(findings, list):
            raise MaintenanceError("drift.findings должен быть массивом.")
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                raise MaintenanceError(f"drift.findings[{index}] должен быть объектом.")
            for key in ("document", "claim", "evidence", "impact"):
                nonempty_string(finding.get(key), f"drift.findings[{index}].{key}")
            if finding["document"] not in load_state(run_dir)["baseline_docs"]:
                validate_new_agent_doc_path(Path(load_state(run_dir)["root"]), finding["document"], must_exist=False)
    elif node == "impact-classification":
        classification = value.get("classification")
        expected = {"no-change": "no-change", "factual": "factual", "semantic": "semantic"}.get(outcome)
        if expected is None or classification != expected:
            raise MaintenanceError(f"classification должен совпадать с outcome {outcome}.")
        nonempty_string(value.get("rationale"), "classification.rationale")
        affected = string_list(value.get("affected_docs"), "classification.affected_docs")
        run_state = load_state(run_dir)
        unknown = sorted(set(affected) - set(run_state["baseline_docs"]))
        for relative in unknown:
            validate_new_agent_doc_path(Path(run_state["root"]), relative, must_exist=False)
        if classification == "no-change" and affected:
            raise MaintenanceError("no-change classification требует пустой affected_docs.")
        if classification in {"factual", "semantic"} and not affected:
            raise MaintenanceError(f"{classification} classification требует непустой affected_docs.")
        drift_receipts = load_state(run_dir)["nodes"]["drift-audit"]["receipts"]
        drift = load_json(Path(drift_receipts[-1]["artifact"]))
        finding_docs = {item["document"] for item in drift["findings"]}
        if classification == "no-change" and finding_docs:
            raise MaintenanceError("no-change classification противоречит непустому drift.findings.")
        if classification in {"factual", "semantic"} and not finding_docs:
            raise MaintenanceError(f"{classification} classification требует подтверждённый drift finding.")
        uncovered = sorted(finding_docs - set(affected))
        if uncovered:
            raise MaintenanceError("classification.affected_docs не покрывает drift findings: " + ", ".join(uncovered))
        protected = set(load_state(run_dir).get("protected_docs", []))
        if classification == "factual" and protected.intersection(affected):
            raise MaintenanceError(
                "Factual classification не может переписывать неизменяемое доказательство: "
                + ", ".join(sorted(protected.intersection(affected)))
            )
        if classification == "semantic" and value.get("reopen_stage") not in {"discovery", "foundation", "planning"}:
            raise MaintenanceError("Семантическое изменение требует reopen_stage discovery/foundation/planning.")
    elif node == "documentation-update":
        changed = string_list(value.get("changed_docs"), "update.changed_docs")
        created = string_list(value.get("created_docs", []), "update.created_docs")
        if not changed and not created:
            raise MaintenanceError("documentation-update требует changed_docs или created_docs.")
        string_list(value.get("source_receipts"), "update.source_receipts", allow_empty=False)
        nonempty_string(value.get("summary"), "update.summary")
        baseline = load_state(run_dir)["baseline_docs"]
        unknown = sorted(set(changed) - set(baseline))
        if unknown:
            raise MaintenanceError("Фактическое обновление затронуло неканонические/новые документы: " + ", ".join(unknown))
        root = Path(load_state(run_dir)["root"])
        current = current_snapshot(root, baseline)
        actual = sorted(path for path, digest in current.items() if digest != baseline[path])
        if sorted(changed) != actual:
            raise MaintenanceError(
                "update.changed_docs не совпадает с фактически изменёнными документами: "
                f"declared={sorted(changed)}, actual={actual}"
            )
        root = Path(load_state(run_dir)["root"])
        for relative in created:
            validate_new_agent_doc_path(root, relative, must_exist=True)
        classification_receipts = load_state(run_dir)["nodes"]["impact-classification"]["receipts"]
        classification = load_json(Path(classification_receipts[-1]["artifact"]))
        if sorted(changed + created) != sorted(classification["affected_docs"]):
            raise MaintenanceError("update changed_docs/created_docs не совпадают с classification.affected_docs.")
    elif node == "documentation-verify":
        verdict = value.get("verdict")
        expected = "pass" if outcome == "succeeded" else "reject" if outcome == "rejected" else None
        if expected is None or verdict != expected:
            raise MaintenanceError(f"verification.verdict должен совпадать с outcome {outcome}.")
        checked = string_list(value.get("checked_docs"), "verification.checked_docs", allow_empty=False)
        if sorted(checked) != managed_doc_relatives(load_state(run_dir)):
            raise MaintenanceError("verification.checked_docs не покрывает точный набор канонических документов.")
        string_list(value.get("stale_claims"), "verification.stale_claims")
        string_list(value.get("contradictions"), "verification.contradictions")
        string_list(value.get("residual_risks"), "verification.residual_risks")
        if verdict == "reject":
            string_list(value.get("repair_list"), "verification.repair_list", allow_empty=False)
        else:
            if value["stale_claims"] or value["contradictions"]:
                raise MaintenanceError("PASS невозможен при stale_claims или contradictions.")
            missing = [
                relative
                for relative, digest in snapshot_relatives(
                    Path(load_state(run_dir)["root"]), managed_doc_relatives(load_state(run_dir))
                ).items()
                if digest == "missing"
            ]
            if missing:
                raise MaintenanceError("PASS невозможен при отсутствующих документах: " + ", ".join(missing))
    return value


def current_snapshot(root: Path, baseline: dict[str, str]) -> dict[str, str]:
    current: dict[str, str] = {}
    for relative in baseline:
        path = ensure_within(root / relative, root, "Canonical document")
        if path.is_symlink():
            raise MaintenanceError(f"Канонический документ стал ссылкой: {relative}")
        current[relative] = sha256_file(path) if path.is_file() else "missing"
    return current


def verify_unchanged(state: dict[str, Any]) -> None:
    root = Path(state["root"])
    current = current_snapshot(root, state["baseline_docs"])
    if current != state["baseline_docs"]:
        changed = sorted(path for path in current if current[path] != state["baseline_docs"][path])
        raise MaintenanceError("Документы изменены до разрешённого update-узла: " + ", ".join(changed))


def resolve_artifact(run_dir: Path, raw: str, expected_name: str) -> Path:
    candidate = Path(raw).expanduser()
    path = candidate if candidate.is_absolute() else run_dir / candidate
    path = ensure_within(path, run_dir, "Node artifact")
    if path.name != expected_name:
        raise MaintenanceError(f"Ожидался артефакт {expected_name}, получен {path.name}")
    if path.is_symlink() or not path.is_file():
        raise MaintenanceError(f"Артефакт должен быть обычным файлом: {path}")
    return path


def allowed_outcomes(node: str) -> set[str]:
    if node == "impact-classification":
        return {"no-change", "factual", "semantic", "failed"}
    if node == "documentation-verify":
        return {"succeeded", "rejected", "failed"}
    return {"succeeded", "failed"}


def receipt_snapshot(run_dir: Path, node: str, attempt: int, artifact: Path) -> dict[str, Any]:
    digest = sha256_file(artifact)
    receipts = ensure_within(run_dir / "receipts", run_dir, "Receipt directory")
    if receipts.exists() and (receipts.is_symlink() or not receipts.is_dir()):
        raise MaintenanceError(f"Receipt directory должен быть обычным каталогом: {receipts}")
    receipts.mkdir(exist_ok=True)
    target = receipts / f"{node}-{attempt:02d}-{digest[:12]}.json"
    if target.exists():
        if sha256_file(target) != digest:
            raise MaintenanceError(f"Коллизия receipt snapshot: {target}")
    else:
        shutil.copy2(artifact, target)
    if sha256_file(target) != digest:
        target.unlink(missing_ok=True)
        raise MaintenanceError(f"Не удалось проверить receipt snapshot: {target}")
    return {
        "attempt": attempt,
        "artifact": str(target),
        "artifact_sha256": digest,
        "recorded_at": now(),
    }


def record(run_dir: Path, node: str, artifact_value: str, outcome: str) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        route = maintenance_route()
        if state["status"] != "running":
            raise MaintenanceError(f"Run не активен: {state['status']}")
        if state["current"] != node:
            raise MaintenanceError(f"Нельзя записать {node}; текущий узел: {state['current']}")
        if node == route["terminal"]:
            raise MaintenanceError("Для terminal node используй complete.")
        if outcome not in allowed_outcomes(node):
            raise MaintenanceError(f"Outcome {outcome} недопустим для {node}.")
        artifact = resolve_artifact(run_dir, artifact_value, route["nodes"][node]["artifact"])
        factual_verification = node == "documentation-verify" and state.get("classification") == "factual"
        if node != "documentation-update" and not factual_verification:
            verify_unchanged(state)
        value = validate_artifact(run_dir, node, artifact, outcome)
        if node == "documentation-update":
            state["created_docs"] = sorted(value.get("created_docs", []))
        if factual_verification:
            update_receipts = state["nodes"]["documentation-update"]["receipts"]
            if not update_receipts:
                raise MaintenanceError("Factual verification требует свежий documentation-update receipt.")
            root = Path(state["root"])
            expected_hashes = update_receipts[-1].get("document_hashes", {})
            current_hashes = {
                relative: sha256_file(ensure_within(root / relative, root, "Updated document"))
                for relative in expected_hashes
            }
            if current_hashes != expected_hashes:
                raise MaintenanceError(
                    "Документы изменились после documentation-update; нужен новый update receipt до verifier PASS."
                )
        node_state = state["nodes"][node]
        node_state["attempts"] += 1
        receipt = receipt_snapshot(run_dir, node, node_state["attempts"], artifact)
        if node == "documentation-update":
            root = Path(state["root"])
            receipt["document_hashes"] = {
                relative: sha256_file(ensure_within(root / relative, root, "Updated document"))
                for relative in value["changed_docs"] + value.get("created_docs", [])
            }
        elif node == "documentation-verify":
            receipt["document_hashes"] = snapshot_relatives(
                Path(state["root"]), managed_doc_relatives(state)
            )
        receipt["outcome"] = outcome
        node_state["receipts"].append(receipt)
        stamp = now()
        state["events"].append({"at": stamp, "event": "node_recorded", "node": node, "outcome": outcome})
        if outcome == "failed":
            node_state["status"] = "failed"
            state["status"] = "blocked"
            state["updated_at"] = stamp
            persist_run_status(state, "blocked", node=node, summary=f"Узел {node} завершился ошибкой.")
            write_json_atomic(run_dir / STATE_NAME, state)
            return result(
                "blocked",
                f"Узел {node} завершился ошибкой; граф остановлен без обхода рубежа.",
                artifacts=[str(run_dir / STATE_NAME), str(artifact)],
            )
        node_state["status"] = outcome
        spec = route["nodes"][node]
        if node == "impact-classification":
            state["classification"] = value["classification"]
            if outcome == "semantic":
                root = Path(state["root"])
                current_source = repository_fingerprint(root, set(managed_doc_relatives(state)))
                if current_source != state["source_sha256"]:
                    raise MaintenanceError(
                        "Репозиторий изменился после drift audit; semantic classification нельзя фиксировать по устаревшему снимку."
                    )
                node_state["status"] = "semantic"
                state["current"] = "reopen-required"
                state["nodes"]["reopen-required"]["status"] = "ready"
                state["status"] = "reopen-required"
                state["reopen_stage"] = value["reopen_stage"]
                persist_pending_reopen(state, value, artifact)
                state["updated_at"] = stamp
                write_json_atomic(run_dir / STATE_NAME, state)
                command = (
                    "python3 scripts/project_start.py reopen "
                    f"--root {shlex.quote(state['root'])} "
                    f"--stage {value['reopen_stage']} --note {shlex.quote(value['rationale'])}"
                )
                return result(
                    "reopen-required",
                    "Обнаружено семантическое изменение; тихая правка документации запрещена.",
                    next_actions=[command, "После проверки повторить команду с --apply и пройти открытые рубежи."],
                    artifacts=[str(artifact), str(run_dir / STATE_NAME)],
                    data={"reopen_stage": value["reopen_stage"]},
                )
            next_node = spec["on_no_change"] if outcome == "no-change" else spec["on_factual"]
        elif node == "documentation-verify" and outcome == "rejected":
            limit = int(route["limits"]["max_update_repairs"])
            if state["update_repairs"] >= limit:
                state["status"] = "blocked"
                state["updated_at"] = stamp
                persist_run_status(
                    state,
                    "blocked",
                    node=node,
                    summary="Исчерпан лимит исправлений документации.",
                )
                write_json_atomic(run_dir / STATE_NAME, state)
                return result(
                    "blocked",
                    "Исчерпан лимит исправлений документации.",
                    next_actions=["Разобрать остаточный риск вручную; не объявлять документы актуальными."],
                    artifacts=[str(run_dir / STATE_NAME), str(artifact)],
                )
            state["update_repairs"] += 1
            state["nodes"]["documentation-verify"]["status"] = "pending"
            if state["classification"] == "no-change":
                for reset in ("drift-audit", "impact-classification"):
                    state["nodes"][reset]["status"] = "pending"
                state["classification"] = None
                next_node = spec["on_rejected_no_change"]
            else:
                state["nodes"]["documentation-update"]["status"] = "pending"
                next_node = spec["on_rejected_factual"]
        else:
            next_node = spec["on_success"]
        state["current"] = next_node
        state["nodes"][next_node]["status"] = "ready"
        state["updated_at"] = stamp
        persist_run_status(state, "running", node=next_node)
        write_json_atomic(run_dir / STATE_NAME, state)
    return result(
        "ok",
        f"Узел {node} записан; следующий узел: {next_node}.",
        next_actions=[f"Выполнить узел {next_node}."],
        artifacts=[str(artifact), str(run_dir / STATE_NAME)],
        data={"current": next_node, "classification": state["classification"]},
    )


def validate_receipts(state: dict[str, Any]) -> None:
    for node, node_state in state["nodes"].items():
        for receipt in node_state["receipts"]:
            path = Path(receipt["artifact"])
            if path.is_symlink() or not path.is_file() or sha256_file(path) != receipt["artifact_sha256"]:
                raise MaintenanceError(f"Receipt узла {node} изменён или исчез: {path}")


def retry(run_dir: Path, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise MaintenanceError("Retry требует причину.")
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] != "blocked":
            raise MaintenanceError(f"Retry допустим только для blocked run, сейчас: {state['status']}")
        node = state["current"]
        limit = int(maintenance_route()["limits"]["max_node_retries"])
        if state["node_retries"][node] >= limit:
            raise MaintenanceError(f"Исчерпан лимит retry для {node}.")
        state["node_retries"][node] += 1
        state["status"] = "running"
        state["nodes"][node]["status"] = "ready"
        stamp = now()
        state["updated_at"] = stamp
        state["events"].append({"at": stamp, "event": "node_retry", "node": node, "reason": reason.strip()})
        persist_run_status(state, "running", node=node)
        write_json_atomic(run_dir / STATE_NAME, state)
    return result("ok", f"Узел {node} открыт для безопасного retry.", data={"current": node})


def refresh_approvals(root: Path, state: dict[str, Any], changed_docs: list[str], run_id: str) -> list[str]:
    refreshed: list[str] = []
    changed = set(changed_docs)
    for gate, approval in state.get("approvals", {}).items():
        if not isinstance(approval, dict):
            continue
        files = list(approval.get("files", {}))
        if not changed.intersection(files):
            continue
        try:
            snapshot = project_start_runtime.gate_snapshot(root, state, gate)
        except ValueError as exc:
            raise MaintenanceError(str(exc)) from exc
        approval.update(snapshot)
        approval["maintenance_refresh"] = {"at": now(), "run_id": run_id, "classification": "factual"}
        refreshed.append(gate)
    return refreshed


def complete(run_dir: Path) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        route = maintenance_route()
        if state["status"] == "completed":
            validate_receipts(state)
            return result(
                "ok",
                "Maintenance run уже завершён.",
                artifacts=[str(run_dir / route["nodes"][route["terminal"]]["artifact"]), str(run_dir / STATE_NAME)],
            )
        if state["status"] != "running" or state["current"] != route["terminal"]:
            raise MaintenanceError(f"Completion gate ещё не достигнут: {state['status']} / {state['current']}")
        if state["nodes"]["documentation-verify"]["status"] != "succeeded":
            raise MaintenanceError("Независимая проверка документации не дала PASS.")
        validate_receipts(state)
        root = Path(state["root"])
        project = project_state(root)
        if sha256_file(root / PROJECT_STATE_REL) != state["project_state_sha256"]:
            raise MaintenanceError("Project Start state изменился во время maintenance run; требуется новый audit.")
        if project["phase"] != state["project_phase"]:
            raise MaintenanceError("Project Start phase изменилась во время maintenance run; требуется новый audit.")
        project_maintenance = project.get("maintenance") if isinstance(project.get("maintenance"), dict) else {}
        active = project_maintenance.get("active_run") if isinstance(project_maintenance.get("active_run"), dict) else {}
        if project_maintenance.get("status") != "running" or active.get("run_id") != state["run_id"]:
            raise MaintenanceError("Completion не владеет активным Project Start maintenance obligation.")
        managed_docs = managed_doc_relatives(state)
        current_source = repository_fingerprint(root, set(managed_docs))
        if current_source != state["source_sha256"]:
            raise MaintenanceError("Репозиторий изменился после drift audit; требуется новый maintenance run.")
        current = snapshot_relatives(root, managed_docs)
        verification_receipt = state["nodes"]["documentation-verify"]["receipts"][-1]
        if current != verification_receipt.get("document_hashes"):
            raise MaintenanceError("Канонические документы изменились после независимого documentation-verify PASS.")
        changed = sorted(
            path
            for path in current
            if path in state.get("created_docs", []) or current[path] != state["baseline_docs"][path]
        )
        if state["classification"] == "no-change" and changed:
            raise MaintenanceError("No-change run не может завершиться с изменёнными документами.")
        if state["classification"] == "factual":
            update_receipts = state["nodes"]["documentation-update"]["receipts"]
            if not update_receipts:
                raise MaintenanceError("Factual run не содержит update receipt.")
            update = load_json(Path(update_receipts[-1]["artifact"]))
            if sorted(update["changed_docs"] + update.get("created_docs", [])) != changed:
                raise MaintenanceError("Документы изменились после update receipt.")
        refreshed = refresh_approvals(root, project, changed, state["run_id"])
        integrity_issues = project_start_runtime.state_integrity_issues(root, project)
        if integrity_issues:
            messages = [item["message"] for item in integrity_issues[:8]]
            raise MaintenanceError(
                "Project Start state не прошёл итоговую проверку целостности: " + "; ".join(messages)
            )
        maintenance = project.setdefault("maintenance", {"status": "operational", "history": []})
        existing_entry = next(
            (
                item
                for item in maintenance.get("history", [])
                if isinstance(item, dict) and item.get("run_id") == state["run_id"]
            ),
            None,
        )
        stamp = existing_entry.get("at") if isinstance(existing_entry, dict) else now()
        entry = existing_entry or {
            "run_id": state["run_id"],
            "at": stamp,
            "trigger": state["trigger"],
            "reason": state["reason"],
            "classification": state["classification"],
            "changed_docs": changed,
            "refreshed_approvals": refreshed,
            "change_receipt": state["change_receipt"],
            "source_sha256": state["source_sha256"],
            "cycle": state["cycle"],
        }
        maintenance["status"] = "operational"
        maintenance.pop("active_run", None)
        maintenance.pop("maintenance_required", None)
        pending = maintenance.get("pending_reopen") if isinstance(maintenance.get("pending_reopen"), dict) else None
        if isinstance(pending, dict):
            raise MaintenanceError("Нельзя завершить factual/no-change run поверх semantic pending_reopen.")
        maintenance["agent_instruction_docs"] = sorted(
            path for path in managed_docs if Path(path).name == "AGENTS.md"
        )
        maintenance["canonical_docs"] = managed_docs
        maintenance["last_run"] = entry
        if existing_entry is None:
            maintenance.setdefault("history", []).append(entry)
        project["updated_at"] = stamp
        if not any(
            isinstance(item, dict)
            and item.get("event") == "documentation-maintained"
            and item.get("run_id") == state["run_id"]
            for item in project.setdefault("history", [])
        ):
            project["history"].append(
                {"at": stamp, "event": "documentation-maintained", "phase": project["phase"], **entry}
            )
        state["project_state_sha256"] = save_project_state(
            root, project, state["project_state_sha256"]
        )
        report = {
            "schema_version": 1,
            "graph_id": "project-start",
            "run_id": state["run_id"],
            "status": "completed",
            "completed_at": stamp,
            "classification": state["classification"],
            "changed_docs": changed,
            "refreshed_approvals": refreshed,
            "verification_receipt": state["nodes"]["documentation-verify"]["receipts"][-1],
        }
        report_path = run_dir / route["nodes"][route["terminal"]]["artifact"]
        write_json_atomic(report_path, report)
        terminal = state["nodes"][route["terminal"]]
        terminal["status"] = "succeeded"
        terminal["attempts"] += 1
        terminal["receipts"].append(
            {
                "attempt": terminal["attempts"],
                "artifact": str(report_path),
                "artifact_sha256": sha256_file(report_path),
                "recorded_at": stamp,
                "outcome": "succeeded",
            }
        )
        state["status"] = "completed"
        state["updated_at"] = stamp
        state["events"].append({"at": stamp, "event": "maintenance_completed", "node": route["terminal"]})
        write_json_atomic(run_dir / STATE_NAME, state)
    return result(
        "ok",
        "Документация проверена и возвращена в operational state.",
        next_actions=["Продолжить Task Delivery; следующий change receipt снова запускает maintenance route."],
        artifacts=[str(report_path), str(root / PROJECT_STATE_REL)],
        data={"classification": state["classification"], "changed_docs": changed, "refreshed_approvals": refreshed},
    )


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Инициализировать или возобновить maintenance route")
    init.add_argument("--root", required=True)
    init.add_argument("--reason", required=True)
    init.add_argument(
        "--trigger",
        required=True,
        choices=("manual", "task-delivery", "scheduled", "repository-change"),
    )
    init.add_argument("--change-receipt")
    init.add_argument("--skills-root")
    init.add_argument("--cycle", help="Явный ключ повторной проверки; scheduled по умолчанию использует UTC-день")
    for name in ("status", "ready", "complete"):
        item = sub.add_parser(name)
        item.add_argument("--run", required=True)
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--run", required=True)
    record_parser.add_argument("--node", required=True)
    record_parser.add_argument("--artifact", required=True)
    record_parser.add_argument("--outcome", required=True)
    retry_parser = sub.add_parser("retry")
    retry_parser.add_argument("--run", required=True)
    retry_parser.add_argument("--reason", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            payload = initialize(args.root, args.reason, args.trigger, args.change_receipt, args.skills_root, args.cycle)
        else:
            run_dir = run_directory(args.run)
            if args.command == "status":
                payload = status(run_dir)
            elif args.command == "ready":
                payload = ready(run_dir)
            elif args.command == "record":
                payload = record(run_dir, args.node, args.artifact, args.outcome)
            elif args.command == "retry":
                payload = retry(run_dir, args.reason)
            elif args.command == "complete":
                payload = complete(run_dir)
            else:
                raise MaintenanceError(f"Неизвестная команда: {args.command}")
    except MaintenanceError as exc:
        payload = result("failed", str(exc), next_actions=["Исправить нарушение контракта и повторить безопасный шаг."])
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] != "failed" else 2


if __name__ == "__main__":
    sys.exit(main())
