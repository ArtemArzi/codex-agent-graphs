#!/usr/bin/env python3
"""Repository snapshots and path safety for task-delivery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any, Iterable


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "coverage",
    "__pycache__",
}


class SnapshotError(RuntimeError):
    pass


def safe_relative(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise SnapshotError("Путь должен быть непустым и относительным к корню репозитория.")
    return path


def safe_join(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    lexical = root / safe_relative(relative)
    resolved = lexical.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SnapshotError(f"Путь выходит за корень репозитория: {relative}") from exc
    return resolved


def safe_join_no_symlinks(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    relative_path = safe_relative(relative)
    current = root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise SnapshotError(f"Симлинк запрещён в машинном пути задачи: {relative}")
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SnapshotError(f"Путь выходит за корень репозитория: {relative}") from exc
    return current


def logical_join(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    path = root / safe_relative(relative)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SnapshotError(f"Путь выходит за корень репозитория: {relative}") from exc
    return path


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path) -> dict[str, Any]:
    if not os.path.lexists(path):
        return {"kind": "missing"}
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return {"kind": "symlink", "mode": mode, "target": os.readlink(path)}
    if stat.S_ISREG(info.st_mode):
        return {"kind": "file", "mode": mode, "sha256": hash_file(path)}
    if stat.S_ISDIR(info.st_mode):
        return {"kind": "dir", "mode": mode}
    return {"kind": "special", "mode": mode, "size": info.st_size}


def _git_paths(root: Path) -> list[str] | None:
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
            env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return sorted({part.decode("utf-8", errors="surrogateescape") for part in result.stdout.split(b"\0") if part})


def _excluded(relative: str, exclusions: Iterable[str]) -> bool:
    normalized = relative.strip("/")
    return any(normalized == prefix.strip("/") or normalized.startswith(prefix.strip("/") + "/") for prefix in exclusions)


def _walk_paths(root: Path, exclusions: list[str]) -> list[str]:
    paths: list[str] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in dirs:
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            if name in SKIP_DIRS or _excluded(relative, exclusions):
                continue
            if child.is_symlink():
                paths.append(relative)
            else:
                kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in files:
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            if not _excluded(relative, exclusions):
                paths.append(relative)
    return sorted(set(paths))


def repo_manifest(root: Path, exclusions: Iterable[str]) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    excluded = [str(item).strip("/") for item in exclusions]
    git_paths = _git_paths(root) or []
    filesystem_paths = _walk_paths(root, excluded)
    paths = sorted(set(git_paths) | set(filesystem_paths))
    manifest: dict[str, dict[str, Any]] = {}
    for relative in paths:
        normalized = Path(relative).as_posix().strip("/")
        parts = Path(normalized).parts
        if (
            not normalized
            or _excluded(normalized, excluded)
            or any(part in SKIP_DIRS for part in parts)
            or Path(normalized).suffix.lower() in {".pyc", ".pyo"}
        ):
            continue
        manifest[normalized] = _entry(logical_join(root, normalized))
    return manifest


def manifest_digest(manifest: dict[str, dict[str, Any]]) -> str:
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_manifest(path: Path, manifest: dict[str, dict[str, Any]]) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SnapshotError("Baseline manifest повреждён.")
    return value


def changed_paths(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def parse_scope(plan_text: str) -> list[str]:
    match = re.search(r"<!--\s*task-delivery:scope\s*\n(.*?)\n\s*-->", plan_text, flags=re.DOTALL)
    if not match:
        raise SnapshotError("PLAN.md не содержит машинный блок task-delivery:scope.")
    paths = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    if not paths:
        raise SnapshotError("Блок области PLAN.md пуст.")
    for raw in paths:
        path = safe_relative(raw)
        if path == Path("."):
            raise SnapshotError("Не указывайте весь репозиторий как область; перечислите конкретные пути.")
    return paths


def outside_scope(paths: Iterable[str], scope: Iterable[str]) -> list[str]:
    normalized_scope = [Path(item).as_posix().rstrip("/") for item in scope]
    return sorted(
        path
        for path in paths
        if not any(path == allowed or path.startswith(allowed + "/") for allowed in normalized_scope)
    )


def looks_like_test_path(relative: str) -> bool:
    path = Path(relative)
    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return bool(
        {"test", "tests", "__tests__", "spec", "specs"} & lowered_parts
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
        or name.endswith("_test.py")
        or name.endswith("_spec.rb")
    )


def _ensure_inside(root: Path, path: Path, relative: str) -> None:
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise SnapshotError(f"Симлинк области выходит за root: {relative}") from exc


def scope_manifest(root: Path, scope: Iterable[str]) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    manifest: dict[str, dict[str, Any]] = {}
    for relative in sorted(set(scope)):
        start = logical_join(root, relative)
        _ensure_inside(root, start, relative)
        normalized = Path(relative).as_posix().rstrip("/")
        manifest[normalized] = _entry(start)
        if start.is_symlink() or not start.is_dir():
            continue
        for current, dirs, files in os.walk(start, followlinks=False):
            current_path = Path(current)
            kept: list[str] = []
            for name in sorted(dirs):
                child = current_path / name
                rel = child.relative_to(root).as_posix()
                if name in SKIP_DIRS:
                    continue
                if child.is_symlink():
                    _ensure_inside(root, child, rel)
                manifest[rel] = _entry(child)
                if not child.is_symlink():
                    kept.append(name)
            dirs[:] = kept
            for name in sorted(files):
                child = current_path / name
                rel = child.relative_to(root).as_posix()
                if child.is_symlink():
                    _ensure_inside(root, child, rel)
                manifest[rel] = _entry(child)
    return manifest


def scope_fingerprint(root: Path, plan_path: Path) -> str:
    scope = parse_scope(plan_path.read_text(encoding="utf-8"))
    return manifest_digest(scope_manifest(root, scope))
