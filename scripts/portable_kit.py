from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from portable_bundle import KitError, build, verify_bundle
import portable_install
from portable_sources import profile_from_catalog, capture


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    command = commands.add_parser("capture")
    command.add_argument("--home", type=Path, required=True)
    command.add_argument("--cwd", type=Path, required=True)
    command.add_argument("--codex", type=Path)
    command.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--knowledge", type=Path)
    command.add_argument("--knowledge-policy", type=Path)
    command = commands.add_parser("sources")
    command.add_argument("--catalog", type=Path, required=True)
    command.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--knowledge", type=Path)
    command.add_argument("--knowledge-policy", type=Path)
    command = commands.add_parser("build")
    command.add_argument("--profile", type=Path, required=True)
    command.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("verify-bundle")
    command.add_argument("--bundle", type=Path, required=True)
    for action in ("plan", "install"):
        command = commands.add_parser(action)
        command.add_argument("--bundle", type=Path, required=True)
        command.add_argument("--target", type=Path, required=True)
    for action in ("verify", "doctor", "rollback", "run", "retire"):
        command = commands.add_parser(action)
        command.add_argument("--target", type=Path, required=True)
        if action == "rollback":
            command.add_argument("--release")
        if action == "retire":
            command.add_argument("--release", required=True)
        if action == "run":
            command.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "capture":
            result = capture(args.home, args.cwd, args.output, args.repo, args.knowledge, args.knowledge_policy, args.codex)
        elif args.action == "sources":
            result = profile_from_catalog(args.catalog, args.output, args.repo, args.knowledge, args.knowledge_policy)
        elif args.action == "build":
            result = build(args.profile, args.output, args.repo)
        elif args.action == "verify-bundle":
            lock = verify_bundle(args.bundle)
            result = {"status": "verified", "id": lock["id"], "skills": len(lock.get("skills", []))}
        elif args.action in ("plan", "install"):
            result = getattr(portable_install, args.action)(args.bundle, args.target)
        elif args.action == "rollback":
            result = portable_install.rollback(args.target, args.release)
        elif args.action == "retire":
            result = portable_install.retire(args.target, args.release)
        elif args.action == "run":
            argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            if not argv:
                raise KitError("Run requires a command after --")
            return portable_install.run(args.target, argv)
        elif args.action == "doctor":
            result = portable_install.describe(args.target)
            lock = result.pop("manifest")
            result["python"] = ".".join(map(str, sys.version_info[:3]))
            result["commands"] = {name: bool(shutil.which(name)) for name in ("python3", "node", "git", "codex")}
            result["requirements"] = lock.get("requirements", [])
            result["dependency_files"] = lock.get("dependency_files", [])
            result["external_paths"] = lock.get("external_paths", [])
            result["host_capabilities"] = lock.get("host_capabilities", [])
            result["readiness"] = "requires-capability-review"
            result["mcp"] = "deferred"
        else:
            result = portable_install.verify(args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (KitError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
