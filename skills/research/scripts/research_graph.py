#!/usr/bin/env python3
"""Deterministic control, budget, and integrity layer for native Research work."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urldefrag


SKILL_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = SKILL_DIR / "graph.json"
STATE_NAME = "state.json"
LOCK_NAME = ".state.lock"
WORK_ARTIFACT = "research.json"
VERIFICATION_ARTIFACT = "verification.json"
LEGACY_ACTIVE_GRAPH_IDENTITIES = {
    ("2.1.0", "b3c872a1b1b673cc545a8c0ae16a687333d8d3aaa19ae2362861c61f0d6ef5a2"),
    ("2.2.0", "41458f1adc556e6fcc87979af1e1d5fefeb8340f15bd49a153e8ee305ed620e6"),
}


class GraphError(RuntimeError):
    """A user-actionable graph contract error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GraphError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GraphError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GraphError(f"Expected a JSON object in {path}")
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


def ensure_within(path: Path, root: Path, label: str) -> Path:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise GraphError(f"{label} escapes allowed root {resolved_root}: {resolved_path}") from exc
    return resolved_path


def graph_contract() -> dict[str, Any]:
    graph = load_json(GRAPH_PATH)
    required = {
        "schema_version",
        "graph_id",
        "graph_version",
        "entry",
        "terminal",
        "default_depth",
        "limits",
        "work_policy",
        "execution_policy",
        "optional_agents",
        "mcp_policy",
        "nodes",
    }
    missing = required.difference(graph)
    if missing:
        raise GraphError(f"Graph contract is missing keys: {sorted(missing)}")
    if graph["schema_version"] != 2:
        raise GraphError("Research graph contract must use schema version 2")
    if graph["default_depth"] != "auto":
        raise GraphError("Research graph must default to auto depth")
    nodes = graph["nodes"]
    if set(nodes) != {"work", "verify", "complete"}:
        raise GraphError("Research graph must expose only work, verify, and complete")
    if graph["entry"] != "work" or graph["terminal"] != "complete":
        raise GraphError("Research graph entry or terminal node is invalid")
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
        raise GraphError("Research graph conditional MCP policy is invalid")
    if graph.get("work_policy", {}).get("fast_path") != "root-only":
        raise GraphError("Research graph fast path must remain root-only")
    execution = graph.get("execution_policy", {})
    if (
        execution.get("default_tier") != "skill-only"
        or set(execution.get("tiers", {}))
        != {"skill-only", "tracked", "verified"}
    ):
        raise GraphError("Research graph execution tiers are invalid")
    for profile in ("fast", "deep"):
        if profile not in graph["limits"]:
            raise GraphError(f"Research graph is missing {profile} limits")
        limits = graph["limits"][profile]
        checkpoints = limits.get("source_checkpoints")
        maximum = limits.get("max_sources")
        if (
            not isinstance(checkpoints, list)
            or not checkpoints
            or any(type(value) is not int or value < 1 for value in checkpoints)
            or checkpoints != sorted(set(checkpoints))
        ):
            raise GraphError(f"Research {profile} source checkpoints must be unique ascending integers")
        if type(maximum) is not int or maximum < 1 or checkpoints[-1] != maximum:
            raise GraphError(f"Research {profile} final source checkpoint must equal max_sources")
    return graph


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


def fingerprint(
    question: str,
    workspace: Path,
    output: Path,
    graph_version: str,
    requested_depth: str,
) -> str:
    canonical = json.dumps(
        {
            "question": question.strip(),
            "workspace": str(workspace),
            "output": str(output),
            "graph_version": graph_version,
            "requested_depth": requested_depth,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def run_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir() or not (path / STATE_NAME).is_file():
        raise GraphError(f"Not a research run directory: {path}")
    return path


@contextlib.contextmanager
def state_lock(
    run_dir: Path, stale_after_seconds: int = 120, wait_seconds: float = 5.0
) -> Iterator[None]:
    lock_path = run_dir / LOCK_NAME
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > stale_after_seconds:
                lock_path.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise GraphError(f"Run is locked by another process: {run_dir}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()} created={utc_now()}\n".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def initial_state(
    graph: dict[str, Any],
    question: str,
    workspace: Path,
    output: Path,
    run_id: str,
    requested_depth: str,
) -> dict[str, Any]:
    nodes = {
        name: {"status": "pending", "attempts": 0, "receipts": []}
        for name in graph["nodes"]
    }
    nodes[graph["entry"]]["status"] = "ready"
    now = utc_now()
    return {
        "schema_version": 2,
        "graph_id": graph["graph_id"],
        "graph_version": graph["graph_version"],
        "graph_sha256": sha256_file(GRAPH_PATH),
        "run_id": run_id,
        "question": question.strip(),
        "workspace": str(workspace),
        "output": str(output),
        "requested_depth": requested_depth,
        "mode": "deep" if requested_depth == "deep" else "fast",
        "status": "running",
        "current": graph["entry"],
        "verification_required": False,
        "verification_repairs": 0,
        "capabilities_used": [],
        "agents_used": [],
        "node_retries": {name: 0 for name in graph["nodes"]},
        "created_at": now,
        "updated_at": now,
        "nodes": nodes,
        "events": [{"at": now, "event": "run_initialized", "node": graph["entry"]}],
    }


def initialize(
    question: str,
    workspace_value: str,
    output_value: str,
    requested_depth: str = "auto",
) -> dict[str, Any]:
    if not question.strip():
        raise GraphError("Question must not be empty")
    if requested_depth not in {"auto", "deep"}:
        raise GraphError("Depth must be auto or deep")
    workspace = Path(workspace_value).expanduser().resolve()
    if not workspace.is_dir():
        raise GraphError(f"Workspace does not exist: {workspace}")
    raw_output = Path(output_value).expanduser()
    output = raw_output.resolve() if raw_output.is_absolute() else (workspace / raw_output).resolve()
    ensure_within(output, workspace, "Output")
    graph = graph_contract()
    run_id = fingerprint(question, workspace, output, graph["graph_version"], requested_depth)
    runtime_root = ensure_within(workspace / ".agent-graphs", workspace, "Runtime root")
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_ignore = ensure_within(runtime_root / ".gitignore", runtime_root, "Runtime ignore file")
    if runtime_ignore.exists() and (runtime_ignore.is_symlink() or not runtime_ignore.is_file()):
        raise GraphError(f"Runtime ignore path is not a regular file: {runtime_ignore}")
    if not runtime_ignore.exists():
        write_text_atomic(runtime_ignore, "*\n")
    elif "*" not in {line.strip() for line in runtime_ignore.read_text(encoding="utf-8").splitlines()}:
        write_text_atomic(runtime_ignore, runtime_ignore.read_text(encoding="utf-8").rstrip() + "\n*\n")
    runs_root = ensure_within(runtime_root / "research-runs", runtime_root, "Runs root")
    run_dir = ensure_within(runs_root / run_id, runs_root, "Run directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / STATE_NAME
    with state_lock(run_dir):
        if state_path.exists():
            state = load_state(run_dir)
            expected = (question.strip(), str(workspace), str(output), requested_depth)
            actual = (
                state.get("question"),
                state.get("workspace"),
                state.get("output"),
                state.get("requested_depth"),
            )
            if actual != expected:
                raise GraphError(f"Run fingerprint collision at {run_dir}")
            return result(
                "ok",
                "Existing research run resumed",
                next_actions=[f"Inspect control state with: ready --run {run_dir}"],
                artifacts=[str(state_path)],
                data={"run_dir": str(run_dir), "current": state["current"]},
            )
        state = initial_state(graph, question, workspace, output, run_id, requested_depth)
        write_json_atomic(state_path, state)
    return result(
        "ok",
        "Native research run initialized",
        next_actions=["Execute one native work loop"],
        artifacts=[str(state_path)],
        data={"run_dir": str(run_dir), "current": graph["entry"], "mode": state["mode"]},
    )


def load_state(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    graph = graph_contract()
    if state.get("schema_version") != 2:
        raise GraphError(
            "This run uses the retired Research v1 state. Keep its artifacts as evidence and start a new v2 run."
        )
    if state.get("graph_id") != graph["graph_id"]:
        raise GraphError("Run belongs to another graph")
    identity = (state.get("graph_version"), state.get("graph_sha256"))
    current_identity = (graph["graph_version"], sha256_file(GRAPH_PATH))
    if identity != current_identity and identity not in LEGACY_ACTIVE_GRAPH_IDENTITIES:
        raise GraphError(
            f"Run graph identity {identity[0]} does not match installed {graph['graph_version']}"
        )
    return state


def state_summary(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    return result(
        "ok",
        f"Research run is {state['status']} at {state['current']}",
        next_actions=[] if state["status"] != "running" else [f"Execute node: {state['current']}"],
        artifacts=[str(run_dir / STATE_NAME)],
        data={
            "run_id": state["run_id"],
            "status": state["status"],
            "current": state["current"],
            "requested_depth": state["requested_depth"],
            "mode": state["mode"],
            "verification_required": state["verification_required"],
            "verification_repairs": state["verification_repairs"],
            "capabilities_used": state["capabilities_used"],
            "agents_used": state["agents_used"],
            "output": state["output"],
        },
    )


def ready_node(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    if state["status"] != "running":
        raise GraphError(f"Run is not active: {state['status']}")
    graph = graph_contract()
    node_name = state["current"]
    node_state = state["nodes"][node_name]
    if node_state["status"] != "ready":
        raise GraphError(f"Current node {node_name} is not ready")
    node = graph["nodes"][node_name]
    artifact = Path(state["output"]) if node_name == graph["terminal"] else run_dir / node["artifact"]
    data: dict[str, Any] = {
        "node": node_name,
        "role": node["role"],
        "expected_artifact": str(artifact),
        "attempt": node_state["attempts"] + 1,
    }
    if node_name == "work":
        default_mode = "deep" if state["requested_depth"] == "deep" else "fast"
        data.update(
            {
                "execution": "one native root-agent loop",
                "default_mode": default_mode,
                "budgets": graph["limits"][default_mode],
                "adaptive_budgets": {
                    profile: graph["limits"][profile] for profile in ("fast", "deep")
                },
                "mcp_policy": graph["mcp_policy"],
                "execution_policy": graph["execution_policy"],
                "allowed_outcomes": ["succeeded", "verify", "failed"],
            }
        )
        next_actions = [
            "Use relevant skills/tools natively, write the report and research.json, then record work once"
        ]
    elif node_name == "verify":
        data["allowed_outcomes"] = ["succeeded", "rejected", "failed"]
        next_actions = ["Run one bounded independent claim check; do not expand research"]
    else:
        next_actions = [f"Run check-report, then complete the run for {artifact}"]
    return result(
        "ok",
        f"Node {node_name} is ready",
        next_actions=next_actions,
        artifacts=[str(artifact)],
        data=data,
    )


def resolve_artifact(run_dir: Path, workspace: Path, value: str, expected_name: str) -> Path:
    raw = Path(value).expanduser()
    if raw.is_absolute():
        path = raw.resolve()
    else:
        run_relative = (run_dir / raw).resolve()
        workspace_relative = (workspace / raw).resolve()
        path = run_relative if run_relative.exists() or not workspace_relative.exists() else workspace_relative
    ensure_within(path, run_dir, "Artifact")
    if path.name != expected_name:
        raise GraphError(f"Expected artifact named {expected_name}, got {path.name}")
    if path.is_symlink() or not path.is_file():
        raise GraphError(f"Artifact must be a regular non-symlink file: {path}")
    return path


def allowed_outcomes(node_name: str) -> set[str]:
    if node_name == "work":
        return {"succeeded", "verify", "failed"}
    if node_name == "verify":
        return {"succeeded", "rejected", "failed"}
    return {"failed"}


def validate_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        return [f"{label} must be an array of non-empty strings"]
    return []


def normalize_url(value: str) -> str:
    return urldefrag(value.strip())[0].rstrip("/")


def validate_sources(value: Any) -> tuple[list[str], dict[str, Any]]:
    errors = validate_string_list(value, "sources")
    if errors:
        return errors, {"source_count": 0, "web_sources": set(), "local_sources": set()}
    if not value:
        return ["sources must contain at least one cited source"], {
            "source_count": 0,
            "web_sources": set(),
            "local_sources": set(),
        }
    web_sources: set[str] = set()
    local_sources: set[str] = set()
    for index, source_value in enumerate(value):
        source = source_value.strip()
        if re.fullmatch(r"https?://\S+", source):
            web_sources.add(normalize_url(source))
            continue
        path = Path(source).expanduser()
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            errors.append(f"Source {index} is neither an HTTP(S) URL nor a readable absolute file")
        else:
            local_sources.add(str(path.resolve()))
    if len(web_sources) + len(local_sources) != len(value):
        errors.append("sources must not contain duplicates")
    return errors, {
        "source_count": len(value),
        "web_sources": web_sources,
        "local_sources": local_sources,
    }


def validate_report_file(state: dict[str, Any]) -> tuple[list[str], str, str]:
    output = Path(state["output"])
    errors: list[str] = []
    try:
        ensure_within(output, Path(state["workspace"]), "Output")
    except GraphError as exc:
        errors.append(str(exc))
    if output.is_symlink() or not output.is_file():
        errors.append(f"Report is missing or not a regular file: {output}")
        return errors, "", ""
    text = output.read_text(encoding="utf-8")
    if len(text.strip()) < 120:
        errors.append("Report is too short to satisfy the research contract")
    return errors, text, sha256_file(output)


def validate_work(path: Path, state: dict[str, Any], outcome: str) -> tuple[list[str], dict[str, Any]]:
    work = load_json(path)
    errors: list[str] = []
    required = {
        "schema_version",
        "mode",
        "reason",
        "capabilities",
        "agents",
        "sources",
        "verification",
        "confidence",
        "gaps",
    }
    missing = required.difference(work)
    if missing:
        errors.append(f"research.json missing {sorted(missing)}")
    if work.get("schema_version") != 2:
        errors.append("research.json must use schema_version 2")
    for label in ("capabilities", "agents", "gaps"):
        errors.extend(validate_string_list(work.get(label), label))
    capabilities = work.get("capabilities") if isinstance(work.get("capabilities"), list) else []
    if state.get("graph_version") == graph_contract()["graph_version"]:
        errors.extend(validate_mcp_capabilities(capabilities))
    if not isinstance(work.get("reason"), str) or not work["reason"].strip():
        errors.append("reason must be a non-empty string")
    mode = work.get("mode")
    if mode not in {"fast", "deep"}:
        errors.append("mode must be fast or deep")
        mode = "fast"
    if state["requested_depth"] == "deep" and mode != "deep":
        errors.append("An explicitly deep run cannot record fast work")
    if work.get("confidence") not in {"high", "medium", "low"}:
        errors.append("confidence must be high, medium, or low")
    verification = work.get("verification")
    if verification not in {"self", "independent"}:
        errors.append("verification must be self or independent")
    source_errors, source_metrics = validate_sources(work.get("sources"))
    errors.extend(source_errors)
    graph = graph_contract()
    limits = graph["limits"][mode]
    source_count = int(source_metrics["source_count"])
    if source_count > int(limits["max_sources"]):
        if mode == "fast":
            errors.append("fast source limit exceeded; use deep mode when the 10-source coverage check still finds a material gap")
        else:
            errors.append("deep source hard limit exceeded; narrow the claims and report residual gaps instead of crossing 40 sources")
    agents = work.get("agents") if isinstance(work.get("agents"), list) else []
    unknown_agents = sorted(set(agents).difference(graph["optional_agents"]))
    if unknown_agents:
        errors.append(f"Unknown optional research agents: {unknown_agents}")
    scout_count = agents.count("research_scout")
    if scout_count > int(limits["max_parallel_scouts"]):
        errors.append(f"{mode} scout limit exceeded")
    for single_role in ("research_planner", "research_synthesizer"):
        if agents.count(single_role) > 1:
            errors.append(f"Use at most one {single_role}")
    if mode == "fast" and agents:
        errors.append("Fast mode must remain native and use no internal agents")
    if outcome == "verify":
        if mode != "deep":
            errors.append("Independent verification requires deep mode")
        if verification != "independent":
            errors.append("verify outcome requires verification independent")
    elif outcome == "succeeded" and verification == "independent":
        errors.append("Record outcome verify when verification is independent")
    report_errors, report_text, report_hash = validate_report_file(state)
    errors.extend(report_errors)
    return errors, {
        "work": work,
        "mode": mode,
        "source_count": source_count,
        "web_sources": source_metrics["web_sources"],
        "local_sources": source_metrics["local_sources"],
        "report_text": report_text,
        "report_sha256": report_hash,
    }


def validate_mcp_capabilities(capabilities: list[Any]) -> list[str]:
    policy = graph_contract()["mcp_policy"]
    prefix = policy["receipt_prefix"]
    fallback_prefix = policy["fallback_prefix"]
    not_applicable_prefix = policy["not_applicable_prefix"]
    receipts = [item for item in capabilities if isinstance(item, str) and item.startswith(prefix)]
    if not receipts:
        return [
            "capabilities must record mcp:<server>, mcp:fallback:<reason>, "
            "or mcp:not-applicable:<reason>"
        ]
    used: list[str] = []
    fallbacks: list[str] = []
    not_applicable: list[str] = []
    for receipt in receipts:
        if receipt.startswith(not_applicable_prefix):
            reason = receipt[len(not_applicable_prefix) :]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,}", reason):
                return ["MCP not-applicable requires a substantive machine-readable reason"]
            not_applicable.append(receipt)
            continue
        if receipt.startswith(fallback_prefix):
            reason = receipt[len(fallback_prefix) :]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,}", reason):
                return ["MCP fallback requires a substantive machine-readable reason"]
            fallbacks.append(receipt)
            continue
        server = receipt[len(prefix) :]
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", server)
            or server in {"fallback", "discovery", "none", "not-needed"}
        ):
            return [f"Invalid MCP server receipt: {receipt}"]
        used.append(receipt)
    if sum(bool(group) for group in (used, fallbacks, not_applicable)) != 1:
        return ["Record exactly one MCP receipt type: used, fallback, or not-applicable"]
    return []


def validate_verification(path: Path, outcome: str, report_hash: str) -> list[str]:
    verification = load_json(path)
    errors: list[str] = []
    verdict = str(verification.get("verdict", "")).lower()
    if outcome == "succeeded" and verdict != "pass":
        errors.append("Successful verification artifact must contain verdict pass")
    if outcome == "rejected" and verdict != "reject":
        errors.append("Rejected verification artifact must contain verdict reject")
    if verification.get("report_sha256") != report_hash:
        errors.append("Verification report_sha256 does not match the current report")
    checked_claims = verification.get("checked_claims")
    if type(checked_claims) is int:
        has_checked_claims = checked_claims >= 1
    else:
        has_checked_claims = isinstance(checked_claims, list) and len(checked_claims) >= 1
    if not has_checked_claims:
        errors.append("Verification artifact must record checked_claims as a positive count or non-empty array")
    if not isinstance(verification.get("residual_risks"), list):
        errors.append("Verification artifact must contain residual_risks array")
    repairs = verification.get("repair_list")
    if outcome == "rejected" and (not isinstance(repairs, list) or not repairs):
        errors.append("Rejected verification artifact must contain a non-empty repair_list")
    return errors


def validate_failure(path: Path) -> list[str]:
    artifact = load_json(path)
    if not isinstance(artifact.get("error"), str) or not artifact["error"].strip():
        return ["Failed node artifact must contain a non-empty error string"]
    return []


def reset_nodes(state: dict[str, Any], names: list[str]) -> None:
    for name in names:
        state["nodes"][name]["status"] = "pending"


def snapshot_artifact(
    run_dir: Path, node_name: str, node_state: dict[str, Any], artifact: Path, outcome: str
) -> dict[str, Any]:
    node_state["attempts"] += 1
    artifact_hash = sha256_file(artifact)
    receipt_dir = ensure_within(run_dir / "receipts", run_dir, "Receipt directory")
    if receipt_dir.exists() and (receipt_dir.is_symlink() or not receipt_dir.is_dir()):
        raise GraphError(f"Receipt path is not a regular directory: {receipt_dir}")
    receipt_dir.mkdir(exist_ok=True)
    snapshot = receipt_dir / (
        f"{node_name}-{node_state['attempts']:02d}-{artifact_hash[:12]}{artifact.suffix}"
    )
    if snapshot.exists():
        if sha256_file(snapshot) != artifact_hash:
            raise GraphError(f"Receipt snapshot collision: {snapshot}")
    else:
        shutil.copy2(artifact, snapshot)
    if sha256_file(snapshot) != artifact_hash:
        snapshot.unlink(missing_ok=True)
        raise GraphError(f"Receipt snapshot failed verification: {snapshot}")
    return {
        "attempt": node_state["attempts"],
        "artifact": str(snapshot),
        "source_artifact": str(artifact),
        "artifact_sha256": artifact_hash,
        "outcome": outcome,
        "recorded_at": utc_now(),
    }


def record_node(run_dir: Path, node_name: str, artifact_value: str, outcome: str) -> dict[str, Any]:
    with state_lock(run_dir):
        state = load_state(run_dir)
        graph = graph_contract()
        if state["status"] != "running":
            raise GraphError(f"Run is not active: {state['status']}")
        if node_name != state["current"]:
            raise GraphError(f"Cannot record {node_name}; current node is {state['current']}")
        if node_name == graph["terminal"]:
            raise GraphError("Use the complete command for the terminal node")
        if outcome not in allowed_outcomes(node_name):
            raise GraphError(f"Outcome {outcome} is not allowed for {node_name}")
        expected_name = graph["nodes"][node_name]["artifact"]
        artifact = resolve_artifact(run_dir, Path(state["workspace"]), artifact_value, expected_name)
        details: dict[str, Any] = {}
        if outcome == "failed":
            errors = validate_failure(artifact)
        elif node_name == "work":
            errors, details = validate_work(artifact, state, outcome)
        else:
            report_errors, _report_text, report_hash = validate_report_file(state)
            errors = report_errors + validate_verification(artifact, outcome, report_hash)
            details["report_sha256"] = report_hash
        if errors:
            raise GraphError("; ".join(errors))

        now = utc_now()
        node_state = state["nodes"][node_name]
        receipt = snapshot_artifact(run_dir, node_name, node_state, artifact, outcome)
        receipt["recorded_at"] = now
        if node_name == "work" and outcome != "failed":
            receipt["report_sha256"] = details["report_sha256"]
            receipt["mode"] = details["mode"]
        elif node_name == "verify" and outcome != "failed":
            receipt["report_sha256"] = details["report_sha256"]
        node_state["receipts"].append(receipt)
        state["events"].append(
            {"at": now, "event": "node_recorded", "node": node_name, "outcome": outcome}
        )

        if outcome == "failed":
            node_state["status"] = "failed"
            state["status"] = "blocked"
            state["updated_at"] = now
            write_json_atomic(run_dir / STATE_NAME, state)
            return result(
                "blocked",
                f"Node {node_name} failed; run stopped without bypassing the control gate",
                artifacts=[str(artifact), str(run_dir / STATE_NAME)],
                data={"run_dir": str(run_dir), "node": node_name},
            )

        node_state["status"] = "succeeded" if outcome == "succeeded" else outcome
        node = graph["nodes"][node_name]
        if node_name == "work":
            work = details["work"]
            state["mode"] = details["mode"]
            state["capabilities_used"] = work["capabilities"]
            state["agents_used"] = work["agents"]
            if outcome == "verify":
                state["verification_required"] = True
                next_node = node["on_verify"]
                state["events"].append(
                    {
                        "at": now,
                        "event": "verification_requested",
                        "reason": work["reason"],
                    }
                )
            else:
                state["verification_required"] = False
                next_node = node["on_success"]
        elif outcome == "rejected":
            max_repairs = int(graph["limits"]["max_verification_repairs"])
            if state["verification_repairs"] < max_repairs:
                state["verification_repairs"] += 1
                reset_nodes(state, ["work", "verify"])
                next_node = node["on_rejected"]
                state["mode"] = "deep"
                state["events"].append(
                    {
                        "at": now,
                        "event": "verification_repair",
                        "repair": state["verification_repairs"],
                    }
                )
            else:
                state["status"] = "blocked"
                state["updated_at"] = now
                state["events"].append({"at": now, "event": "verification_bound_reached"})
                write_json_atomic(run_dir / STATE_NAME, state)
                return result(
                    "blocked",
                    "Verifier still rejects the material claims after one bounded delta repair",
                    artifacts=[str(artifact), str(run_dir / STATE_NAME)],
                    data={"run_dir": str(run_dir), "node": node_name},
                )
        else:
            next_node = node["on_success"]

        state["current"] = next_node
        state["nodes"][next_node]["status"] = "ready"
        state["updated_at"] = now
        state["events"].append({"at": now, "event": "node_ready", "node": next_node})
        write_json_atomic(run_dir / STATE_NAME, state)
        return result(
            "ok",
            f"Recorded {node_name}; {next_node} is ready",
            next_actions=[f"Execute node: {next_node}"],
            artifacts=[str(artifact), str(run_dir / STATE_NAME)],
            data={"run_dir": str(run_dir), "current": next_node, "mode": state["mode"]},
        )


def retry_node(run_dir: Path, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise GraphError("Retry reason must describe the fallback or correction")
    with state_lock(run_dir):
        state = load_state(run_dir)
        graph = graph_contract()
        if state["status"] != "blocked":
            raise GraphError(f"Run is not blocked: {state['status']}")
        node_name = state["current"]
        node_state = state["nodes"][node_name]
        if node_state["status"] != "failed":
            raise GraphError("Only a failed node can be retried; verification repair bounds remain final")
        retries = state.setdefault("node_retries", {name: 0 for name in graph["nodes"]})
        max_retries = int(graph["limits"]["max_node_retries"])
        if int(retries.get(node_name, 0)) >= max_retries:
            raise GraphError(f"Retry bound reached for node {node_name}")
        retries[node_name] = int(retries.get(node_name, 0)) + 1
        now = utc_now()
        node_state["status"] = "ready"
        state["status"] = "running"
        state["updated_at"] = now
        state["events"].append(
            {
                "at": now,
                "event": "node_retry",
                "node": node_name,
                "retry": retries[node_name],
                "reason": reason.strip(),
            }
        )
        write_json_atomic(run_dir / STATE_NAME, state)
        return result(
            "ok",
            f"Node {node_name} reopened for bounded retry",
            next_actions=[f"Execute node: {node_name} using the recorded fallback"],
            artifacts=[str(run_dir / STATE_NAME)],
            data={"run_dir": str(run_dir), "current": node_name, "retry": retries[node_name]},
        )


def validate_receipt_hashes(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for node_name, node_state in state["nodes"].items():
        for receipt in node_state["receipts"]:
            artifact = Path(receipt["artifact"])
            if not artifact.is_file():
                errors.append(f"{node_name}: missing artifact {artifact}")
            elif sha256_file(artifact) != receipt["artifact_sha256"]:
                errors.append(f"{node_name}: artifact hash changed for {artifact}")
        if node_state["receipts"]:
            latest = node_state["receipts"][-1]
            source_value = latest.get("source_artifact")
            if source_value:
                source = Path(source_value)
                if not source.is_file():
                    errors.append(f"{node_name}: missing current artifact {source}")
                elif sha256_file(source) != latest["artifact_sha256"]:
                    errors.append(f"{node_name}: current artifact differs from latest receipt {source}")
    return errors


def markdown_http_urls(text: str) -> set[str]:
    """Extract CommonMark-style HTTP destinations, including balanced parentheses."""
    urls: set[str] = set()
    for match in re.finditer(r"\[[^\]]+\]\(", text):
        index = match.end()
        depth = 1
        destination: list[str] = []
        while index < len(text) and depth:
            character = text[index]
            if character == "\\" and index + 1 < len(text):
                destination.append(text[index + 1])
                index += 2
                continue
            if character == "(":
                depth += 1
                destination.append(character)
            elif character == ")":
                depth -= 1
                if depth:
                    destination.append(character)
            else:
                destination.append(character)
            index += 1
        if depth:
            continue
        value = "".join(destination).strip()
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1].strip()
        elif any(character.isspace() for character in value):
            value = value.split(maxsplit=1)[0]
        if re.fullmatch(r"https?://\S+", value):
            urls.add(normalize_url(value))
    return urls


def latest_receipt(state: dict[str, Any], node_name: str) -> dict[str, Any] | None:
    receipts = state["nodes"][node_name]["receipts"]
    return receipts[-1] if receipts else None


def report_checks(run_dir: Path) -> tuple[list[str], dict[str, Any]]:
    state = load_state(run_dir)
    errors = validate_receipt_hashes(state)
    if state["current"] != "complete" or state["status"] not in {"running", "completed"}:
        errors.append("Run has not reached the complete gate")
    report_errors, report_text, report_hash = validate_report_file(state)
    errors.extend(report_errors)

    work_receipt = latest_receipt(state, "work")
    work_metrics = {
        "mode": state["mode"],
        "source_count": 0,
        "web_sources": set(),
        "local_sources": set(),
    }
    if work_receipt is None:
        errors.append("Run has no durable work receipt")
    else:
        work_path = run_dir / WORK_ARTIFACT
        try:
            work_errors, work_metrics = validate_work(work_path, state, work_receipt["outcome"])
            errors.extend(work_errors)
        except GraphError as exc:
            errors.append(str(exc))
        if work_receipt.get("report_sha256") != report_hash:
            errors.append("Current report differs from the report recorded by work")

    web_sources = work_metrics.get("web_sources", set())
    local_sources = work_metrics.get("local_sources", set())
    markdown_urls = markdown_http_urls(report_text)
    declared_citations = markdown_urls.intersection(web_sources)
    if declared_citations != web_sources:
        errors.append("Every declared web source must appear as a report citation")
    local_citations = {source for source in local_sources if source in report_text}
    if local_citations != local_sources:
        errors.append("Every declared local source must be referenced in the report")

    if state["verification_required"]:
        verification_receipt = latest_receipt(state, "verify")
        if verification_receipt is None or verification_receipt["outcome"] != "succeeded":
            errors.append("Independent verification was requested but did not pass")
        else:
            try:
                errors.extend(
                    validate_verification(run_dir / VERIFICATION_ARTIFACT, "succeeded", report_hash)
                )
            except GraphError as exc:
                errors.append(str(exc))
            if verification_receipt.get("report_sha256") != report_hash:
                errors.append("Verifier checked a different report hash")

    return errors, {
        "report": state["output"],
        "mode": work_metrics.get("mode", state["mode"]),
        "sources": work_metrics.get("source_count", 0),
        "unique_web_sources": len(web_sources),
        "unique_local_sources": len(local_sources),
        "markdown_links": len(markdown_urls),
        "declared_citations": len(declared_citations),
        "verification_required": state["verification_required"],
        "verification_repairs": state["verification_repairs"],
    }


def check_report(run_dir: Path) -> dict[str, Any]:
    errors, metrics = report_checks(run_dir)
    if errors:
        return result(
            "failed",
            "Report failed the completion gate",
            next_actions=errors,
            artifacts=[metrics["report"], str(run_dir / STATE_NAME)],
            data=metrics,
        )
    state = load_state(run_dir)
    if state["status"] == "completed":
        return result(
            "ok",
            "Completed research report passed the lightweight integrity gate",
            artifacts=[metrics["report"], str(run_dir / STATE_NAME)],
            data=metrics,
        )
    return result(
        "ok",
        "Report passed the lightweight deterministic completion gate",
        next_actions=[f"Finalize with: complete --run {run_dir}"],
        artifacts=[metrics["report"], str(run_dir / STATE_NAME)],
        data=metrics,
    )


def complete_run(run_dir: Path) -> dict[str, Any]:
    with state_lock(run_dir):
        existing = load_state(run_dir)
        if existing["status"] == "completed":
            integrity_errors = validate_receipt_hashes(existing)
            if integrity_errors:
                raise GraphError("Completed run failed integrity check: " + "; ".join(integrity_errors))
            return result(
                "ok",
                "Research graph was already completed",
                artifacts=[existing["output"], str(run_dir / STATE_NAME)],
                data={"run_id": existing["run_id"], "mode": existing["mode"]},
            )
        errors, metrics = report_checks(run_dir)
        if errors:
            raise GraphError("Completion gate failed: " + "; ".join(errors))
        state = load_state(run_dir)
        graph = graph_contract()
        now = utc_now()
        report = Path(state["output"])
        terminal = graph["terminal"]
        terminal_state = state["nodes"][terminal]
        terminal_state["status"] = "succeeded"
        terminal_state["attempts"] += 1
        terminal_state["receipts"].append(
            {
                "attempt": terminal_state["attempts"],
                "artifact": str(report),
                "source_artifact": str(report),
                "artifact_sha256": sha256_file(report),
                "outcome": "succeeded",
                "recorded_at": now,
            }
        )
        state["status"] = "completed"
        state["updated_at"] = now
        state["events"].append({"at": now, "event": "run_completed", "node": terminal})
        write_json_atomic(run_dir / STATE_NAME, state)
        return result(
            "ok",
            "Research graph completed",
            artifacts=[str(report), str(run_dir / STATE_NAME)],
            data=metrics | {"run_id": state["run_id"]},
        )


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize or resume a native research run")
    init.add_argument("--question", required=True)
    init.add_argument("--workspace", required=True)
    init.add_argument("--output", required=True)
    init.add_argument("--depth", choices=("auto", "deep"), default="auto")

    for name in ("status", "ready", "check-report", "complete"):
        item = sub.add_parser(name)
        item.add_argument("--run", required=True)

    retry = sub.add_parser("retry", help="Reopen a failed node within the retry bound")
    retry.add_argument("--run", required=True)
    retry.add_argument("--reason", required=True)

    record = sub.add_parser("record", help="Record a durable work or verification artifact")
    record.add_argument("--run", required=True)
    record.add_argument("--node", required=True)
    record.add_argument("--artifact", required=True)
    record.add_argument("--outcome", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            payload = initialize(args.question, args.workspace, args.output, args.depth)
        else:
            run_dir = run_path(args.run)
            if args.command == "status":
                payload = state_summary(run_dir)
            elif args.command == "ready":
                payload = ready_node(run_dir)
            elif args.command == "record":
                payload = record_node(run_dir, args.node, args.artifact, args.outcome)
            elif args.command == "retry":
                payload = retry_node(run_dir, args.reason)
            elif args.command == "check-report":
                payload = check_report(run_dir)
            elif args.command == "complete":
                payload = complete_run(run_dir)
            else:
                raise GraphError(f"Unknown command: {args.command}")
    except GraphError as exc:
        payload = result("failed", str(exc), next_actions=["Fix the reported contract error and retry"])
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] != "failed" else 2


if __name__ == "__main__":
    sys.exit(main())
