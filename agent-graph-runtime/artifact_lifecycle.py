#!/usr/bin/env python3
"""Inventory, compact, and explicitly prune Codex agent-graph run artifacts."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = 1
STATE_NAME = "state.json"
FINAL_NAME = "FINAL.json"
DEFAULT_POLICY = {
    "schema_version": 1,
    "completed": {"raw_days": 7, "archive_days": 30},
    "superseded": {"raw_days": 7, "archive_days": 30, "require_successor": True},
}
MANAGED_ROOTS = {
    PurePosixPath(".agent-graphs/continuous-improvement-runs"): (
        "continuous-improvement",
        "run",
    ),
    PurePosixPath(".agent-graphs/project-start-maintenance"): (
        "project-start-maintenance",
        "run",
    ),
    PurePosixPath(".agent-graphs/project-start-runs"): ("project-start", "run"),
    PurePosixPath(".agent-graphs/research-runs"): ("research", "run"),
    PurePosixPath(".agent-graphs/task-delivery-runs"): ("task-delivery", "run"),
    PurePosixPath(".codex/task-delivery"): ("task-delivery-task-state", "task-state"),
}
ACTIVE_STATUSES = {
    "blocked",
    "decision",
    "pending",
    "ready",
    "running",
    "awaiting_implementation",
}
TERMINAL_STATUSES = {"completed", "superseded"}
LOCK_NAME = ".artifact-gc.lock"


class ArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunSpec:
    graph_id: str
    kind: str
    managed_root: PurePosixPath


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def parse_time(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactError(f"{label} is missing.")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ArtifactError(f"{label} is not an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"Cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ArtifactError(f"JSON must be an object: {path}")
    return value


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ArtifactError(f"Refusing symlinked destination parent: {path.parent}")
    descriptor, temporary_raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write(path, json_bytes(value))


@contextlib.contextmanager
def artifact_lock(run_dir: Path) -> Iterable[None]:
    lock = run_dir / LOCK_NAME
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ArtifactError(f"Artifact lifecycle is already operating on: {run_dir}") from exc
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock.unlink(missing_ok=True)


def project_root(raw: str | Path) -> Path:
    path = Path(raw).expanduser()
    if not path.exists() or not path.is_dir() or path.is_symlink():
        raise ArtifactError(f"Project root must be a real directory: {path}")
    return path.resolve()


def no_symlink_path(path: Path, root: Path) -> None:
    root = root.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ArtifactError(f"Path escapes project root: {path}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ArtifactError(f"Managed path contains a symlink: {current}")


def safe_managed(root: Path, relative: PurePosixPath) -> Path:
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ArtifactError(f"Managed relative path is unsafe: {relative}")
    path = root.joinpath(*relative.parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ArtifactError(f"Managed path escapes project root: {path}") from exc
    no_symlink_path(path, root)
    return path


def identify_run(root: Path, run_dir: Path) -> RunSpec:
    resolved = run_dir.expanduser()
    if not resolved.exists() or not resolved.is_dir() or resolved.is_symlink():
        raise ArtifactError(f"Run must be a real directory: {resolved}")
    resolved = resolved.resolve()
    no_symlink_path(resolved, root)
    relative = PurePosixPath(resolved.relative_to(root).as_posix())
    for managed_root, (graph_id, kind) in MANAGED_ROOTS.items():
        if relative.parent == managed_root and len(relative.parts) == len(managed_root.parts) + 1:
            return RunSpec(graph_id=graph_id, kind=kind, managed_root=managed_root)
    raise ArtifactError(f"Run is outside supported managed roots: {resolved}")


def discover(root: Path) -> Iterable[tuple[Path, RunSpec]]:
    for relative, (graph_id, kind) in MANAGED_ROOTS.items():
        parent = safe_managed(root, relative)
        if not parent.exists():
            continue
        if not parent.is_dir():
            yield parent, RunSpec(graph_id=graph_id, kind=f"invalid:{kind}", managed_root=relative)
            continue
        for child in sorted(parent.iterdir()):
            yield child, RunSpec(graph_id=graph_id, kind=kind, managed_root=relative)


def files_in_run(run_dir: Path) -> list[Path]:
    files: list[Path] = []
    for current_raw, directories, names in os.walk(run_dir, followlinks=False):
        current = Path(current_raw)
        for name in list(directories):
            candidate = current / name
            if candidate.is_symlink():
                raise ArtifactError(f"Run contains a symlinked directory: {candidate}")
        for name in names:
            candidate = current / name
            if candidate.name == LOCK_NAME:
                continue
            if candidate.is_symlink() or not candidate.is_file():
                raise ArtifactError(f"Run contains an unsafe file: {candidate}")
            files.append(candidate)
    return sorted(files, key=lambda item: item.relative_to(run_dir).as_posix())


def manifest(run_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(run_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files_in_run(run_dir)
    ]


def manifest_digest(entries: list[dict[str, Any]]) -> str:
    return sha256_bytes(json_bytes(entries))


def state_status(state: dict[str, Any], spec: RunSpec) -> str:
    if spec.kind == "task-state":
        value = state.get("phase", state.get("status"))
    else:
        value = state.get("status", state.get("phase"))
    return str(value).strip() if value is not None else "unknown"


def validate_state_identity(
    root: Path,
    run_dir: Path,
    state: dict[str, Any],
    spec: RunSpec,
) -> None:
    if spec.kind == "task-state":
        task_id = state.get("task_id")
        if isinstance(task_id, str) and task_id != run_dir.name:
            raise ArtifactError("Task Delivery task-state identity does not match its directory.")
    else:
        expected_graph = (
            "project-start" if spec.graph_id == "project-start-maintenance" else spec.graph_id
        )
        if state.get("graph_id") != expected_graph or state.get("run_id") != run_dir.name:
            raise ArtifactError("Graph run identity does not match its managed directory.")
    declared_root = state.get("root")
    if isinstance(declared_root, str) and declared_root:
        try:
            if Path(declared_root).expanduser().resolve() != root:
                raise ArtifactError("Graph run is bound to a different project root.")
        except OSError as exc:
            raise ArtifactError("Graph run has an invalid project root.") from exc


def completion_time(state: dict[str, Any], state_path: Path) -> dt.datetime:
    candidates = [
        state.get("completed_at"),
        state.get("updated_at"),
        state.get("created_at"),
    ]
    runs = state.get("runs")
    if isinstance(runs, list) and runs and isinstance(runs[-1], dict):
        candidates.insert(0, runs[-1].get("completed_at"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            try:
                return parse_time(candidate, "completion timestamp")
            except ArtifactError:
                continue
    return dt.datetime.fromtimestamp(state_path.stat().st_mtime, tz=dt.timezone.utc)


def load_policy(root: Path) -> dict[str, Any]:
    path = safe_managed(root, PurePosixPath(".agent-graphs/retention.json"))
    policy = load_json(path) if path.is_file() else json.loads(json.dumps(DEFAULT_POLICY))
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactError("Retention policy has an unsupported schema.")
    for status in ("completed", "superseded"):
        rule = policy.get(status)
        if not isinstance(rule, dict):
            raise ArtifactError(f"Retention policy is missing {status}.")
        raw_days = rule.get("raw_days")
        archive_days = rule.get("archive_days")
        if (
            not isinstance(raw_days, int)
            or not isinstance(archive_days, int)
            or raw_days < 0
            or archive_days < raw_days
        ):
            raise ArtifactError(f"Retention policy has invalid {status} days.")
    return policy


def task_plan_waiting(root: Path, run_state: dict[str, Any], spec: RunSpec) -> bool:
    if spec.graph_id == "task-delivery-task-state":
        return state_status(run_state, spec) == "awaiting_implementation"
    if spec.graph_id != "task-delivery" or run_state.get("mode") != "plan":
        return False
    task_id = run_state.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return True
    task_path = safe_managed(root, PurePosixPath(f".codex/task-delivery/{task_id}/{STATE_NAME}"))
    if not task_path.is_file():
        return True
    return load_json(task_path).get("phase") == "awaiting_implementation"


def verified_successor(root: Path, state: dict[str, Any], spec: RunSpec) -> bool:
    if state_status(state, spec) != "superseded":
        return True
    successor = state.get("successor_run_id")
    if not isinstance(successor, str) or not successor:
        return False
    successor_dir = safe_managed(root, spec.managed_root / successor)
    successor_state = successor_dir / STATE_NAME
    if not successor_state.is_file():
        return False
    return state_status(load_json(successor_state), spec) == "completed"


def terminal_eligibility(root: Path, run_dir: Path, state: dict[str, Any], spec: RunSpec) -> tuple[bool, str]:
    try:
        validate_state_identity(root, run_dir, state, spec)
    except ArtifactError as exc:
        return False, str(exc)
    status = state_status(state, spec)
    if task_plan_waiting(root, state, spec):
        return False, "awaiting-implementation"
    if status in ACTIVE_STATUSES:
        return False, status
    if status not in TERMINAL_STATUSES:
        return False, f"unsupported-status:{status}"
    if status == "superseded" and not verified_successor(root, state, spec):
        return False, "superseded-successor-unverified"
    try:
        files_in_run(run_dir)
    except ArtifactError as exc:
        return False, str(exc)
    return True, "terminal"


def inspect_run(root: Path, run_dir: Path, spec: RunSpec) -> dict[str, Any]:
    record: dict[str, Any] = {
        "graph_id": spec.graph_id,
        "kind": spec.kind,
        "run": str(run_dir),
        "run_id": run_dir.name,
        "status": "invalid",
        "eligible_for_compaction": False,
        "hold_reason": None,
        "files": 0,
        "bytes": 0,
    }
    if spec.kind.startswith("invalid:") or not run_dir.is_dir() or run_dir.is_symlink():
        record["hold_reason"] = "invalid-managed-entry"
        return record
    state_path = run_dir / STATE_NAME
    if not state_path.is_file() or state_path.is_symlink():
        record["hold_reason"] = "missing-or-unsafe-state"
        return record
    try:
        state = load_json(state_path)
        record["status"] = state_status(state, spec)
        entries = manifest(run_dir)
        record["files"] = len(entries)
        record["bytes"] = sum(item["bytes"] for item in entries)
        eligible, reason = terminal_eligibility(root, run_dir, state, spec)
        record["eligible_for_compaction"] = eligible
        record["hold_reason"] = None if eligible else reason
        history = history_final_path(root, spec.graph_id, run_dir.name)
        record["compacted"] = history.is_file()
    except ArtifactError as exc:
        record["hold_reason"] = str(exc)
    return record


def history_root(root: Path) -> Path:
    return safe_managed(root, PurePosixPath(".agent-graphs/history"))


def history_final_path(root: Path, graph_id: str, run_id: str) -> Path:
    return safe_managed(
        root,
        PurePosixPath(f".agent-graphs/history/{graph_id}/{run_id}/{FINAL_NAME}"),
    )


def archive_path(root: Path, graph_id: str, run_id: str) -> Path:
    return safe_managed(
        root,
        PurePosixPath(f".agent-graphs/archives/{graph_id}/{run_id}.tar.gz"),
    )


def known_output_values(
    state: dict[str, Any],
    root: Path,
    run_dir: Path,
    graph_id: str,
) -> list[Path]:
    values: list[str] = []
    for key in ("output", "plan_path"):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
    artifacts = state.get("artifacts")
    if isinstance(artifacts, dict):
        values.extend(value for value in artifacts.values() if isinstance(value, str) and value.strip())
    nodes = state.get("nodes")
    if isinstance(nodes, dict):
        terminal_nodes = [
            node
            for name, node in nodes.items()
            if (name == "complete" or str(name).endswith("-complete")) and isinstance(node, dict)
        ]
        for complete in terminal_nodes:
            receipts = complete.get("receipts")
            if isinstance(receipts, list):
                for receipt in receipts:
                    if not isinstance(receipt, dict):
                        continue
                    for key in ("artifact", "path", "source_artifact"):
                        value = receipt.get(key)
                        if isinstance(value, str) and value.strip():
                            values.append(value)
    if graph_id in {"project-start", "project-start-maintenance"}:
        values.append(".project-start/state.json")
    if graph_id == "continuous-improvement":
        values.append(str(run_dir / "IMPROVEMENT.md"))
    task_id = state.get("task_id")
    if isinstance(task_id, str) and task_id:
        values.append(f".agent-graphs/task-delivery-handoffs/{task_id}/HANDOFF.md")
    outputs: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        raw = Path(value).expanduser()
        candidate = raw if raw.is_absolute() else root / raw
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            continue
        if resolved.is_file() and not resolved.is_symlink() and resolved not in seen:
            no_symlink_path(resolved, root)
            outputs.append(resolved)
            seen.add(resolved)
    return outputs


def preserve_outputs(
    root: Path,
    run_dir: Path,
    graph_id: str,
    run_id: str,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    final_parent = history_final_path(root, graph_id, run_id).parent
    for source in known_output_values(state, root, run_dir, graph_id):
        record = {
            "path": source.relative_to(root).as_posix(),
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
            "preserved_copy": None,
        }
        try:
            source_relative = source.relative_to(run_dir)
        except ValueError:
            records.append(record)
            continue
        destination = final_parent / "outputs" / source_relative
        no_symlink_path(destination, root)
        atomic_write(destination, source.read_bytes())
        if sha256_file(destination) != record["sha256"]:
            raise ArtifactError(f"Preserved output copy failed verification: {source}")
        record["preserved_copy"] = destination.relative_to(root).as_posix()
        records.append(record)
    return records


def write_archive(run_dir: Path, destination: Path, entries: list[dict[str, Any]]) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    no_symlink_path(destination, destination.parents[3])
    descriptor, temporary_raw = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_raw)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT) as archive:
                    for entry in entries:
                        source = run_dir / entry["path"]
                        if sha256_file(source) != entry["sha256"]:
                            raise ArtifactError(f"Run changed during compaction: {source}")
                        info = tarfile.TarInfo(entry["path"])
                        info.size = entry["bytes"]
                        info.mode = 0o600
                        info.mtime = 0
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        with source.open("rb") as handle:
                            archive.addfile(info, handle)
        verify_archive(temporary, entries)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return sha256_file(destination)


def verify_archive(path: Path, entries: list[dict[str, Any]]) -> None:
    expected = {entry["path"]: entry for entry in entries}
    found: dict[str, dict[str, Any]] = {}
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive.getmembers():
                member_path = PurePosixPath(member.name)
                if (
                    not member.isfile()
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or member.name not in expected
                ):
                    raise ArtifactError(f"Archive contains an unsafe member: {member.name}")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ArtifactError(f"Archive member cannot be read: {member.name}")
                digest = hashlib.sha256()
                size = 0
                for chunk in iter(lambda: extracted.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
                found[member.name] = {"sha256": digest.hexdigest(), "bytes": size}
    except (OSError, tarfile.TarError) as exc:
        raise ArtifactError(f"Archive verification failed: {path}") from exc
    if set(found) != set(expected):
        raise ArtifactError("Archive manifest does not match the run manifest.")
    for name, actual in found.items():
        if actual != {"sha256": expected[name]["sha256"], "bytes": expected[name]["bytes"]}:
            raise ArtifactError(f"Archive member changed: {name}")


def final_receipt_valid(root: Path, final_path: Path) -> dict[str, Any]:
    receipt = load_json(final_path)
    if (
        receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("kind") != "agent-graph-final"
        or not isinstance(receipt.get("graph_id"), str)
        or not isinstance(receipt.get("run_id"), str)
    ):
        raise ArtifactError(f"Invalid final receipt: {final_path}")
    expected = history_final_path(root, receipt["graph_id"], receipt["run_id"])
    if expected.resolve() != final_path.resolve():
        raise ArtifactError("Final receipt is outside its canonical history path.")
    return receipt


def compact(root: Path, run_dir: Path) -> dict[str, Any]:
    spec = identify_run(root, run_dir)
    with artifact_lock(run_dir):
        return compact_locked(root, run_dir, spec)


def compact_locked(root: Path, run_dir: Path, spec: RunSpec) -> dict[str, Any]:
    state_path = run_dir / STATE_NAME
    if not state_path.is_file() or state_path.is_symlink():
        raise ArtifactError("Run has no safe state.json.")
    state = load_json(state_path)
    eligible, reason = terminal_eligibility(root, run_dir, state, spec)
    if not eligible:
        raise ArtifactError(f"Run is not safe to compact: {reason}")
    entries = manifest(run_dir)
    if not entries:
        raise ArtifactError("Run is empty.")
    final_path = history_final_path(root, spec.graph_id, run_dir.name)
    destination = archive_path(root, spec.graph_id, run_dir.name)
    if final_path.is_file():
        receipt = final_receipt_valid(root, final_path)
        if (
            receipt.get("raw", {}).get("manifest_sha256") == manifest_digest(entries)
            and destination.is_file()
            and sha256_file(destination) == receipt.get("raw", {}).get("archive_sha256")
        ):
            verify_archive(destination, entries)
            return response(
                "ok",
                "Run is already compacted and verified.",
                artifacts=[str(final_path), str(destination)],
                data={"final": receipt, "idempotent": True},
            )
        raise ArtifactError("Existing final receipt does not match the current run.")
    if final_path.exists():
        raise ArtifactError("Compaction final destination is occupied.")
    policy = load_policy(root)
    status = state_status(state, spec)
    rule = policy[status]
    completed = completion_time(state, state_path)
    raw_cleanup = completed + dt.timedelta(days=rule["raw_days"])
    archive_cleanup = completed + dt.timedelta(days=rule["archive_days"])
    outputs = preserve_outputs(root, run_dir, spec.graph_id, run_dir.name, state)
    if destination.exists():
        if not destination.is_file() or destination.is_symlink():
            raise ArtifactError("Compaction archive destination is unsafe.")
        verify_archive(destination, entries)
        archive_sha = sha256_file(destination)
    else:
        archive_sha = write_archive(run_dir, destination, entries)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "kind": "agent-graph-final",
        "graph_id": spec.graph_id,
        "run_id": run_dir.name,
        "source_kind": spec.kind,
        "source_run": run_dir.relative_to(root).as_posix(),
        "terminal_status": status,
        "completed_at": iso(completed),
        "compacted_at": iso(utc_now()),
        "state_sha256": sha256_file(state_path),
        "canonical_outputs": outputs,
        "raw": {
            "files": len(entries),
            "bytes": sum(entry["bytes"] for entry in entries),
            "manifest": entries,
            "manifest_sha256": manifest_digest(entries),
            "archive": destination.relative_to(root).as_posix(),
            "archive_sha256": archive_sha,
            "archive_bytes": destination.stat().st_size,
        },
        "retention": {
            "raw_cleanup_after": iso(raw_cleanup),
            "archive_cleanup_after": iso(archive_cleanup),
            "automatic_cleanup": False,
        },
    }
    atomic_json(final_path, receipt)
    reread = final_receipt_valid(root, final_path)
    if reread != receipt or sha256_file(destination) != archive_sha:
        raise ArtifactError("Compaction receipt failed final verification.")
    return response(
        "ok",
        "Terminal run compacted; raw state remains until an explicit due prune.",
        artifacts=[str(final_path), str(destination), str(run_dir)],
        data={"final": receipt, "idempotent": False},
    )


def verify_raw_against_receipt(root: Path, receipt: dict[str, Any]) -> Path:
    raw = receipt.get("raw")
    if not isinstance(raw, dict) or not isinstance(raw.get("manifest"), list):
        raise ArtifactError("Final receipt has no raw manifest.")
    run_dir = safe_managed(root, PurePosixPath(receipt["source_run"]))
    spec = identify_run(root, run_dir)
    if spec.graph_id != receipt["graph_id"] or run_dir.name != receipt["run_id"]:
        raise ArtifactError("Final receipt source identity is invalid.")
    current = manifest(run_dir)
    if manifest_digest(current) != raw.get("manifest_sha256") or current != raw["manifest"]:
        raise ArtifactError(f"Raw run changed after compaction: {run_dir}")
    return run_dir


def verify_archive_against_receipt(root: Path, receipt: dict[str, Any]) -> Path:
    raw = receipt.get("raw")
    if not isinstance(raw, dict):
        raise ArtifactError("Final receipt has no raw archive.")
    path_value = raw.get("archive")
    if not isinstance(path_value, str):
        raise ArtifactError("Final receipt has no archive path.")
    path = safe_managed(root, PurePosixPath(path_value))
    expected = archive_path(root, receipt["graph_id"], receipt["run_id"])
    if path.resolve() != expected.resolve() or not path.is_file() or path.is_symlink():
        raise ArtifactError("Final receipt archive is missing or misplaced.")
    if sha256_file(path) != raw.get("archive_sha256"):
        raise ArtifactError("Final receipt archive digest is invalid.")
    verify_archive(path, raw.get("manifest", []))
    return path


def remove_tree(path: Path, root: Path) -> None:
    no_symlink_path(path, root)
    files_in_run(path)
    shutil.rmtree(path)


def gc_receipt(root: Path, graph_id: str, run_id: str, action: str, target: Path) -> Path:
    stamp = utc_now()
    name = f"{stamp.strftime('%Y%m%dT%H%M%SZ')}-{action}.json"
    destination = safe_managed(
        root,
        PurePosixPath(f".agent-graphs/history/{graph_id}/{run_id}/gc-receipts/{name}"),
    )
    atomic_json(
        destination,
        {
            "schema_version": SCHEMA_VERSION,
            "kind": "agent-graph-gc",
            "graph_id": graph_id,
            "run_id": run_id,
            "action": action,
            "target": target.relative_to(root).as_posix(),
            "applied_at": iso(stamp),
        },
    )
    return destination


def final_receipts(root: Path) -> Iterable[Path]:
    history = history_root(root)
    if not history.exists():
        return []
    if not history.is_dir() or history.is_symlink():
        raise ArtifactError("History root is unsafe.")
    return sorted(history.glob(f"*/*/{FINAL_NAME}"))


def prune(root: Path, apply: bool, now: dt.datetime | None = None) -> dict[str, Any]:
    current = now or utc_now()
    actions: list[dict[str, Any]] = []
    receipts: list[str] = []
    for final_path in final_receipts(root):
        no_symlink_path(final_path, root)
        receipt = final_receipt_valid(root, final_path)
        retention = receipt.get("retention")
        if not isinstance(retention, dict):
            raise ArtifactError(f"Final receipt has no retention policy: {final_path}")
        raw_due = current >= parse_time(retention.get("raw_cleanup_after"), "raw_cleanup_after")
        archive_due = current >= parse_time(
            retention.get("archive_cleanup_after"), "archive_cleanup_after"
        )
        source = safe_managed(root, PurePosixPath(receipt["source_run"]))
        archive = safe_managed(root, PurePosixPath(receipt["raw"]["archive"]))
        if raw_due and source.exists():
            action = {
                "action": "prune-raw",
                "target": str(source),
                "graph_id": receipt["graph_id"],
                "run_id": receipt["run_id"],
                "applied": apply,
            }
            if apply:
                with artifact_lock(source):
                    verify_archive_against_receipt(root, receipt)
                    verify_raw_against_receipt(root, receipt)
                    remove_tree(source, root)
                gc = gc_receipt(root, receipt["graph_id"], receipt["run_id"], "prune-raw", source)
                receipts.append(str(gc))
            else:
                verify_archive_against_receipt(root, receipt)
                verify_raw_against_receipt(root, receipt)
            actions.append(action)
        if archive_due and archive.exists():
            if source.exists():
                continue
            verify_archive_against_receipt(root, receipt)
            action = {
                "action": "prune-archive",
                "target": str(archive),
                "graph_id": receipt["graph_id"],
                "run_id": receipt["run_id"],
                "applied": apply,
            }
            if apply:
                archive.unlink()
                gc = gc_receipt(root, receipt["graph_id"], receipt["run_id"], "prune-archive", archive)
                receipts.append(str(gc))
            actions.append(action)
    return response(
        "ok",
        "Prune applied to due verified artifacts." if apply else "Dry-run only; no artifacts were removed.",
        artifacts=receipts,
        data={"apply": apply, "actions": actions},
    )


def inventory(root: Path) -> dict[str, Any]:
    runs = [inspect_run(root, path, spec) for path, spec in discover(root)]
    totals = {
        "runs": len(runs),
        "files": sum(item["files"] for item in runs),
        "bytes": sum(item["bytes"] for item in runs),
        "eligible_for_compaction": sum(bool(item["eligible_for_compaction"]) for item in runs),
        "held": sum(not bool(item["eligible_for_compaction"]) for item in runs),
    }
    return response(
        "ok",
        "Artifact inventory completed without mutation.",
        artifacts=[str(root)],
        data={"root": str(root), "totals": totals, "runs": runs},
    )


def response(
    status: str,
    summary: str,
    *,
    artifacts: list[str] | None = None,
    data: dict[str, Any] | None = None,
    next_actions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "summary": summary,
        "next_actions": next_actions or [],
        "artifacts": artifacts or [],
        "data": data or {},
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    inventory_parser = sub.add_parser("inventory")
    inventory_parser.add_argument("--root", required=True)
    compact_parser = sub.add_parser("compact")
    compact_parser.add_argument("--root", required=True)
    compact_parser.add_argument("--run", required=True)
    prune_parser = sub.add_parser("prune")
    prune_parser.add_argument("--root", required=True)
    prune_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply due verified cleanup. Without this flag prune is a dry-run.",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = project_root(args.root)
        if args.command == "inventory":
            payload = inventory(root)
        elif args.command == "compact":
            run = Path(args.run).expanduser()
            payload = compact(root, run if run.is_absolute() else root / run)
        else:
            payload = prune(root, args.apply)
    except (ArtifactError, OSError) as exc:
        payload = response(
            "failed",
            str(exc),
            next_actions=["Resolve the reported lifecycle condition and retry."],
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
