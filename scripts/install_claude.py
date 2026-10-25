#!/usr/bin/env python3
"""Explicit native Claude install; preserves settings, accounts and Codex homes."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
import tempfile

import claude_projection as projection

shared = projection.installer
STAGING_LIMIT = 128 * 1024 * 1024
BACKUP_LIMIT = 256 * 1024 * 1024


def safe_parents(home):
    for parent in home.parents:
        if parent.is_symlink():
            raise shared.InstallError(f"Symlinked native home ancestor: {parent}")
    for path in [home, home / "skills", home / "agents", home / "backups", home / "backups/agent-graphs-native"]:
        if path.is_symlink() or path.exists() and not path.is_dir():
            raise shared.InstallError(f"Unsafe native install parent: {path}")


def ownership(home):
    path = home / "agent-graph-runtime/claude-native.json"
    if not path.exists():
        return {}
    if path.is_symlink():
        raise shared.InstallError("Symlinked Claude provenance")
    value = json.loads(path.read_text())
    checksum = value.pop("integrity", None)
    if checksum != projection.digest(value) or value.get("format") != projection.FORMAT or value.get("home") != str(home):
        raise shared.InstallError("Claude provenance changed or belongs to another home")
    return value["owned"]


def prepare(home, *, names=None, creator=None, adopt=()):
    home = Path(home).expanduser()
    safe_parents(home)
    home = home.resolve()
    units, record = projection.build(home, names=names, creator_source=creator)
    prior = ownership(home)
    rows = []
    for name, files in units.items():
        before = shared.directory_preimage(home / name)
        desired = projection.hashes(files)
        owned_before = dict(before or {})
        if name == "agent-graph-runtime":
            owned_before.pop("claude-native.json", None)
        private_drift = before is not None and prior.get(name) != owned_before
        adopted = name.removeprefix("skills/") in set(adopt) and name.startswith("skills/")
        if private_drift and before != desired and not adopted:
            raise shared.InstallError(f"Unmanaged/private drift at {name}; inspect and explicitly --adopt this skill")
        if name in prior and prior[name] != owned_before and not adopted:
            raise shared.InstallError(f"Managed Claude drift at {name}; preserve the private edit")
        rows.append({"name": name, "kind": "native", "relative": Path(name), "before": before, "desired": desired, "status": "missing" if before is None else "in-sync" if before == desired else "adopt" if private_drift else "update"})
    missing = set(prior) - set(units)
    if missing:
        raise shared.InstallError(f"Selection would orphan managed units; keep original selection: {sorted(missing)}")
    total = sum(len(data) for files in units.values() for data in files.values())
    if total > STAGING_LIMIT:
        raise shared.InstallError("Claude staging exceeds 128 MiB; no new namespace fallback")
    return home, units, record, rows, total


def backup_bytes(root):
    if not root.exists():
        return 0
    return sum((root / relative).stat().st_size for relative in shared.manifest(root))


def install(home, units, rows, total, *, names=None, creator=None):
    if all(row["status"] == "in-sync" for row in rows):
        return {"status": "already-installed", "changes": []}
    backup_root = home / "backups/agent-graphs-native"
    if backup_bytes(backup_root) + sum((home / row["relative"] / path).stat().st_size for row in rows for path in (row["before"] or {})) > BACKUP_LIMIT:
        raise shared.InstallError("Native backup history would exceed 256 MiB; preserve it and reconcile")
    with tempfile.TemporaryDirectory(prefix="cag-claude-stage-") as scratch:
        scratch = Path(scratch)
        for row in rows:
            directory = scratch / row["relative"]
            directory.mkdir(parents=True)
            for relative, data in units[row["name"]].items():
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                original = projection.ROOT / row["relative"] / relative
                if row["name"] == "skills/skill-creator":
                    original = (Path(creator) if creator else home / "skills/skill-creator") / relative
                if original.is_file() and not original.is_symlink():
                    shutil.copy2(original, target)
                target.write_bytes(data)
            row["source"] = directory
        backup = backup_root / shared.backup_root(home).name
        code_sources = [projection.ROOT / "scripts" / name for name in
                        ["install_claude.py", "claude_projection.py", "install.py", "claude_agents_sync.py", "model_routing.py"]]
        code_hashes = {path: shared.sha256_file(path) for path in code_sources}
        expected = {name: projection.hashes(files) for name, files in units.items()}
        def source_guard(_touched):
            if any(shared.sha256_file(path) != sha for path, sha in code_hashes.items()):
                raise shared.InstallError("Concurrent native installer source edit")
            current, _record = projection.build(home, names=names, creator_source=creator)
            if {name: projection.hashes(files) for name, files in current.items()} != expected:
                raise shared.InstallError("Concurrent canonical skill/role source edit")
        def make_backup(_home):
            backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            if backup_root.stat().st_mode & 0o077:
                raise shared.InstallError("Native backup namespace must be private (0700)")
            backup.mkdir(mode=0o700)
            return backup
        result = shared.apply_skills_plans([("claude-native", home, rows)],
                                          make_backup=make_backup,
                                          validate=source_guard)
    return {"status": "installed", "bytes": total, "environments": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "install", "verify"])
    parser.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--skill-creator", type=Path)
    parser.add_argument("--adopt", action="append", default=[], help="Explicitly adopt only this inspected existing skill")
    parser.add_argument("--pack", choices=["interface-design"], help="Install only this ordinary skill pack; preserve engineering ownership and profile")
    parser.add_argument("--skill-root", type=Path, help="Explicit native discovery root for --pack; default: <claude-home>/skills")
    args = parser.parse_args()
    if args.pack and (args.skill or args.skill_creator or args.adopt):
        parser.error("--pack cannot be combined with --skill, --skill-creator or --adopt")
    if args.skill_root and not args.pack:
        parser.error("--skill-root requires --pack")
    try:
        if args.pack:
            packs = projection.load("claude_shared_packs", shared.REPO_ROOT / "scripts/business_pack.py")
            summary = packs.run(args.action, [("claude", args.claude_home)], args.skill_root,
                                api=shared, pack_id=args.pack, provider="claude")
            print(json.dumps(summary, indent=2))
            return 0 if summary["status"] == "ok" else 1
        home, units, record, rows, total = prepare(args.claude_home, names=args.skill or None, creator=args.skill_creator, adopt=args.adopt)
        summary = {"status": "ok", "provider": "claude", "home": str(home), "bytes": total, "roles": len(record["roles"]), "items": [{key: row[key] for key in ["name", "status"]} for row in rows]}
        if args.action == "install":
            summary["result"] = install(home, units, rows, total, names=args.skill or None, creator=args.skill_creator)
        elif args.action == "verify" and any(row["status"] != "in-sync" for row in rows):
            summary["status"] = "drift"
        print(json.dumps(summary, indent=2))
        return 0 if summary["status"] == "ok" else 1
    except (shared.InstallError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "stopped", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
