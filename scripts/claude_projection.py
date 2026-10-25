"""Build ordinary Claude skills and namespaced roles from the shared CAG source."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
FORMAT = 1
BEGIN = "<!-- BEGIN CAG Claude native adapter -->"
END = "<!-- END CAG Claude native adapter -->"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


installer = load("claude_shared_installer", ROOT / "scripts/install.py")
roles = load("claude_shared_roles", ROOT / "scripts/claude_agents_sync.py")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def hashes(files):
    return {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}


def read_tree(source):
    return {name: (source / name).read_bytes() for name in installer.manifest(source)}


def native_skill(text, name, home):
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise installer.InstallError("Ambiguous installed Claude adapter header")
        start, end = text.index(BEGIN), text.index(END) + len(END)
        text = text[:start] + text[end:].lstrip("\n")
    if name == "skill-creator":
        # Adapt the copied dependency itself, including executable examples;
        # a header alone must not leave a competing Codex output destination.
        text = text.replace("Codex", "Claude Code")
        text = text.replace('`$CODEX_HOME/skills`, or `~/.codex/skills` when `CODEX_HOME` is unset',
                            f'`{home / "skills"}`')
        text = text.replace('${CODEX_HOME:-$HOME/.codex}/skills', str(home / "skills"))
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise installer.InstallError(f"Invalid skill frontmatter: {name}")
    split = text.index("\n---\n", 4) + len("\n---\n")
    root = home / "skills" / name
    header = f"""{BEGIN}
## Claude Code native execution

Invoke this ordinary skill as `/{name}`. Its installed directory is `{root}`.
Resolve bundled `scripts/...` and references from this directory, even when the
project working directory is different. Commands belonging to the project keep
their project paths. No CAG plugin or Codex installation is required.

For this Claude profile, HARNESS_HOME is `{home}`. Use its sibling
`agent-graph-runtime`, not a Codex home. Codex-specific columns and tools in the
shared source describe the other provider; do not claim they exist here.

Before calling a CAG subagent, read `{home / 'agent-graph-runtime/claude-native.json'}`
and resolve its canonical role ID to the `cag-` agent_type. Keep canonical IDs in
existing graph artifacts, and record the actual Claude agent/model separately
in the ordinary evidence owner. Never present a Claude result as a Sol receipt.
Project state paths such as `.codex/task-delivery` are legacy CAG format names;
do not rename them or migrate active runs because the execution host changed.
{END}

"""
    body = text[split:].lstrip("\n").replace("/cag:", "/")
    body = body.replace("<HARNESS_HOME>", str(home)).replace("${CLAUDE_PLUGIN_ROOT}", str(home))
    if name == "skill-creator":
        header = header.replace(END, f"For a new personal skill, pass `--path {home / 'skills'}` to the bundled initializer unless the user requests another destination. Its generated OpenAI UI file is optional for Claude; do not require its generator. Claude uses SKILL.md frontmatter. Preserve generic structure, supporting resources, licensing and validation.\n" + END)
    return text[:split] + "\n" + header + body


def role_projection():
    generated = roles.render_all()
    policy = installer.routing.load_policy()
    files, aliases = {}, {}
    for role_id, spec in policy["roles"].items():
        name = roles.claude_name(role_id)
        native = "cag-" + name
        text = generated[name].replace(f"\nname: {name}\n", f"\nname: {native}\n", 1)
        files[native + ".md"] = text.encode()
        aliases[role_id] = {"agent_type": native, "plugin_agent_type": "cag:" + name, "model": spec["claude_model"], "effort": spec["claude_effort"]}
    return files, aliases


def build(home, *, names=None, creator_source=None):
    home = Path(home).expanduser().resolve()
    names = tuple(names or installer.SKILLS)
    unknown = set(names) - set(installer.SKILLS)
    if unknown:
        raise installer.InstallError(f"Not a maintained engineering skill: {sorted(unknown)}")
    units = {}
    for name in names:
        files = read_tree(ROOT / "skills" / name)
        files["SKILL.md"] = native_skill(files["SKILL.md"].decode(), name, home).encode()
        units["skills/" + name] = files
    if "agent-graph-builder" in names:
        creator = Path(creator_source).expanduser().resolve() if creator_source else home / "skills/skill-creator"
        if not (creator / "SKILL.md").is_file():
            raise installer.InstallError("Supply --skill-creator with a reviewed installed skill source; no implicit download")
        files = read_tree(creator)
        files["SKILL.md"] = native_skill(files["SKILL.md"].decode(), "skill-creator", home).encode()
        units["skills/skill-creator"] = files
    agent_files, aliases = role_projection()
    units["agents/cag"] = agent_files
    units["agent-graph-runtime"] = read_tree(ROOT / "agent-graph-runtime")
    record = {"format": FORMAT, "provider": "claude", "home": str(home), "roles": aliases, "owned": {name: hashes(files) for name, files in units.items()}}
    record["integrity"] = digest(record)
    units["agent-graph-runtime"]["claude-native.json"] = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode()
    return units, record
