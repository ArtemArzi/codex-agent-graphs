#!/usr/bin/env python3
"""Prepare isolated offline skill exercises; never call or grade a model."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path("tests/fixtures/skill-cases/cases.json")


def relative_file(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Fixture paths must be nonempty relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or str(path) == ".":
        raise ValueError(f"Invalid fixture path: {value}")
    return Path(*path.parts)


def load_cases(root: Path) -> dict[str, dict]:
    root = root.resolve()
    catalog = root / CATALOG
    data = json.loads(catalog.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("cases"), list) or not data["cases"]:
        raise ValueError("Expected a nonempty schema_version 1 case catalogue")
    cases = {}
    for case in data["cases"]:
        if not isinstance(case, dict):
            raise ValueError("Each case must be an object")
        name = case.get("id", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name in cases:
            raise ValueError(f"Invalid or duplicate case id: {name}")
        if not isinstance(case.get("request"), str) or not case["request"].strip():
            raise ValueError(f"Missing request: {name}")
        skills, rubric, files = case.get("skills"), case.get("rubric"), case.get("files", {})
        if not isinstance(skills, list) or not skills:
            raise ValueError(f"Expected distinct skill names: {name}")
        for skill in skills:
            if not isinstance(skill, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill):
                raise ValueError(f"Invalid skill name: {name}")
            entry = root / "skills" / skill / "SKILL.md"
            if not entry.is_file() or not entry.resolve().is_relative_to(root):
                raise ValueError(f"Missing local skill: {skill}")
        if len(set(skills)) != len(skills):
            raise ValueError(f"Expected distinct skill names: {name}")
        if not isinstance(rubric, list) or not rubric or any(not isinstance(item, str) or not item.strip() for item in rubric):
            raise ValueError(f"Missing manual rubric: {name}")
        if not isinstance(files, dict):
            raise ValueError(f"Expected fixture mapping: {name}")
        targets = []
        for target, source in files.items():
            target_path = relative_file(target)
            source_path = catalog.parent / relative_file(source)
            if target_path.parts[0] == "TASK.md" or not source_path.is_file() or source_path.resolve() == catalog.resolve() or not source_path.resolve().is_relative_to(catalog.parent.resolve()):
                raise ValueError(f"Invalid or missing fixture: {name}/{target}")
            if any(target_path == prior or target_path in prior.parents or prior in target_path.parents for prior in targets):
                raise ValueError(f"Conflicting fixture targets: {name}/{target}")
            targets.append(target_path)
        cases[name] = case
    return cases


def prepare(root: Path, name: str, output: Path) -> dict:
    root = root.resolve()
    cases = load_cases(root)
    if name not in cases:
        raise ValueError(f"Unknown case: {name}")
    if output.exists() or output.is_symlink():
        raise ValueError(f"Destination already exists: {output}")
    case = cases[name]
    entries = "\n".join(f"- ${skill}: {(root / 'skills' / skill / 'SKILL.md')}" for skill in case["skills"])
    task = (
        f"# Skill exercise: {name}\n\nUse these skill instructions:\n{entries}\n\n"
        "All company data and files are synthetic. Work only in this exercise directory. "
        "Do not change the skill repository or real accounts, use the network, install tools, "
        "start schedules, spawn agents or send messages. Do not read the case catalogue, "
        "task audit, assessment rubrics or other cases.\n\n"
        f"## Request\n\n{case['request']}\n\n"
        "Write the response and actual checks to answer.md here. Distinguish performed "
        "actions from proposals and unverified claims.\n"
    )
    output.mkdir(parents=True)
    for target, source in case.get("files", {}).items():
        destination = output / relative_file(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / CATALOG.parent / relative_file(source), destination)
    (output / "TASK.md").write_text(task, encoding="utf-8")
    return {"status": "prepared", "case": name, "directory": str(output.resolve()), "task": str((output / "TASK.md").resolve())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("check")
    command = commands.add_parser("prepare")
    command.add_argument("case")
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(ROOT, args.case, args.output)
        else:
            cases = load_cases(ROOT)
            result = {"status": "catalogue-valid", "coverage": "fixture-structure-only", "cases": list(cases)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError) as error:
        parser.exit(2, f"skill_cases: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
