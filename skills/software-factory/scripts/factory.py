#!/usr/bin/env python3
"""Local Git preparation and integration checks. Does not launch/approve agents."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid


class PilotError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def run(argv, cwd, *, timeout=120):
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                                timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PilotError(f"Command failed to run: {argv!r}: {exc}") from exc
    if result.returncode:
        raise PilotError(f"Command failed ({result.returncode}): {argv!r}\n"
                         f"{result.stdout}{result.stderr}")
    return result.stdout.strip()


def git(repo, *args):
    return run(["git", *args], repo)


def save(path, value):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


@contextmanager
def locked(workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    lock = workspace / ".lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise PilotError("Workspace is locked. Inspect the active operation; no automatic unlock.") from exc
    try:
        yield
    finally:
        lock.rmdir()


def read(workspace):
    try:
        value = json.loads((workspace / "workspace.json").read_text())
    except (OSError, ValueError) as exc:
        raise PilotError(f"Cannot read workspace manifest: {exc}") from exc
    if value.get("version") != 1:
        raise PilotError("Unsupported workspace manifest version")
    return value


def clean(repo):
    return not git(repo, "status", "--porcelain", "--untracked-files=all")


def head(repo):
    return git(repo, "rev-parse", "HEAD")


def base_head(manifest):
    return git(manifest["repo"], "rev-parse", "--verify", "--end-of-options",
               manifest["base_ref"] + "^{commit}")


def owned_path(raw):
    path = PurePosixPath(raw)
    if (not raw or path.is_absolute() or "\\" in raw or
            any(part in ("", ".", "..") for part in raw.split("/")) or
            path.parts[0] in (".git", ".codex", ".project-start")):
        raise PilotError(f"Ownership must name an exact repository file: {raw!r}")
    return path.as_posix()


def paths_overlap(left, right):
    a, b = PurePosixPath(left), PurePosixPath(right)
    return a == b or a in b.parents or b in a.parents


def prepare(args):
    workspace = Path(args.workspace).resolve()
    repo = Path(args.repo).resolve()
    if workspace == repo or workspace.is_relative_to(repo) or repo.is_relative_to(workspace):
        raise PilotError("Workspace and repository must be separate, non-nested directories")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", args.job):
        raise PilotError("Job ID must be 1-40 lowercase letters, digits or hyphens, starting with a letter")
    git(repo, "check-ref-format", "--branch", args.base)
    base_ref = "refs/heads/" + args.base
    base = git(repo, "rev-parse", "--verify", "--end-of-options", base_ref + "^{commit}")
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise PilotError("--repo must be a Git worktree root")
    if (not clean(repo) or head(repo) != base or
            git(repo, "symbolic-ref", "--short", "HEAD") != args.base):
        raise PilotError("Source checkout must be clean and at the selected base commit")
    owns = sorted(set(owned_path(p) for p in args.owns))
    if not owns:
        raise PilotError("At least one owned file is required")
    if any(paths_overlap(a, b) for index, a in enumerate(owns) for b in owns[index + 1:]):
        raise PilotError("Owned files have overlapping file/directory paths")
    context = ""
    context_digest = None
    if args.context:
        try:
            context_bytes = Path(args.context).read_bytes()
            context = context_bytes.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise PilotError("Context must be a readable nonempty UTF-8 file") from exc
        if not context.strip():
            raise PilotError("Context must be a readable nonempty UTF-8 file")
        context_digest = hashlib.sha256(context_bytes).hexdigest()
    with locked(workspace):
        if (workspace / "workspace.json").exists():
            manifest = read(workspace)
            if (manifest["repo"], manifest["base_ref"], manifest["base_sha"]) != (str(repo), base_ref, base):
                raise PilotError("Workspace is bound to a different repository/base; use a new workspace")
        else:
            manifest = dict(version=1, id=uuid.uuid4().hex[:12], repo=str(repo),
                            base_ref=base_ref, base_sha=base, jobs={})
        if args.job in manifest["jobs"]:
            raise PilotError("Job ID already exists")
        if len(manifest["jobs"]) >= 2:
            raise PilotError("Factory supports at most two jobs per workspace")
        existing = {p for job in manifest["jobs"].values() for p in job["owns"]}
        if any(paths_overlap(a, b) for a in existing for b in owns):
            raise PilotError("Jobs have overlapping file ownership")
        path = workspace / "jobs" / args.job
        branch = f"pilot/{manifest['id']}/{args.job}"
        path.parent.mkdir(parents=True, exist_ok=True)
        git(repo, "worktree", "add", "-b", branch, str(path), base)
        manifest["jobs"][args.job] = dict(path=str(path), branch=branch, owns=owns)
        if context_digest:
            manifest["jobs"][args.job]["context_sha256"] = context_digest
        save(workspace / "workspace.json", manifest)
        briefs = workspace / "briefs"
        briefs.mkdir(exist_ok=True)
        (briefs / f"{args.job}.md").write_text(
            f"# Job {args.job}\n\nRepository: {path}\nBranch: {branch}\nBase SHA: {base}\n"
            f"Source checkout (read-only): {repo}\n"
            f"Owned files: {', '.join(owns)}\n\nObjective: {args.objective}\n\n"
            "Read this brief, its context snapshot and the relevant project instructions "
            "before editing. Use the Repository above as explicit CWD for every command "
            "and absolute worktree paths for file tools. Confirm branch and base ancestry "
            "before work; do not rely on inherited CWD or sibling context. "
            "Use installed Task Delivery quick mode and the applicable project instructions. "
            "Work only in this worktree and owned files; no other workers, merges, push, "
            "global changes, or TD/PS state copying. Git isolation is not a permission sandbox. "
            "Run the relevant checks, inspect the diff, commit owned changes locally, "
            "and return commit SHA, changed files, commands/results, assumptions and remaining limits. "
            "Stop and report needs_context if the owned scope is insufficient or a shared contract "
            "is missing. Do not decide it silently or edit another job.\n" +
            (f"\n## Context snapshot\n\nSource content SHA256: {context_digest}\n\n{context}"
             if context_digest else
             "\nNo context packet supplied. Root must provide the task requirements, sources "
             "and acceptance before dispatch; this generated brief alone is insufficient.\n"),
            encoding="utf-8")
    return {"job": args.job, "path": str(path), "branch": branch,
            "base_sha": base, "brief": str(briefs / f"{args.job}.md")}


def snapshot(manifest):
    rows = {}
    for name, job in manifest["jobs"].items():
        repo = Path(job["path"])
        candidate = head(repo)
        branch = git(repo, "symbolic-ref", "--short", "HEAD")
        git(repo, "merge-base", "--is-ancestor", manifest["base_sha"], candidate)
        # Human-readable Git output quotes unusual paths. Read raw NUL-delimited
        # bytes so Unicode, whitespace and CR/LF inside filenames survive.
        result = subprocess.run(["git", "diff", "--name-only", "-z", "--no-renames",
                                 manifest["base_sha"], candidate], cwd=repo,
                                capture_output=True, timeout=120)
        if result.returncode:
            raise PilotError(f"Cannot read changed paths: {os.fsdecode(result.stderr)}")
        changed = [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]
        rows[name] = dict(sha=candidate, branch=branch, clean=clean(repo),
                          changed=changed, outside_scope=sorted(set(changed) - set(job["owns"])))
    return rows


def current(manifest, rows):
    return (base_head(manifest) == manifest["base_sha"] and
            head(manifest["repo"]) == manifest["base_sha"] and clean(manifest["repo"]) and
            git(manifest["repo"], "symbolic-ref", "HEAD") == manifest["base_ref"] and
            all(row["clean"] and not row["outside_scope"] and
                row["branch"] == manifest["jobs"][name]["branch"]
                for name, row in rows.items()))


def status(args):
    workspace = Path(args.workspace).resolve()
    with locked(workspace):
        manifest = read(workspace)
        rows = snapshot(manifest)
        verdict = None
        if (workspace / "verification.json").exists():
            prior = json.loads((workspace / "verification.json").read_text())
            fresh = (current(manifest, rows) and prior.get("jobs") == rows and
                     prior.get("base_sha") == manifest["base_sha"])
            if fresh and prior.get("candidate_path"):
                candidate = Path(prior["candidate_path"])
                fresh = (head(candidate) == prior.get("candidate_sha") and clean(candidate) and
                         git(candidate, "symbolic-ref", "--short", "HEAD") == prior.get("candidate_branch"))
            verdict = dict(check=prior["check"], fresh=fresh,
                           candidate_sha=prior.get("candidate_sha"))
        return dict(repo=manifest["repo"], base_sha=manifest["base_sha"],
                    source_unchanged=current(manifest, rows), jobs=rows,
                    verification=verdict, note="Check evidence only; no task approval/completion implied")


def verify(args):
    workspace = Path(args.workspace).resolve()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise PilotError("Supply an explicit check argv after --")
    with locked(workspace):
        manifest = read(workspace)
        rows = snapshot(manifest)
        if not rows or not current(manifest, rows):
            raise PilotError("Source/job changed, dirty, on wrong branch or outside ownership")
        if any(row["sha"] == manifest["base_sha"] for row in rows.values()):
            raise PilotError("Every job must have a committed candidate")
        token = uuid.uuid4().hex[:12]
        candidate = workspace / "integration" / token
        candidate.parent.mkdir(exist_ok=True)
        branch = f"pilot/{manifest['id']}/integration-{token}"
        git(manifest["repo"], "worktree", "add", "-b", branch, str(candidate), manifest["base_sha"])
        evidence = dict(started=now(), base_sha=manifest["base_sha"], jobs=rows,
                        candidate_path=str(candidate), candidate_branch=branch,
                        candidate_sha=None, command=command, check="incomplete")
        save(workspace / "verification.json", evidence)
        try:
            for name, row in sorted(rows.items()):
                git(candidate, "merge", "--no-ff", "--no-edit", row["sha"])
            evidence["candidate_sha"] = head(candidate)
            try:
                result = subprocess.run(command, cwd=candidate, text=True, capture_output=True,
                                        timeout=args.timeout)
                log = result.stdout + result.stderr
                evidence["returncode"] = result.returncode
                evidence["check"] = "pass" if result.returncode == 0 else "fail"
            except (OSError, subprocess.TimeoutExpired) as exc:
                log = str(exc)
                evidence["check"] = "error"
                evidence["returncode"] = None
            (candidate.parent / f"{token}.log").write_text(log)
            evidence["log"] = str(candidate.parent / f"{token}.log")
            after = snapshot(manifest)
            if (not current(manifest, after) or after != rows or
                    head(candidate) != evidence["candidate_sha"] or not clean(candidate) or
                    git(candidate, "symbolic-ref", "--short", "HEAD") != branch):
                evidence["check"] = "stale"
        except PilotError as exc:
            evidence["check"] = "merge-error"
            evidence["error"] = str(exc)
        evidence["finished"] = now()
        save(workspace / "verification.json", evidence)
        return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("prepare", help="Prepare one independent job; never launch agents")
    p.add_argument("--repo", required=True)
    p.add_argument("--workspace", required=True)
    p.add_argument("--base", default="main")
    p.add_argument("--job", required=True)
    p.add_argument("--owns", action="append", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--context", type=Path,
                   help="UTF-8 task packet to snapshot into the brief (no secret filtering)")
    p = commands.add_parser("status", help="Read observed Git state and check freshness")
    p.add_argument("--workspace", required=True)
    p = commands.add_parser("verify", help="Merge exact job commits into a retained candidate and check")
    p.add_argument("--workspace", required=True)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        result = globals()[args.action](args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.action != "verify" or result["check"] == "pass" else 1
    except (PilotError, OSError, ValueError, KeyError) as exc:
        print(f"software-factory: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
