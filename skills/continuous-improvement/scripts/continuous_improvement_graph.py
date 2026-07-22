#!/usr/bin/env python3
"""Deterministic controller for one bounded Continuous Improvement run."""

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
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


SKILL_DIR = Path(__file__).resolve().parents[1]
GRAPH_PATH = SKILL_DIR / "graph.json"
RUNS_REL = PurePosixPath(".agent-graphs/continuous-improvement-runs")
STATE_NAME = "state.json"
WORK_NAME = "improvement.json"
VERIFY_NAME = "verification.json"
COMPLETE_NAME = "IMPROVEMENT.md"
LOCK_NAME = ".state.lock"
IGNORED_TOP_LEVEL = {".git", ".agent-graphs", ".codex", ".project-start", "__pycache__", ".pytest_cache"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[0-9a-f]{16}$")


class GraphError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def result(status: str, summary: str, *, actions: list[str] | None = None, artifacts: list[str] | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": status, "summary": summary, "next_actions": actions or [], "artifacts": artifacts or [], "data": data or {}}


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
        raise GraphError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GraphError(f"Expected JSON object: {path}")
    return value


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def root_path(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise GraphError(f"Repository root not found: {root}")
    return root


def safe_relative(raw: Any, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip() or "\\" in raw or "\x00" in raw:
        raise GraphError(f"{field} must be a non-empty portable relative path.")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise GraphError(f"Unsafe {field}: {raw}")
    return path.as_posix()


def safe_join(root: Path, raw: Any, field: str, *, require_file: bool = False) -> Path:
    relative = safe_relative(raw, field)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise GraphError(f"Unsafe symlink in {field}: {relative}")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise GraphError(f"Path escapes repository: {raw}") from exc
    if require_file and (not candidate.is_file() or candidate.is_symlink()):
        raise GraphError(f"Expected ordinary file for {field}: {relative}")
    return candidate


def graph_contract() -> dict[str, Any]:
    graph = load_json(GRAPH_PATH)
    if graph.get("schema_version") != 2 or graph.get("graph_id") != "continuous-improvement":
        raise GraphError("Continuous Improvement requires graph schema v2.")
    if not isinstance(graph.get("graph_version"), str):
        raise GraphError("graph.json has no graph_version.")
    if set(graph.get("routes", {})) != {"full", "audit"}:
        raise GraphError("graph.json must define full and audit routes.")
    for route in graph["routes"].values():
        if route.get("entry") != "work" or route.get("terminal") != "complete" or set(route.get("nodes", {})) != {"work", "verify", "complete"}:
            raise GraphError("graph.json route contract changed.")
    limits = graph.get("limits")
    if not isinstance(limits, dict) or any(not isinstance(limits.get(key), int) for key in ("max_node_retries", "max_verification_repairs", "max_changed_files")):
        raise GraphError("graph.json limits are invalid.")
    return graph


def manifest(root: Path) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for current_raw, directories, names in os.walk(root, followlinks=False):
        current = Path(current_raw)
        directories[:] = sorted(name for name in directories if name not in IGNORED_TOP_LEVEL)
        for name in sorted(names):
            path = current / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file():
                raise GraphError(f"Repository contains unsupported unsafe entry: {relative}")
            values[relative] = {"sha256": sha256_file(path), "mode": path.stat().st_mode & 0o777}
    return values


def manifest_digest(value: dict[str, dict[str, Any]]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def changed_paths(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def command(args: list[str], root: Path) -> str | None:
    try:
        completed = subprocess.run(args, cwd=root, text=True, capture_output=True, check=False)
    except OSError:
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def git_info(root: Path) -> dict[str, str | None]:
    inside = command(["git", "rev-parse", "--is-inside-work-tree"], root)
    if inside != "true":
        return {"head": None, "branch": None}
    return {"head": command(["git", "rev-parse", "HEAD"], root), "branch": command(["git", "branch", "--show-current"], root)}


def git_dirty(root: Path) -> bool:
    try:
        completed = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=root, capture_output=True, check=False)
    except OSError:
        return True
    if completed.returncode:
        return True
    entries = [item for item in completed.stdout.decode("utf-8", errors="surrogateescape").split("\0") if item]
    return any(not entry[3:].startswith((".agent-graphs/", ".codex/", ".project-start/")) for entry in entries)


@contextlib.contextmanager
def state_lock(run_dir: Path) -> Iterator[None]:
    lock = run_dir / LOCK_NAME
    deadline = time.monotonic() + 5
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise GraphError(f"Run is busy: {run_dir}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} at={now()}\n".encode())
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def run_directory(root: Path, run_id: str) -> Path:
    if not RUN_ID.fullmatch(run_id):
        raise GraphError("Run id is invalid.")
    return safe_join(root, f"{RUNS_REL}/{run_id}", "run directory")


def load_state(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    graph = graph_contract()
    if state.get("schema_version") != 1 or state.get("graph_id") != "continuous-improvement":
        raise GraphError("Run is not a Continuous Improvement v1 state.")
    if state.get("graph_version") != graph["graph_version"] or state.get("graph_sha256") != sha256_file(GRAPH_PATH):
        raise GraphError("graph.json changed after run initialization.")
    root = root_path(str(state.get("root", "")))
    if run_directory(root, str(state.get("run_id", ""))).resolve() != run_dir.resolve():
        raise GraphError("Run directory is incompatible with state identity.")
    if state.get("mode") not in {"full", "audit"} or state.get("status") not in {"running", "blocked", "completed"}:
        raise GraphError("Run state is invalid.")
    if not isinstance(state.get("baseline_manifest"), dict) or state.get("baseline_repo_digest") != manifest_digest(state["baseline_manifest"]):
        raise GraphError("Run baseline is tampered.")
    return state


def save_state(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    atomic_json(run_dir / STATE_NAME, state)


def runner_command() -> str:
    return f"python3 {shlex.quote(str(Path(__file__).resolve()))}"


def initialize(root_raw: str, mode: str, focus: str) -> dict[str, Any]:
    if mode not in {"full", "audit"} or len(focus.strip()) < 3:
        raise GraphError("mode must be full|audit and focus must be substantive.")
    root = root_path(root_raw)
    graph = graph_contract()
    git = git_info(root)
    if mode == "full" and (not git["head"] or git_dirty(root)):
        raise GraphError("full mode requires a clean Git worktree with an initial commit.")
    raw = json.dumps({"root": str(root), "mode": mode, "focus": focus.strip(), "graph": graph["graph_version"]}, sort_keys=True)
    trigger_sequence = 0
    while True:
        identity = raw if trigger_sequence == 0 else f"{raw}\ntrigger_sequence={trigger_sequence}"
        run_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        run_dir = run_directory(root, run_id)
        if (run_dir / STATE_NAME).is_file():
            existing = load_state(run_dir)
            if existing["status"] != "completed":
                return ready(run_dir)
            trigger_sequence += 1
            continue
        if run_dir.exists():
            raise GraphError(f"Run directory is occupied: {run_dir}")
        break
    baseline = manifest(root)
    stamp = now()
    nodes = {name: {"status": "pending", "attempts": 0, "receipts": []} for name in ("work", "verify", "complete")}
    nodes["work"]["status"] = "ready"
    state = {
        "schema_version": 1, "graph_id": "continuous-improvement", "graph_version": graph["graph_version"], "graph_sha256": sha256_file(GRAPH_PATH),
        "run_id": run_id, "trigger_sequence": trigger_sequence, "root": str(root), "mode": mode, "focus": focus.strip(), "status": "running", "current": "work",
        "baseline_manifest": baseline, "baseline_repo_digest": manifest_digest(baseline), "git": git,
        "verification_required": False, "verification_repairs": 0, "node_retries": {"work": 0, "verify": 0}, "nodes": nodes,
        "created_at": stamp, "updated_at": stamp,
    }
    run_dir.mkdir(parents=True)
    atomic_json(run_dir / STATE_NAME, state)
    return ready(run_dir)


def ready(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    if state["status"] == "completed":
        return result("completed", "Continuous Improvement run already completed.", artifacts=[str(run_dir)])
    if state["status"] == "blocked":
        return result("blocked", "Run is blocked; retry only the failed node within its bound.", artifacts=[str(run_dir)])
    current = state["current"]
    artifact = WORK_NAME if current == "work" else VERIFY_NAME if current == "verify" else None
    actions = [f"{runner_command()} complete --run {shlex.quote(str(run_dir))}"] if artifact is None else [f"Create {run_dir / artifact}", f"{runner_command()} record --run {shlex.quote(str(run_dir))} --node {current} --outcome <...>"]
    return result("ready", f"Ready for {current}.", actions=actions, artifacts=[str(run_dir)], data={"run": str(run_dir), "mode": state["mode"], "current": current})


def strings(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value) or len(value) != len(set(value)):
        raise GraphError(f"{field} must be a unique list of non-empty strings.")
    if nonempty and not value:
        raise GraphError(f"{field} must not be empty.")
    return value


def digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise GraphError(f"{field} must be SHA-256.")
    return value


def safe_paths(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    paths = [safe_relative(item, field) for item in strings(value, field, nonempty=nonempty)]
    if len(paths) != len(set(paths)):
        raise GraphError(f"{field} has duplicate paths.")
    return paths


def path_allowed(path: str, scope: list[str]) -> bool:
    return any(path == item or path.startswith(item.rstrip("/") + "/") for item in scope)


def mcp_capability(capabilities: Any) -> list[str]:
    values = strings(capabilities, "capabilities", nonempty=True)
    mcp = [item for item in values if item.startswith("mcp:")]
    if len(mcp) != 1:
        raise GraphError("capabilities requires exactly one MCP receipt.")
    receipt = mcp[0]
    if receipt.startswith("mcp:fallback:"):
        if not re.fullmatch(r"mcp:fallback:[A-Za-z0-9][A-Za-z0-9._-]{7,}", receipt):
            raise GraphError("MCP fallback reason is invalid.")
    elif not re.fullmatch(r"mcp:[A-Za-z0-9][A-Za-z0-9._-]*", receipt) or receipt in {"mcp:none", "mcp:discovery"}:
        raise GraphError("MCP receipt is invalid.")
    return values


def validate_candidate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GraphError("candidate must be an object.")
    for field in ("candidate_id", "title"):
        if not isinstance(value.get(field), str) or len(value[field].strip()) < 3:
            raise GraphError(f"candidate.{field} is not substantive.")
    if value.get("source_kind") not in graph_contract()["candidate_policy"]["delivery_source_kinds"]:
        # Issue-ready is intentionally allowed to capture a non-deliverable source below.
        if not isinstance(value.get("source_kind"), str) or not value["source_kind"].strip():
            raise GraphError("candidate.source_kind is invalid.")
    if value.get("risk") not in {"low", "medium", "high"}:
        raise GraphError("candidate.risk must be low|medium|high.")
    domains = strings(value.get("protected_domains"), "candidate.protected_domains")
    scope = safe_paths(value.get("scope"), "candidate.scope", nonempty=True)
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence or any(not isinstance(item, dict) or any(not isinstance(item.get(key), str) or len(item[key].strip()) < 3 for key in ("kind", "reference", "observation")) for item in evidence):
        raise GraphError("candidate.evidence must contain concrete observations.")
    strings(value.get("reproduction_commands"), "candidate.reproduction_commands", nonempty=True)
    strings(value.get("acceptance"), "candidate.acceptance", nonempty=True)
    return {"source_kind": value["source_kind"], "risk": value["risk"], "protected_domains": domains, "scope": scope}


def validate_tests(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise GraphError("task_delivery.tests must be a non-empty list.")
    checked: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("command"), str) or len(item["command"].strip()) < 3 or item.get("status") != "passed" or item.get("exit_code") != 0:
            raise GraphError("Task Delivery test receipt must be passing with exit_code 0.")
        checked.append(item)
    return checked


def relative_existing(root: Path, raw: Any, field: str) -> Path:
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        return safe_join(root, str(raw), field, require_file=True)
    resolved = path.resolve(strict=False)
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise GraphError(f"{field} escapes repository.") from exc
    return safe_join(root, relative, field, require_file=True)


def validate_task_delivery(root: Path, state: dict[str, Any], receipt: Any, changed: list[str], scope: list[str]) -> None:
    if not isinstance(receipt, dict):
        raise GraphError("delivered requires task_delivery receipt.")
    run_rel = safe_relative(receipt.get("run_dir"), "task_delivery.run_dir")
    match = re.fullmatch(r"\.agent-graphs/task-delivery-runs/([0-9a-f]{16})", run_rel)
    if not match:
        raise GraphError("Task Delivery run_dir is incompatible.")
    run_dir = safe_join(root, run_rel, "task_delivery.run_dir")
    state_path = run_dir / "state.json"
    if not state_path.is_file() or state_path.is_symlink() or sha256_file(state_path) != digest(receipt.get("state_sha256"), "task_delivery.state_sha256"):
        raise GraphError("Task Delivery state receipt is missing or tampered.")
    td = load_json(state_path)
    if td.get("schema_version") != 3 or td.get("graph_id") != "task-delivery" or td.get("status") != "completed" or td.get("run_id") != match.group(1) or Path(str(td.get("root", ""))).resolve() != root:
        raise GraphError("Task Delivery run is not a completed compatible v3 run.")
    task_plan = safe_relative(td.get("plan_path"), "Task Delivery plan_path")
    expected_plan = f"{RUNS_REL}/{state['run_id']}/task-delivery/"
    if not task_plan.startswith(expected_plan) or not task_plan.endswith("/PLAN.md"):
        raise GraphError("Task Delivery plan must remain inside this Continuous Improvement run.")
    if td.get("profile") not in {"standard", "complex", "critical"}:
        raise GraphError("Task Delivery profile is below standard.")
    work = td.get("nodes", {}).get("work", {})
    records = work.get("receipts") if isinstance(work, dict) else None
    if not isinstance(records, list) or not records or not isinstance(records[-1], dict):
        raise GraphError("Task Delivery has no immutable work receipt.")
    work_receipt = records[-1]
    work_path = relative_existing(root, work_receipt.get("path"), "Task Delivery work receipt")
    work_sha = digest(work_receipt.get("sha256"), "Task Delivery work receipt sha")
    if sha256_file(work_path) != work_sha or work_sha != digest(receipt.get("task_sha256"), "task_delivery.task_sha256"):
        raise GraphError("Task Delivery task receipt is tampered or mismatched.")
    if sorted(safe_paths(work_receipt.get("changed_paths"), "Task Delivery changed_paths", nonempty=True)) != sorted(safe_paths(receipt.get("changed_paths"), "task_delivery.changed_paths", nonempty=True)):
        raise GraphError("Task Delivery changed paths do not bind its immutable work receipt.")
    task_id = td.get("task_id")
    if not isinstance(task_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9-]{2,127}", task_id):
        raise GraphError("Task Delivery task id is invalid.")
    task_path = safe_join(root, f".codex/task-delivery/{task_id}/state.json", "Task Delivery task state", require_file=True)
    task = load_json(task_path)
    checkpoint = task.get("checkpoints", {}).get("handoff") if isinstance(task.get("checkpoints"), dict) else None
    if task.get("schema_version") != 3 or task.get("phase") != "completed" or task.get("last_work_receipt") != str(work_receipt.get("path")) or not isinstance(checkpoint, dict):
        raise GraphError("Task Delivery task state is incomplete.")
    handoff = safe_join(root, checkpoint.get("path"), "Task Delivery handoff", require_file=True)
    handoff_sha = digest(checkpoint.get("sha256"), "Task Delivery handoff sha")
    if sha256_file(handoff) != handoff_sha or handoff_sha != digest(receipt.get("handoff_sha256"), "task_delivery.handoff_sha256"):
        raise GraphError("Task Delivery handoff is tampered or mismatched.")
    tests = validate_tests(receipt.get("tests"))
    if not tests:
        raise GraphError("Task Delivery tests are required.")
    declared = safe_paths(receipt.get("changed_paths"), "task_delivery.changed_paths", nonempty=True)
    if sorted(declared) != changed or len(changed) > graph_contract()["limits"]["max_changed_files"] or any(not path_allowed(path, scope) for path in changed):
        raise GraphError("Delivered change set is outside the bounded candidate scope.")


def validate_git_delivery(root: Path, state: dict[str, Any], git: Any, changed: list[str]) -> None:
    if not isinstance(git, dict):
        raise GraphError("delivered requires git receipt.")
    branch = git.get("branch")
    commit = git.get("commit")
    expected = graph_contract()["delivery_policy"]["branch_prefix"] + state["run_id"]
    if branch != expected or branch in graph_contract()["delivery_policy"]["default_branches"] or not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", commit):
        raise GraphError("Git branch or commit receipt is invalid.")
    baseline = state.get("git", {})
    if not isinstance(baseline, dict) or not isinstance(baseline.get("head"), str) or not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", baseline["head"]):
        raise GraphError("Delivered run lacks a Git baseline.")
    info = git_info(root)
    if info.get("branch") != branch or info.get("head") != commit or git_dirty(root):
        raise GraphError("Working tree, branch, or HEAD drifted after delivery.")
    count = command(["git", "rev-list", "--count", f"{baseline['head']}..HEAD"], root)
    paths = command(["git", "diff", "--name-only", "--no-renames", baseline["head"], "HEAD"], root)
    if count != "1" or sorted(filter(None, (paths or "").splitlines())) != changed:
        raise GraphError("Delivered commit is not the exact one-commit bounded delta.")


def validate_work(state: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    root = root_path(state["root"])
    required = {"schema_version", "run_id", "mode", "focus", "disposition", "confidence", "capabilities", "agents", "scan", "candidate", "issue", "task_delivery", "git", "residual_risks"}
    if required - set(artifact) or artifact.get("schema_version") != 1 or artifact.get("run_id") != state["run_id"] or artifact.get("mode") != state["mode"] or artifact.get("focus") != state["focus"]:
        raise GraphError("improvement.json is incompatible with this run.")
    if artifact.get("disposition") not in {"no-op", "issue-ready", "delivered"} or artifact.get("confidence") not in {"high", "medium", "low"}:
        raise GraphError("improvement disposition or confidence is invalid.")
    mcp_capability(artifact.get("capabilities"))
    strings(artifact.get("agents"), "agents")
    strings(artifact.get("residual_risks"), "residual_risks")
    scan = artifact.get("scan")
    if not isinstance(scan, dict) or not isinstance(scan.get("no_candidate_reason"), (str, type(None))) or not strings(scan.get("sources_checked"), "scan.sources_checked", nonempty=True):
        raise GraphError("scan is invalid.")
    disposition = artifact["disposition"]
    current = manifest(root)
    changed = changed_paths(state["baseline_manifest"], current)
    if disposition == "no-op":
        if any(artifact.get(key) is not None for key in ("candidate", "issue", "task_delivery", "git")) or not isinstance(scan.get("no_candidate_reason"), str) or len(scan["no_candidate_reason"].strip()) < 8 or changed:
            raise GraphError("no-op requires substantive no-candidate evidence and zero repository drift.")
    else:
        candidate = validate_candidate(artifact.get("candidate"))
        if disposition == "issue-ready":
            issue = artifact.get("issue")
            if not isinstance(issue, dict) or any(not isinstance(issue.get(key), str) or len(issue[key].strip()) < 4 for key in ("title", "body", "reason")) or artifact.get("task_delivery") is not None or artifact.get("git") is not None or changed:
                raise GraphError("issue-ready requires an issue and zero repository drift.")
        else:
            policy = graph_contract()["candidate_policy"]
            if state["mode"] != "full" or candidate["risk"] != "low" or candidate["protected_domains"] or candidate["source_kind"] not in policy["delivery_source_kinds"]:
                raise GraphError("delivered violates the low-risk candidate boundary.")
            for path in candidate["scope"]:
                if any(fragment in path.lower() for fragment in policy["protected_path_fragments"]):
                    raise GraphError("delivered candidate scope contains a protected path.")
            validate_task_delivery(root, state, artifact.get("task_delivery"), changed, candidate["scope"])
            validate_git_delivery(root, state, artifact.get("git"), changed)
    return {"disposition": disposition, "changed_paths": changed}


def preserve(run_dir: Path, node: str, attempt: int, source: Path) -> tuple[Path, str]:
    digest_value = sha256_file(source)
    target = run_dir / "receipts" / f"{node}-{attempt}-{digest_value[:12]}.json"
    atomic_text(target, source.read_text(encoding="utf-8"))
    if sha256_file(target) != digest_value:
        raise GraphError("Could not preserve immutable receipt.")
    return target, digest_value


def validate_verification(state: dict[str, Any], artifact: dict[str, Any], outcome: str) -> None:
    work = state["nodes"]["work"]["receipts"][-1]
    if artifact.get("schema_version") != 1 or artifact.get("run_id") != state["run_id"] or artifact.get("reviewer_role") != "improvement_verifier" or not isinstance(artifact.get("reviewer_receipt"), str) or len(artifact["reviewer_receipt"].strip()) < 6 or artifact.get("work_sha256") != work["sha256"]:
        raise GraphError("verification.json is not bound to the exact work receipt.")
    if artifact.get("verdict") not in {"pass", "reject"}:
        raise GraphError("Verifier verdict is invalid.")
    strings(artifact.get("checked_claims"), "verification.checked_claims", nonempty=True)
    strings(artifact.get("residual_risks"), "verification.residual_risks")
    repairs = strings(artifact.get("repair_list"), "verification.repair_list")
    if (outcome == "succeeded" and artifact["verdict"] != "pass") or (outcome == "failed" and (artifact["verdict"] != "reject" or not repairs)):
        raise GraphError("Verification outcome and verdict are incompatible.")


def record(run_dir: Path, node: str, outcome: str) -> dict[str, Any]:
    if node not in {"work", "verify"}:
        raise GraphError("record accepts work or verify only.")
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] != "running" or state["current"] != node or state["nodes"][node]["status"] != "ready":
            raise GraphError("Node is not ready.")
        source = run_dir / (WORK_NAME if node == "work" else VERIFY_NAME)
        if node == "work" and outcome == "failed":
            state["nodes"][node]["status"] = "failed"; state["nodes"][node]["attempts"] += 1; state["status"] = "blocked"; save_state(run_dir, state)
            return result("blocked", "Work failed; one bounded retry may be available.", artifacts=[str(run_dir)])
        if not source.is_file() or source.is_symlink():
            raise GraphError(f"Missing ordinary artifact: {source}")
        if node == "work":
            if outcome not in {"succeeded", "verify"}:
                raise GraphError("work outcome must be succeeded|verify|failed.")
            details = validate_work(state, load_json(source))
            target, receipt_sha = preserve(run_dir, node, state["nodes"][node]["attempts"] + 1, source)
            state["nodes"][node]["attempts"] += 1; state["nodes"][node]["receipts"].append({"path": str(target), "sha256": receipt_sha, **details}); state["nodes"][node]["status"] = "completed"
            if outcome == "verify":
                state["verification_required"] = True; state["current"] = "verify"; state["nodes"]["verify"]["status"] = "ready"
            else:
                state["current"] = "complete"; state["nodes"]["complete"]["status"] = "ready"
        else:
            if outcome not in {"succeeded", "failed"}:
                raise GraphError("verify outcome must be succeeded|failed.")
            validate_verification(state, load_json(source), outcome)
            target, receipt_sha = preserve(run_dir, node, state["nodes"][node]["attempts"] + 1, source)
            state["nodes"][node]["attempts"] += 1; state["nodes"][node]["receipts"].append({"path": str(target), "sha256": receipt_sha, "work_sha256": state["nodes"]["work"]["receipts"][-1]["sha256"]})
            if outcome == "succeeded":
                state["nodes"][node]["status"] = "completed"; state["current"] = "complete"; state["nodes"]["complete"]["status"] = "ready"
            else:
                state["verification_repairs"] += 1
                if state["verification_repairs"] > graph_contract()["limits"]["max_verification_repairs"]:
                    state["nodes"][node]["status"] = "failed"; state["status"] = "blocked"
                else:
                    state["nodes"][node]["status"] = "pending"; state["nodes"]["work"]["status"] = "ready"; state["current"] = "work"
        save_state(run_dir, state)
    return ready(run_dir)


def retry(run_dir: Path, node: str) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        if node not in {"work", "verify"} or state["status"] != "blocked" or state["nodes"].get(node, {}).get("status") != "failed":
            raise GraphError("Only a failed node in a blocked run can retry.")
        if (node == "verify" and state["verification_repairs"] > graph_contract()["limits"]["max_verification_repairs"]) or state["node_retries"][node] >= graph_contract()["limits"]["max_node_retries"]:
            raise GraphError("Retry bound is exhausted.")
        state["node_retries"][node] += 1; state["status"] = "running"; state["current"] = node; state["nodes"][node]["status"] = "ready"; save_state(run_dir, state)
    return ready(run_dir)


def completion_markdown(artifact: dict[str, Any], changed: list[str]) -> str:
    lines = [
        "# Continuous Improvement result",
        "",
        f"Status: {artifact['disposition']}",
        "",
        "## Summary",
        "",
        f"Focus: {artifact['focus']}",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(f"- Source checked: {source}" for source in artifact["scan"]["sources_checked"])
    candidate = artifact.get("candidate")
    if isinstance(candidate, dict):
        lines.append(f"- Candidate: {candidate['title']} ({candidate['source_kind']}, risk={candidate['risk']})")
        lines.extend(f"- {item['kind']}: {item['reference']} — {item['observation']}" for item in candidate["evidence"])
    elif artifact["disposition"] == "no-op":
        lines.append(f"- No candidate: {artifact['scan']['no_candidate_reason']}")
    lines += ["", "## Changed paths", ""]
    lines.extend(f"- {path}" for path in changed) if changed else lines.append("- None")
    tests = artifact.get("task_delivery", {}).get("tests", []) if isinstance(artifact.get("task_delivery"), dict) else []
    lines += ["", "## Verification", ""]
    lines.extend(f"- PASS: `{item['command']}`" for item in tests) if tests else lines.append("- No implementation tests required")
    risks = artifact.get("residual_risks", [])
    lines += ["", "## Residual risks", ""] + ([f"- {risk}" for risk in risks] or ["- None recorded"])
    return "\n".join(lines) + "\n"


def complete(run_dir: Path) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        if state["status"] == "completed":
            output = run_dir / COMPLETE_NAME
            if not output.is_file() or sha256_file(output) != state.get("complete_sha256"):
                raise GraphError("Completion artifact was tampered.")
            return result("completed", "Continuous Improvement run already completed.", artifacts=[str(output), str(run_dir)])
        if state["status"] != "running" or state["current"] != "complete":
            raise GraphError("Run is not ready for completion.")
        work = state["nodes"]["work"]["receipts"][-1]
        source = relative_existing(root_path(state["root"]), work["path"], "immutable work receipt")
        if sha256_file(source) != work["sha256"]:
            raise GraphError("Work receipt was tampered.")
        artifact = load_json(source)
        details = validate_work(state, artifact)
        if state["verification_required"]:
            verify = state["nodes"]["verify"]
            if verify["status"] != "completed" or not verify["receipts"] or verify["receipts"][-1].get("work_sha256") != work["sha256"]:
                raise GraphError("Required verifier pass is missing or mismatched.")
            verify_path = relative_existing(root_path(state["root"]), verify["receipts"][-1]["path"], "immutable verification receipt")
            if sha256_file(verify_path) != verify["receipts"][-1]["sha256"]:
                raise GraphError("Verification receipt was tampered.")
        output = run_dir / COMPLETE_NAME
        atomic_text(output, completion_markdown(artifact, details["changed_paths"]))
        complete_sha = sha256_file(output)
        if sha256_file(output) != complete_sha:
            raise GraphError("Completion artifact cannot be rechecked.")
        state["nodes"]["complete"]["status"] = "completed"; state["status"] = "completed"; state["complete_sha256"] = complete_sha; save_state(run_dir, state)
    return result("completed", "Continuous Improvement completion receipt created.", artifacts=[str(output), str(run_dir)], data={"disposition": details["disposition"]})


def status(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    return result(state["status"], "Continuous Improvement state read without mutation.", artifacts=[str(run_dir / STATE_NAME)], data={"run_id": state["run_id"], "mode": state["mode"], "current": state["current"], "verification_repairs": state["verification_repairs"]})


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(description=__doc__)
    sub = command_parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--root", required=True); init.add_argument("--mode", choices=("full", "audit"), default="full"); init.add_argument("--focus", required=True)
    for name in ("ready", "status", "complete"):
        item = sub.add_parser(name); item.add_argument("--run", required=True)
    record_parser = sub.add_parser("record"); record_parser.add_argument("--run", required=True); record_parser.add_argument("--node", choices=("work", "verify"), required=True); record_parser.add_argument("--outcome", required=True)
    retry_parser = sub.add_parser("retry"); retry_parser.add_argument("--run", required=True); retry_parser.add_argument("--node", choices=("work", "verify"), required=True)
    return command_parser


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init": payload = initialize(args.root, args.mode, args.focus)
        else:
            run_dir = Path(args.run).expanduser().resolve()
            if not run_dir.is_dir() or not (run_dir / STATE_NAME).is_file(): raise GraphError("Run directory not found.")
            if args.command == "ready": payload = ready(run_dir)
            elif args.command == "status": payload = status(run_dir)
            elif args.command == "record": payload = record(run_dir, args.node, args.outcome)
            elif args.command == "retry": payload = retry(run_dir, args.node)
            else: payload = complete(run_dir)
    except (GraphError, OSError, ValueError, KeyError) as exc:
        print(json.dumps(result("failed", str(exc)), ensure_ascii=False, indent=2)); return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0 if payload["status"] not in {"failed", "blocked"} else 2


if __name__ == "__main__":
    sys.exit(main())
