#!/usr/bin/env python3
"""Install and verify Codex workflows in WSL CLI and Codex Desktop homes."""

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
GRAPH_RUNTIME_ROOT = REPO_ROOT / "agent-graph-runtime"
GRAPH_RUNTIME_TARGET = "agent-graph-runtime"
GLOBAL_POLICY_SOURCE = REPO_ROOT / "policies" / "development-recovery.md"
DISCOVERY_POLICY_SOURCE = REPO_ROOT / "policies" / "large-codebase-discovery.md"
SKILLS = (
    "agent-graph-builder",
    "continuous-improvement",
    "development-recovery",
    "project-start",
    "research",
    "task-delivery",
)
AGENT_ROLES = (
    "improvement_verifier",
    "project_docs_auditor",
    "project_docs_curator",
    "project_docs_verifier",
    "research_planner",
    "research_scout",
    "research_synthesizer",
    "research_verifier",
    "task_explorer",
    "task_worker",
    "task_plan_reviewer",
    "task_result_reviewer",
    "task_risk_reviewer",
)
BLOCK_START = "# BEGIN codex-agent-graphs: graph agents"
BLOCK_END = "# END codex-agent-graphs: graph agents"
LEGACY_BLOCK_START = "# BEGIN codex-agent-graphs: research agents"
LEGACY_BLOCK_END = "# END codex-agent-graphs: research agents"
POLICY_BLOCK_START = "<!-- BEGIN codex-development-recovery -->"
POLICY_BLOCK_END = "<!-- END codex-development-recovery -->"
DISCOVERY_POLICY_BLOCK_START = "<!-- BEGIN codex-large-codebase-discovery -->"
DISCOVERY_POLICY_BLOCK_END = "<!-- END codex-large-codebase-discovery -->"
MANAGED_RE = re.compile(
    rf"(?ms)^\s*(?:{re.escape(BLOCK_START)}|{re.escape(LEGACY_BLOCK_START)})\n.*?^\s*(?:{re.escape(BLOCK_END)}|{re.escape(LEGACY_BLOCK_END)})\n?"
)
POLICY_MANAGED_RE = re.compile(
    rf"(?ms)^[ \t]*{re.escape(POLICY_BLOCK_START)}[ \t]*\r?\n.*?"
    rf"^[ \t]*{re.escape(POLICY_BLOCK_END)}[ \t]*(?:\r?\n|$)"
)
DISCOVERY_POLICY_MANAGED_RE = re.compile(
    rf"(?ms)^[ \t]*{re.escape(DISCOVERY_POLICY_BLOCK_START)}[ \t]*\r?\n.*?"
    rf"^[ \t]*{re.escape(DISCOVERY_POLICY_BLOCK_END)}[ \t]*(?:\r?\n|$)"
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
        "improvement_verifier": "Conditional Continuous Improvement candidate verifier.",
        "project_docs_auditor": "Legacy v2 Project Start drift auditor.",
        "project_docs_curator": "Legacy v2 Project Start factual updater.",
        "project_docs_verifier": "Conditional Project Start v3 documentation verifier.",
        "research_planner": "Optional deep-research decomposition helper.",
        "research_scout": "Optional read-only deep-research branch scout.",
        "research_synthesizer": "Optional deep-research evidence synthesizer.",
        "research_verifier": "Conditional bounded research claim verifier.",
        "task_explorer": "Optional read-only Task Delivery codebase explorer.",
        "task_worker": "Optional bounded Task Delivery implementation worker.",
        "task_plan_reviewer": "Conditional Task Delivery plan reviewer.",
        "task_result_reviewer": "Conditional Task Delivery final verifier.",
        "task_risk_reviewer": "Critical-only Task Delivery risk reviewer.",
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


def exact_unmarked_managed_block() -> str:
    block = managed_block()
    body = block.removeprefix(f"{BLOCK_START}\n")
    return body.removesuffix(f"\n{BLOCK_END}\n").strip()


def config_with_block(original: str) -> str:
    without_managed = MANAGED_RE.sub("", original).rstrip()
    exact_unmarked = exact_unmarked_managed_block()
    if BLOCK_START not in original and without_managed.count(exact_unmarked) == 1:
        without_unmarked = without_managed.replace(exact_unmarked, "", 1).rstrip()
        adopted = (
            f"{without_unmarked}\n\n{managed_block()}"
            if without_unmarked
            else managed_block()
        )
        try:
            tomllib.loads(adopted)
        except tomllib.TOMLDecodeError as exc:
            raise InstallError(f"Adopted managed config would be invalid TOML: {exc}") from exc
        return adopted
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
    if config.is_symlink():
        raise InstallError(f"Symlinked config.toml is not managed automatically: {config}")
    original = config.read_text(encoding="utf-8") if config.exists() else ""
    return "in-sync" if original == config_with_block(original) else ("missing" if not config.exists() else "drift")


def policy_block(source: Path, start: str, end: str) -> str:
    if not source.is_file() or source.is_symlink():
        raise InstallError(f"Invalid global policy source: {source}")
    policy = source.read_text(encoding="utf-8").strip()
    if not policy:
        raise InstallError(f"Empty global policy source: {source}")
    managed_markers = (
        POLICY_BLOCK_START,
        POLICY_BLOCK_END,
        DISCOVERY_POLICY_BLOCK_START,
        DISCOVERY_POLICY_BLOCK_END,
    )
    if any(marker in policy for marker in managed_markers):
        raise InstallError(f"Global policy source contains a managed marker: {source}")
    return f"{start}\n{policy}\n{end}\n"


def global_policy_block() -> str:
    return policy_block(GLOBAL_POLICY_SOURCE, POLICY_BLOCK_START, POLICY_BLOCK_END)


def discovery_policy_block() -> str:
    return policy_block(
        DISCOVERY_POLICY_SOURCE,
        DISCOVERY_POLICY_BLOCK_START,
        DISCOVERY_POLICY_BLOCK_END,
    )


def agents_with_policy(original: str) -> str:
    managed = (
        (
            "development-recovery",
            POLICY_BLOCK_START,
            POLICY_BLOCK_END,
            POLICY_MANAGED_RE,
        ),
        (
            "large-codebase-discovery",
            DISCOVERY_POLICY_BLOCK_START,
            DISCOVERY_POLICY_BLOCK_END,
            DISCOVERY_POLICY_MANAGED_RE,
        ),
    )
    without_managed = original
    for name, start, end, pattern in managed:
        start_count = without_managed.count(start)
        end_count = without_managed.count(end)
        if start_count != end_count or start_count > 1:
            raise InstallError(f"Malformed or duplicate managed {name} policy block")
        if start_count and len(list(pattern.finditer(without_managed))) != 1:
            raise InstallError(f"Malformed or embedded managed {name} policy block")
        without_managed = pattern.sub("", without_managed)
    without_managed = without_managed.rstrip()
    blocks = f"{global_policy_block()}\n{discovery_policy_block()}"
    return f"{without_managed}\n\n{blocks}" if without_managed else blocks


def agents_policy_status(codex_home: Path) -> str:
    agents_file = codex_home / "AGENTS.md"
    if agents_file.is_symlink():
        raise InstallError(f"Symlinked AGENTS.md is not managed automatically: {agents_file}")
    original = agents_file.read_text(encoding="utf-8") if agents_file.exists() else ""
    return "in-sync" if original == agents_with_policy(original) else ("missing" if not agents_file.exists() else "drift")


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


def preflight_environment(codex_home: Path) -> tuple[str, str, str, str]:
    codex_home = codex_home.expanduser().resolve()
    manifest(GRAPH_RUNTIME_ROOT)
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
    if config.is_symlink():
        raise InstallError(f"Symlinked config.toml is not managed automatically: {config}")
    original = config.read_text(encoding="utf-8") if config.exists() else ""
    candidate = config_with_block(original)
    agents_file = codex_home / "AGENTS.md"
    if agents_file.is_symlink():
        raise InstallError(f"Symlinked AGENTS.md is not managed automatically: {agents_file}")
    agents_original = agents_file.read_text(encoding="utf-8") if agents_file.exists() else ""
    agents_candidate = agents_with_policy(agents_original)
    return original, candidate, agents_original, agents_candidate


def install_environment(codex_home: Path) -> dict[str, Any]:
    codex_home = codex_home.expanduser().resolve()
    original, candidate, agents_original, agents_candidate = preflight_environment(codex_home)
    config = codex_home / "config.toml"
    agents_file = codex_home / "AGENTS.md"
    backup = backup_root(codex_home)
    changes: list[dict[str, str]] = []
    runtime_target = codex_home / GRAPH_RUNTIME_TARGET
    runtime_status = replace_directory(
        GRAPH_RUNTIME_ROOT,
        runtime_target,
        backup / GRAPH_RUNTIME_TARGET,
    )
    changes.append(
        {
            "kind": "runtime",
            "name": GRAPH_RUNTIME_TARGET,
            "status": runtime_status,
            "target": str(runtime_target),
        }
    )
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

    if agents_candidate == agents_original:
        policy_change = "in-sync"
    else:
        if agents_file.exists():
            agents_backup = backup / "AGENTS.md"
            agents_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agents_file, agents_backup)
        atomic_write(agents_file, agents_candidate)
        policy_change = "installed"
    changes.append(
        {
            "kind": "policy",
            "name": "managed-global-policies",
            "status": policy_change,
            "target": str(agents_file),
        }
    )
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
    runtime_status = path_status(GRAPH_RUNTIME_ROOT, codex_home / GRAPH_RUNTIME_TARGET)
    statuses.append(
        {"kind": "runtime", "name": GRAPH_RUNTIME_TARGET, "status": runtime_status}
    )
    if runtime_status != "in-sync":
        issues.append(f"runtime {GRAPH_RUNTIME_TARGET}: {runtime_status}")
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
    try:
        policy_status = agents_policy_status(codex_home)
    except InstallError as exc:
        policy_status = "conflict"
        issues.append(str(exc))
    statuses.append({"kind": "policy", "name": "managed-global-policies", "status": policy_status})
    if policy_status != "in-sync" and not any("managed" in issue and "policy block" in issue for issue in issues):
        issues.append(f"policy managed-global-policies: {policy_status}")
    return {
        "status": "ok" if not issues else "failed",
        "codex_home": str(codex_home),
        "issues": issues,
        "items": statuses,
    }


def plan_environment(codex_home: Path) -> dict[str, Any]:
    codex_home = codex_home.expanduser().resolve()
    items: list[dict[str, str]] = [
        {
            "kind": "runtime",
            "name": GRAPH_RUNTIME_TARGET,
            "status": path_status(GRAPH_RUNTIME_ROOT, codex_home / GRAPH_RUNTIME_TARGET),
        }
    ]
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
    try:
        policy = agents_policy_status(codex_home)
    except InstallError:
        policy = "conflict"
    items.append({"kind": "policy", "name": "managed-global-policies", "status": policy})
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
