#!/usr/bin/env python3
"""Install this task's exact skill/role set using the existing installer helpers.

Never edits config.toml, global policies or other installed skills. A prepare
receipt binds both source and installed manifests; apply refuses intervening drift.
On failure, move the candidate aside and restore exact prior files without deletion.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import install

SKILLS = ("project-start", "task-delivery")
ROLES = ("project_docs_verifier", "task_plan_reviewer", "task_result_reviewer", "task_worker", "worker")
TARGETS = tuple(f"skills/{name}" for name in SKILLS) + tuple(f"agents/{name}.toml" for name in ROLES)


def snapshot(home):
    result = {}
    for relative in TARGETS:
        path = home / relative
        if path.is_symlink() or not path.exists():
            raise ValueError(f"Expected existing regular managed target: {path}")
        result[relative] = install.manifest(path) if path.is_dir() else install.sha256_file(path)
    return result


def desired(home):
    generated = install.generated_files(home)
    result = {f"skills/{name}": install.manifest(ROOT / "skills" / name) for name in SKILLS}
    for role in ROLES:
        key = f"agents/{role}.toml"
        result[key] = hashlib.sha256(generated[Path(key)][1].encode()).hexdigest()
    return result


def restore(home, backup, before):
    for relative in reversed(TARGETS):
        saved = backup / relative
        target = home / relative
        if saved.exists():
            rejected = backup / "rejected" / relative
            rejected.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                os.replace(target, rejected)
            os.replace(saved, target)
    if snapshot(home) != before:
        raise RuntimeError(f"Restore verification failed; inspect {backup}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "apply", "verify"))
    parser.add_argument("--home", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    home = Path(args.home).resolve()
    install.validate_install_parents(home)
    receipt = Path(args.receipt).resolve()
    if args.action == "prepare":
        if receipt.exists():
            raise ValueError("Prepare receipt must be new")
        data = {"home": str(home), "before": snapshot(home), "desired": desired(home),
                "config_sha256": install.sha256_file(home / "config.toml")}
        install.atomic_write(receipt, json.dumps(data, indent=2) + "\n")
        print(json.dumps({"prepared": str(receipt), "targets": TARGETS}))
        return
    data = json.loads(receipt.read_text())
    if data["home"] != str(home) or data["desired"] != desired(home):
        raise ValueError("Source or target differs from prepared scope")
    if install.sha256_file(home / "config.toml") != data["config_sha256"]:
        raise ValueError("Configuration changed since prepare")
    if args.action == "verify":
        if snapshot(home) != data["desired"]:
            raise ValueError("Installed manifests differ from source")
        print(json.dumps({"status": "PASS", "targets": TARGETS, "config": "unchanged"}))
        return
    if snapshot(home) != data["before"]:
        raise ValueError("Installed targets changed since prepare; refusing overwrite")
    backup = install.backup_root(home)
    install.atomic_write(backup / "architecture-update.json", json.dumps(data, indent=2) + "\n")
    try:
        for name in SKILLS:
            relative = f"skills/{name}"
            install.replace_directory(ROOT / relative, home / relative, backup / relative)
        generated = install.generated_files(home)
        for role in ROLES:
            relative = f"agents/{role}.toml"
            install.replace_generated(generated[Path(relative)][1], home / relative, backup / relative)
        if snapshot(home) != data["desired"]:
            raise RuntimeError("Post-install manifest verification failed")
        if install.sha256_file(home / "config.toml") != data["config_sha256"]:
            raise RuntimeError("Configuration changed during apply")
    except Exception:
        restore(home, backup, data["before"])
        raise
    print(json.dumps({"status": "PASS", "backup": str(backup), "config": "unchanged"}))


if __name__ == "__main__":
    main()
