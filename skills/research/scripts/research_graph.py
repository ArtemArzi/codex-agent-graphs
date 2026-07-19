#!/usr/bin/env python3
"""Deterministic state and integrity layer for the Research agent graph."""

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
    required = {"graph_id", "graph_version", "entry", "terminal", "limits", "nodes"}
    missing = required.difference(graph)
    if missing:
        raise GraphError(f"Graph contract is missing keys: {sorted(missing)}")
    nodes = graph["nodes"]
    if not isinstance(nodes, dict) or graph["entry"] not in nodes or graph["terminal"] not in nodes:
        raise GraphError("Graph entry or terminal node is invalid")
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


def fingerprint(question: str, workspace: Path, output: Path) -> str:
    canonical = json.dumps(
        {"question": question.strip(), "workspace": str(workspace), "output": str(output)},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def run_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    state_path = path / STATE_NAME
    if not path.is_dir() or not state_path.is_file():
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
    graph: dict[str, Any], question: str, workspace: Path, output: Path, run_id: str
) -> dict[str, Any]:
    nodes = {
        name: {"status": "pending", "attempts": 0, "receipts": []}
        for name in graph["nodes"]
    }
    nodes[graph["entry"]]["status"] = "ready"
    now = utc_now()
    return {
        "schema_version": 1,
        "graph_id": graph["graph_id"],
        "graph_version": graph["graph_version"],
        "graph_sha256": sha256_file(GRAPH_PATH),
        "run_id": run_id,
        "question": question.strip(),
        "workspace": str(workspace),
        "output": str(output),
        "status": "running",
        "current": graph["entry"],
        "collection_retries": 0,
        "synthesis_repairs": 0,
        "node_retries": {name: 0 for name in graph["nodes"]},
        "created_at": now,
        "updated_at": now,
        "nodes": nodes,
        "events": [{"at": now, "event": "run_initialized", "node": graph["entry"]}],
    }


def initialize(question: str, workspace_value: str, output_value: str) -> dict[str, Any]:
    if not question.strip():
        raise GraphError("Question must not be empty")
    workspace = Path(workspace_value).expanduser().resolve()
    if not workspace.is_dir():
        raise GraphError(f"Workspace does not exist: {workspace}")
    raw_output = Path(output_value).expanduser()
    output = raw_output.resolve() if raw_output.is_absolute() else (workspace / raw_output).resolve()
    ensure_within(output, workspace, "Output")
    graph = graph_contract()
    run_id = fingerprint(question, workspace, output)
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
            state = load_json(state_path)
            expected = (question.strip(), str(workspace), str(output))
            actual = (state.get("question"), state.get("workspace"), state.get("output"))
            if actual != expected:
                raise GraphError(f"Run fingerprint collision at {run_dir}")
            return result(
                "ok",
                "Existing research run resumed",
                next_actions=[f"Inspect ready node with: ready --run {run_dir}"],
                artifacts=[str(state_path)],
                data={"run_dir": str(run_dir), "current": state["current"]},
            )
        state = initial_state(graph, question, workspace, output, run_id)
        write_json_atomic(state_path, state)
    return result(
        "ok",
        "Research run initialized",
        next_actions=[f"Execute node: {graph['entry']}"],
        artifacts=[str(state_path)],
        data={"run_dir": str(run_dir), "current": graph["entry"]},
    )


def load_state(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / STATE_NAME)
    graph = graph_contract()
    if state.get("graph_id") != graph["graph_id"]:
        raise GraphError("Run belongs to another graph")
    if state.get("graph_version") != graph["graph_version"]:
        raise GraphError(
            f"Run graph version {state.get('graph_version')} does not match installed {graph['graph_version']}"
        )
    if state.get("graph_sha256") != sha256_file(GRAPH_PATH):
        raise GraphError("Installed graph contract changed since this run started")
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
            "collection_retries": state["collection_retries"],
            "synthesis_repairs": state["synthesis_repairs"],
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
    return result(
        "ok",
        f"Node {node_name} is ready",
        next_actions=[f"Run role {node['role']} and create {artifact}"],
        artifacts=[str(artifact)],
        data={
            "node": node_name,
            "role": node["role"],
            "expected_artifact": str(artifact),
            "attempt": node_state["attempts"] + 1,
        },
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
    if node_name == "gap_check":
        return {"succeeded", "needs-more", "failed"}
    if node_name == "verify":
        return {"succeeded", "rejected", "failed"}
    return {"succeeded", "failed"}


def validate_verification(path: Path, outcome: str) -> list[str]:
    verification = load_json(path)
    errors: list[str] = []
    verdict = str(verification.get("verdict", "")).lower()
    if outcome == "succeeded" and verdict != "pass":
        errors.append("Successful verification artifact must contain verdict pass")
    if outcome == "rejected" and verdict != "reject":
        errors.append("Rejected verification artifact must contain verdict reject")
    checked_claims = verification.get("checked_claims")
    if type(checked_claims) is int:
        has_checked_claims = checked_claims >= 1
    else:
        has_checked_claims = isinstance(checked_claims, list) and len(checked_claims) >= 1
    if not has_checked_claims:
        errors.append("Verification artifact must record checked_claims as a positive count or non-empty array")
    if not isinstance(verification.get("residual_risks"), list):
        errors.append("Verification artifact must contain residual_risks array")
    if outcome == "rejected" and not isinstance(verification.get("repair_list"), list):
        errors.append("Rejected verification artifact must contain repair_list array")
    return errors


def reset_nodes(state: dict[str, Any], names: list[str]) -> None:
    for name in names:
        state["nodes"][name]["status"] = "pending"


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
        if artifact.suffix == ".json":
            load_json(artifact)
        if node_name == "verify" and outcome in {"succeeded", "rejected"}:
            verification_errors = validate_verification(artifact, outcome)
            if verification_errors:
                raise GraphError("; ".join(verification_errors))
        now = utc_now()
        node_state = state["nodes"][node_name]
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
        receipt = {
            "attempt": node_state["attempts"],
            "artifact": str(snapshot),
            "source_artifact": str(artifact),
            "artifact_sha256": artifact_hash,
            "outcome": outcome,
            "recorded_at": now,
        }
        node_state["receipts"].append(receipt)
        state["events"].append({"at": now, "event": "node_recorded", "node": node_name, "outcome": outcome})

        if outcome == "failed":
            node_state["status"] = "failed"
            state["status"] = "blocked"
            state["updated_at"] = now
            write_json_atomic(run_dir / STATE_NAME, state)
            return result(
                "blocked",
                f"Node {node_name} failed; run stopped without bypassing the gate",
                artifacts=[str(artifact), str(run_dir / STATE_NAME)],
                data={"run_dir": str(run_dir), "node": node_name},
            )

        node_state["status"] = "succeeded" if outcome == "succeeded" else outcome
        node = graph["nodes"][node_name]
        if node_name == "gap_check" and outcome == "needs-more":
            max_retries = int(graph["limits"]["max_collection_cycles"]) - 1
            if state["collection_retries"] < max_retries:
                state["collection_retries"] += 1
                reset_nodes(state, ["collect", "evidence", "reconcile", "gap_check"])
                next_node = node["on_needs_more"]
                state["events"].append(
                    {"at": now, "event": "collection_retry", "retry": state["collection_retries"]}
                )
            else:
                next_node = node["on_success"]
                state["events"].append({"at": now, "event": "collection_bound_reached"})
        elif node_name == "verify" and outcome == "rejected":
            max_repairs = int(graph["limits"]["max_synthesis_repairs"])
            if state["synthesis_repairs"] < max_repairs:
                state["synthesis_repairs"] += 1
                reset_nodes(state, ["synthesize", "verify"])
                next_node = node["on_rejected"]
                state["events"].append(
                    {"at": now, "event": "synthesis_repair", "repair": state["synthesis_repairs"]}
                )
            else:
                state["status"] = "blocked"
                state["updated_at"] = now
                state["events"].append({"at": now, "event": "verification_bound_reached"})
                write_json_atomic(run_dir / STATE_NAME, state)
                return result(
                    "blocked",
                    "Verifier still rejects the report after the bounded repair attempts",
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
            data={"run_dir": str(run_dir), "current": next_node},
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


def normalize_url(value: str) -> str:
    return urldefrag(value.strip())[0].rstrip("/")


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


def validate_evidence(path: Path) -> tuple[list[str], int, set[str]]:
    errors: list[str] = []
    evidence = load_json(path)
    items = evidence.get("items")
    if not isinstance(items, list) or not items:
        return ["Evidence ledger must contain a non-empty items array"], 0, set()
    required = {
        "claim_id",
        "claim",
        "stance",
        "source_url",
        "source_title",
        "publisher",
        "published_at",
        "accessed_at",
        "source_class",
        "paraphrase",
        "confidence",
        "branch",
        "notes",
    }
    claim_ids: set[str] = set()
    urls: set[str] = set()
    allowed_stances = {"supports", "contradicts", "context"}
    allowed_source_classes = {"primary", "authoritative-secondary", "secondary", "community"}
    allowed_confidence = {"high", "medium", "low"}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Evidence item {index} is not an object")
            continue
        missing = required.difference(item)
        if missing:
            errors.append(f"Evidence item {index} missing {sorted(missing)}")
        claim_id = str(item.get("claim_id", ""))
        if not claim_id.strip() or not str(item.get("claim", "")).strip():
            errors.append(f"Evidence item {index} has an empty claim_id or claim")
        if claim_id in claim_ids:
            errors.append(f"Duplicate claim_id: {claim_id}")
        claim_ids.add(claim_id)
        url = str(item.get("source_url", ""))
        if not re.fullmatch(r"https?://\S+", url):
            errors.append(f"Evidence item {index} has invalid source_url")
        else:
            urls.add(normalize_url(url))
        if item.get("stance") not in allowed_stances:
            errors.append(f"Evidence item {index} has invalid stance")
        if item.get("source_class") not in allowed_source_classes:
            errors.append(f"Evidence item {index} has invalid source_class")
        if item.get("confidence") not in allowed_confidence:
            errors.append(f"Evidence item {index} has invalid confidence")
    return errors, len(items), urls


def report_checks(run_dir: Path) -> tuple[list[str], dict[str, Any]]:
    state = load_state(run_dir)
    errors = validate_receipt_hashes(state)
    if state["current"] != "complete" or state["status"] not in {"running", "completed"}:
        errors.append("Run has not reached the complete gate")

    output = Path(state["output"])
    workspace = Path(state["workspace"])
    try:
        ensure_within(output, workspace, "Output")
    except GraphError as exc:
        errors.append(str(exc))
    if output.is_symlink() or not output.is_file():
        errors.append(f"Report is missing or not a regular file: {output}")
        report_text = ""
    else:
        report_text = output.read_text(encoding="utf-8")
        if len(report_text.strip()) < 200:
            errors.append("Report is too short to satisfy the research contract")

    evidence_path = run_dir / "evidence.json"
    try:
        evidence_errors, evidence_items, evidence_urls = validate_evidence(evidence_path)
        errors.extend(evidence_errors)
    except GraphError as exc:
        errors.append(str(exc))
        evidence_items, evidence_urls = 0, set()

    verification_path = run_dir / "verification.json"
    try:
        errors.extend(validate_verification(verification_path, "succeeded"))
    except GraphError as exc:
        errors.append(str(exc))

    markdown_urls = markdown_http_urls(report_text)
    markdown_links = len(markdown_urls)
    if markdown_links < 1:
        errors.append("Report has no claim-adjacent Markdown citations")
    ledger_citations = markdown_urls.intersection(evidence_urls)
    required_ledger_citations = min(len(evidence_urls), 2)
    if evidence_items and len(ledger_citations) < required_ledger_citations:
        errors.append("Report citations do not match enough sources in the evidence ledger")
    return errors, {
        "report": str(output),
        "evidence_items": evidence_items,
        "unique_sources": len(evidence_urls),
        "markdown_links": markdown_links,
        "ledger_citations": len(ledger_citations),
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
    return result(
        "ok",
        "Report passed the mechanical completion gate",
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
            report = Path(existing["output"])
            return result(
                "ok",
                "Research graph was already completed",
                artifacts=[str(report), str(run_dir / STATE_NAME)],
                data={"run_id": existing["run_id"]},
            )
        errors, metrics = report_checks(run_dir)
        if errors:
            raise GraphError("Completion gate failed: " + "; ".join(errors))
        state = load_state(run_dir)
        graph = graph_contract()
        now = utc_now()
        report = Path(state["output"])
        terminal = graph["terminal"]
        state["nodes"][terminal]["status"] = "succeeded"
        state["nodes"][terminal]["attempts"] += 1
        state["nodes"][terminal]["receipts"].append(
            {
                "attempt": state["nodes"][terminal]["attempts"],
                "artifact": str(report),
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

    init = sub.add_parser("init", help="Initialize or resume a deterministic run")
    init.add_argument("--question", required=True)
    init.add_argument("--workspace", required=True)
    init.add_argument("--output", required=True)

    for name in ("status", "ready", "check-report", "complete"):
        item = sub.add_parser(name)
        item.add_argument("--run", required=True)

    retry = sub.add_parser("retry", help="Reopen a failed node within the retry bound")
    retry.add_argument("--run", required=True)
    retry.add_argument("--reason", required=True)

    record = sub.add_parser("record", help="Record a node artifact and transition")
    record.add_argument("--run", required=True)
    record.add_argument("--node", required=True)
    record.add_argument("--artifact", required=True)
    record.add_argument("--outcome", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            payload = initialize(args.question, args.workspace, args.output)
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
