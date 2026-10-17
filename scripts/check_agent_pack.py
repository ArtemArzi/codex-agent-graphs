#!/usr/bin/env python3
"""Validate/package only the agent lifecycle overlay, without installing skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
PRODUCT = Path("products/agent-lifecycle")
MANIFEST = PRODUCT / "manifest.json"
SKILLS = (
    "agent-project-design",
    "agent-memory-lifecycle",
    "agent-outcome-e2e",
    "agent-commercial-delivery",
)
EXCLUDED = {"__pycache__", ".pytest_cache", ".DS_Store"}


class PackError(ValueError):
    """An invalid or conflicting package, never an installation request."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pack(root: Path) -> dict:
    path = root / PRODUCT / "pack.json"
    if path.is_symlink() or not path.is_file():
        raise PackError("Missing or symlinked pack.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("id") != "agent-lifecycle":
        raise PackError("Unsupported pack identity/schema")
    members = data.get("managed_skills")
    if not isinstance(members, list) or len(members) != len(set(members)):
        raise PackError("Duplicate or invalid managed skills")
    if set(members) != set(SKILLS) or data.get("entrypoint") != "agent-project-design":
        raise PackError("Unexpected managed skills/entrypoint")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(data.get("version", ""))):
        raise PackError("Invalid package version")
    reused = data.get("reused_capabilities", {}).get("skills", [])
    if set(members) & set(reused):
        raise PackError("A managed skill is also declared reused")
    if data.get("runtime_dependencies") != []:
        raise PackError("Instruction-only pack unexpectedly requires a runtime")
    return data


def owned_files(root: Path) -> dict[str, Path]:
    """Enumerate this overlay, even when it lives in a larger repository."""
    root = root.resolve()
    scopes = [root / "skills" / name for name in SKILLS]
    scopes += [root / PRODUCT, root / "scripts/check_agent_pack.py", root / "tests/test_agent_pack.py"]
    files: dict[str, Path] = {}
    for scope in scopes:
        if not scope.exists() or scope.is_symlink():
            raise PackError(f"Missing or symlinked owned path: {scope.relative_to(root)}")
        # Reject symlinked parents too, including a symlinked skills directory.
        for parent in (scope, *scope.parents):
            if parent == root:
                break
            if parent.is_symlink():
                raise PackError(f"Symlinked owned parent: {parent.relative_to(root)}")
        paths = [scope] if scope.is_file() else sorted(scope.rglob("*"))
        for path in paths:
            relative = path.relative_to(root)
            if any(part in EXCLUDED for part in relative.parts):
                continue
            if path.is_symlink():
                raise PackError(f"Symlink in package: {relative}")
            if path.is_dir():
                continue
            if not stat.S_ISREG(path.stat().st_mode):
                raise PackError(f"Non-regular package file: {relative}")
            files[relative.as_posix()] = path
    return files


def file_hashes(root: Path) -> dict[str, str]:
    return {name: digest(path) for name, path in owned_files(root).items() if name != MANIFEST.as_posix()}


def validate_structure(root: Path) -> dict:
    data = load_pack(root)
    files = owned_files(root)
    for name in SKILLS:
        folder = root / "skills" / name
        body = (folder / "SKILL.md").read_text(encoding="utf-8")
        header = body.split("---", 2)
        if len(header) != 3 or header[0] or not re.search(rf"(?m)^name: {re.escape(name)}$", header[1]):
            raise PackError(f"Invalid skill frontmatter: {name}")
        if not re.search(r"(?m)^description: .+", header[1]):
            raise PackError(f"Missing description: {name}")
        version = re.search(r'(?m)^  version: "([^"]+)"$', header[1])
        if not version or not re.fullmatch(r"\d+\.\d+\.\d+", version.group(1)):
            raise PackError(f"Missing/invalid skill version: {name}")
        metadata = (folder / "agents/openai.yaml").read_text(encoding="utf-8")
        short = re.search(r'(?m)^  short_description: "([^"\n]+)"$', metadata)
        if not short or not 25 <= len(short.group(1)) <= 64 or f"${name}" not in metadata:
            raise PackError(f"Invalid native metadata: {name}")
        if "allow_implicit_invocation: false" in metadata:
            raise PackError(f"Unexpected explicit-only invocation: {name}")
    # Local Markdown references must close over owned files, not personal paths
    # or undeclared copies of optional skills. Anchors are not resolved here.
    for name, path in files.items():
        if path.suffix != ".md":
            continue
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if link.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = unquote(link.split("#", 1)[0])
            if Path(target).is_absolute() or re.match(r"^[A-Za-z]:", target):
                raise PackError(f"Absolute local reference in {name}: {link}")
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()):
                raise PackError(f"Reference escapes package in {name}: {link}")
            relative = resolved.relative_to(root.resolve()).as_posix()
            if relative not in files or not resolved.is_file():
                raise PackError(f"Unowned/missing reference in {name}: {link}")
    return data


def write_manifest(root: Path) -> None:
    data = validate_structure(root)
    payload = {"schema_version": 1, "pack_version": data["version"], "files": file_hashes(root)}
    (root / MANIFEST).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(root: Path) -> None:
    data = validate_structure(root)
    path = root / MANIFEST
    if not path.is_file() or path.is_symlink():
        raise PackError("Missing/invalid manifest; use --write-manifest after reviewing source changes")
    expected = json.loads(path.read_text(encoding="utf-8"))
    if expected.get("schema_version") != 1 or expected.get("pack_version") != data["version"]:
        raise PackError("Manifest schema/version differs from the package")
    if expected.get("files") != file_hashes(root):
        raise PackError("Manifest file membership or hashes differ")


def inspect_installed(root: Path, roots: list[Path]) -> dict[str, str]:
    """Check only four owned names; resolve intentional root aliases once."""
    physical = sorted({p.resolve() for p in roots})
    results = {}
    for name in SKILLS:
        matches = []
        for candidate in physical:
            member = candidate / name
            if member.exists() or member.is_symlink():
                if member.is_symlink() or not member.is_dir():
                    raise PackError(f"Invalid installed member: {member}")
                matches.append(member)
        if len(matches) > 1:
            raise PackError(f"Duplicate installed name {name}: {', '.join(map(str, matches))}")
        if not matches:
            results[name] = "not-installed"
            continue
        source = root / "skills" / name
        def tree_hashes(folder: Path) -> dict[str, str]:
            values = {}
            for path in sorted(folder.rglob("*")):
                if any(part in EXCLUDED for part in path.relative_to(folder).parts):
                    continue
                if path.is_symlink():
                    raise PackError(f"Symlink in installed/source skill: {path}")
                if path.is_file():
                    values[path.relative_to(folder).as_posix()] = digest(path)
            return values
        if tree_hashes(source) != tree_hashes(matches[0]):
            raise PackError(f"Installed skill drift; preserve and reconcile before replacing: {name}")
        results[name] = "in-sync"
    return results


def archive(root: Path, destination: Path) -> int:
    verify_manifest(root)
    destination = destination.resolve()
    if destination.is_relative_to(root.resolve()):
        raise PackError("Archive destination must be outside the source tree")
    files = owned_files(root)
    # Freeze bytes and prove that the snapshot, not later live reads, matches
    # the reviewed manifest. A concurrent edit must not silently change the ZIP.
    snapshot = {name: path.read_bytes() for name, path in files.items()}
    recorded = json.loads(snapshot[MANIFEST.as_posix()].decode("utf-8"))
    frozen_hashes = {name: hashlib.sha256(value).hexdigest() for name, value in snapshot.items()
                     if name != MANIFEST.as_posix()}
    if recorded.get("files") != frozen_hashes:
        raise PackError("Source changed while taking the archive snapshot")
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as output:
        for name, value in sorted(snapshot.items()):
            info = zipfile.ZipInfo(f"agent-lifecycle-pack/{name}", date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, value)
    with zipfile.ZipFile(destination) as readback:
        if readback.testzip() is not None:
            raise PackError("Archive CRC readback failed")
        expected = {f"agent-lifecycle-pack/{name}" for name in files}
        if set(readback.namelist()) != expected or len(readback.namelist()) != len(expected):
            raise PackError("Archive membership readback failed")
        for name, value in snapshot.items():
            if readback.read(f"agent-lifecycle-pack/{name}") != value:
                raise PackError(f"Archive content readback failed: {name}")
    verify_manifest(root)
    return len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true", help="Record reviewed source bytes; no installation")
    parser.add_argument("--skill-root", action="append", type=Path, default=[], help="Explicit native discovery root to inspect read-only")
    parser.add_argument("--archive", type=Path, help="Create a new exact ZIP outside the source tree; refuses overwrite")
    args = parser.parse_args(argv)
    try:
        if args.write_manifest:
            write_manifest(ROOT)
        verify_manifest(ROOT)
        installed = inspect_installed(ROOT, args.skill_root) if args.skill_root else {}
        count = archive(ROOT, args.archive) if args.archive else len(owned_files(ROOT))
        print(json.dumps({"status": "PASS", "pack": "agent-lifecycle", "files": count, "installed": installed,
                          "scope": "structure-links-hashes-packaging; not agent runtime E2E"}, ensure_ascii=False))
        return 0
    except (PackError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
