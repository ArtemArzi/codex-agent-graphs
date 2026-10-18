#!/usr/bin/env python3
"""Resolve and install reviewed shared skill packs using installer primitives."""

from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any


PACK_ID = "business-automation"
PACK_IDS = (PACK_ID, "agent-lifecycle", "business-model")


def load_pack(repo: Path, pack_id: str = PACK_ID) -> dict[str, Any]:
    if pack_id not in PACK_IDS:
        raise ValueError(f"Unsupported shared skill pack: {pack_id}")
    pack = json.loads((repo / "products" / pack_id / "pack.json").read_text(encoding="utf-8"))
    if not isinstance(pack, dict):
        raise ValueError("Business pack manifest must be an object")
    names = pack.get("managed_skills")
    if (pack.get("schema_version") != 1 or pack.get("id") != pack_id
            or not isinstance(pack.get("version"), str) or not pack["version"]
            or not isinstance(names, list) or not names
            or any(not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
                   for name in names)
            or len(names) != len(set(names)) or pack.get("entrypoint") not in names):
        raise ValueError("Invalid business pack identity, version or managed skill list")
    if pack_id == "business-model":
        reused = pack.get("reused_capabilities")
        if (pack.get("update_owner") != "canonical-repository-first"
                or pack.get("entrypoint") != "business-work"
                or set(names) != {"business-work", "business-model-design",
                                     "business-economics", "process-to-product"}
                or not isinstance(reused, dict) or reused.get("required") is not False
                or not isinstance(reused.get("skills"), list)
                or any(not isinstance(name, str) for name in reused["skills"])
                or set(names).intersection(reused["skills"])
                or pack.get("runtime_dependencies") != []):
            raise ValueError("Invalid Business Model pack ownership, members or optional companions")
        return pack
    if pack_id == "agent-lifecycle":
        if pack.get("update_owner") != "canonical-repository-first":
            raise ValueError("Agent pack must retain its canonical repository owner")
        spec = importlib.util.spec_from_file_location("agent_pack_manifest", repo / "scripts/check_agent_pack.py")
        if spec is None or spec.loader is None:
            raise ValueError("Missing agent pack manifest validator")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        checker.verify_manifest(repo)
        return pack
    metadata = json.loads((repo / "skills/business-work/references/installation.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("Canonical business installation metadata must be an object")
    pins = pack.get("upstream_pins", {})
    installed_pins = metadata.get("pins", {})
    if (metadata.get("schema_version") != 2 or metadata.get("package_id") != PACK_ID
            or metadata.get("package_version") != pack["version"]
            or metadata.get("skills") != names
            or pack.get("update_owner") != "canonical-repository-first"
            or metadata.get("update_owner") != pack["update_owner"]
            or not isinstance(pins, dict) or not isinstance(installed_pins, dict)
            or set(pins) != set(installed_pins) or not pins):
        raise ValueError("Business pack and canonical installation metadata disagree")
    for name, pin in pins.items():
        if (not isinstance(pin, dict) or not isinstance(installed_pins[name], dict)
                or not isinstance(pin.get("commit"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", pin["commit"])
                or pin["commit"] != installed_pins[name].get("commit")
                or not isinstance(pin.get("repository"), str)
                or pin["repository"] != "https://github.com/" + str(installed_pins[name].get("repo"))):
            raise ValueError(f"Business pack upstream pin disagrees with canonical metadata: {name}")
    return pack


def absolute(path: Path) -> Path:
    """Preserve intentional root aliases instead of resolving them prematurely."""
    return Path(os.path.abspath(path.expanduser()))


def root_identity(path: Path, api: Any) -> tuple[Path, tuple[int, int] | None]:
    resolved = path.resolve()
    if path.is_symlink() and not path.exists():
        raise api.InstallError(f"Dangling business root alias: {path}")
    if path.exists() and not path.is_dir():
        raise api.InstallError(f"Business discovery root is not a directory: {path}")
    stat = path.stat() if path.exists() else None
    return resolved, (stat.st_dev, stat.st_ino) if stat else None


def resolve(homes: list[tuple[str, Path]], requested: Path | None, api: Any) -> dict[str, Any]:
    if not homes:
        raise api.InstallError("Select at least one environment")
    modern = {label: [absolute(home / ".agents/skills"), absolute(home.parent / ".agents/skills")]
              for label, home in homes}
    known = {path for paths in modern.values() for path in paths}
    known.update(absolute(home / "skills") for _, home in homes)
    explicit = absolute(requested) if requested is not None else None
    if explicit is not None:
        known.add(explicit)
    identities = {path: root_identity(path, api) for path in sorted(known)}
    if explicit is None:
        existing = [{identities[path][0] for path in modern[label] if identities[path][1] is not None}
                    for label, _ in homes]
        if len(homes) == 1 and not existing[0]:
            selected = modern[homes[0][0]][1]
        elif all(len(roots) == 1 for roots in existing) and len(set.union(*existing)) == 1:
            physical = next(iter(existing[0]))
            selected = next(path for path in modern[homes[0][0]] if identities[path][0] == physical)
        else:
            raise api.InstallError("Business roots are fresh or ambiguous across selected environments; "
                                   "pass --business-root PATH for a shared root or select one environment at a time")
    else:
        selected = explicit
    resolved = identities[selected][0]
    # Staging, backups and the lock must not live in another discovery root.
    for physical, _ in identities.values():
        if resolved != physical and (resolved.is_relative_to(physical) or physical.is_relative_to(resolved)):
            raise api.InstallError(f"Nested discovery roots are unsafe: {resolved} and {physical}")
    sources = api.SKILLS_ROOT.resolve()
    if resolved == sources or resolved.is_relative_to(sources) or sources.is_relative_to(resolved):
        raise api.InstallError("Business target must be separate from canonical skill sources")
    return {"selected": selected, "root": resolved, "identities": identities,
            "requested": explicit, "homes": homes,
            "physical_identity": root_identity(resolved, api)}


def declared_name(skill: Path, api: Any) -> str | None:
    """Read the top-level native name scalar; reject unsupported ambiguity.

    This deliberately handles scalar names, not arbitrary YAML documents. JSON
    double quotes and YAML single quotes cover normal quoted skill names. More
    complex declarations require explicit inspection instead of being ignored.
    """
    lines = skill.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    closing = next((index for index, line in enumerate(lines[1:], 1)
                    if line.strip() in {"---", "..."}), None)
    if closing is None:
        raise api.InstallError(f"Unclosed skill frontmatter prevents name inventory: {skill}")
    front = lines[1:closing]
    content = [line for line in front if line.strip() and not line.lstrip().startswith("#")]
    if not content:
        raise api.InstallError(f"Missing skill name in frontmatter: {skill}")
    level = min(len(line) - len(line.lstrip()) for line in content)
    fields = []
    for line in content:
        if len(line) - len(line.lstrip()) != level:
            continue
        match = re.fullmatch(r"(?:name|\"name\"|'name')\s*:\s*(.*)", line.lstrip())
        if match:
            fields.append(match.group(1).strip())
    if not fields:
        # Flow mappings, encoded keys and other YAML forms could conceal a name.
        # Refuse uncertainty rather than treating a native skill as unnamed.
        raise api.InstallError(f"Cannot inventory top-level skill name: {skill}; use a plain or quoted name field")
    if len(fields) != 1:
        raise api.InstallError(f"Duplicate skill name declarations: {skill}")
    value = fields[0]
    if value.startswith('"'):
        match = re.fullmatch(r'("(?:[^"\\]|\\.)*")(?:\s+#.*)?', value)
        if match:
            try:
                return json.loads(match.group(1))
            except ValueError:
                pass
    elif value.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'(?:\s+#.*)?", value)
        if match:
            return match.group(1).replace("''", "'")
    elif re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*(?:\s+#.*)?", value):
        return re.split(r"\s+#", value, maxsplit=1)[0]
    raise api.InstallError(f"Ambiguous or unsupported skill name scalar: {skill}; use a plain or quoted name")


def discovered_skills(roots: set[Path], api: Any):
    """Mirror recursive native discovery without leaving the bounded known roots.

    Native discovery follows directory aliases, deduplicates their physical
    destinations and file identities, skips hidden directories, and descends inside existing skills.
    An alias outside this inventory requires explicit inspection, not a home scan.
    """
    seen: set[tuple[int, int]] = set()
    seen_files: set[tuple[int, int]] = set()

    def walk_error(error: OSError) -> None:
        raise error

    for root in sorted(roots):
        if not root.exists():
            continue
        for requested, children, files in os.walk(root, topdown=True, followlinks=True, onerror=walk_error):
            directory = Path(requested).resolve()
            if not any(directory.is_relative_to(known) for known in roots):
                raise api.InstallError(f"Discovery directory alias changed outside known skill roots: {requested} -> {directory}")
            stat = directory.stat()
            identity = (stat.st_dev, stat.st_ino)
            if identity in seen:
                children[:] = []
                continue
            seen.add(identity)
            visible = []
            for name in sorted(children):
                if name.startswith("."):
                    # Includes this run's hidden staging trees, like the native loader.
                    continue
                child = directory / name
                destination = child.resolve()
                if not any(destination.is_relative_to(known) for known in roots):
                    raise api.InstallError(f"Discovery directory alias leaves known skill roots: {child} -> {destination}; "
                                           "inspect this alias explicitly before installing")
                visible.append(name)
            children[:] = visible
            if "SKILL.md" in files:
                requested_skill = directory / "SKILL.md"
                skill = requested_skill.resolve()
                if not any(skill.is_relative_to(known) for known in roots):
                    raise api.InstallError(f"Discovery skill file alias leaves known skill roots: {requested_skill} -> {skill}; "
                                           "inspect this alias explicitly before installing")
                if skill.is_file():
                    stat = skill.stat()
                    identity = (stat.st_dev, stat.st_ino)
                    if identity not in seen_files:
                        seen_files.add(identity)
                        yield skill


def inspect_duplicates(context: dict[str, Any], names: list[str], api: Any) -> None:
    physical_roots = {path.resolve() for path in context["identities"]}
    present: dict[str, set[Path]] = {name: set() for name in names}
    for root in sorted(physical_roots):
        for name in names:
            member = root / name
            if member.exists() or member.is_symlink():
                # Direct managed targets remain reserved even when locally drifted.
                api.directory_preimage(member)
                present[name].add(member)
    for skill in discovered_skills(physical_roots, api):
        name = declared_name(skill, api)
        if name in present:
            member = skill.parent
            api.directory_preimage(member)
            present[name].add(member)
    for name, paths in present.items():
        expected = context["root"] / name
        if paths - {expected}:
            raise api.InstallError(f"Managed business skill name {name} occurs outside its selected target "
                                   f"{expected}: {', '.join(map(str, sorted(paths)))}; "
                                   "preserve existing skills and resolve their discovery names before installing")


def prepare(homes: list[tuple[str, Path]], requested: Path | None, api: Any,
            *, pack_id: str = PACK_ID) -> dict[str, Any]:
    pack = load_pack(api.REPO_ROOT, pack_id)
    context = resolve(homes, requested, api)
    context["pack"] = pack
    context["pack_bytes"] = (api.REPO_ROOT / "products" / pack_id / "pack.json").read_bytes()
    inspect_duplicates(context, pack["managed_skills"], api)
    items = []
    for name in pack["managed_skills"]:
        source = api.SKILLS_ROOT / name
        if source.is_symlink() or not source.is_dir():
            raise api.InstallError(f"Unsafe business skill source: {source}")
        desired = api.manifest(source)
        if "SKILL.md" not in desired:
            raise api.InstallError(f"Business skill is missing SKILL.md: {source}")
        if declared_name(source / "SKILL.md", api) != name:
            raise api.InstallError(f"Canonical skill name disagrees with pack member {name}: {source}")
        before = api.directory_preimage(context["root"] / name)
        items.append({"kind": "skill", "name": name, "relative": Path(name), "source": source,
                      "desired": desired, "before": before,
                      "status": "missing" if before is None else "in-sync" if before == desired else "drift"})
    context["items"] = items
    validate(context, [], api)
    return context


def validate(context: dict[str, Any], touched: list[dict[str, Any]], api: Any) -> None:
    pack_id = context["pack"]["id"]
    for path, identity in context["identities"].items():
        if root_identity(path, api) != identity:
            raise api.InstallError(f"Business root changed during installation: {path}")
    if (api.REPO_ROOT / "products" / pack_id / "pack.json").read_bytes() != context["pack_bytes"]:
        raise api.InstallError("Concurrent business pack manifest edit")
    if load_pack(api.REPO_ROOT, pack_id) != context["pack"]:
        raise api.InstallError("Concurrent business pack metadata edit")
    inspect_duplicates(context, context["pack"]["managed_skills"], api)
    validate_storage(context, api)
    installed = {item["target"]: item["desired"] for item in touched}
    for item in context["items"]:
        source = item["source"]
        if source.is_symlink() or api.manifest(source) != item["desired"]:
            raise api.InstallError(f"Concurrent business source edit: {source}")
        target = context["root"] / item["relative"]
        if api.directory_preimage(target) != installed.get(target, item["before"]):
            raise api.InstallError(f"Concurrent business skill edit: {target}")


def validate_storage(context: dict[str, Any], api: Any) -> None:
    root = context["root"]
    backup_parent = root.parent / "backups/agent-graphs"
    if any(backup_parent.is_relative_to(identity[0]) for identity in context["identities"].values()):
        raise api.InstallError(f"Business backups would be discoverable skills: {backup_parent}")
    if root.exists() and root.stat().st_dev != root.parent.stat().st_dev:
        raise api.InstallError("Business root requires a backup parent on the same filesystem")
    for parent in (backup_parent.parent, backup_parent):
        if (parent.is_symlink() or (parent.exists() and not parent.is_dir())
                or (root.exists() and parent.exists() and parent.stat().st_dev != root.stat().st_dev)):
            raise api.InstallError(f"Unsafe business backup parent: {parent}")


def payload(context: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "scope": "skills-only", "pack": context["pack"]["id"],
            "version": context["pack"]["version"],
            "environments": [{"environment": label, "codex_home": str(home)} for label, home in context["homes"]],
            "requested_root": str(context["requested"]) if context["requested"] is not None else None,
            "selected_root": str(context["selected"]), "resolved_root": str(context["root"]),
            "items": [{"kind": item["kind"], "name": item["name"], "status": item["status"],
                       "target": str(context["root"] / item["relative"]), "version": context["pack"]["version"]}
                      for item in context["items"]]}


def run(action: str, homes: list[tuple[str, Path]], requested: Path | None, *, api: Any,
        pack_id: str = PACK_ID) -> dict[str, Any]:
    context = prepare(homes, requested, api, pack_id=pack_id)
    result = payload(context)
    if action == "plan":
        return result
    if action == "verify":
        issues = [f"skill {item['name']}: {item['status']}" for item in context["items"]
                  if item["status"] != "in-sync"]
        result.update(status="failed" if issues else "ok", issues=issues)
        return result
    if action != "install":
        raise ValueError(f"Unknown business pack action: {action}")
    if pack_id in ("agent-lifecycle", "business-model") and any(item["status"] == "drift" for item in context["items"]):
        raise api.InstallError("Shared skill drift must be explicitly reconciled before installation; "
                               "preserve local changes and compare their source/version")

    def check(touched: list[dict[str, Any]]) -> None:
        validate(context, touched, api)

    def backup(root: Path) -> Path:
        # Called after acquiring the physical parent lock and validating preimages.
        # Create the target once and record its identity for later staging checks.
        root.mkdir(parents=True, exist_ok=True)
        for path, identity in list(context["identities"].items()):
            if identity[0] == root and identity[1] is None:
                context["identities"][path] = root_identity(path, api)
        context["physical_identity"] = root_identity(root, api)
        check([])
        return api.backup_root(root.parent)

    def rollback_allowed() -> bool:
        # A discovery alias may change while the original physical root remains ours.
        # A replacement of the physical directory itself belongs to the other writer.
        validate_storage(context, api)
        return root_identity(context["root"], api) == context["physical_identity"]

    label = "business-shared" if pack_id == PACK_ID else f"{pack_id}-shared"
    batch = api.apply_skills_plans([(label, context["root"], context["items"])],
                                  validate=check, lock_roots=[context["root"].parent], make_backup=backup,
                                  rollback_allowed=rollback_allowed)
    result.update(changes=batch[0]["changes"], backup=batch[0]["backup"])
    return result
