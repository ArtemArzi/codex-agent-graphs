#!/usr/bin/env python3
"""Install and verify Codex workflows in WSL CLI and Codex Desktop homes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
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
ORCHESTRATION_POLICY_SOURCE = REPO_ROOT / "policies" / "orchestration.md"
SKILLS = (
    "agent-graph-builder",
    "continuous-improvement",
    "development-recovery",
    "project-start",
    "research",
    "task-delivery",
)
_routing_spec = importlib.util.spec_from_file_location("codex_model_routing", REPO_ROOT / "scripts/model_routing.py")
assert _routing_spec and _routing_spec.loader
routing = importlib.util.module_from_spec(_routing_spec)
_routing_spec.loader.exec_module(routing)
AGENT_ROLES = tuple(routing.load_policy()["roles"])
NATIVE_ROLES = {role for role, spec in routing.load_policy()["roles"].items() if "/native/" in spec["template"]}
BLOCK_START = "# BEGIN codex-agent-graphs: graph agents"
BLOCK_END = "# END codex-agent-graphs: graph agents"
LEGACY_BLOCK_START = "# BEGIN codex-agent-graphs: research agents"
LEGACY_BLOCK_END = "# END codex-agent-graphs: research agents"
POLICY_BLOCK_START = "<!-- BEGIN codex-development-recovery -->"
POLICY_BLOCK_END = "<!-- END codex-development-recovery -->"
DISCOVERY_POLICY_BLOCK_START = "<!-- BEGIN codex-large-codebase-discovery -->"
DISCOVERY_POLICY_BLOCK_END = "<!-- END codex-large-codebase-discovery -->"
ORCHESTRATION_POLICY_BLOCK_START = "<!-- BEGIN codex-orchestration -->"
ORCHESTRATION_POLICY_BLOCK_END = "<!-- END codex-orchestration -->"
# Only this audited unmarked policy may be adopted automatically. Unknown local
# edits are never removed just because they share a heading.
LEGACY_ORCHESTRATION_SHA256 = "1e0afaf5c6a78ca52ecb08e4c0262d1704a069e328e26377de947c86457b3da9"
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
ORCHESTRATION_POLICY_MANAGED_RE = re.compile(
    rf"(?ms)^[ \t]*{re.escape(ORCHESTRATION_POLICY_BLOCK_START)}[ \t]*\r?\n.*?"
    rf"^[ \t]*{re.escape(ORCHESTRATION_POLICY_BLOCK_END)}[ \t]*(?:\r?\n|$)"
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


def role_descriptions() -> dict[str, str]:
    descriptions = {
        "improvement_verifier": "Independent whole-candidate Continuous Improvement acceptor.",
        "project_docs_auditor": "Legacy v2 Project Start drift auditor.",
        "project_docs_curator": "Legacy v2 Project Start factual updater.",
        "project_docs_verifier": "Independent whole-result Project Start documentation acceptor.",
        "research_planner": "Optional deep-research decomposition helper.",
        "research_scout": "Optional read-only deep-research branch scout.",
        "research_synthesizer": "Optional deep-research evidence synthesizer.",
        "research_verifier": "Independent whole-result research acceptor.",
        "task_explorer": "Optional read-only Task Delivery codebase explorer.",
        "task_worker": "Optional bounded Task Delivery implementation worker.",
        "task_plan_reviewer": "Fresh independent whole-plan acceptor for any substantive workflow.",
        "task_result_reviewer": "Fresh independent whole-result Task Delivery acceptor.",
        "task_risk_reviewer": "Focused risk reviewer supporting independent acceptance.",
    }
    for role in NATIVE_ROLES:
        descriptions[role] = tomllib.loads(routing.role_template(role).read_text(encoding="utf-8"))["description"]
    return descriptions


def managed_block(extras: dict[str, dict] | None = None) -> str:
    lines = [BLOCK_START]
    descriptions = role_descriptions()
    for role in AGENT_ROLES:
        lines.extend(
            [
                "",
                f"[agents.{role}]",
                f'description = "{descriptions[role]}"',
                f'config_file = "./agents/{role}.toml"',
            ]
        )
        for key, value in (extras or {}).get(role, {}).items():
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["", BLOCK_END, ""])
    return "\n".join(lines)


def exact_unmarked_managed_block() -> str:
    block = managed_block()
    body = block.removeprefix(f"{BLOCK_START}\n")
    return body.removesuffix(f"\n{BLOCK_END}\n").strip()


def config_with_block(original: str) -> str:
    try:
        parsed = tomllib.loads(original)
    except tomllib.TOMLDecodeError as exc:
        raise InstallError(f"Invalid original config TOML: {exc}") from exc
    extras = {role: {"nickname_candidates": spec["nickname_candidates"]}
              for role, spec in parsed.get("agents", {}).items()
              if role in AGENT_ROLES and isinstance(spec, dict) and "nickname_candidates" in spec}
    # Only standalone structural comments are markers, never prompt examples.
    markers = {BLOCK_START: BLOCK_END, LEGACY_BLOCK_START: LEGACY_BLOCK_END}
    opened = None
    removed: set[int] = set()
    seen = 0
    for number, line in routing._structural_lines(original):
        token = line.strip()
        if token in markers:
            if opened is not None or seen:
                raise InstallError("Duplicate or nested managed config block")
            opened = (number, markers[token])
            seen += 1
        elif token in markers.values():
            if opened is None or token != opened[1]:
                raise InstallError("Mismatched managed config block")
            removed.update(range(opened[0], number + 1))
            opened = None
        elif any(marker in line for marker in (*markers, *markers.values())):
            raise InstallError("Embedded managed config marker")
    if opened is not None:
        raise InstallError("Unclosed managed config block")
    without_managed = "".join(line for number, line in enumerate(original.splitlines(keepends=True))
                              if number not in removed).rstrip()
    exact_unmarked = exact_unmarked_managed_block()
    if BLOCK_START not in original and without_managed.count(exact_unmarked) == 1:
        without_unmarked = without_managed.replace(exact_unmarked, "", 1).rstrip()
        adopted = routing.config_defaults(without_unmarked).rstrip() + "\n\n" + managed_block(extras)
        try:
            tomllib.loads(adopted)
        except tomllib.TOMLDecodeError as exc:
            raise InstallError(f"Adopted managed config would be invalid TOML: {exc}") from exc
        return adopted
    try:
        without_managed, _ = routing.adopt_native_registrations(without_managed, NATIVE_ROLES)
    except ValueError as exc:
        raise InstallError(str(exc)) from exc
    remaining = tomllib.loads(without_managed)
    for role in AGENT_ROLES:
        if role in remaining.get("agents", {}):
            raise InstallError(f"Unmanaged config already defines [agents.{role}]")
    candidate = routing.config_defaults(without_managed).rstrip() + "\n\n" + managed_block(extras)
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
        ORCHESTRATION_POLICY_BLOCK_START,
        ORCHESTRATION_POLICY_BLOCK_END,
        routing.POLICY_START,
        routing.POLICY_END,
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
    if ORCHESTRATION_POLICY_BLOCK_START not in original and "# Global Codex Orchestration Policy" in original:
        # The legacy block occupies the document prefix, ending at the first
        # managed block. Preserve all following instructions byte-for-byte here.
        boundary = original.find("<!-- BEGIN ")
        prior = original if boundary < 0 else original[:boundary]
        if hashlib.sha256(prior.rstrip().encode("utf-8")).hexdigest() != LEGACY_ORCHESTRATION_SHA256:
            raise InstallError("Unrecognized local orchestration policy; inspect drift before adoption")
        original = "" if boundary < 0 else original[boundary:]
    managed = (
        (
            "model-routing",
            routing.POLICY_START,
            routing.POLICY_END,
            re.compile(rf"(?ms)^[ \t]*{re.escape(routing.POLICY_START)}[ \t]*\r?\n.*?^[ \t]*{re.escape(routing.POLICY_END)}[ \t]*(?:\r?\n|$)"),
        ),
        (
            "orchestration",
            ORCHESTRATION_POLICY_BLOCK_START,
            ORCHESTRATION_POLICY_BLOCK_END,
            ORCHESTRATION_POLICY_MANAGED_RE,
        ),
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
    orchestration = policy_block(
        ORCHESTRATION_POLICY_SOURCE, ORCHESTRATION_POLICY_BLOCK_START, ORCHESTRATION_POLICY_BLOCK_END
    )
    model_policy = f"{routing.POLICY_START}\n{routing.render_policy()}{routing.POLICY_END}\n"
    blocks = f"{model_policy}\n{orchestration}\n{global_policy_block()}\n{discovery_policy_block()}"
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


def generated_status(content: str, target: Path) -> str:
    if target.is_symlink():
        raise InstallError(f"Symlinked generated file is not managed automatically: {target}")
    if not target.exists():
        return "missing"
    if not target.is_file():
        raise InstallError(f"Generated target is not a regular file: {target}")
    return "in-sync" if target.read_text(encoding="utf-8") == content else "drift"


def replace_generated(content: str, target: Path, backup: Path) -> str:
    if generated_status(content, target) == "in-sync":
        return "in-sync"
    if target.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
    atomic_write(target, content)
    return "installed"


def generated_files(codex_home: Path) -> dict[Path, tuple[str, str]]:
    files = {Path(routing.POLICY_TARGET): ("routing-policy", routing.POLICY_PATH.read_text(encoding="utf-8"))}
    for role, description in role_descriptions().items():
        files[Path("agents") / f"{role}.toml"] = ("agent", routing.render_agent(role, description))
    for alias in routing.load_policy()["profile_aliases"]:
        path = Path(f"{alias}.config.toml")
        target = codex_home / path
        if target.is_symlink():
            raise InstallError(f"Symlinked profile is not managed automatically: {target}")
        original = target.read_text(encoding="utf-8") if target.exists() else ""
        try:
            candidate = routing.profile_candidate(original, alias)
        except ValueError as exc:
            raise InstallError(str(exc)) from exc
        files[path] = ("profile", candidate)
    return files


def validate_install_parents(codex_home: Path) -> None:
    # A linked parent can redirect otherwise regular targets outside this home.
    for relative in ("agents", "skills", "backups", "backups/agent-graphs"):
        parent = codex_home / relative
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise InstallError(f"Unsafe install parent: {parent}")


def validate_routing_environment(codex_home: Path) -> None:
    validate_install_parents(codex_home)
    known_profiles = set(routing.load_policy()["profile_aliases"])
    for profile in codex_home.glob("*.config.toml"):
        if profile.name.removesuffix(".config.toml") in known_profiles:
            continue
        if profile.is_symlink() or not profile.is_file():
            raise InstallError(f"Unmanaged profile is not a regular file: {profile}")
        try:
            overlay = tomllib.loads(profile.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InstallError(f"Cannot inspect unmanaged profile: {profile}") from exc
        if routing.has_routing_override(overlay):
            raise InstallError(f"Unmanaged profile contains routing overrides: {profile}")


def preflight_environment(codex_home: Path) -> tuple[str, str, str, str]:
    codex_home = codex_home.expanduser().resolve()
    validate_routing_environment(codex_home)
    manifest(GRAPH_RUNTIME_ROOT)
    for skill in SKILLS:
        manifest(SKILLS_ROOT / skill)
    for role in AGENT_ROLES:
        source = routing.role_template(role)
        if not source.is_file() or source.is_symlink():
            raise InstallError(f"Invalid agent source: {source}")
        try:
            tomllib.loads(source.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise InstallError(f"Invalid agent TOML {source}: {exc}") from exc
    for relative, (_, content) in generated_files(codex_home).items():
        generated_status(content, codex_home / relative)
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
    try:
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
        for relative, (kind, content) in generated_files(codex_home).items():
            target = codex_home / relative
            status = replace_generated(content, target, backup / relative)
            changes.append({"kind": kind, "name": relative.stem, "status": status, "target": str(target)})

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

    except (OSError, ValueError, InstallError) as exc:
        error = InstallError(f"Installation stopped for {codex_home}: {exc}")
        error.partial_install = {"codex_home": str(codex_home), "changes": changes,
                                 "backup": str(backup) if backup.exists() else None}
        raise error from exc


def verify_environment(codex_home: Path) -> dict[str, Any]:
    codex_home = codex_home.expanduser().resolve()
    try:
        validate_routing_environment(codex_home)
    except InstallError as exc:
        return {"status": "failed", "codex_home": str(codex_home), "issues": [str(exc)], "items": []}
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
    try:
        for relative, (kind, content) in generated_files(codex_home).items():
            status = generated_status(content, codex_home / relative)
            statuses.append({"kind": kind, "name": relative.stem, "status": status})
            if status != "in-sync":
                issues.append(f"{kind} {relative}: {status}")
    except (ValueError, InstallError) as exc:
        issues.append(str(exc))
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
    try:
        validate_routing_environment(codex_home)
    except InstallError as exc:
        return {"codex_home": str(codex_home), "items": [
            {"kind": "environment", "name": "routing-preflight", "status": "conflict", "error": str(exc)}]}
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
    try:
        for relative, (kind, content) in generated_files(codex_home).items():
            items.append({"kind": kind, "name": relative.stem, "status": generated_status(content, codex_home / relative)})
    except (ValueError, InstallError) as exc:
        items.append({"kind": "routing", "name": "generated-files", "status": "conflict", "error": str(exc)})
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
    environments: list[dict[str, Any]] = []
    try:
        homes = selected_homes(args)
        if args.action == "install":
            for _, home in homes:
                preflight_environment(home)
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
    except (InstallError, OSError, ValueError) as exc:
        response = {
            "status": "failed",
            "summary": str(exc),
            "next_actions": ["Fix the reported install condition and retry"],
            "artifacts": [str(REPO_ROOT)],
            "data": {"environments": environments, "partial_install": getattr(exc, "partial_install", None)},
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
