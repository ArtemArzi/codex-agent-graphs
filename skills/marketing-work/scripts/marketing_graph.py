#!/usr/bin/env python3
"""Optional, local-only marketing-work evidence controller (stdlib only)."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


SKILL = Path(__file__).resolve().parents[1]
MANAGED = ".agent-graphs/marketing-work-runs"
SCHEMA = 1


class ControlError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ControlError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, relative):
    """Reject traversal and symlinks, including symlinked parent directories."""
    path = Path(relative)
    require(not path.is_absolute() and path.parts and str(relative) == path.as_posix() and
            all(p not in {".", ".."} for p in str(relative).split("/")),
            "Paths must use canonical root-relative spelling without traversal")
    target = root / path
    for part in [root, *reversed(root.parents)]:
        require(not part.is_symlink(), f"Symlink forbidden: {part}")
    current = root
    for part in path.parts:
        current /= part
        require(not current.is_symlink(), f"Symlink forbidden: {current}")
        if current.exists() and current != target:
            require(current.is_dir(), f"Non-directory parent: {current}")
    return target


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "Regular file required")
        return handle.read()


def load(path):
    value = json.loads(read(path))
    require(isinstance(value, dict), "JSON object required")
    return value


def exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def seal(value):
    return dict(value, integrity=digest(encoded({k: v for k, v in value.items() if k != "integrity"})))


def identities():
    graph = load(SKILL / "graph.json")
    require(graph.get("graph_id") == "marketing-work" and graph.get("graph_version") == "1.0.0",
            "Unsupported graph identity")
    return {"graph_id": graph["graph_id"], "graph_version": graph["graph_version"],
            "graph_sha256": digest(read(SKILL / "graph.json")),
            "controller_sha256": digest(read(Path(__file__))), "schema_version": SCHEMA}


def domain_path(root, relative):
    require(isinstance(relative, str) and bool(Path(relative).parts), "Domain path required")
    require(Path(relative).parts[0] != ".agent-graphs", "Domain files must stay outside graph state")
    return safe_path(root, relative)


def distinct_files(root, paths, optional=()):
    """Separate roles by file identity, not only spelling or content hashes."""
    require(len(paths) == len(set(paths)), "Input/output/evidence paths must be separate")
    seen = set()
    for relative in paths:
        path = domain_path(root, relative)
        try:
            info = path.stat(follow_symlinks=False)
        except FileNotFoundError:
            require(relative in optional, "Bound file missing")
            continue
        require(stat.S_ISREG(info.st_mode), "Regular file required")
        identity = (info.st_dev, info.st_ino)
        require(identity not in seen, "Input/output/evidence files must be physically separate")
        seen.add(identity)


def check_separation(root, state, work=(), review=()):
    work_paths, review_paths = set(work), set(review)
    directory = run_path(root, state["run_id"])
    for name in state["receipts"]:
        item = load(safe_path(directory, name))
        if item.get("kind") == "work":
            work_paths.update(item["evidence"])
        elif item.get("kind") == "verification":
            review_paths.update(item["evidence"])
    distinct_files(root, [*state["inputs"], state["output"], *sorted(work_paths), *sorted(review_paths)],
                   optional=[state["output"]] if state["phase"] == "work" else [])


def snapshot(root, paths):
    require(paths and len(paths) == len(set(paths)), "Provide distinct evidence/source paths")
    distinct_files(root, paths)
    return {p: digest(read(domain_path(root, p))) for p in sorted(paths)}


def check_files(root, files):
    require(snapshot(root, list(files)) == files, "Source or evidence changed")


def run_path(root, run_id):
    require(isinstance(run_id, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id),
            "Invalid run id")
    return safe_path(root, f"{MANAGED}/{run_id}")


@contextmanager
def locked(directory):
    lock = directory / ".lock"
    exclusive(lock, encoded({"pid": os.getpid(), "created_at": stamp()}))
    try:
        yield
    finally:
        lock.unlink()


def save(directory, state, previous=None):
    path = directory / "state.json"
    if previous is not None:
        require(digest(read(path)) == previous, "State changed during operation")
    state["updated_at"] = stamp()
    state = seal(state)
    temporary = directory / ".state.tmp"
    exclusive(temporary, encoded(state))
    os.replace(temporary, path)
    return state


def binding(state):
    return {k: state[k] for k in ["schema_version", "graph_id", "graph_version", "graph_sha256",
            "controller_sha256", "root", "run_id", "mode", "tier", "company", "objective", "inputs", "output"]}


def receipt(directory, state, name, data):
    value = dict(data, binding=binding(state), created_at=stamp())
    exclusive(directory / name, encoded(value))
    state["receipts"][name] = digest(encoded(value))
    return value


def checked_state(root, run_id, writing=False):
    directory = run_path(root, run_id)
    if not writing:
        require(not (directory / ".lock").exists(), "Writer active or stale lock; reconcile before resuming")
    raw = read(directory / "state.json")
    state = json.loads(raw)
    require(isinstance(state, dict) and state.get("integrity") == seal(state)["integrity"], "State integrity failed")
    for key, value in dict(identities(), root=str(root), run_id=run_id, mode="marketing").items():
        require(state.get(key) == value, f"Unknown or changed state identity: {key}")
    require(state.get("tier") in {"tracked", "verified"} and state.get("status") in {"running", "completed"},
            "Unknown state contract")
    require(state.get("phase") in {"work", "verify", "complete", "exhausted", "done"}, "Unknown phase")
    require((state["status"] == "completed") == (state["phase"] == "done"), "Inconsistent completion")
    require(type(state.get("repairs")) is int and 0 <= state["repairs"] <= 1, "Invalid repair budget")
    domain_path(root, state["output"])
    check_files(root, state["inputs"])
    receipts = state["receipts"]
    require(isinstance(receipts, dict) and set(receipts).issubset({"work-0.json", "work-1.json",
            "verification-0.json", "verification-1.json", "FINAL.json"}), "Unknown receipts")
    require({p.name for p in directory.iterdir()} == {"state.json", *receipts, *([".lock"] if writing else [])},
            "Unexpected run files; reconcile interrupted/foreign writes")
    for name, expected in receipts.items():
        require(digest(read(safe_path(directory, name))) == expected, "Receipt integrity failed")
        item = load(directory / name)
        require(item.get("binding") == binding(state), "Receipt context changed")
        if "evidence" in item:
            check_files(root, item["evidence"])
    check_separation(root, state)
    if state["phase"] in {"verify", "complete", "done"}:
        work = load(directory / state["work"])
        require(snapshot(root, [state["output"]])[state["output"]] == work["output_sha256"], "Candidate changed")
        if state["phase"] in {"complete", "done"} and state["verification_required"]:
            review = load(directory / state["verification"])
            require(review["verdict"] == "accept" and review["work_sha256"] == receipts[state["work"]]
                    and review["output_sha256"] == work["output_sha256"], "Exact-candidate acceptance missing")
    if not writing:
        require(not (directory / ".lock").exists() and read(directory / "state.json") == raw,
                "Concurrent transition; read again")
    return state, digest(raw)


def init(args, root):
    require(args.company.strip() and args.objective.strip(), "Company and objective required")
    inputs = snapshot(root, args.input)
    domain_path(root, args.output)
    distinct_files(root, [*inputs, args.output], optional=[args.output])
    directory = run_path(root, args.run)
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()  # Exclusive run allocation, including parallel init.
    with locked(directory):
        state = dict(identities(), root=str(root), run_id=args.run, mode="marketing", tier=args.tier,
                     company=args.company, objective=args.objective, inputs=inputs, output=args.output,
                     status="running", phase="work", repairs=0, work=None, verification=None,
                     verification_required=args.tier == "verified", receipts={},
                     created_at=stamp(), completed_at=None)
        return save(directory, state)


def transition(args, root):
    directory = run_path(root, args.run)
    with locked(directory):
        state, previous = checked_state(root, args.run, writing=True)
        require(state["status"] == "running", "Run already completed")
        if args.command == "work":
            require(state["phase"] == "work", "Work transition unavailable")
            evidence = snapshot(root, args.evidence)
            check_separation(root, state, work=evidence)
            require(args.author.strip() and args.capability and any(c.startswith("mcp:") for c in args.capability),
                    "Author and actual capability/MCP or not-applicable receipt required")
            output_sha = snapshot(root, [state["output"]])[state["output"]]
            if state["repairs"]:
                old = load(directory / state["work"])
                require(args.first_false_assumption and args.first_false_assumption.strip(), "Repair needs first false assumption")
                require(output_sha != old["output_sha256"] and set(evidence.values()).difference(old["evidence"].values()),
                        "Repair requires changed candidate and new evidence")
            name = f"work-{state['repairs']}.json"
            receipt(directory, state, name, {"kind": "work", "author": args.author, "evidence": evidence,
                    "capabilities": args.capability, "output_sha256": output_sha,
                    "first_false_assumption": args.first_false_assumption})
            state["work"] = name
            state["verification_required"] |= args.verify
            state["phase"] = "verify" if state["verification_required"] else "complete"
        elif args.command == "verify":
            require(state["phase"] == "verify", "Verification transition unavailable")
            work = load(directory / state["work"])
            require(args.work_sha == state["receipts"][state["work"]] and args.output_sha == work["output_sha256"],
                    "Verification must name the exact work receipt and candidate hashes")
            require(args.reviewer.strip() and args.reviewer != work["author"] and args.role != "root" and args.role.strip(),
                    "Independent reviewer identity and host-policy role required")
            require(args.reason.strip(), "Review conclusion required")
            evidence = snapshot(root, args.evidence)
            check_separation(root, state, review=evidence)
            name = f"verification-{state['repairs']}.json"
            receipt(directory, state, name, {"kind": "verification", "verdict": args.verdict,
                    "reviewer": args.reviewer, "role": args.role, "reason": args.reason, "evidence": evidence,
                    "work_sha256": args.work_sha, "output_sha256": args.output_sha})
            state["verification"] = name
            if args.verdict == "accept":
                state["phase"] = "complete"
            elif state["repairs"] == 0:
                state["repairs"] = 1
                state["phase"] = "work"
            else:
                state["phase"] = "exhausted"
        elif args.command == "complete":
            require(state["phase"] == "complete", "Completion unavailable: work/review missing or repairs exhausted")
            work = load(directory / state["work"])
            receipt(directory, state, "FINAL.json", {"kind": "completion", "output": state["output"],
                    "output_sha256": work["output_sha256"], "work_sha256": state["receipts"][state["work"]],
                    "verification_sha256": state["receipts"].get(state["verification"])})
            # Recheck after artifact creation, before committing completion.
            check_files(root, state["inputs"])
            for key, value in identities().items():
                require(state[key] == value, "Graph/controller changed during completion")
            require(snapshot(root, [state["output"]])[state["output"]] == work["output_sha256"],
                    "Candidate changed during completion")
            state.update(status="completed", phase="done", completed_at=stamp())
        save(directory, state, previous)
        return checked_state(root, args.run, writing=True)[0]


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ["init", "ready", "resume", "work", "verify", "complete"]:
        sub = commands.add_parser(name)
        sub.add_argument("--root", required=True)
        sub.add_argument("--run", required=True)
        if name == "init":
            sub.add_argument("--tier", required=True, choices=["tracked", "verified"])
            sub.add_argument("--company", required=True)
            sub.add_argument("--objective", required=True)
            sub.add_argument("--input", action="append", required=True)
            sub.add_argument("--output", required=True)
        if name in {"work", "verify"}:
            sub.add_argument("--evidence", action="append", required=True)
        if name == "work":
            sub.add_argument("--author", required=True)
            sub.add_argument("--capability", action="append", required=True)
            sub.add_argument("--first-false-assumption")
            sub.add_argument("--verify", action="store_true")
        if name == "verify":
            for field in ["reviewer", "role", "reason", "work-sha", "output-sha"]:
                sub.add_argument(f"--{field}", required=True)
            sub.add_argument("--verdict", required=True, choices=["accept", "reject"])
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = Path(os.path.abspath(args.root))
        require(root.is_dir(), "Root directory missing")
        safe_path(root, "root-check")
        if args.command == "init":
            state = init(args, root)
        elif args.command in {"ready", "resume"}:
            state, _ = checked_state(root, args.run)
        else:
            state = transition(args, root)
        print(json.dumps({"status": state["status"], "phase": state["phase"], "run_id": state["run_id"],
              "next": None if state["phase"] in {"done", "exhausted"} else state["phase"],
              "state": f"{MANAGED}/{state['run_id']}/state.json",
              "work_sha256": state["receipts"].get(state["work"]),
              "output_sha256": load(run_path(root, state["run_id"]) / state["work"])["output_sha256"] if state["work"] else None}))
        return 0
    except (ControlError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Control refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
