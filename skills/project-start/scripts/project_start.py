#!/usr/bin/env python3
"""Deterministic project-start state, scaffold, and validation helper."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"
GRAPH_PATH = SKILL_DIR / "graph.json"
STATE_REL = Path(".project-start/state.json")
STATE_LOCK_REL = Path(".project-start/.state.lock")
REQUIRED_MARKER = "PROJECT-START:REQUIRED"
REQUIRED_VALUE = "__REQUIRED__"


def load_graph_contract() -> dict[str, Any]:
    try:
        graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Некорректный контракт графа Project Start: {exc}") from exc
    routes = graph.get("routes")
    registry = graph.get("capability_registry")
    if graph.get("graph_id") != "project-start" or not isinstance(routes, dict):
        raise RuntimeError("graph.json не содержит граф project-start и его routes.")
    if not isinstance(routes.get("bootstrap"), dict) or not isinstance(routes.get("maintenance"), dict):
        raise RuntimeError("graph.json обязан содержать bootstrap и maintenance routes.")
    if not isinstance(registry, dict) or not isinstance(registry.get("skills"), list):
        raise RuntimeError("graph.json не содержит capability_registry.skills.")
    return graph


GRAPH = load_graph_contract()
BOOTSTRAP_GRAPH = GRAPH["routes"]["bootstrap"]
LEGACY_BOOTSTRAP = GRAPH["legacy_v2_bootstrap"]
EXPECTED_SKILLS = tuple(GRAPH["capability_registry"]["skills"])
GATE_TO_PHASE = {
    "business": "foundation",
    "foundation": "planning",
    "plan": "tickets",
}
PHASE_ORDER = tuple(LEGACY_BOOTSTRAP["phases"])
FOUNDATION_EVENTS = tuple(LEGACY_BOOTSTRAP["events"]["foundation"])
TICKET_EVENTS = tuple(LEGACY_BOOTSTRAP["events"]["tickets"])
COMPLETION_EVENTS = tuple(LEGACY_BOOTSTRAP["events"]["completion"])
RECORD_EVENTS = FOUNDATION_EVENTS + TICKET_EVENTS + COMPLETION_EVENTS
GATE_ARTIFACT_KEYS = {
    "business": ("business", "decisions", "context"),
    "foundation": ("foundation_manifest", "foundation", "codebase", "quality", "authority", "agent_operations"),
    "plan": ("plan",),
}
MARKDOWN_SECTIONS = {
    "business": (
        "Результат и болезненная проблема",
        "Участники и ответственность",
        "Сквозной поток",
        "Состояния и переходы",
        "Бизнес-правила и инварианты",
        "Данные и владение",
        "Ошибки, исключения и ручная работа",
        "Первая версия",
        "Не входит",
        "Нефункциональные ограничения",
        "Критерии приёмки",
        "Открытые вопросы",
    ),
    "foundation": (
        "Ограничения из бизнес-логики",
        "Исследование стека",
        "Выбранный профиль и стек",
        "Модульная архитектура",
        "Исполняемые архитектурные правила",
        "Интеграции и договоры",
        "Локальная среда",
        "Наблюдаемость и диагностика",
        "Развёртывание и откат",
        "Карта документации",
        "Исключения и технический долг",
    ),
    "codebase": (
        "Версии и инструменты",
        "Модули и каталоги",
        "Типы, схемы и внешние данные",
        "Ошибки и восстановление",
        "Состояние, транзакции и конкурентность",
        "Конфигурация и секреты",
        "Журналы и наблюдаемость",
        "Размер, связность и сложность",
        "Зависимости и созданный код",
        "Миграции и обратная совместимость",
        "Исполняемые правила",
        "Исключения",
    ),
    "quality": (
        "Карта рисков",
        "Публичные швы",
        "Базовые проверки",
        "Условные проверки",
        "Проверочные рубежи",
        "Нестабильность и восстановление",
        "Дефект → проверка",
        "Метрики",
    ),
    "authority": ("Дополнительные ограничения проекта",),
    "agent_operations": (
        "Карта контекста",
        "Основные команды",
        "Порядок одной задачи",
        "Делегация",
        "Контрольные точки и восстановление",
        "Документация",
        "Полномочия и опасные действия",
        "Коррекции",
    ),
    "verification": ("Непроверенное",),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def emit(
    status: str,
    summary: str,
    *,
    next_actions: list[str] | None = None,
    artifacts: list[str] | None = None,
    data: dict[str, Any] | None = None,
    code: int = 0,
) -> int:
    payload = {
        "status": status,
        "summary": summary,
        "next_actions": next_actions or [],
        "artifacts": artifacts or [],
        "data": data or {},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return code


def root_path(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Корень репозитория не существует или не является каталогом: {root}")
    return root


def inside(root: Path, raw: str | Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Путь выходит за пределы репозитория: {candidate}") from exc
    return candidate


def safe_repo_path(root: Path, raw: str | Path, *, expected: str | None = None) -> Path:
    """Return a lexical in-repo path and reject every existing symlink component."""
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = Path(os.path.abspath(os.fspath(candidate)))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Путь выходит за пределы репозитория: {candidate}") from exc

    current = root
    if current.is_symlink():
        raise ValueError(f"Корень репозитория не должен быть символической ссылкой: {current}")
    for index, part in enumerate(relative.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Символическая ссылка запрещена в служебном пути: {current}")
        if index < len(relative.parts) - 1 and current.exists() and not current.is_dir():
            raise ValueError(f"Компонент пути не является каталогом: {current}")

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Путь через ссылку выходит за пределы репозитория: {candidate}") from exc
    if expected == "file" and candidate.exists() and not candidate.is_file():
        raise ValueError(f"Ожидался обычный файл: {candidate}")
    if expected == "dir" and candidate.exists() and not candidate.is_dir():
        raise ValueError(f"Ожидался каталог: {candidate}")
    return candidate


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Файл не найден: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON в {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Ожидался JSON-объект: {path}")
    return value


def write_text_atomic(root: Path, path: Path, text: str) -> None:
    destination = safe_repo_path(root, path, expected="file")
    parent = safe_repo_path(root, destination.parent, expected="dir")
    parent.mkdir(parents=True, exist_ok=True)
    parent = safe_repo_path(root, parent, expected="dir")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=os.fspath(parent),
        text=True,
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        safe_repo_path(root, temporary, expected="file")
        safe_repo_path(root, destination, expected="file")
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_json_atomic(root: Path, path: Path, value: dict[str, Any]) -> None:
    write_text_atomic(
        root,
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextlib.contextmanager
def project_state_lock(
    root: Path, *, wait_seconds: float = 5.0, stale_seconds: int = 120
) -> Iterator[None]:
    """Serialize Project Start state writers and recover only demonstrably stale locks."""
    lock = safe_repo_path(root, STATE_LOCK_REL, expected="file")
    lock.parent.mkdir(parents=True, exist_ok=True)
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
            if age > stale_seconds and not _pid_is_alive(pid):
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise ValueError(f"Project Start state занят другим процессом: {root}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} at={now()}\n".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def save_project_state(
    root: Path,
    state: dict[str, Any],
    *,
    expected_sha256: str | None = None,
    require_absent: bool = False,
) -> str:
    """CAS-write the shared state under the same lock used by maintenance."""
    path = safe_repo_path(root, STATE_REL, expected="file")
    loaded_sha256 = state.get("_loaded_state_sha256")
    expected = expected_sha256 if expected_sha256 is not None else loaded_sha256
    payload = dict(state)
    payload.pop("_loaded_state_sha256", None)
    with project_state_lock(root):
        current = sha256_file(root, STATE_REL) if path.is_file() else None
        if require_absent and current is not None:
            raise ValueError("Project Start state появился после preview; повтори команду на свежем состоянии.")
        if expected is not None and current != expected:
            raise ValueError("Project Start state изменился конкурентно; перечитай состояние и повтори шаг.")
        write_json_atomic(root, path, payload)
        digest = sha256_file(root, STATE_REL)
    state["_loaded_state_sha256"] = digest
    return digest


def copy_template(root: Path, template_name: str, destination_rel: str) -> tuple[str, str]:
    destination = safe_repo_path(root, destination_rel, expected="file")
    if destination.exists():
        return "existing", rel(root, destination)
    source = TEMPLATE_DIR / template_name
    if not source.is_file():
        raise ValueError(f"Отсутствует шаблон навыка: {source}")
    write_text_atomic(root, destination, source.read_text(encoding="utf-8"))
    return "created", rel(root, destination)


def default_artifacts(docs_dir: str, business_doc: str | None, decisions_doc: str | None) -> dict[str, str]:
    base = Path(docs_dir)
    return {
        "business": business_doc or (base / "PROJECT.md").as_posix(),
        "decisions": decisions_doc or (base / "DECISIONS.md").as_posix(),
        "context": "CONTEXT.md",
        "adr_dir": "docs/adr",
        "foundation_manifest": ".project-start/foundation.json",
        "foundation": (base / "FOUNDATION.md").as_posix(),
        "codebase": (base / "CODEBASE.md").as_posix(),
        "quality": (base / "QUALITY.md").as_posix(),
        "authority": (base / "AUTHORITY.md").as_posix(),
        "agent_operations": (base / "AGENT-OPERATIONS.md").as_posix(),
        "plan": (base / "PLAN.md").as_posix(),
        "verification": (base / "VERIFICATION.md").as_posix(),
    }


def new_state(docs_dir: str, business_doc: str | None, decisions_doc: str | None) -> dict[str, Any]:
    stamp = now()
    return {
        "schema_version": 2,
        "graph_version": GRAPH["graph_version"],
        "graph_sha256": hashlib.sha256(GRAPH_PATH.read_bytes()).hexdigest(),
        "phase": "discovery",
        "created_at": stamp,
        "updated_at": stamp,
        "approvals": {"business": None, "foundation": None, "plan": None},
        "records": {},
        "maintenance": {"status": "not-ready", "history": []},
        "artifacts": default_artifacts(docs_dir, business_doc, decisions_doc),
        "history": [{"at": stamp, "event": "initialized", "phase": "discovery"}],
    }


def validate_artifact_paths(root: Path, state: dict[str, Any]) -> None:
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("В state отсутствует объект artifacts.")
    required = set(default_artifacts("docs/project", None, None))
    missing = sorted(required - set(artifacts))
    if missing:
        raise ValueError("В state отсутствуют пути артефактов: " + ", ".join(missing))
    if artifacts.get("foundation_manifest") != ".project-start/foundation.json":
        raise ValueError("foundation_manifest обязан оставаться .project-start/foundation.json")

    checked: dict[str, Path] = {}
    for key in sorted(required):
        raw = artifacts.get(key)
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"Некорректный путь артефакта {key}.")
        if Path(raw).is_absolute():
            raise ValueError(f"Путь артефакта {key} должен быть относительным к репозиторию: {raw}")
        expected = "dir" if key == "adr_dir" else "file"
        path = safe_repo_path(root, raw, expected=expected)
        relative = Path(rel(root, path))
        if key != "foundation_manifest" and (
            relative == Path(".project-start") or Path(".project-start") in relative.parents
        ):
            raise ValueError(f"Артефакт {key} не может находиться в .project-start: {relative}")
        if relative == STATE_REL:
            raise ValueError(f"Артефакт {key} пересекается с состоянием project-start.")
        checked[key] = path

    reverse: dict[Path, str] = {}
    for key, path in checked.items():
        if path in reverse:
            raise ValueError(f"Артефакты {reverse[path]} и {key} используют один путь: {path}")
        reverse[path] = key
    items = list(checked.items())
    for index, (left_key, left) in enumerate(items):
        for right_key, right in items[index + 1 :]:
            if left in right.parents or right in left.parents:
                raise ValueError(
                    f"Пути артефактов пересекаются как файл и каталог: {left_key}={left}, {right_key}={right}"
                )
    safe_repo_path(root, STATE_REL, expected="file")


def load_state(root: Path) -> dict[str, Any]:
    path = safe_repo_path(root, STATE_REL, expected="file")
    state = load_json(path)
    if state.get("schema_version") != 2:
        raise ValueError("Неподдерживаемая версия .project-start/state.json")
    if state.get("phase") not in PHASE_ORDER:
        raise ValueError(f"Некорректная фаза project-start: {state.get('phase')}")
    if not isinstance(state.get("approvals"), dict) or not isinstance(state.get("records"), dict):
        raise ValueError("Некорректная структура approvals/records в state.")
    validate_artifact_paths(root, state)
    state["_loaded_state_sha256"] = sha256_file(root, STATE_REL)
    return state


def maintenance_blocking_reason(state: dict[str, Any]) -> str | None:
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    status = maintenance.get("status")
    legacy_state = not isinstance(state.get("graph_v3"), dict)
    if status == "operational" or (
        status == "not-ready"
        and (legacy_state or state.get("phase") not in {"execution", "complete"})
    ):
        return None
    known = {"maintenance-required", "running", "blocked", "reopen-required", "restart-required"}
    if status not in known:
        return f"Неизвестный maintenance status {status!r}; Project Start блокирует продолжение fail-closed."
    active = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
    pending = maintenance.get("pending_reopen") if isinstance(maintenance.get("pending_reopen"), dict) else {}
    run_id = active.get("run_id") or pending.get("run_id") or "unknown"
    if status == "reopen-required":
        return (
            f"Документация требует reopen {pending.get('stage')}: {pending.get('rationale')} "
            f"(maintenance run {run_id})."
        )
    if status == "blocked":
        return f"Документационный maintenance run {run_id} заблокирован; сначала выполни retry/разбор причины."
    if status == "maintenance-required":
        required = maintenance.get("maintenance_required") if isinstance(maintenance.get("maintenance_required"), dict) else {}
        return (
            "Документация ожидает обработку Task Delivery handoff "
            f"задачи {required.get('task_id')}; сначала запусти maintenance route."
        )
    if status == "restart-required":
        restart = maintenance.get("pending_restart") if isinstance(maintenance.get("pending_restart"), dict) else {}
        return (
            "Документационный maintenance требует свежий Project Start run после прерывания "
            f"{restart.get('run_id')}: {restart.get('reason')}."
        )
    return f"Документационный maintenance run {run_id} ещё выполняется; дождись PASS или явного reopen."


def v3_integrity_issues(root: Path, state: dict[str, Any]) -> list[dict[str, str]]:
    graph_v3 = state.get("graph_v3") if isinstance(state.get("graph_v3"), dict) else {}
    issues: list[dict[str, str]] = []
    canonical = graph_v3.get("canonical_docs")
    hashes = graph_v3.get("canonical_doc_hashes")
    if graph_v3.get("status") != "operational" or not isinstance(canonical, list) or not canonical:
        return [{"severity": "error", "artifact": STATE_REL.as_posix(), "message": "graph_v3 operational ledger повреждён."}]
    if not isinstance(hashes, dict) or set(hashes) != set(canonical):
        issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": "graph_v3 canonical hashes не совпадают с canonical_docs."})
        return issues
    try:
        current = {relative: sha256_file(root, relative) for relative in canonical}
    except ValueError as exc:
        issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": str(exc)})
        return issues
    current_digest = hashlib.sha256(
        json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if current != hashes or current_digest != graph_v3.get("docs_sha256"):
        issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": "Канонические документы дрейфовали после последнего v3 completion."})
    agent_hashes = graph_v3.get("agent_instruction_doc_hashes")
    discovered_agents: set[str] = set()
    for current_dir, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current_dir)
        directories[:] = [
            name
            for name in directories
            if name not in {
                ".agent-graphs", ".codex", ".git", ".mypy_cache", ".project-start",
                ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "build",
                "coverage", "dist", "generated", "node_modules", "vendor",
            }
            and not (current_path / name).is_symlink()
        ]
        if "AGENTS.md" in names:
            path = current_path / "AGENTS.md"
            if path.is_file() and not path.is_symlink():
                discovered_agents.add(path.relative_to(root).as_posix())
    if not isinstance(agent_hashes, dict) or set(agent_hashes) != discovered_agents:
        issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": "Набор AGENTS.md дрейфовал после последнего v3 completion."})
    elif any(sha256_file(root, relative) != digest for relative, digest in agent_hashes.items()):
        issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": "Содержимое AGENTS.md дрейфовало после последнего v3 completion."})
    if state.get("graph_version") != GRAPH.get("graph_version") or state.get("graph_sha256") != hashlib.sha256(GRAPH_PATH.read_bytes()).hexdigest():
        issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": "Shared state связан с другой версией Project Start graph."})
    return issues


def reject_legacy_mutation_of_v3(state: dict[str, Any]) -> None:
    if isinstance(state.get("graph_v3"), dict) and state["graph_v3"].get("status") == "operational":
        raise ValueError("Состоянием владеет Project Start v3; используй project_graph.py, а не legacy-команду.")


def cmd_dependencies(args: argparse.Namespace) -> int:
    roots: list[Path] = []
    if args.skills_root:
        roots.append(Path(args.skills_root).expanduser())
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    roots.append(Path.home() / ".codex" / "skills")

    unique_roots: list[Path] = []
    for item in roots:
        resolved = item.resolve()
        if resolved not in unique_roots:
            unique_roots.append(resolved)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in EXPECTED_SKILLS:
        found: Path | None = None
        for base in unique_roots:
            candidate = base / name
            if (candidate / "SKILL.md").is_file():
                found = candidate
                break
        if found is None:
            missing.append(name)
            rows.append({"name": name, "found": False, "path": None, "openai_metadata": False})
        else:
            rows.append(
                {
                    "name": name,
                    "found": True,
                    "path": str(found),
                    "openai_metadata": (found / "agents" / "openai.yaml").is_file(),
                }
            )

    if missing:
        return emit(
            "warning",
            f"Не найдены вспомогательные навыки: {', '.join(missing)}",
            next_actions=["Завершить их установку или явно описать замену; project-start может продолжить осмотр без них."],
            artifacts=[str(path) for path in unique_roots],
            data={"skills": rows, "missing": missing},
        )
    return emit(
        "success",
        "Все вспомогательные навыки project-start найдены.",
        artifacts=[row["path"] for row in rows if row["path"]],
        data={"skills": rows, "missing": []},
    )


def git_snapshot(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        return {"is_repo": False, "branch": None, "dirty_entries": None, "error": None}
    try:
        branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {
            "is_repo": True,
            "branch": branch.stdout.strip() or None,
            "dirty_entries": len([line for line in dirty.stdout.splitlines() if line.strip()]),
            "error": (branch.stderr or dirty.stderr).strip() or None,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"is_repo": True, "branch": None, "dirty_entries": None, "error": str(exc)}


def cmd_inspect(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
    except ValueError as exc:
        return emit("error", str(exc), next_actions=["Исправить --root и повторить."], code=2)

    manifests = {
        "javascript": ["package.json", "pnpm-workspace.yaml", "yarn.lock", "package-lock.json", "bun.lock"],
        "python": ["pyproject.toml", "requirements.txt", "uv.lock", "poetry.lock"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "go": ["go.mod", "go.sum"],
        "jvm": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "other": ["Gemfile", "composer.json", "Dockerfile", "docker-compose.yml", "compose.yaml"],
    }
    found_manifests = {
        group: [name for name in names if (root / name).exists()]
        for group, names in manifests.items()
    }
    found_manifests = {group: names for group, names in found_manifests.items() if names}
    docs = [
        name
        for name in (
            "AGENTS.md",
            "CLAUDE.md",
            "CONTEXT.md",
            "CONTEXT-MAP.md",
            "ARCHITECTURE.md",
            "README.md",
            "docs",
        )
        if (root / name).exists()
    ]
    ci = [name for name in (".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml") if (root / name).exists()]
    tests = [name for name in ("tests", "test", "spec", "e2e", "playwright.config.ts", "pytest.ini") if (root / name).exists()]
    sources = [name for name in ("src", "app", "apps", "packages", "services", "lib") if (root / name).exists()]
    state_path = root / STATE_REL
    state_data: dict[str, Any] | None = None
    state_error: str | None = None
    integrity_issues: list[dict[str, str]] = []
    if state_path.exists():
        try:
            state_data = load_state(root)
            integrity_issues = state_integrity_issues(root, state_data)
        except ValueError as exc:
            state_error = str(exc)

    status = "warning" if state_error or integrity_issues else "success"
    summary = "Репозиторий осмотрен."
    if not state_path.exists():
        summary += " Состояние project-start ещё не создано."
    elif state_error or integrity_issues:
        summary += " Состояние нельзя безопасно продолжать без явного восстановления."
    return emit(
        status,
        summary,
        next_actions=(
            ["Показать ошибку/расхождения и выполнить migrate либо reopen; не продолжать текущую фазу."]
            if state_error or integrity_issues
            else [
                "Сопоставить найденные соглашения с каноническими артефактами.",
                "Показать предварительный bootstrap discovery перед записью.",
            ]
        ),
        artifacts=[str(root / name) for name in docs] + ([str(state_path)] if state_path.exists() else []),
        data={
            "root": str(root),
            "git": git_snapshot(root),
            "manifests": found_manifests,
            "docs": docs,
            "ci": ci,
            "tests": tests,
            "source_roots": sources,
            "state": state_data,
            "state_error": state_error,
            "state_integrity_issues": integrity_issues,
        },
    )


def stage_files(state: dict[str, Any], stage: str) -> list[tuple[str, str]]:
    artifacts = state["artifacts"]
    mapping = {
        "discovery": [
            ("PROJECT.md", artifacts["business"]),
            ("DECISIONS.md", artifacts["decisions"]),
            ("CONTEXT.md", artifacts["context"]),
        ],
        "foundation": [
            ("foundation.json", artifacts["foundation_manifest"]),
            ("FOUNDATION.md", artifacts["foundation"]),
            ("CODEBASE.md", artifacts["codebase"]),
            ("QUALITY.md", artifacts["quality"]),
            ("AUTHORITY.md", artifacts["authority"]),
            ("AGENT-OPERATIONS.md", artifacts["agent_operations"]),
            ("VERIFICATION.md", artifacts["verification"]),
        ],
        "planning": [("PLAN.md", artifacts["plan"])],
    }
    return mapping[stage]


def cmd_bootstrap(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state_path = safe_repo_path(root, STATE_REL, expected="file")
        if state_path.exists():
            state = load_state(root)
            reject_legacy_mutation_of_v3(state)
        else:
            docs_dir = rel(root, safe_repo_path(root, args.docs_dir, expected="dir"))
            business_doc = rel(root, safe_repo_path(root, args.business_doc, expected="file")) if args.business_doc else None
            decisions_doc = rel(root, safe_repo_path(root, args.decisions_doc, expected="file")) if args.decisions_doc else None
            state = new_state(docs_dir, business_doc, decisions_doc)
        validate_artifact_paths(root, state)
        if args.stage == "foundation" and not state["approvals"].get("business"):
            raise ValueError("Нельзя создавать основание до одобрения бизнес-логики.")
        if args.stage == "planning" and not state["approvals"].get("foundation"):
            raise ValueError("Нельзя создавать план до одобрения основания.")
        planned = []
        for template, destination_rel in stage_files(state, args.stage):
            destination = safe_repo_path(root, destination_rel, expected="file")
            planned.append(
                {
                    "template": template,
                    "destination": rel(root, destination),
                    "action": "keep" if destination.exists() else "create",
                }
            )
    except (KeyError, ValueError) as exc:
        return emit(
            "error",
            str(exc),
            next_actions=["Исправить состояние/пути или получить недостающее одобрение; затем повторить предварительный просмотр."],
            code=2,
        )

    if not args.apply:
        return emit(
            "success",
            f"Предварительный просмотр bootstrap {args.stage}; файлы не изменены.",
            next_actions=["Показать план пользователю и повторить с --apply после подтверждения."],
            artifacts=[str(root / item["destination"]) for item in planned],
            data={"apply": False, "planned": planned},
        )

    changed: list[str] = []
    kept: list[str] = []
    try:
        for template, destination_rel in stage_files(state, args.stage):
            action, destination = copy_template(root, template, destination_rel)
            (changed if action == "created" else kept).append(destination)
        if args.stage == "foundation" and state["artifacts"]["foundation_manifest"] in changed:
            manifest_path = safe_repo_path(root, state["artifacts"]["foundation_manifest"], expected="file")
            manifest = load_json(manifest_path)
            manifest["authority_document"] = state["artifacts"]["authority"]
            manifest["codebase_document"] = state["artifacts"]["codebase"]
            manifest["agent_operations_document"] = state["artifacts"]["agent_operations"]
            manifest["quality_document"] = state["artifacts"]["quality"]
            manifest["verification_document"] = state["artifacts"]["verification"]
            write_json_atomic(root, manifest_path, manifest)
        if not state_path.exists():
            save_project_state(root, state, require_absent=True)
            changed.append(STATE_REL.as_posix())
    except (OSError, ValueError) as exc:
        return emit(
            "error",
            f"Bootstrap остановлен: {exc}",
            next_actions=["Устранить причину; существующие файлы не перезаписывать; повторить команду безопасно."],
            artifacts=[str(root / item) for item in changed],
            data={"created_before_error": changed},
            code=2,
        )
    return emit(
        "success",
        f"Bootstrap {args.stage} применён без перезаписи существующих файлов.",
        next_actions=["Заполнить обязательные маркеры и выполнить validate для этапа."],
        artifacts=[str(root / item) for item in changed + kept],
        data={"created": changed, "kept": kept},
    )


def marker_issues(root: Path, path_rel: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return [{"severity": "error", "artifact": path_rel, "message": "Обязательный файл отсутствует."}]
    text = path.read_text(encoding="utf-8")
    count = text.count(REQUIRED_MARKER)
    if count:
        return [
            {
                "severity": "error",
                "artifact": path_rel,
                "message": f"Остались обязательные маркеры: {count}.",
            }
        ]
    return []


def meaningful_markdown(value: str) -> bool:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.DOTALL)
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"\[[^\]]+\]\([^)]+\)", " ссылка ", value)
    value = re.sub(r"[|#>*_`\-:]+", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    compact = " ".join(value.split()).strip()
    if len(compact) < 12 or len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]", compact)) < 10:
        return False
    lowered = compact.casefold()
    rejected = (
        "project start required",
        "tbd",
        "todo",
        "заполнить позже",
        "запиши осознанные",
        "перечисли оставшиеся",
        "отслеживай первую",
    )
    return not any(item in lowered for item in rejected)


def filled_string(value: Any, minimum: int = 2) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum and value.strip() not in {REQUIRED_VALUE, "<required>"}


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end() : end].strip()
    return sections


def markdown_section_issues(root: Path, path_rel: str, artifact_key: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return []
    sections = markdown_sections(path.read_text(encoding="utf-8"))
    issues: list[dict[str, str]] = []
    for heading in MARKDOWN_SECTIONS.get(artifact_key, ()):
        body = sections.get(heading)
        if body is None:
            issues.append({"severity": "error", "artifact": path_rel, "message": f"Отсутствует раздел: {heading}."})
        elif not meaningful_markdown(body):
            issues.append({"severity": "error", "artifact": path_rel, "message": f"Раздел не содержит проверяемого содержания: {heading}."})
    return issues


def decisions_issues(root: Path, path_rel: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return []
    valid_rows = 0
    allowed_kinds = {"fact", "assumption", "decision", "risk"}
    allowed_states = {"open", "validated", "rejected", "accepted", "mitigated"}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9 or cells[0] in {"ID", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        if (
            re.fullmatch(r"[A-Za-z]+-\d+", cells[0])
            and cells[1] in allowed_kinds
            and meaningful_markdown(cells[2])
            and cells[3] in allowed_states
            and all(filled_string(cell, 3) for cell in cells[4:9])
        ):
            valid_rows += 1
    if valid_rows:
        return []
    return [{"severity": "error", "artifact": path_rel, "message": "Нет полной строки факта, предположения, решения или риска с источником, владельцем и проверкой."}]


def authority_issues(root: Path, path_rel: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return []
    rows = 0
    invalid: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in {"Эффект", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        rows += 1
        if cells[1] not in {"allow", "approval", "deny"}:
            invalid.append(cells[0])
    issues: list[dict[str, str]] = []
    if rows < 10:
        issues.append({"severity": "error", "artifact": path_rel, "message": "Таблица полномочий должна покрывать не менее 10 внешних эффектов."})
    if invalid:
        issues.append({"severity": "error", "artifact": path_rel, "message": "Некорректный режим полномочий для: " + ", ".join(invalid)})
    return issues


def context_issues(root: Path, path_rel: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return [{"severity": "error", "artifact": path_rel, "message": "Обязательный словарь CONTEXT.md отсутствует."}]
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^\*\*([^*<>]+)\*\*:\s*$", text, flags=re.MULTILINE))
    valid = 0
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        body = re.sub(r"(?im)^_Avoid_:\s*.*$", "", body)
        if filled_string(match.group(1), 2) and meaningful_markdown(body):
            valid += 1
    if valid:
        return []
    return [{"severity": "error", "artifact": path_rel, "message": "CONTEXT.md должен содержать хотя бы один канонический предметный термин с определением."}]


def plan_issues(root: Path, path_rel: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    issues: list[dict[str, str]] = []
    sections = markdown_sections(text)
    for heading in ("Цель", "Порядок и открытый фронт", "Правило дробления"):
        if heading not in sections or not meaningful_markdown(sections[heading]):
            issues.append({"severity": "error", "artifact": path_rel, "message": f"Раздел плана не заполнен: {heading}."})

    matches = list(re.finditer(r"^###\s+(\d+)\.\s+(.+?)\s*$", text, flags=re.MULTILINE))
    if not 5 <= len(matches) <= 10:
        issues.append({"severity": "error", "artifact": path_rel, "message": f"План должен содержать 5–10 крупных частей; найдено: {len(matches)}."})
        return issues
    numbers = [int(match.group(1)) for match in matches]
    if numbers != list(range(1, len(matches) + 1)):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Крупные части плана должны быть последовательно пронумерованы с 1."})
    labels = ("Поведение", "Доказательство готовности", "Зависит от", "Основные риски", "Не входит")
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else text.find("\n## ", match.end())
        if end < 0:
            end = len(text)
        block = text[match.end() : end]
        if not meaningful_markdown(match.group(2)):
            issues.append({"severity": "error", "artifact": path_rel, "message": f"Часть {numbers[index]} не имеет содержательного названия."})
        for label in labels:
            found = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+?)(?=\n-\s+\*\*|\Z)", block, flags=re.DOTALL)
            if not found or not meaningful_markdown(found.group(1)):
                issues.append({"severity": "error", "artifact": path_rel, "message": f"Часть {numbers[index]}: не заполнено поле «{label}»."})
    return issues


def verification_history_rows(root: Path, path_rel: str) -> list[dict[str, Any]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 8 or cells[0] in {"Дата", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        if not cells[2]:
            continue
        status = cells[5].casefold()
        actual = cells[4].casefold()
        failure_words = ("fail", "error", "nonzero", "failed", "ошиб", "сбой")
        success = status in {"0", "success", "pass", "passed", "ok", "успех", "пройдено"} and not any(
            word in actual or word in status for word in failure_words
        )
        rows.append(
            {
                "date": cells[0],
                "area": cells[1],
                "command": cells[2],
                "expected": cells[3],
                "actual": cells[4],
                "status": cells[5],
                "artifact": cells[6],
                "reviewer": cells[7],
                "success": success,
            }
        )
    return rows


def verification_rows(root: Path, path_rel: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in verification_history_rows(root, path_rel):
        latest[row["command"]] = row
    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    for row in latest.values():
        public = {key: str(row[key]) for key in ("command", "date", "area", "actual", "status", "artifact")}
        (successes if row["success"] else failures).append(public)
    return successes, failures


def verification_row_fingerprint(row: dict[str, Any]) -> str:
    public = {key: row[key] for key in sorted(row) if key != "success"}
    canonical = json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def markdown_link_issues(root: Path, path_rel: str) -> list[dict[str, str]]:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return []
    issues: list[dict[str, str]] = []
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for target in pattern.findall(path.read_text(encoding="utf-8")):
        target = target.strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            issues.append({"severity": "warning", "artifact": path_rel, "message": f"Ссылка выходит за корень: {target}"})
            continue
        if not candidate.exists():
            issues.append({"severity": "warning", "artifact": path_rel, "message": f"Битая относительная ссылка: {target}"})
    return issues


def find_required_values(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if value is None or value == REQUIRED_VALUE:
        found.append(prefix or "<root>")
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(find_required_values(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_required_values(item, f"{prefix}[{index}]"))
    return found


def foundation_issues(root: Path, state: dict[str, Any]) -> list[dict[str, str]]:
    path_rel = state["artifacts"]["foundation_manifest"]
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        return [{"severity": "error", "artifact": path_rel, "message": "Манифест основания отсутствует."}]
    try:
        manifest = load_json(path)
    except ValueError as exc:
        return [{"severity": "error", "artifact": path_rel, "message": str(exc)}]
    issues: list[dict[str, str]] = []
    unresolved = find_required_values(manifest)
    if unresolved:
        issues.append(
            {
                "severity": "error",
                "artifact": path_rel,
                "message": "Не заполнены обязательные значения: " + ", ".join(unresolved[:20]),
            }
        )
    if manifest.get("schema_version") != 1:
        issues.append({"severity": "error", "artifact": path_rel, "message": "schema_version foundation.json должен быть 1."})
    if not filled_string(manifest.get("profile")):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Не задан содержательный профиль основания."})
    if not isinstance(manifest.get("profile_version"), int) or manifest.get("profile_version", 0) < 1:
        issues.append({"severity": "error", "artifact": path_rel, "message": "profile_version должен быть положительным целым числом."})
    product_shape = manifest.get("product_shape")
    if not isinstance(product_shape, list) or not product_shape or not all(isinstance(item, str) and item.strip() for item in product_shape):
        issues.append({"severity": "error", "artifact": path_rel, "message": "product_shape должен быть непустым списком строк."})

    research = manifest.get("stack_research")
    if not isinstance(research, dict):
        research = {}
        issues.append({"severity": "error", "artifact": path_rel, "message": "stack_research должен быть объектом."})
    if research.get("completed") is not True:
        issues.append({"severity": "error", "artifact": path_rel, "message": "Исследование стека не отмечено завершённым."})
    if not isinstance(research.get("date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", research.get("date", "")):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Дата исследования должна иметь формат YYYY-MM-DD."})
    research_artifact = research.get("artifact")
    if not isinstance(research_artifact, str) or research_artifact in ("", REQUIRED_VALUE):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Не указан артефакт исследования стека."})
    elif isinstance(research_artifact, str):
        if not research_artifact.startswith(("http://", "https://")):
            research_path = research_artifact.split("#", 1)[0]
            try:
                exists = safe_repo_path(root, research_path, expected="file").is_file()
            except ValueError:
                exists = False
            if not exists:
                issues.append({"severity": "error", "artifact": path_rel, "message": f"Артефакт исследования стека не найден: {research_artifact}"})
    alternatives = research.get("alternatives_compared", [])
    external = research.get("external_constraint", False)
    if not isinstance(external, bool):
        issues.append({"severity": "error", "artifact": path_rel, "message": "external_constraint должен быть boolean."})
        external = False
    if not isinstance(alternatives, list) or not all(isinstance(item, str) and meaningful_markdown(item) for item in alternatives):
        issues.append({"severity": "error", "artifact": path_rel, "message": "alternatives_compared должен быть списком содержательных вариантов."})
        alternatives = []
    if not external and len(alternatives) < 2:
        issues.append({"severity": "error", "artifact": path_rel, "message": "Нужно сравнить минимум два варианта стека."})
    if external and not filled_string(research.get("constraint_reason"), 12):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Для обязательного стека нужна причина внешнего ограничения."})

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}
    for key in ("language", "version", "package_manager"):
        if not filled_string(runtime.get(key)):
            issues.append({"severity": "error", "artifact": path_rel, "message": f"runtime.{key} не заполнен содержательно."})

    architecture = manifest.get("architecture")
    if not isinstance(architecture, dict):
        architecture = {}
    if not filled_string(architecture.get("style")):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Не описан стиль архитектуры."})
    modules = architecture.get("modules")
    if not isinstance(modules, list) or len(modules) < 2 or not all(filled_string(item) for item in modules):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Не описаны модули архитектуры."})
    dependency_rules = architecture.get("dependency_rules")
    if not isinstance(dependency_rules, list) or not dependency_rules or not all(isinstance(item, str) and meaningful_markdown(item) for item in dependency_rules):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Не описаны исполняемые правила зависимостей."})
    if not filled_string(architecture.get("structural_check_command"), 3):
        issues.append({"severity": "error", "artifact": path_rel, "message": "Не задана команда структурной проверки."})

    required_commands = (
        "install", "run", "stop", "seed", "reset", "format", "lint", "typecheck", "test_fast", "test_full", "verify", "smoke"
    )
    commands = manifest.get("commands")
    if not isinstance(commands, dict):
        commands = {}
    for key in required_commands:
        command = commands.get(key)
        if not filled_string(command, 2):
            issues.append({"severity": "error", "artifact": path_rel, "message": f"commands.{key} не заполнена содержательно."})

    required_risk_flags = {
        "public_web", "authentication", "personal_or_sensitive_data", "payments", "file_uploads",
        "user_code_execution", "public_api_or_webhooks", "regulated_market", "accessibility_target",
        "critical_persistence", "published_artifacts", "reliability_targets",
    }
    risk_flags = manifest.get("risk_flags")
    if not isinstance(risk_flags, dict) or not risk_flags:
        issues.append({"severity": "error", "artifact": path_rel, "message": "risk_flags отсутствует."})
    else:
        missing_flags = sorted(required_risk_flags - set(risk_flags))
        if missing_flags:
            issues.append({"severity": "error", "artifact": path_rel, "message": "Не заданы risk_flags: " + ", ".join(missing_flags)})
        if any(not isinstance(risk_flags.get(key), bool) for key in required_risk_flags):
            issues.append({"severity": "error", "artifact": path_rel, "message": "Каждый обязательный risk_flags.* должен быть true или false."})

    document_fields = {
        "authority_document": "authority",
        "codebase_document": "codebase",
        "agent_operations_document": "agent_operations",
        "quality_document": "quality",
        "verification_document": "verification",
    }
    for field, artifact_key in document_fields.items():
        if manifest.get(field) != state["artifacts"][artifact_key]:
            issues.append({"severity": "error", "artifact": path_rel, "message": f"{field} расходится с state artifacts."})

    verification_rel = state["artifacts"]["verification"]
    successes, failures = verification_rows(root, verification_rel)
    if failures:
        issues.append({"severity": "error", "artifact": verification_rel, "message": f"Последний результат {len(failures)} команд неуспешен."})
    successful_commands = {item["command"] for item in successes}
    required_executions = {
        command for command in commands.values()
        if isinstance(command, str) and not command.casefold().startswith(("not-applicable:", "неприменимо:"))
    }
    structural_command = architecture.get("structural_check_command")
    if isinstance(structural_command, str) and not structural_command.casefold().startswith(("not-applicable:", "неприменимо:")):
        required_executions.add(structural_command)
    missing_executions = sorted(required_executions - successful_commands)
    if missing_executions:
        issues.append({"severity": "error", "artifact": verification_rel, "message": "Нет успешного фактического результата команд: " + ", ".join(missing_executions[:12])})
    return issues


def sha256_file(root: Path, path_rel: str) -> str:
    path = safe_repo_path(root, path_rel, expected="file")
    if not path.is_file():
        raise ValueError(f"Доказательство не является обычным файлом: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gate_snapshot(root: Path, state: dict[str, Any], gate: str) -> dict[str, Any]:
    files: dict[str, str] = {}
    for key in GATE_ARTIFACT_KEYS[gate]:
        path_rel = state["artifacts"][key]
        files[path_rel] = sha256_file(root, path_rel)
    snapshot: dict[str, Any] = {"files": files}
    if gate == "foundation":
        snapshot["milestones"] = {
            event: state.get("records", {}).get(event, {}).get("sha256") for event in FOUNDATION_EVENTS
        }
        implementation_areas = {"implementation", "execution", "release", "реализация", "выпуск"}
        foundation_rows = [
            {key: value for key, value in row.items() if key != "success"}
            for row in verification_history_rows(root, state["artifacts"]["verification"])
            if row["area"].strip().casefold() not in implementation_areas
        ]
        snapshot["foundation_verification"] = sorted(
            foundation_rows,
            key=lambda row: (row["command"], row["date"], row["status"], row["actual"], row["area"]),
        )
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot["fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return snapshot


def approval_issues(root: Path, state: dict[str, Any], gate: str) -> list[dict[str, str]]:
    approval = state.get("approvals", {}).get(gate)
    if not isinstance(approval, dict):
        return [{"severity": "error", "artifact": STATE_REL.as_posix(), "message": f"Рубеж {gate} не одобрен."}]
    try:
        current = gate_snapshot(root, state, gate)
    except ValueError as exc:
        return [{"severity": "error", "artifact": STATE_REL.as_posix(), "message": str(exc)}]
    if approval.get("fingerprint") != current["fingerprint"] or approval.get("files") != current["files"]:
        return [{"severity": "error", "artifact": STATE_REL.as_posix(), "message": f"Одобренные артефакты рубежа {gate} изменились; требуется явный reopen и повторное одобрение."}]
    return []


def record_issues(root: Path, state: dict[str, Any], events: tuple[str, ...]) -> list[dict[str, str]]:
    records = state.get("records", {})
    issues: list[dict[str, str]] = []
    for event in events:
        record = records.get(event)
        if not isinstance(record, dict):
            issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": f"Не зафиксирован обязательный подэтап: {event}."})
            continue
        evidence_rel = record.get("evidence")
        if not isinstance(evidence_rel, str):
            issues.append({"severity": "error", "artifact": STATE_REL.as_posix(), "message": f"У {event} нет пути доказательства."})
            continue
        try:
            current = sha256_file(root, evidence_rel)
        except ValueError as exc:
            issues.append({"severity": "error", "artifact": evidence_rel, "message": str(exc)})
            continue
        if current != record.get("sha256"):
            issues.append({"severity": "error", "artifact": evidence_rel, "message": f"Доказательство подэтапа {event} изменилось после фиксации."})
    return issues


def existing_record_issues(root: Path, state: dict[str, Any], events: tuple[str, ...]) -> list[dict[str, str]]:
    recorded = tuple(event for event in events if event in state.get("records", {}))
    return record_issues(root, state, recorded)


def state_integrity_issues(root: Path, state: dict[str, Any]) -> list[dict[str, str]]:
    phase = state.get("phase")
    index = PHASE_ORDER.index(phase)
    issues: list[dict[str, str]] = []
    if index >= PHASE_ORDER.index("foundation"):
        issues.extend(approval_issues(root, state, "business"))
    if phase == "foundation":
        issues.extend(existing_record_issues(root, state, FOUNDATION_EVENTS))
    elif index >= PHASE_ORDER.index("planning"):
        issues.extend(record_issues(root, state, FOUNDATION_EVENTS))
        issues.extend(approval_issues(root, state, "foundation"))
    if index >= PHASE_ORDER.index("tickets"):
        issues.extend(approval_issues(root, state, "plan"))
    if phase == "tickets":
        issues.extend(existing_record_issues(root, state, TICKET_EVENTS))
    elif index >= PHASE_ORDER.index("execution"):
        issues.extend(record_issues(root, state, TICKET_EVENTS))
    if phase == "execution":
        issues.extend(existing_record_issues(root, state, COMPLETION_EVENTS))
    elif phase == "complete":
        issues.extend(record_issues(root, state, COMPLETION_EVENTS))
    return issues


def evidence_semantic_issues(root: Path, event: str, evidence_rel: str) -> list[str]:
    path = safe_repo_path(root, evidence_rel, expected="file")
    if not path.is_file() or path.stat().st_size == 0:
        return ["Доказательство отсутствует или пусто."]
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = "binary-evidence"
    structured_events = {"foundation-ready", "tickets-approved", "tickets-published", "user-acceptance"}
    if event in structured_events and (
        REQUIRED_MARKER in text or re.search(r"(?im)\bPENDING\b|<[^>]+>", text)
    ):
        return ["Структурированное доказательство осталось шаблоном или содержит незаполненные поля."]
    if event == "foundation-ready":
        required = (
            r"(?im)^PROJECT-START-REVIEW:\s*PASS\s*$",
            r"(?im)^Critical:\s*0\s*$",
            r"(?im)^High:\s*0\s*$",
            r"(?im)^Reviewer:\s*\S.+$",
            r"(?im)^Reviewed-at:\s*\d{4}-\d{2}-\d{2}(?:[T ][0-9:]+(?:Z|[+-][0-9:]+)?)?\s*$",
        )
        if not all(re.search(pattern, text) for pattern in required):
            return ["Обзор должен содержать PASS, нули critical/high, Reviewer и Reviewed-at."]
        sections = markdown_sections(text)
        for heading in ("Область", "Замечания", "Доказательства"):
            if heading not in sections or not meaningful_markdown(sections[heading]):
                return [f"В обзоре не заполнен содержательный раздел «{heading}»."]
    if event == "tickets-approved":
        required = (
            r"(?im)^PROJECT-START-TICKETS-APPROVED:\s*YES\s*$",
            r"(?im)^Approved-by:\s*\S.+$",
            r"(?im)^Approved-at:\s*\d{4}-\d{2}-\d{2}(?:[T ][0-9:]+(?:Z|[+-][0-9:]+)?)?\s*$",
            r"(?im)^Scope:\s*\S.+$",
        )
        if not all(re.search(pattern, text) for pattern in required):
            return ["Одобрение задач должно содержать YES, Approved-by, Approved-at и Scope."]
    if event == "tickets-published":
        if not re.search(r"(?im)^PROJECT-START-TICKETS-PUBLISHED:\s*YES\s*$", text):
            return ["Индекс должен содержать PROJECT-START-TICKETS-PUBLISHED: YES."]
        tracker_match = re.search(r"(?im)^Tracker:\s*(\S.+?)\s*$", text)
        if not tracker_match or not re.search(
            r"(?im)^Published-at:\s*\d{4}-\d{2}-\d{2}(?:[T ][0-9:]+(?:Z|[+-][0-9:]+)?)?\s*$", text
        ):
            return ["Индекс задач должен содержать Tracker и Published-at."]
        receipt_match = re.search(r"(?im)^Receipt:\s*(\S.+?)\s*$", text)
        if not receipt_match or receipt_match.group(1).startswith(("http://", "https://")):
            return ["Индекс задач должен ссылаться на локально сохранённое подтверждение трекера в поле Receipt."]
        receipt = safe_repo_path(root, path.parent / receipt_match.group(1).strip(), expected="file")
        if not receipt.is_file() or receipt == path:
            return ["Локальное подтверждение трекера не найдено или совпадает с индексом задач."]
        receipt_text = receipt.read_text(encoding="utf-8")
        receipt_tracker = re.search(r"(?im)^Tracker:\s*(\S.+?)\s*$", receipt_text)
        if (
            not re.search(r"(?im)^PROJECT-START-TRACKER-RECEIPT:\s*VERIFIED\s*$", receipt_text)
            or not receipt_tracker
            or receipt_tracker.group(1).strip() != tracker_match.group(1).strip()
            or not re.search(r"(?im)^Captured-at:\s*\d{4}-\d{2}-\d{2}(?:[T ][0-9:]+(?:Z|[+-][0-9:]+)?)?\s*$", receipt_text)
            or not re.search(r"(?im)^[-*]\s+\S.+$", receipt_text)
            or REQUIRED_MARKER in receipt_text
            or re.search(r"(?im)\bPENDING\b|<[^>]+>", receipt_text)
        ):
            return ["Подтверждение трекера должно иметь VERIFIED, совпадающий Tracker, Captured-at, сырой идентификатор и не содержать шаблонных полей."]
        ticket_refs = re.findall(r"(?im)^[-*]\s+.+(?:https?://|#[0-9]+|[A-Z]+-[0-9]+|\.md\b).*$", text)
        if not ticket_refs:
            return ["Индекс публикации не содержит ни одной ссылки или идентификатора задачи."]
        markdown_targets = [target.strip() for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)]
        bare_identifiers = re.findall(r"(?<![\w/])(?:[A-Z][A-Z0-9]+-\d+|#\d+)\b", text)
        receipt_refs = [target for target in markdown_targets if target] + bare_identifiers
        if not receipt_refs or not any(reference in receipt_text for reference in receipt_refs):
            return ["Подтверждение трекера не содержит ни одной точной ссылки или идентификатора из опубликованного индекса."]
        for target in markdown_targets:
            target = target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://")):
                continue
            candidate = safe_repo_path(root, path.parent / target)
            if not candidate.is_file():
                return [f"Локальная опубликованная задача не найдена: {target}."]
    if event == "implementation-evidence":
        successes, failures = verification_rows(root, evidence_rel)
        if failures or not successes:
            return ["Доказательство реализации должно содержать успешные строки таблицы VERIFICATION без актуальных сбоев."]
        implementation_areas = {"implementation", "execution", "release", "реализация", "выпуск"}
        if not any(row["area"].strip().casefold() in implementation_areas for row in successes):
            return ["Нужна отдельная успешная строка с областью implementation/execution/release, созданная после реализации."]
    if event == "user-acceptance":
        required = (
            r"(?im)^PROJECT-START-USER-ACCEPTANCE:\s*YES\s*$",
            r"(?im)^Accepted-by:\s*\S.+$",
            r"(?im)^Accepted-at:\s*\d{4}-\d{2}-\d{2}(?:[T ][0-9:]+(?:Z|[+-][0-9:]+)?)?\s*$",
            r"(?im)^Accepted-result:\s*\S.+$",
            r"(?im)^Verified-evidence:\s*\S.+$",
            r"(?im)^Known-followups:\s*\S.+$",
        )
        if not all(re.search(pattern, text) for pattern in required):
            return ["Приёмка должна содержать YES, Accepted-by, Accepted-at, Accepted-result, Verified-evidence и Known-followups."]
        verified_match = re.search(r"(?im)^Verified-evidence:\s*(\S.+?)\s*$", text)
        try:
            verified = safe_repo_path(root, verified_match.group(1).strip(), expected="file") if verified_match else None
        except ValueError:
            verified = None
        if verified is None or not verified.is_file():
            return ["Verified-evidence должен указывать на существующее локальное доказательство внутри репозитория."]
    if text != "binary-evidence" and len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]", text)) < 20:
        return ["Доказательство не содержит содержательного текста."]
    return []


def validate_stage(root: Path, state: dict[str, Any], stage: str, *, include_records: bool = True) -> list[dict[str, str]]:
    artifacts = state.get("artifacts", {})
    issues: list[dict[str, str]] = []
    semantic_keys = ["business"]
    plain_keys = ["decisions"]
    if stage in ("foundation", "planning", "tickets", "execution"):
        issues.extend(approval_issues(root, state, "business"))
        semantic_keys.extend(("foundation", "codebase", "quality", "authority", "agent_operations", "verification"))
        issues.extend(foundation_issues(root, state))
        if include_records:
            issues.extend(record_issues(root, state, FOUNDATION_EVENTS))
    if stage in ("planning", "tickets", "execution"):
        issues.extend(approval_issues(root, state, "foundation"))
        plain_keys.append("plan")
    if stage in ("tickets", "execution"):
        issues.extend(approval_issues(root, state, "plan"))
        if include_records:
            issues.extend(record_issues(root, state, TICKET_EVENTS))

    for key in semantic_keys + plain_keys:
        path_rel = artifacts.get(key)
        if not path_rel:
            continue
        issues.extend(marker_issues(root, path_rel))
        issues.extend(markdown_link_issues(root, path_rel))
        if key in semantic_keys:
            issues.extend(markdown_section_issues(root, path_rel, key))
    issues.extend(decisions_issues(root, artifacts["decisions"]))
    issues.extend(marker_issues(root, artifacts["context"]))
    issues.extend(markdown_link_issues(root, artifacts["context"]))
    issues.extend(context_issues(root, artifacts["context"]))
    if stage in ("foundation", "planning", "tickets", "execution"):
        issues.extend(authority_issues(root, artifacts["authority"]))
    if stage in ("planning", "tickets", "execution"):
        issues.extend(plan_issues(root, artifacts["plan"]))
    return issues


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state = load_state(root)
        issues = validate_stage(root, state, args.stage)
    except ValueError as exc:
        return emit("error", str(exc), next_actions=["Создать или исправить состояние и повторить."], code=2)
    blocking = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    if blocking:
        return emit(
            "error",
            f"Этап {args.stage} не готов: {len(blocking)} блокирующих замечаний.",
            next_actions=["Исправить замечания и повторить validate; не переходить рубеж."],
            artifacts=[str(root / item["artifact"]) for item in issues],
            data={"stage": args.stage, "issues": issues},
            code=1,
        )
    status = "warning" if warnings else "success"
    return emit(
        status,
        f"Этап {args.stage} прошёл машинную проверку" + (f" с {len(warnings)} предупреждениями." if warnings else "."),
        next_actions=["Провести смысловую независимую проверку перед одобрением."],
        artifacts=[str(root / item) for item in state["artifacts"].values() if (root / item).exists()],
        data={"stage": args.stage, "issues": issues},
    )


def cmd_status(args: argparse.Namespace) -> int:
    root: Path | None = None
    try:
        root = root_path(args.root)
        state = load_state(root)
    except ValueError as exc:
        state_exists = root is not None and (root / STATE_REL).exists()
        if state_exists and "Неподдерживаемая версия" in str(exc):
            actions = ["Запустить migrate без --apply, проверить перенос v1 → v2 и применить только после подтверждения."]
        elif state_exists:
            actions = ["Исправить повреждённое состояние или пути; не запускать bootstrap поверх существующего state."]
        else:
            actions = ["Выполнить предварительный bootstrap discovery и применить после подтверждения."]
        return emit(
            "warning",
            str(exc),
            next_actions=actions,
        )
    phase = state.get("phase", "unknown")
    graph_v3_owned = isinstance(state.get("graph_v3"), dict) and state["graph_v3"].get("status") == "operational"
    integrity = v3_integrity_issues(root, state) if graph_v3_owned else state_integrity_issues(root, state)
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    pending_reopen = maintenance.get("pending_reopen") if maintenance.get("status") == "reopen-required" else None
    active_run = maintenance.get("active_run") if isinstance(maintenance.get("active_run"), dict) else {}
    maintenance_blocked = maintenance_blocking_reason(state)
    next_by_phase = {
        "discovery": "Завершить и одобрить бизнес-логику.",
        "foundation": "Исследовать стек, подготовить архитектуру и качество.",
        "planning": "Согласовать крупный план.",
        "tickets": "Одобрить и опубликовать сквозные задачи.",
        "execution": "Исполнять открытый фронт задач по одной итерации.",
        "complete": "Выбрать следующую цель или сопровождать результат.",
    }
    return emit(
        "warning" if integrity or maintenance_blocked else "success",
        (
            maintenance_blocked
            if maintenance_blocked
            else (f"Текущий этап: {phase}." if not integrity else f"Этап {phase} нельзя безопасно продолжать: {len(integrity)} нарушений целостности.")
        ),
        next_actions=(
            [
                f"python3 {Path(__file__).with_name('project_graph.py')} decide --run {active_run.get('run_dir')} --answer <точный-ответ>"
                if graph_v3_owned
                else f"Выполнить preview reopen --stage {pending_reopen.get('stage')}, затем применить после проверки причины."
            ]
            if isinstance(pending_reopen, dict)
            else ["Завершить или восстановить указанный maintenance run; не открывать новую Task Delivery."]
            if maintenance_blocked
            else ["Показать расхождения и выполнить явный reopen подходящего этапа; не продолжать по устаревшему состоянию."]
            if integrity
            else [next_by_phase.get(phase, "Проверить корректность состояния.")]
        ),
        artifacts=[str(root / item) for item in state.get("artifacts", {}).values() if (root / item).exists()],
        data={
            "state": {key: value for key, value in state.items() if key != "_loaded_state_sha256"},
            "planned_artifacts": [item for item in state.get("artifacts", {}).values() if not (root / item).exists()],
            "integrity_issues": integrity,
        },
    )


def cmd_migrate(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state_path = safe_repo_path(root, STATE_REL, expected="file")
        old = load_json(state_path)
        if old.get("schema_version") == 2:
            return emit(
                "success",
                "Состояние уже использует schema_version 2; миграция не нужна.",
                artifacts=[str(state_path)],
                data={"apply": False, "schema_version": 2},
            )
        if old.get("schema_version") != 1:
            raise ValueError(f"Поддерживается миграция только schema_version 1; найдено: {old.get('schema_version')}")
        old_artifacts = old.get("artifacts") if isinstance(old.get("artifacts"), dict) else {}
        business = old_artifacts.get("business") if isinstance(old_artifacts.get("business"), str) else "docs/project/PROJECT.md"
        decisions = old_artifacts.get("decisions") if isinstance(old_artifacts.get("decisions"), str) else "docs/project/DECISIONS.md"
        docs_dir = Path(business).parent.as_posix() or "docs/project"
        migrated = new_state(docs_dir, business, decisions)
        for key, value in old_artifacts.items():
            if key in migrated["artifacts"] and isinstance(value, str) and value.strip():
                migrated["artifacts"][key] = value
        migrated["artifacts"]["foundation_manifest"] = ".project-start/foundation.json"
        migrated["schema_version"] = 2
        migrated["phase"] = "discovery"
        migrated["created_at"] = old.get("created_at", migrated["created_at"])
        migrated["approvals"] = {"business": None, "foundation": None, "plan": None}
        migrated["records"] = {}
        migrated["history"] = list(old.get("history", [])) if isinstance(old.get("history"), list) else []
        migrated["history"].append(
            {"at": now(), "event": "migrated:v1-to-v2", "phase": "discovery", "previous_phase": old.get("phase"), "note": args.note}
        )
        migrated["updated_at"] = now()
        validate_artifact_paths(root, migrated)
        backup = safe_repo_path(root, ".project-start/state.v1.backup.json", expected="file")
        backup_preexisting = backup.exists()
        if backup_preexisting and load_json(backup) != old:
            raise ValueError(f"Существующая резервная копия не совпадает с текущим v1 state; требуется ручная проверка: {backup}")
        if not args.note.strip():
            raise ValueError("Миграция требует заметку о причине и контексте обновления.")
    except ValueError as exc:
        return emit("error", str(exc), next_actions=["Проверить старый state и пути; не изменять его вручную."], code=2)

    preview = {
        "apply": bool(args.apply),
        "from_schema": 1,
        "to_schema": 2,
        "previous_phase": old.get("phase"),
        "new_phase": "discovery",
        "backup": rel(root, backup),
        "backup_action": "keep-matching" if backup_preexisting else "create",
        "approvals_reset": ["business", "foundation", "plan"],
        "files_deleted": [],
    }
    if not args.apply:
        return emit(
            "success",
            "Предварительный просмотр миграции v1 → v2; состояние не изменено.",
            next_actions=["Проверить пути и применить с --apply; после миграции заново одобрить бизнес-логику."],
            artifacts=[str(state_path), str(backup)],
            data=preview,
        )
    if not backup_preexisting:
        write_json_atomic(root, backup, old)
    save_project_state(
        root,
        migrated,
        expected_sha256=sha256_file(root, STATE_REL),
    )
    return emit(
        "success",
        "Состояние мигрировано в v2; старая версия сохранена, проект безопасно открыт на discovery.",
        next_actions=["Запустить status и validate discovery, затем получить новое одобрение."],
        artifacts=[str(state_path), str(backup)],
        data=preview,
    )


def cmd_record(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state = load_state(root)
        reject_legacy_mutation_of_v3(state)
        blocked = maintenance_blocking_reason(state)
        if blocked:
            raise ValueError(blocked)
        if not args.note.strip():
            raise ValueError("Фиксация подэтапа требует непустую заметку.")
        if args.event in FOUNDATION_EVENTS:
            sequence = FOUNDATION_EVENTS
            required_phase = "foundation"
        elif args.event in TICKET_EVENTS:
            sequence = TICKET_EVENTS
            required_phase = "tickets"
        else:
            sequence = COMPLETION_EVENTS
            required_phase = "execution"
        if state.get("phase") != required_phase:
            raise ValueError(f"Событие {args.event} допустимо только в фазе {required_phase}; сейчас {state.get('phase')}.")
        records = state.setdefault("records", {})
        present = [event for event in sequence if event in records]
        if present != list(sequence[: len(present)]):
            raise ValueError(f"Записи фазы {required_phase} нарушают последовательность; используй reopen для безопасного восстановления.")
        stale_prior = existing_record_issues(root, state, tuple(present))
        if stale_prior:
            raise ValueError(stale_prior[0]["message"])
        expected = next((event for event in sequence if event not in records), None)
        if expected is None:
            raise ValueError(f"Все подэтапы фазы {required_phase} уже зафиксированы; для пересмотра используй reopen.")
        if args.event != expected:
            raise ValueError(f"Нарушен порядок: сейчас разрешено только событие {expected}.")
        evidence = safe_repo_path(root, args.evidence, expected="file")
        if not evidence.is_file():
            raise ValueError(f"Доказательство не найдено: {evidence}")
        evidence_rel = rel(root, evidence)
        semantic = evidence_semantic_issues(root, args.event, evidence_rel)
        if semantic:
            raise ValueError(" ".join(semantic))
        if args.event == "foundation-codebase" and evidence_rel != state["artifacts"]["codebase"]:
            raise ValueError("foundation-codebase должен ссылаться на канонический CODEBASE.md.")
        if args.event == "foundation-quality" and evidence_rel != state["artifacts"]["quality"]:
            raise ValueError("foundation-quality должен ссылаться на канонический QUALITY.md.")
        if args.event == "foundation-ready":
            blocking = [
                item for item in validate_stage(root, state, "foundation", include_records=False)
                if item["severity"] == "error"
            ]
            if blocking:
                details = "; ".join(item["message"] for item in blocking[:5])
                raise ValueError(f"Нельзя фиксировать готовность основания: {len(blocking)} машинных замечаний. {details}")
        if args.event in TICKET_EVENTS:
            blocking = approval_issues(root, state, "plan") + [
                item for item in validate_stage(root, state, "planning") if item["severity"] == "error"
            ]
            if blocking:
                raise ValueError(f"Рубеж задач заблокирован: {len(blocking)} замечаний плана/основания.")
        if args.event in COMPLETION_EVENTS:
            blocking = [item for item in validate_stage(root, state, "execution") if item["severity"] == "error"]
            if blocking:
                raise ValueError(f"Доказательство результата заблокировано: {len(blocking)} замечаний.")
        digest = sha256_file(root, evidence_rel)
        record_extra: dict[str, Any] = {}
        if args.event == "tickets-published":
            record_extra["verification_baseline_sha256"] = sha256_file(root, state["artifacts"]["verification"])
            implementation_areas = {"implementation", "execution", "release", "реализация", "выпуск"}
            record_extra["implementation_row_baseline"] = sorted(
                verification_row_fingerprint(row)
                for row in verification_history_rows(root, state["artifacts"]["verification"])
                if row["area"].strip().casefold() in implementation_areas
            )
        if args.event == "implementation-evidence":
            if evidence_rel != state["artifacts"]["verification"]:
                raise ValueError("implementation-evidence должен ссылаться на канонический VERIFICATION.md.")
            baseline = records.get("tickets-published", {}).get("verification_baseline_sha256")
            if not isinstance(baseline, str):
                raise ValueError("В записи tickets-published отсутствует базовый дайджест VERIFICATION.md.")
            if digest == baseline:
                raise ValueError("VERIFICATION.md не изменился после публикации задач; старое foundation-доказательство не подтверждает реализацию.")
            baseline_rows = records.get("tickets-published", {}).get("implementation_row_baseline")
            if not isinstance(baseline_rows, list) or not all(isinstance(item, str) for item in baseline_rows):
                raise ValueError("В записи tickets-published отсутствует базовый список строк реализации.")
            implementation_areas = {"implementation", "execution", "release", "реализация", "выпуск"}
            current_rows = {
                verification_row_fingerprint(row)
                for row in verification_history_rows(root, evidence_rel)
                if row["area"].strip().casefold() in implementation_areas and row["success"]
            }
            if not current_rows.difference(baseline_rows):
                raise ValueError("После публикации задач не появилась новая успешная строка проверки реализации.")
    except ValueError as exc:
        return emit("error", str(exc), next_actions=["Исправить доказательство или порядок подэтапов и повторить предварительный просмотр."], code=2)

    preview = {"event": args.event, "phase": state["phase"], "evidence": evidence_rel, "sha256": digest, "note": args.note, **record_extra}
    if not args.apply:
        return emit(
            "success",
            f"Предварительный просмотр события {args.event}; состояние не изменено.",
            next_actions=["Применить с --apply только после проверки доказательства."],
            artifacts=[str(evidence), str(root / STATE_REL)],
            data=preview,
        )
    stamp = now()
    records[args.event] = {"at": stamp, "note": args.note, "evidence": evidence_rel, "sha256": digest, **record_extra}
    if args.event == "tickets-published":
        state["phase"] = "execution"
    state["updated_at"] = stamp
    state.setdefault("history", []).append({"at": stamp, "event": f"recorded:{args.event}", "phase": state["phase"], "evidence": evidence_rel, "sha256": digest, "note": args.note})
    save_project_state(root, state)
    return emit(
        "success",
        f"Событие {args.event} зафиксировано" + ("; открыта фаза execution." if args.event == "tickets-published" else "."),
        next_actions=["Продолжить только следующим разрешённым подэтапом."],
        artifacts=[str(evidence), str(root / STATE_REL)],
        data=preview,
    )


def cmd_reopen(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state = load_state(root)
        reject_legacy_mutation_of_v3(state)
        if not args.note.strip():
            raise ValueError("Пересмотр требует непустую причину.")
        if PHASE_ORDER.index(state["phase"]) < PHASE_ORDER.index(args.stage):
            raise ValueError(f"Нельзя открыть будущую фазу {args.stage} из {state['phase']}.")
        maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
        pending = maintenance.get("pending_reopen") if isinstance(maintenance.get("pending_reopen"), dict) else None
        if maintenance.get("status") in {"maintenance-required", "running", "blocked"}:
            raise ValueError(maintenance_blocking_reason(state) or "Maintenance route не завершён.")
        if maintenance.get("status") == "reopen-required" and isinstance(pending, dict):
            required_stage = pending.get("stage")
            if required_stage not in {"discovery", "foundation", "planning"}:
                raise ValueError("pending_reopen содержит некорректную стадию.")
            if PHASE_ORDER.index(args.stage) > PHASE_ORDER.index(required_stage):
                raise ValueError(
                    f"Семантический audit требует reopen {required_stage}; стадия {args.stage} слишком поздняя."
                )
        if args.stage in ("foundation", "planning"):
            prior_gate = "business" if args.stage == "foundation" else "foundation"
            stale = approval_issues(root, state, prior_gate)
            if stale:
                raise ValueError(stale[0]["message"])
    except ValueError as exc:
        return emit("error", str(exc), next_actions=["Выбрать более ранний этап, чей одобренный вход изменился."], code=2)

    preview = {"from": state["phase"], "to": args.stage, "note": args.note, "files_deleted": []}
    if not args.apply:
        return emit(
            "success",
            f"Предварительный просмотр reopen {args.stage}; файлы и состояние не изменены.",
            next_actions=["Применить с --apply после явного решения о пересмотре."],
            artifacts=[str(root / STATE_REL)],
            data=preview,
        )
    if args.stage == "discovery":
        state["approvals"] = {"business": None, "foundation": None, "plan": None}
        state["records"] = {}
    elif args.stage == "foundation":
        state["approvals"]["foundation"] = None
        state["approvals"]["plan"] = None
        state["records"] = {}
    else:
        state["approvals"]["plan"] = None
        for event in TICKET_EVENTS + COMPLETION_EVENTS:
            state["records"].pop(event, None)
    stamp = now()
    state["phase"] = args.stage
    maintenance = state.setdefault("maintenance", {"history": []})
    maintenance["status"] = "not-ready"
    maintenance.pop("pending_reopen", None)
    maintenance.pop("active_run", None)
    maintenance.pop("maintenance_required", None)
    state["updated_at"] = stamp
    state.setdefault("history", []).append({"at": stamp, "event": f"reopened:{args.stage}", "phase": args.stage, "note": args.note})
    save_project_state(root, state)
    return emit(
        "success",
        f"Этап {args.stage} открыт заново; зависимые одобрения и записи сброшены, файлы сохранены.",
        next_actions=["Обновить артефакты, повторить validate и получить новые одобрения."],
        artifacts=[str(root / STATE_REL)],
        data=preview,
    )


def cmd_approve(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state = load_state(root)
        reject_legacy_mutation_of_v3(state)
        stage_for_gate = {"business": "discovery", "foundation": "foundation", "plan": "planning"}[args.gate]
        if state.get("phase") != stage_for_gate:
            raise ValueError(f"Рубеж {args.gate} допустим только из фазы {stage_for_gate}; сейчас {state.get('phase')}. Для пересмотра используй reopen.")
        issues = validate_stage(root, state, stage_for_gate)
        blocking = [item for item in issues if item["severity"] == "error"]
        if blocking:
            raise ValueError(f"Рубеж заблокирован машинной проверкой: {len(blocking)} замечаний.")
        if not args.note.strip():
            raise ValueError("Одобрение требует непустую заметку о том, что именно подтверждено.")
        snapshot = gate_snapshot(root, state, args.gate)
    except (KeyError, ValueError) as exc:
        return emit(
            "error",
            str(exc),
            next_actions=["Получить явное решение пользователя, исправить проверки и повторить без --apply для просмотра."],
            code=2,
        )

    target = GATE_TO_PHASE[args.gate]
    preview = {"gate": args.gate, "from": state.get("phase"), "to": target, "note": args.note, **snapshot}
    if not args.apply:
        return emit(
            "success",
            f"Предварительный просмотр одобрения рубежа {args.gate}; состояние не изменено.",
            next_actions=["Применить с --apply только после прямого подтверждения пользователя."],
            artifacts=[str(root / STATE_REL)],
            data=preview,
        )

    stamp = now()
    state["approvals"][args.gate] = {"at": stamp, "note": args.note, **snapshot}
    state["phase"] = target
    state["updated_at"] = stamp
    state.setdefault("history", []).append({"at": stamp, "event": f"approved:{args.gate}", "phase": target, "note": args.note})
    save_project_state(root, state)
    return emit(
        "success",
        f"Рубеж {args.gate} одобрен; этап изменён на {target}.",
        next_actions=[{"foundation": "Начать обязательное исследование стека.", "planning": "Создать крупный план.", "tickets": "Одобрить и опубликовать задачи; реализация ещё закрыта."}[target]],
        artifacts=[str(root / STATE_REL)],
        data=preview,
    )


def cmd_complete(args: argparse.Namespace) -> int:
    try:
        root = root_path(args.root)
        state = load_state(root)
        reject_legacy_mutation_of_v3(state)
        blocked = maintenance_blocking_reason(state)
        if blocked:
            raise ValueError(blocked)
        issues = validate_stage(root, state, "execution")
        blocking = [item for item in issues if item["severity"] == "error"]
        if blocking:
            raise ValueError(f"Завершение заблокировано: {len(blocking)} замечаний.")
        if state.get("phase") != "execution":
            raise ValueError(f"Завершение допустимо только из execution, сейчас: {state.get('phase')}")
        if not args.note.strip():
            raise ValueError("Завершение требует заметку о принятом результате и продолжениях.")
        record_blocking = record_issues(root, state, COMPLETION_EVENTS)
        if record_blocking:
            raise ValueError(f"Не хватает неизменённых доказательств реализации/приёмки: {len(record_blocking)}.")
    except ValueError as exc:
        return emit("error", str(exc), next_actions=["Завершить недостающий рубеж и повторить."], code=2)

    if not args.apply:
        return emit(
            "success",
            "Предварительный просмотр завершения; состояние не изменено.",
            next_actions=["Применить с --apply после приёмки результата пользователем."],
            artifacts=[str(root / STATE_REL)],
            data={"note": args.note, "records": {event: state["records"][event] for event in COMPLETION_EVENTS}},
        )
    stamp = now()
    state["phase"] = "complete"
    maintenance = state.setdefault("maintenance", {"history": []})
    maintenance["status"] = "operational"
    maintenance.pop("pending_reopen", None)
    state["updated_at"] = stamp
    state.setdefault("history", []).append(
        {
            "at": stamp,
            "event": "completed",
            "phase": "complete",
            "note": args.note,
            "evidence": {event: state["records"][event] for event in COMPLETION_EVENTS},
        }
    )
    save_project_state(root, state)
    return emit(
        "success",
        "Первая цель project-start завершена; граф перешёл в operational state поддержки документации.",
        next_actions=["Запускать project_maintenance.py после handoff задачи, изменения репозитория или по периодической проверке."],
        artifacts=[str(root / STATE_REL), str(root / state["artifacts"]["verification"])],
        data={"note": args.note, "records": {event: state["records"][event] for event in COMPLETION_EVENTS}},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Безопасная подготовка и проверка project-start")
    sub = parser.add_subparsers(dest="command", required=True)

    dependencies = sub.add_parser("dependencies", help="Проверить вспомогательные навыки")
    dependencies.add_argument("--skills-root", help="Явный корень каталога навыков")
    dependencies.set_defaults(func=cmd_dependencies)

    inspect = sub.add_parser("inspect", help="Осмотреть репозиторий без записи")
    inspect.add_argument("--root", required=True)
    inspect.set_defaults(func=cmd_inspect)

    status = sub.add_parser("status", help="Показать состояние")
    status.add_argument("--root", required=True)
    status.set_defaults(func=cmd_status)

    migrate = sub.add_parser("migrate", help="Безопасно мигрировать state schema v1 в v2")
    migrate.add_argument("--root", required=True)
    migrate.add_argument("--note", required=True)
    migrate.add_argument("--apply", action="store_true")
    migrate.set_defaults(func=cmd_migrate)

    bootstrap = sub.add_parser("bootstrap", help="Показать или применить безопасный scaffold")
    bootstrap.add_argument("--root", required=True)
    bootstrap.add_argument("--stage", required=True, choices=("discovery", "foundation", "planning"))
    bootstrap.add_argument("--docs-dir", default="docs/project")
    bootstrap.add_argument("--business-doc")
    bootstrap.add_argument("--decisions-doc")
    bootstrap.add_argument("--apply", action="store_true")
    bootstrap.set_defaults(func=cmd_bootstrap)

    validate = sub.add_parser("validate", help="Проверить рубеж")
    validate.add_argument("--root", required=True)
    validate.add_argument("--stage", required=True, choices=("discovery", "foundation", "planning", "tickets", "execution"))
    validate.set_defaults(func=cmd_validate)

    record = sub.add_parser("record", help="Зафиксировать последовательный подэтап с доказательством")
    record.add_argument("--root", required=True)
    record.add_argument("--event", required=True, choices=RECORD_EVENTS)
    record.add_argument("--evidence", required=True, help="Путь к обычному файлу внутри репозитория")
    record.add_argument("--note", required=True)
    record.add_argument("--apply", action="store_true")
    record.set_defaults(func=cmd_record)

    reopen = sub.add_parser("reopen", help="Явно открыть этап заново без удаления файлов")
    reopen.add_argument("--root", required=True)
    reopen.add_argument("--stage", required=True, choices=("discovery", "foundation", "planning"))
    reopen.add_argument("--note", required=True)
    reopen.add_argument("--apply", action="store_true")
    reopen.set_defaults(func=cmd_reopen)

    approve = sub.add_parser("approve", help="Записать явное одобрение рубежа")
    approve.add_argument("--root", required=True)
    approve.add_argument("--gate", required=True, choices=("business", "foundation", "plan"))
    approve.add_argument("--note", required=True)
    approve.add_argument("--apply", action="store_true")
    approve.set_defaults(func=cmd_approve)

    complete = sub.add_parser("complete", help="Отметить первую цель завершённой")
    complete.add_argument("--root", required=True)
    complete.add_argument("--note", required=True)
    complete.add_argument("--apply", action="store_true")
    complete.set_defaults(func=cmd_complete)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return emit("error", "Операция прервана пользователем.", next_actions=["Проверить состояние перед безопасным повтором."], code=130)
    except Exception as exc:  # Defensive boundary for deterministic machine output.
        return emit(
            "error",
            f"Непредвиденная ошибка: {exc}",
            next_actions=["Не повторять вслепую; проверить входы и состояние, затем исправить причину."],
            code=3,
        )


if __name__ == "__main__":
    sys.exit(main())
