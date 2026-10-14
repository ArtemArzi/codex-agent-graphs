#!/usr/bin/env python3
"""Read-only deployment contract validation and planning; never execute checks."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

MAX_BYTES = 1024 * 1024
MAX_PLAN_BYTES = 4 * 1024 * 1024
OUTPUT_ENCODER = json.JSONEncoder(sort_keys=True, allow_nan=False, ensure_ascii=True)
PHASES = ("source", "artifact", "environment", "postdeploy", "scheduled")
ID = re.compile(r"[a-z0-9._-]{1,64}\Z")
STATUSES = {"passed", "failed", "skipped", "blocked", "unknown"}


class ValidationError(ValueError):
    """An input violates the closed mapping contract."""


def fail(message: str) -> None:
    raise ValidationError(message)


def obj(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        fail(f"{label} must be an object")
    return value


def fields(value: dict, required: set[str], optional: set[str], label: str) -> None:
    if set(value) - required - optional:
        fail(f"{label} has unknown fields")
    if required - set(value):
        fail(f"{label} is missing required fields")


def string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a nonempty string")
    if any(unicodedata.category(c) in {"Cc", "Cs"} for c in value):
        fail(f"{label} contains control characters")
    return value


def identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        fail(f"{label} must be a valid ID")
    return value


def positive_int(value: Any, label: str) -> None:
    if type(value) is not int or value <= 0:
        fail(f"{label} must be a positive integer")


def version(value: Any, label: str) -> None:
    if type(value) is not int or value != 1:
        fail(f"{label} must be integer 1")


def identifiers(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        fail(f"{label} must be {'a nonempty' if nonempty else 'an'} array")
    for item in value:
        identifier(item, label)
    if len(value) != len(set(value)):
        fail(f"{label} contains duplicate IDs")
    return value


def relative_path(value: Any, label: str) -> PurePosixPath:
    string(value, label)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        fail(f"{label} must be a safe repo-relative path")
    # Drive-qualified Windows paths are not portable repo-relative paths.
    if re.match(r"^[a-zA-Z]:", value):
        fail(f"{label} cannot contain a drive prefix")
    return path


def no_symlinks(path: Path, label: str) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            fail(f"{label} targets a symlink")


def project_root_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    root = Path(value).absolute()
    no_symlinks(root, "project root")
    if not root.is_dir():
        fail("project root must be an existing directory")
    return root.resolve()


def filesystem_path(root: Path, relative: PurePosixPath, label: str, *, directory: bool) -> None:
    target = root.joinpath(*relative.parts)
    no_symlinks(target, label)
    if not target.resolve().is_relative_to(root):
        fail(f"{label} escapes project root")
    if not (target.is_dir() if directory else target.is_file()):
        fail(f"{label} must be an existing {'directory' if directory else 'regular file'}")


def load_json(path: str | Path) -> dict:
    """Read bounded strict JSON, rejecting duplicate keys and nonfinite numbers."""
    def pairs(items: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                fail("JSON contains duplicate object keys")
            result[key] = value
        return result

    def constant(_: str) -> None:
        fail("JSON contains a nonfinite number")

    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            fail("JSON exceeds 1 MiB")
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        # Bound nesting separately from byte size for predictable validation.
        pending = [(result, 0)]
        while pending:
            value, depth = pending.pop()
            if depth > 64:
                fail("JSON nesting exceeds 64 levels")
            if isinstance(value, dict):
                pending.extend((item, depth + 1) for item in value.values())
            elif isinstance(value, list):
                pending.extend((item, depth + 1) for item in value)
            elif isinstance(value, float) and not math.isfinite(value):
                fail("JSON contains a nonfinite number")
        return obj(result, "JSON document")
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError("cannot read valid bounded JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def order_checks(checks: dict, selected: set[str]) -> list[str]:
    indegree = {key: 0 for key in selected}
    children = {key: [] for key in selected}
    for key in selected:
        for dependency in checks[key].get("depends_on", []):
            indegree[key] += 1
            children[dependency].append(key)
    ready = [(PHASES.index(checks[key]["phase"]), key) for key in selected if not indegree[key]]
    heapq.heapify(ready)
    result = []
    while ready:
        _, key = heapq.heappop(ready)
        result.append(key)
        for child in children[key]:
            indegree[child] -= 1
            if not indegree[child]:
                heapq.heappush(ready, (PHASES.index(checks[child]["phase"]), child))
    if len(result) != len(selected):
        fail("checks contain a dependency cycle")
    return result


def validate_contract(contract: Any, project_root: str | Path | None = None) -> dict:
    contract = obj(contract, "contract")
    fields(contract, {"schema_version", "project_id", "owners", "native", "commands", "checks",
                      "profiles", "default_profile"}, set(), "contract")
    version(contract["schema_version"], "schema_version")
    identifier(contract["project_id"], "project_id")
    root = project_root_path(project_root)
    owners = obj(contract["owners"], "owners")
    fields(owners, {"deployment", "quality", "engineering"}, set(), "owners")
    for key, value in owners.items():
        path = relative_path(value, f"owners.{key}")
        if root is not None:
            filesystem_path(root, path, f"owners.{key}", directory=False)
    native = obj(contract["native"], "native")
    fields(native, {"status", "release", "rollback"}, set(), "native")
    for key, value in native.items():
        string(value, f"native.{key}")
    commands = obj(contract["commands"], "commands")
    for key, command in commands.items():
        identifier(key, "command ID")
        command = obj(command, f"command {key}")
        fields(command, {"argv", "cwd"}, {"timeout_seconds"}, f"command {key}")
        if not isinstance(command["argv"], list) or not command["argv"]:
            fail(f"command {key} argv must be a nonempty array")
        for arg in command["argv"]:
            string(arg, f"command {key} argv")
        path = relative_path(command["cwd"], f"command {key} cwd")
        if root is not None:
            filesystem_path(root, path, f"command {key} cwd", directory=True)
        if "timeout_seconds" in command:
            positive_int(command["timeout_seconds"], "timeout_seconds")
    checks = obj(contract["checks"], "checks")
    for key, check in checks.items():
        identifier(key, "check ID")
        check = obj(check, f"check {key}")
        fields(check, {"kind", "phase", "environment", "method", "subject"},
               {"command", "criterion", "acceptance_owner", "depends_on", "binding_keys",
                "reuse_verifier", "max_age_seconds", "fresh"}, f"check {key}")
        string(check["kind"], "kind")
        if check["phase"] not in PHASES:
            fail(f"check {key} has invalid phase")
        identifier(check["environment"], "environment")
        if check["subject"] not in ("source", "artifact"):
            fail(f"check {key} has invalid subject")
        if check["method"] == "command":
            if "command" not in check or "criterion" in check or "acceptance_owner" in check:
                fail(f"check {key} has invalid command method fields")
            identifier(check["command"], "command reference")
            if check["command"] not in commands:
                fail(f"check {key} references unknown command")
        elif check["method"] == "manual":
            if "command" in check or "criterion" not in check or "acceptance_owner" not in check:
                fail(f"check {key} has invalid manual method fields")
            string(check["criterion"], "criterion")
            string(check["acceptance_owner"], "acceptance_owner")
        else:
            fail(f"check {key} has invalid method")
        for name in ("depends_on", "binding_keys"):
            if name in check:
                identifiers(check[name], name)
        if "reuse_verifier" in check:
            identifier(check["reuse_verifier"], "reuse_verifier")
            if check["reuse_verifier"] not in commands:
                fail(f"check {key} references unknown reuse verifier")
        if "max_age_seconds" in check:
            positive_int(check["max_age_seconds"], "max_age_seconds")
        if "fresh" in check and type(check["fresh"]) is not bool:
            fail("fresh must be boolean")
    for key, check in checks.items():
        for dependency in check.get("depends_on", []):
            if dependency not in checks:
                fail(f"check {key} references unknown prerequisite")
            if PHASES.index(checks[dependency]["phase"]) > PHASES.index(check["phase"]):
                fail(f"check {key} depends on a later phase")
    order_checks(checks, set(checks))
    profiles = obj(contract["profiles"], "profiles")
    for key, profile in profiles.items():
        identifier(key, "profile ID")
        identifiers(profile, f"profile {key}", nonempty=True)
        if set(profile) - set(checks):
            fail(f"profile {key} references unknown checks")
    identifier(contract["default_profile"], "default_profile")
    if contract["default_profile"] not in profiles:
        fail("default_profile references unknown profile")
    return {"status": "contract_valid", "schema_version": 1, "project_id": contract["project_id"],
            "filesystem_scope": "project_root" if root is not None else "shape_only"}


def validate_context(context: Any) -> dict:
    context = obj(context, "context")
    fields(context, set(), {"source", "artifact", "environments", "inputs"}, "context")
    for key in ("source", "artifact"):
        if key in context:
            string(context[key], f"context.{key}")
    for key in ("environments", "inputs"):
        if key in context:
            for name, value in obj(context[key], f"context.{key}").items():
                identifier(name, f"context.{key} ID")
                string(value, f"context.{key} identity")
    return context


def validate_subject(subject: Any) -> None:
    subject = obj(subject, "evidence subject")
    fields(subject, {"source", "environment", "contract_digest", "check_digest", "inputs"},
           {"artifact"}, "evidence subject")
    for key in ("source", "environment", "artifact"):
        if key in subject:
            string(subject[key], f"evidence subject {key}")
    for key in ("contract_digest", "check_digest"):
        if not isinstance(subject[key], str) or not re.fullmatch(r"[a-f0-9]{64}", subject[key]):
            fail(f"evidence subject {key} must be SHA256")
    for key, value in obj(subject["inputs"], "evidence subject inputs").items():
        identifier(key, "evidence input ID")
        string(value, "evidence input reference")


def timestamp(value: Any) -> datetime:
    string(value, "completed_at")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValidationError("completed_at must be ISO timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        fail("completed_at must include timezone")
    return result


def validate_evidence(evidence: Any, checks: dict) -> dict:
    evidence = obj(evidence, "evidence")
    fields(evidence, {"schema_version", "checks"}, set(), "evidence")
    version(evidence["schema_version"], "evidence schema_version")
    records = obj(evidence["checks"], "evidence checks")
    for key, record in records.items():
        identifier(key, "evidence check ID")
        if key not in checks:
            fail("evidence references unknown check")
        record = obj(record, f"evidence {key}")
        fields(record, {"status"}, {"subject", "completed_at", "receipt_ref"}, f"evidence {key}")
        if not isinstance(record["status"], str) or record["status"] not in STATUSES:
            fail("evidence status is invalid")
        if "subject" in record:
            validate_subject(record["subject"])
        if "completed_at" in record:
            timestamp(record["completed_at"])
        if "receipt_ref" in record:
            string(record["receipt_ref"], "receipt_ref")
    return records


def command_output(contract: dict, key: str) -> dict:
    return {"id": key, **contract["commands"][key]}


def output_size(value: Any, budget: int) -> int:
    """Count ASCII JSON chunks without allocating the expanded output string."""
    total = 0
    for chunk in OUTPUT_ENCODER.iterencode(value):
        total += len(chunk)
        if total > budget:
            fail("expanded plan exceeds 4 MiB")
    return total


def plan(contract: dict, *, project_root: str | Path | None = None, profile: str | None = None,
         context: dict | None = None, evidence: dict | None = None,
         now: datetime | None = None) -> dict:
    validate_contract(contract, project_root)
    context = validate_context({} if context is None else context)
    records = validate_evidence({"schema_version": 1, "checks": {}} if evidence is None else evidence,
                                contract["checks"])
    profile = contract["default_profile"] if profile is None else identifier(profile, "profile")
    if profile not in contract["profiles"]:
        fail("unknown selected profile")
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        fail("planning time must include timezone")
    selected: set[str] = set()
    pending = list(contract["profiles"][profile])
    while pending:
        key = pending.pop()
        if key not in selected:
            selected.add(key)
            pending.extend(contract["checks"][key].get("depends_on", []))
    contract_digest = digest(contract)
    output = []
    result = {"status": "planned", "schema_version": 1, "project_id": contract["project_id"],
              "profile": profile, "contract_digest": contract_digest, "checks": output,
              "release_authorized": False, "release_verified": False}
    # Account for the complete envelope and each expanded check before retaining
    # it. A small input can otherwise repeat a shared command into gigabytes.
    size = output_size(result, MAX_PLAN_BYTES)
    for key in order_checks(contract["checks"], selected):
        check = contract["checks"][key]
        recipe = {"check": check}
        if check["method"] == "command":
            recipe["command"] = contract["commands"][check["command"]]
        expected = {"source": context.get("source"),
                    "environment": context.get("environments", {}).get(check["environment"]),
                    "contract_digest": contract_digest, "check_digest": digest(recipe),
                    "inputs": {name: context.get("inputs", {}).get(name)
                               for name in check.get("binding_keys", [])}}
        missing = []
        if expected["source"] is None:
            missing.append("source")
        if expected["environment"] is None:
            missing.append(f"environments.{check['environment']}")
        if check["subject"] == "artifact":
            expected["artifact"] = context.get("artifact")
            if expected["artifact"] is None:
                missing.append("artifact")
        missing.extend(f"inputs.{name}" for name, value in expected["inputs"].items() if value is None)
        item = {"id": key, **{name: check[name] for name in
                              ("kind", "phase", "environment", "method", "subject")},
                "depends_on": list(check.get("depends_on", [])), "expected_subject": expected,
                "action": "run_required" if check["method"] == "command" else "manual_required"}
        if check["method"] == "command":
            item["command"] = command_output(contract, check["command"])
        else:
            item.update({name: check[name] for name in ("criterion", "acceptance_owner")})
        record = records.get(key, {})
        if missing:
            item.update(action="await_bindings", missing_bindings=missing)
        elif (not check.get("fresh", False) and check["phase"] != "postdeploy"
              and "reuse_verifier" in check and record.get("status") == "passed"
              and record.get("subject") == expected and record.get("receipt_ref")
              and record.get("completed_at")):
            age = (now - timestamp(record["completed_at"])).total_seconds()
            if age >= 0 and ("max_age_seconds" not in check or age <= check["max_age_seconds"]):
                item.update(action="verify_reuse", receipt_ref=record["receipt_ref"],
                            verifier_command=command_output(contract, check["reuse_verifier"]))
        size += 2 if output else 0  # The encoder's comma-space list separator.
        size += output_size(item, MAX_PLAN_BYTES - size)
        output.append(item)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("validate", "plan"):
        command = subparsers.add_parser(operation)
        command.add_argument("--contract", required=True)
        command.add_argument("--project-root")
        if operation == "plan":
            command.add_argument("--profile")
            command.add_argument("--context")
            command.add_argument("--evidence")
    args = parser.parse_args(argv)
    try:
        contract = load_json(args.contract)
        if args.operation == "validate":
            result = validate_contract(contract, args.project_root)
        else:
            result = plan(contract, project_root=args.project_root, profile=args.profile,
                          context=load_json(args.context) if args.context else None,
                          evidence=load_json(args.evidence) if args.evidence else None)
        print(OUTPUT_ENCODER.encode(result))
        return 0
    except (ValidationError, OSError, TypeError, OverflowError, RecursionError) as exc:
        # Do not echo untrusted source values or file contents into diagnostics.
        message = str(exc) if isinstance(exc, ValidationError) else "invalid input"
        print(json.dumps({"status": "invalid", "error": message}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
