#!/usr/bin/env python3
"""Synchronize portable Codex behavior from WSL CLI to Windows Desktop.

The WSL profile owns portable model defaults, global AGENTS.md, custom agents
and multi-agent policy. Each home retains its valid manual root effort choice. Windows-only Desktop, plugin, MCP, auth, state,
and session data are intentionally preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import tomllib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


_routing_spec = importlib.util.spec_from_file_location("desktop_shared_routing", Path(__file__).with_name("model_routing.py"))
assert _routing_spec and _routing_spec.loader
routing = importlib.util.module_from_spec(_routing_spec)
_routing_spec.loader.exec_module(routing)
_install_spec = importlib.util.spec_from_file_location("desktop_shared_install", Path(__file__).with_name("install.py"))
assert _install_spec and _install_spec.loader
installer = importlib.util.module_from_spec(_install_spec)
_install_spec.loader.exec_module(installer)

DEFAULT_SOURCE = Path("/home/artem/.codex")
DEFAULT_TARGET = Path("/mnt/c/Users/artem/.codex")

SYNC_TOP_LEVEL_KEYS = (
    "suppress_unstable_features_warning",
    "model",
    "model_reasoning_effort",
    "approvals_reviewer",
    "project_doc_fallback_filenames",
    "project_doc_max_bytes",
    "service_tier",
    "personality",
    "model_verbosity",
    "model_reasoning_summary",
)

# These Windows-profile keys change agent behavior but are absent from the
# authoritative WSL profile. Removing them restores the shared/default layer.
REMOVE_TOP_LEVEL_KEYS = {
    "persistent_instructions",
    "plan_mode_reasoning_effort",
    "review_model",
    "web_search",
}

SYNC_FEATURE_KEYS = (
    "multi_agent",
    "hooks",
    "memories",
    "mentions_v2",
    "prevent_idle_sleep",
)

PROTECTED_KEYS = (
    "approval_policy",
    "desktop",
    "history",
    "marketplaces",
    "mcp_servers",
    "model_provider",
    "notify",
    "plugins",
    "projects",
    "sandbox_mode",
    "shell_environment_policy",
)

REQUIRED_AGENT_KEYS = {"name", "description", "developer_instructions"}


class SyncError(RuntimeError):
    """Raised when synchronization cannot be completed safely."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_toml_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        return tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SyncError(f"Invalid TOML in {label}: {exc}") from exc


def parse_toml_path(path: Path) -> dict[str, Any]:
    return parse_toml_bytes(path.read_bytes(), str(path))


def patch_top_level(text: str, source: dict[str, Any]) -> str:
    for key in SYNC_TOP_LEVEL_KEYS:
        if key not in source:
            raise SyncError(f"Authoritative WSL config is missing top-level key: {key}")
    values = {key: source[key] for key in SYNC_TOP_LEVEL_KEYS}
    values.update({key: None for key in REMOVE_TOP_LEVEL_KEYS})
    return routing.rewrite_fields(text, (), values)


def patch_simple_table(text: str, table: str, source_table: dict[str, Any],
                       keys: tuple[str, ...]) -> str:
    for key in keys:
        if key not in source_table:
            raise SyncError(f"Authoritative WSL config is missing {table}.{key}")
    return routing.rewrite_fields(text, (table,), {key: source_table[key] for key in keys})


def replace_or_insert_family(target_text: str, source_text: str, family: str,
                             *, insert_after_table: str | None = None) -> str:
    """Replace every structural family span, including separated registrations."""
    parts = tuple(family.split("."))
    source_lines = source_text.splitlines(keepends=True)
    selected = [span for span in routing.table_spans(source_text)
                if span[0][:len(parts)] == parts]
    if not selected:
        raise SyncError(f"Source config is missing [{family}]")
    block = "".join("".join(source_lines[start:end]) for _, start, end in selected)
    cleaned = remove_family(target_text, family)
    return cleaned.rstrip() + "\n\n" + block.rstrip() + "\n"


def remove_family(text: str, family: str) -> str:
    parts = tuple(family.split("."))
    lines = text.splitlines(keepends=True)
    removed = set()
    for path, start, end in routing.table_spans(text):
        if path[:len(parts)] == parts:
            removed.update(range(start, end))
    return "".join(line for number, line in enumerate(lines) if number not in removed)


def without_registration_markers(text: str) -> str:
    markers = {installer.BLOCK_START, installer.BLOCK_END,
               installer.LEGACY_BLOCK_START, installer.LEGACY_BLOCK_END}
    removed = {number for number, line in routing._structural_lines(text) if line.strip() in markers}
    return "".join(line for number, line in enumerate(text.splitlines(keepends=True)) if number not in removed)


def build_desktop_config(source_bytes: bytes, target_bytes: bytes) -> bytes:
    source = parse_toml_bytes(source_bytes, "authoritative WSL config")
    before = parse_toml_bytes(target_bytes, "current Windows Desktop config")
    source_text = source_bytes.decode("utf-8")
    target_text = target_bytes.decode("utf-8")
    source = {**source, "model_reasoning_effort": routing.root_effort(before)}
    managed = any(line.strip() in {installer.BLOCK_START, installer.LEGACY_BLOCK_START}
                  for _, line in routing._structural_lines(source_text))
    if managed:
        # Markers precede headers and belong to the registration block, not the
        # preceding table span. Validate them, then regenerate the owned block.
        installer.config_with_block(source_text)
        installer.config_with_block(target_text)
        source_text = without_registration_markers(source_text)
        target_text = without_registration_markers(target_text)

    result = patch_top_level(target_text, source)
    source_features = source.get("features")
    if not isinstance(source_features, dict):
        raise SyncError("Authoritative WSL config is missing [features]")
    result = patch_simple_table(result, "features", source_features, SYNC_FEATURE_KEYS)
    result = replace_or_insert_family(
        result,
        source_text,
        "features.multi_agent_v2",
        insert_after_table="features",
    )
    result = remove_family(result, "profiles")
    result = replace_or_insert_family(result, source_text, "agents")
    if managed:
        result, extras = routing.adopt_native_registrations(result, set(installer.AGENT_ROLES))
        result = installer.config_with_block(result.rstrip() + "\n\n" + installer.managed_block(extras))

    result_bytes = result.encode("utf-8")
    after = parse_toml_bytes(result_bytes, "planned Windows Desktop config")

    for key in SYNC_TOP_LEVEL_KEYS:
        if after.get(key) != source.get(key):
            raise SyncError(f"Planned config failed to synchronize top-level key: {key}")
    for key in REMOVE_TOP_LEVEL_KEYS:
        if key in after:
            raise SyncError(f"Planned config still contains obsolete override: {key}")
    for key in SYNC_FEATURE_KEYS:
        if after.get("features", {}).get(key) != source_features.get(key):
            raise SyncError(f"Planned config failed to synchronize features.{key}")
    if after.get("features", {}).get("multi_agent_v2") != source_features.get(
        "multi_agent_v2"
    ):
        raise SyncError("Planned config failed to synchronize features.multi_agent_v2")
    if after.get("agents") != source.get("agents"):
        raise SyncError("Planned config failed to synchronize [agents]")
    if "profiles" in after:
        raise SyncError("Legacy inline [profiles.*] tables were not removed")

    missing = object()
    for key in PROTECTED_KEYS:
        if before.get(key, missing) != after.get(key, missing):
            raise SyncError(f"Windows-specific config changed unexpectedly: {key}")

    return result_bytes


def agent_files(path: Path) -> list[Path]:
    return sorted(item for item in path.glob("*.toml") if item.is_file())


def validate_agent_directory(path: Path) -> None:
    files = agent_files(path)
    if not files:
        raise SyncError(f"No agent TOML files found in {path}")
    seen_names: set[str] = set()
    for file in files:
        if file.is_symlink():
            raise SyncError(f"Symlinked agent file is not synchronized: {file}")
        data = parse_toml_path(file)
        missing = REQUIRED_AGENT_KEYS - set(data)
        if missing:
            raise SyncError(f"{file} is missing required keys: {sorted(missing)}")
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise SyncError(f"{file} has an invalid agent name")
        if name in seen_names:
            raise SyncError(f"Duplicate agent name in source directory: {name}")
        seen_names.add(name)


def directory_manifest(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {file.name: sha256_file(file) for file in agent_files(path)}


def snapshot_hashes(target: Path) -> dict[str, Any]:
    return {
        "config.toml": sha256_file(target / "config.toml"),
        "AGENTS.md": sha256_file(target / "AGENTS.md"),
        "agents": directory_manifest(target / "agents"),
    }


def timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")


def create_backup(target: Path, label: str) -> Path:
    backup = target / "backups" / "desktop-sync" / f"{label}-{timestamp()}"
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(target / "config.toml", backup / "config.toml")
    shutil.copy2(target / "AGENTS.md", backup / "AGENTS.md")
    shutil.copytree(target / "agents", backup / "agents")
    manifest = {
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(target),
        "hashes": snapshot_hashes(target),
    }
    (backup / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return backup


def deploy_snapshot(
    target: Path,
    config_bytes: bytes,
    agents_md_bytes: bytes,
    new_agents: Path,
    *,
    label: str,
    expected_current: dict[str, Any] | None = None,
    expected_source: tuple[Path, dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    validate_agent_directory(new_agents)
    parse_toml_bytes(config_bytes, "deployment config")

    if expected_current is None:
        expected_current = snapshot_hashes(target)
    if snapshot_hashes(target) != expected_current:
        raise SyncError("Windows profile changed after planning; no files were deployed")
    if expected_source and snapshot_hashes(expected_source[0]) != expected_source[1]:
        raise SyncError("WSL profile changed after planning; no files were deployed")
    stage_root = Path(tempfile.mkdtemp(prefix=".desktop-sync-stage-", dir=target))
    stage_config = stage_root / "config.toml"
    stage_agents_md = stage_root / "AGENTS.md"
    stage_agents = stage_root / "agents"
    stage_config.write_bytes(config_bytes)
    stage_agents_md.write_bytes(agents_md_bytes)
    shutil.copytree(new_agents, stage_agents)
    shutil.copymode(target / "config.toml", stage_config)
    shutil.copymode(target / "AGENTS.md", stage_agents_md)

    parse_toml_path(stage_config)
    validate_agent_directory(stage_agents)
    if expected_source and (snapshot_hashes(expected_source[0]) != expected_source[1]
                            or directory_manifest(stage_agents) != expected_source[1]["agents"]):
        shutil.rmtree(stage_root, ignore_errors=True)
        raise SyncError("WSL profile changed while staging; no files were deployed")
    if snapshot_hashes(target) != expected_current:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise SyncError("Windows profile changed while staging; no files were deployed")

    backup = create_backup(target, label)
    if snapshot_hashes(target) != expected_current:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise SyncError("Windows profile changed during backup; no files were deployed")
    if expected_source and snapshot_hashes(expected_source[0]) != expected_source[1]:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise SyncError("WSL profile changed during backup; no files were deployed")

    suffix = f"{timestamp()}-{uuid.uuid4().hex[:8]}"
    old_agents = target / f"agents.before-{label}-{suffix}"
    failed_agents = target / f"agents.failed-{label}-{suffix}"
    agents_swapped = False
    try:
        os.replace(target / "agents", old_agents)
        os.replace(stage_agents, target / "agents")
        agents_swapped = True
        os.replace(stage_config, target / "config.toml")
        os.replace(stage_agents_md, target / "AGENTS.md")
    except Exception:
        shutil.copy2(backup / "config.toml", target / "config.toml")
        shutil.copy2(backup / "AGENTS.md", target / "AGENTS.md")
        if agents_swapped and (target / "agents").exists():
            os.replace(target / "agents", failed_agents)
        if old_agents.exists() and not (target / "agents").exists():
            os.replace(old_agents, target / "agents")
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)

    return backup, old_agents


def planned_state(source: Path, target: Path) -> tuple[bytes, bytes, Path]:
    source_config = source / "config.toml"
    target_config = target / "config.toml"
    source_agents_md = source / "AGENTS.md"
    source_agents = source / "agents"

    for required in (
        source_config,
        target_config,
        source_agents_md,
        target / "AGENTS.md",
        source_agents,
        target / "agents",
    ):
        if required.is_symlink():
            raise SyncError(f"Symlinked profile path is not synchronized: {required}")
        if not required.exists():
            raise SyncError(f"Required path does not exist: {required}")

    validate_agent_directory(source_agents)
    config_bytes = build_desktop_config(
        source_config.read_bytes(), target_config.read_bytes()
    )
    return config_bytes, source_agents_md.read_bytes(), source_agents


def drift_report(source: Path, target: Path) -> tuple[bool, list[str]]:
    config_bytes, agents_md_bytes, source_agents = planned_state(source, target)
    details = []
    config_drift = (target / "config.toml").read_bytes() != config_bytes
    agents_md_drift = (target / "AGENTS.md").read_bytes() != agents_md_bytes
    source_manifest = directory_manifest(source_agents)
    target_manifest = directory_manifest(target / "agents")
    agents_drift = source_manifest != target_manifest

    details.append(f"config.toml={'drift' if config_drift else 'ok'}")
    details.append(f"AGENTS.md={'drift' if agents_md_drift else 'ok'}")
    details.append(f"agents={'drift' if agents_drift else 'ok'}")
    details.append(f"source_agent_files={len(source_manifest)}")
    details.append(f"target_agent_files={len(target_manifest)}")
    details.append(
        "target_only_agents="
        + ",".join(sorted(set(target_manifest) - set(source_manifest)))
    )
    return config_drift or agents_md_drift or agents_drift, details


def verify(source: Path, target: Path) -> None:
    drift, details = drift_report(source, target)
    if drift:
        raise SyncError("Profile verification failed: " + "; ".join(details))
    data = parse_toml_path(target / "config.toml")
    required_roles = {file.stem for file in agent_files(source / "agents")}
    actual_roles = {file.stem for file in agent_files(target / "agents")}
    if actual_roles != required_roles:
        raise SyncError("Active Desktop role set differs from WSL role set")
    print("status=verified")
    for detail in details:
        print(detail)
    print(f"model={data.get('model')}")
    print(f"model_reasoning_effort={data.get('model_reasoning_effort')}")
    print(f"agents.max_threads={data.get('agents', {}).get('max_threads')}")
    print(f"agents.max_depth={data.get('agents', {}).get('max_depth')}")
    print("active_roles=" + ",".join(sorted(actual_roles)))


def run_check(source: Path, target: Path) -> None:
    drift, details = drift_report(source, target)
    print(f"status={'drift' if drift else 'synchronized'}")
    for detail in details:
        print(detail)


def run_apply(source: Path, target: Path) -> None:
    source_snapshot = snapshot_hashes(source)
    target_snapshot = snapshot_hashes(target)
    config_bytes, agents_md_bytes, source_agents = planned_state(source, target)
    if snapshot_hashes(target) != target_snapshot or snapshot_hashes(source) != source_snapshot:
        raise SyncError("Profile changed while planning; no files were deployed")
    drift = (sha256_bytes(config_bytes) != target_snapshot["config.toml"]
             or sha256_bytes(agents_md_bytes) != target_snapshot["AGENTS.md"]
             or source_snapshot["agents"] != target_snapshot["agents"])
    if not drift:
        print("status=already-synchronized")
        verify(source, target)
        return
    backup, old_agents = deploy_snapshot(
        target,
        config_bytes,
        agents_md_bytes,
        source_agents,
        label="apply",
        expected_current=target_snapshot,
        expected_source=(source, source_snapshot),
    )
    verify(source, target)
    print(f"backup={backup}")
    print(f"legacy_agents_archive={old_agents}")


def run_restore(source: Path, target: Path, backup: Path) -> None:
    target_snapshot = snapshot_hashes(target)
    backup = backup.resolve()
    allowed_root = (target / "backups" / "desktop-sync").resolve()
    if backup != allowed_root and allowed_root not in backup.parents:
        raise SyncError(f"Restore path must be inside {allowed_root}")
    for required in (backup / "config.toml", backup / "AGENTS.md", backup / "agents"):
        if not required.exists():
            raise SyncError(f"Backup is incomplete: missing {required}")
    parse_toml_path(backup / "config.toml")
    validate_agent_directory(backup / "agents")
    pre_restore, old_agents = deploy_snapshot(
        target,
        (backup / "config.toml").read_bytes(),
        (backup / "AGENTS.md").read_bytes(),
        backup / "agents",
        label="pre-restore",
        expected_current=target_snapshot,
    )
    print("status=restored")
    print(f"restored_from={backup}")
    print(f"pre_restore_backup={pre_restore}")
    print(f"replaced_agents_archive={old_agents}")
    run_check(source, target)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Show synchronization drift")
    action.add_argument("--apply", action="store_true", help="Apply synchronization safely")
    action.add_argument("--verify", action="store_true", help="Fail unless profiles match")
    action.add_argument(
        "--restore", type=Path, metavar="BACKUP", help="Restore a generated backup"
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.source.resolve()
    target = args.target.resolve()
    try:
        if args.check:
            run_check(source, target)
        elif args.apply:
            run_apply(source, target)
        elif args.verify:
            verify(source, target)
        else:
            run_restore(source, target, args.restore)
    except (SyncError, OSError, ValueError) as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
