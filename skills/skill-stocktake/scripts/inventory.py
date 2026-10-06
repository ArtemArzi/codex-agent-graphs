#!/usr/bin/env python3
"""Inventory explicit current-host skill roots; no home/cache discovery or writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def metadata(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    front = text.split("\n---", 1)[0].splitlines()[1:]
    result: dict[str, str] = {}
    for index, line in enumerate(front):
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if value in {">", ">-", "|", "|-"}:
            continuation = []
            for following in front[index + 1 :]:
                if following and not following[0].isspace():
                    break
                continuation.append(following.strip())
            value = " ".join(continuation)
        result[key] = value.strip("\"'")
    return result


def inventory(roots: list[Path], files: list[Path]) -> dict:
    selected: set[Path] = set()
    scope = []
    for original in roots:
        root = original.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"Not a skill directory: {original}")
        # Plugin cache roots would include inactive versions; require exact files.
        if "cache" in root.parts and "plugins" in root.parts:
            raise ValueError("For plugin caches pass exact active SKILL.md files via --file")
        found = {p.resolve() for p in root.rglob("SKILL.md") if p.is_file()}
        selected.update(found)
        scope.append({"requested": str(original), "resolved": str(root), "copies": len(found)})
    for original in files:
        file = original.expanduser().resolve(strict=True)
        if not file.is_file() or file.name != "SKILL.md":
            raise ValueError(f"Not a SKILL.md file: {original}")
        selected.add(file)
    items = []
    groups: dict[str, list[str]] = {}
    for file in sorted(selected):
        raw = file.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8")
        info = metadata(text)
        resources = sorted(str(p.relative_to(file.parent)) for p in file.parent.rglob("*")
                           if p.is_file() and "__pycache__" not in p.parts and p != file)
        items.append({"path": str(file), **info, "sha256": sha, "bytes": len(raw),
                      "lines": len(text.splitlines()), "resources": resources,
                      "enabled": "unknown", "usage": "unknown"})
        groups.setdefault(sha, []).append(str(file))
    return {"schema_version": 1, "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "coverage": "static-inventory", "roots": scope,
            "copies": len(items), "distinct_bodies": len(groups), "skills": items,
            "duplicates": [paths for paths in groups.values() if len(paths) > 1]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, default=[])
    parser.add_argument("--file", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.root and not args.file:
        parser.error("Select at least one explicit current root or file")
    try:
        result = inventory(args.root, args.file)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
