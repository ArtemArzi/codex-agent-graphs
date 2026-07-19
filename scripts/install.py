#!/usr/bin/env python3
"""Install and verify graph-skills in WSL CLI and Codex Desktop homes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
AGENTS_ROOT = REPO_ROOT / "agents"
SKILLS = ("project-start", "research", "task-delivery")
AGENT_ROLES = (
    "research_planner",
    "research_scout",
    "research_synthesizer",
    "research_verifier",
)
BLOCK_START = "# BEGIN codex-agent-graphs: research agents"
BLOCK_END = "# END codex-agent-graphs: research agents"
MANAGED_RE = re.compile(
    rf"(?ms)^\s*{re.escape(BLOCK_START)}\n.*?^\s*{re.escape(BLOCK_END)}\n?"
)
EXCLUDED_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store"}


class InstallError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise InstallError(f"Missing source directory: {root}")
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_NAMES for part in relative.parts):
            continue
        if path.is_symlink():
            raise InstallError(f"Symlinks are not allowed in install sources: {path}")
        if path.is_file():
            files[relative.as_posix()] = sha256_file(path)
    return files


def path_status(source: Path, target: Path) -> str:
    if not target.exists():
        return "missing"
    if target.is_symlink() or not target.is_dir():
        return "drift"
    return "in-sync" if manifest(source) == manifest(target) else "drift"


def file_status(source: Path, target: Path) -> str:
    if not target.exists():
        return "missing"
    if target.is_symlink() or not target.is_file():
        return "drift"
    return "in-sync" if sha256_file(source) == sha256_file(target) else "drift"


def managed_block() -> str:
    lines = [BLOCK_START]
    descriptions = {
        "research_planner": "Research graph planner and gap analyst.",
        "research_scout": "Read-only branch-specific research scout.",
        "research_synthesizer": "Research evidence reconciler and synthesizer.",
        "research_verifier": "Independent research claim and citation verifier.",
    }
    for role in AGENT_ROLES:
        lines.extend(
            [
                "",
                f"[agents.{role}]",
                f'description = "{descriptions[role]}"',
                f'config_file = "./agents/{role}.toml"',
            ]
        )
    lines.extend(["", BLOCK_END, ""])
    return "\n".join(lines)


def config_with_block(original: str) -> str:
    without_managed = MANAGED_RE.sub("", original).rstrip()
    for role in AGENT_ROLES:
        if re.search(rf"(?m)^\s*\[agents\.{re.escape(role)}\]\s*$", without_managed):
            raise InstallError(f"Unmanaged config already defines [agents.{role}]")
    candidate = f"{without_managed}\n\n{managed_block()}" if without_managed else managed_block()
    try:
        tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as exc:
        raise InstallError(f"Managed config would be invalid TOML: {exc}") from exc
    return candidate


def config_status(codex_home: Path) -> str:
    config = codex_home / "config.toml"
    original = config.read_text(encoding="utf-8") if config.exists() else ""
    return "in-sync" if original == config_with_block(original) else ("missing" if not config.exists() else "drift")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def backup_root(codex_home: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return codex_home / "backups" / "agent-graphs" / f"{stamp}-{os.getpid()}"


def replace_directory(source: Path, target: Path, backup: Path) -> str:
    status = path_status(source, target)
    if status == "in-sync":
        return status
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.parent / f".{target.name}.graph-install-{os.getpid()}"
    if staged.exists():
        raise InstallError(f"Staging path already exists: {staged}")
    prior_moved = False
    try:
        shutil.copytree(source, staged)
        if manifest(source) != manifest(staged):
            raise InstallError(f"Staged copy failed verification: {source}")
        if target.exists() or target.is_symlink():
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            prior_moved = True
        os.replace(staged, target)
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        if prior_moved and not target.exists() and backup.exists():
            os.replace(backup, target)
        raise
    return "installed"


def replace_file(source: Path, target: Path, backup: Path) -> str:
    status = file_status(source, target)
    if status == "in-sync":
        return status
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.parent / f".{target.name}.graph-install-{os.getpid()}"
    shutil.copy2(source, staged)
    if sha256_file(source) != sha256_file(staged):
        staged.unlink(missing_ok=True)
        raise InstallError(f"Staged file failed verification: {source}")
    prior_moved = False
    try:
        if target.exists() or target.is_symlink():
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            prior_moved = True
        os.replace(staged, target)
    except Exception:
        staged.unlink(missing_ok=True)
        if prior_moved and not target.exists() and backup.exists():
            os.replace(backup, target)
        raise
    return "installed"


def preflight_environment(codex_home: Path) -> tuple[str, str]:
    codex_home = codex_home.expanduser().resolve()
    for skill in SKILLS:
        manifest(SKILLS_ROOT / skill)
    for role in AGENT_ROLES:
        source = AGENTS_ROOT / f"{role}.toml"
        if not source.is_file() or source.is_symlink():
            raise InstallError(f"Invalid agent source: {source}")
        try:
            tomllib.loads(source.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise InstallError(f"Invalid agent TOML {source}: {exc}") from exc
    config = codex_home / "config.toml"
    original = config.read_text(encoding="utf-8") if config.exists() else ""
    candidate = config_with_block(original)
    return original, candidate


def install_environment(codex_home: Path) -> dict[str, Any]:
    codex_home = codex_home.expanduser().resolve()
    original, candidate = preflight_environment(codex_home)
    config = codex_home / "config.toml"
    backup = backup_root(codex_home)
    changes: list[dict[str, str]] = []
    for skill in SKILLS:
        source = SKILLS_ROOT / skill
        target = codex_home / "skills" / skill
        status = replace_directory(source, target, backup / "skills" / skill)
        changes.append({"kind": "skill", "name": skill, "status": status, "target": str(target)})
    for role in AGENT_ROLES:
        source = AGENTS_ROOT / f"{role}.toml"
        target = codex_home / "agents" / f"{role}.toml"
        status = replace_file(source, target, backup / "agents" / f"{role}.toml")
        changes.append({"kind": "agent", "name": role, "status": status, "target": str(target)})

    if candidate == original:
        config_change = "in-sync"
    else:
        if config.exists():
            config_backup = backup / "config.toml"
            config_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config, config_backup)
        atomic_write(config, candidate)
        config_change = "installed"
    changes.append({"kind": "config", "name": "managed-agent-block", "status": config_change, "target": str(config)})
    verification = verify_environment(codex_home)
    if verification["status"] != "ok":
        raise InstallError(f"Post-install verification failed for {codex_home}: {verification['issues']}")
    backup_used = any(change["status"] == "installed" for change in changes) and backup.exists()
    return {
        "codex_home": str(codex_home),
        "changes": changes,
        "backup": str(backup) if backup_used else None,
    }


def verify_environment(codex_home: Path) -> dict[str, Any]:
    codex_home = codex_home.expanduser().resolve()
    issues: list[str] = []
    statuses: list[dict[str, str]] = []
    for skill in SKILLS:
        status = path_status(SKILLS_ROOT / skill, codex_home / "skills" / skill)
        statuses.append({"kind": "skill", "name": skill, "status": status})
        if status != "in-sync":
            issues.append(f"skill {skill}: {status}")
    for role in AGENT_ROLES:
        status = file_status(AGENTS_ROOT / f"{role}.toml", codex_home / "agents" / f"{role}.toml")
        statuses.append({"kind": "agent", "name": role, "status": status})
        if status != "in-sync":
            issues.append(f"agent {role}: {status}")
    try:
        status = config_status(codex_home)
    except InstallError as exc:
        status = "conflict"
        issues.append(str(exc))
    statuses.append({"kind": "config", "name": "managed-agent-block", "status": status})
    if status != "in-sync" and not any("Unmanaged config" in issue for issue in issues):
        issues.append(f"config managed-agent-block: {status}")
    return {
        "status": "ok" if not issues else "failed",
        "codex_home": str(codex_home),
        "issues": issues,
        "items": statuses,
    }


def plan_environment(codex_home: Path) -> dict[str, Any]:
    codex_home = codex_home.expanduser().resolve()
    items: list[dict[str, str]] = []
    for skill in SKILLS:
        items.append(
            {
                "kind": "skill",
                "name": skill,
                "status": path_status(SKILLS_ROOT / skill, codex_home / "skills" / skill),
            }
        )
    for role in AGENT_ROLES:
        items.append(
            {
                "kind": "agent",
                "name": role,
                "status": file_status(AGENTS_ROOT / f"{role}.toml", codex_home / "agents" / f"{role}.toml"),
            }
        )
    try:
        config = config_status(codex_home)
    except InstallError:
        config = "conflict"
    items.append({"kind": "config", "name": "managed-agent-block", "status": config})
    return {"codex_home": str(codex_home), "items": items}


def detect_desktop_home() -> Path | None:
    candidates = sorted(Path("/mnt/c/Users").glob("*/.codex/config.toml")) if Path("/mnt/c/Users").is_dir() else []
    if len(candidates) == 1:
        return candidates[0].parent
    repo_parts = REPO_ROOT.parts
    if len(repo_parts) >= 5 and repo_parts[:4] == ("/", "mnt", "c", "Users"):
        candidate = Path(*repo_parts[:5]) / ".codex"
        if candidate.is_dir():
            return candidate
    return None


def selected_homes(args: argparse.Namespace) -> list[tuple[str, Path]]:
    use_all = args.all or (not args.wsl and not args.desktop)
    homes: list[tuple[str, Path]] = []
    if use_all or args.wsl:
        homes.append(("wsl", Path(args.wsl_home).expanduser()))
    if use_all or args.desktop:
        desktop = Path(args.desktop_home).expanduser() if args.desktop_home else detect_desktop_home()
        if desktop is None:
            raise InstallError("Could not auto-detect Desktop CODEX_HOME; pass --desktop-home")
        homes.append(("desktop", desktop))
    unique: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for label, home in homes:
        resolved = home.resolve()
        if resolved not in seen:
            unique.append((label, resolved))
            seen.add(resolved)
    return unique


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("action", choices=("plan", "install", "verify"))
    command.add_argument("--all", action="store_true", help="Target both WSL and Desktop")
    command.add_argument("--wsl", action="store_true", help="Target WSL only")
    command.add_argument("--desktop", action="store_true", help="Target Desktop only")
    command.add_argument("--wsl-home", default=str(Path.home() / ".codex"))
    command.add_argument("--desktop-home")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        homes = selected_homes(args)
        if args.action == "install":
            for _, home in homes:
                preflight_environment(home)
        environments: list[dict[str, Any]] = []
        for label, home in homes:
            if args.action == "plan":
                payload = plan_environment(home)
            elif args.action == "install":
                payload = install_environment(home)
            else:
                payload = verify_environment(home)
            payload["environment"] = label
            environments.append(payload)
        failed = any(payload.get("status") == "failed" for payload in environments)
        response = {
            "status": "failed" if failed else "ok",
            "summary": f"{args.action} completed for {len(environments)} environment(s)",
            "next_actions": [] if not failed else ["Resolve drift or conflicts and retry"],
            "artifacts": [str(REPO_ROOT)],
            "data": {"environments": environments},
        }
    except (InstallError, OSError) as exc:
        response = {
            "status": "failed",
            "summary": str(exc),
            "next_actions": ["Fix the reported install condition and retry"],
            "artifacts": [str(REPO_ROOT)],
            "data": {},
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
