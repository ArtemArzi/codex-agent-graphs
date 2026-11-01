from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath


class KitError(RuntimeError):
    pass


CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git", "node_modules", ".venv", "venv"}
BOOTSTRAP = ("portable_kit.py", "portable_bundle.py", "portable_install.py", "portable_sources.py")
MAX_BYTES = 512 * 1024 * 1024
SECRET = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
FORBIDDEN = {"auth.json", "credentials.json", "id_rsa", "id_ed25519", "cookies.json", "cookies.sqlite", ".env"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bundle_id(lock):
    return digest(canonical({k: v for k, v in lock.items() if k != "id"}))


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise KitError("Invalid relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise KitError("Unsafe relative path")
    return Path(*path.parts)


def read_file(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
            raise KitError(f"Unsafe selected file: {path.name}")
        data = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise KitError("Selected file changed while reading")
        return data


def read_relative(root, name):
    parts = relative(name).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return read_file(Path(f"/proc/self/fd/{fd}") / parts[-1])
    finally:
        os.close(fd)


def validate_input_file(path, data):
    path = Path(path)
    if path.name in FORBIDDEN or path.name.startswith(".env.") or path.suffix.lower() in {".pem", ".key", ".sqlite", ".db"}:
        raise KitError(f"Private state file in selected input: {path.name}")
    if SECRET.search(data):
        raise KitError(f"Secret-bearing selected input: {path.name}")


def manifest_files(root, skip_caches=True):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise KitError(f"Not a regular directory: {root}")
    result = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not skip_caches or d not in CACHES)
        for name in dirs + sorted(n for n in names if not skip_caches or n not in CACHES):
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise KitError(f"Symlink inside selected input: {path}")
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise KitError(f"Special or linked input: {path}")
            result[path.relative_to(root).as_posix()] = {
                "sha256": digest(read_relative(root, path.relative_to(root).as_posix())), "bytes": info.st_size,
                "mode": 0o755 if info.st_mode & 0o111 else 0o644,
            }
    if sum(v["bytes"] for v in result.values()) > MAX_BYTES or len(result) > 50000:
        raise KitError("Selected input exceeds bundle budget")
    return result


def checked_files(value):
    if not isinstance(value, dict):
        raise KitError("Invalid file manifest")
    for name, entry in value.items():
        relative(name)
        if (not isinstance(entry, dict) or set(entry) != {"sha256", "bytes", "mode"}
                or not re.fullmatch("[0-9a-f]{64}", str(entry["sha256"]))
                or type(entry["bytes"]) is not int or entry["bytes"] < 0
                or entry["mode"] not in (0o644, 0o755)):
            raise KitError("Invalid file identity")
    if sum(v["bytes"] for v in value.values()) > MAX_BYTES or len(value) > 50000:
        raise KitError("Bundle exceeds budget")


def verify_bundle(bundle):
    bundle = Path(bundle)
    if bundle.is_symlink() or (bundle / "manifest.json").is_symlink():
        raise KitError("Bundle links are not accepted")
    try:
        lock = json.loads((bundle / "manifest.json").read_text())
    except (OSError, ValueError) as exc:
        raise KitError("Cannot read bundle manifest") from exc
    if (not isinstance(lock, dict) or lock.get("schema_version") != 1
            or lock.get("id") != bundle_id(lock)):
        raise KitError("Bundle identity mismatch")
    checked_files(lock.get("files"))
    checked_files(lock.get("bootstrap"))
    if set(lock["bootstrap"]) != set(BOOTSTRAP):
        raise KitError("Incomplete bootstrap")
    if manifest_files(bundle / "payload", skip_caches=False) != lock["files"]:
        raise KitError("Bundle payload mismatch")
    allowed_dirs = {"skills", "agents", "agent-graph-runtime", "knowledge"}
    for name in lock["files"]:
        allowed_dirs.update(p.as_posix() for p in relative(name).parents if p != Path("."))
    if any(p.is_dir() and p.relative_to(bundle / "payload").as_posix() not in allowed_dirs
           for p in (bundle / "payload").rglob("*")):
        raise KitError("Undeclared bundle directory")
    for name, entry in lock["bootstrap"].items():
        path = bundle / relative(name)
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise KitError("Unsafe bootstrap")
        actual = {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size,
                  "mode": 0o755 if path.stat().st_mode & 0o111 else 0o644}
        if actual != entry:
            raise KitError("Bootstrap mismatch")
    if {p.name for p in bundle.iterdir()} != {"manifest.json", "payload", *BOOTSTRAP}:
        raise KitError("Undeclared bundle content")
    for name in ("skills", "agents", "agent-graph-runtime", "knowledge"):
        if (bundle / "payload" / name).is_symlink() or not (bundle / "payload" / name).is_dir():
            raise KitError(f"Missing payload directory: {name}")
    for name in ("AGENTS.md", "config.toml"):
        if name not in lock["files"]:
            raise KitError(f"Missing managed file: {name}")
    return lock


def selected_path(value, base):
    if not isinstance(value, str) or not value:
        raise KitError("Missing selected input path")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve(strict=True)


def metadata(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        text = text.replace("\r\n", "\n")
    front = text.split("\n---", 1)[0]
    match = re.search(r"(?m)^name:\s*['\"]?([^\n'\"]+)", front)
    if not match:
        raise KitError(f"Skill has no declared name: {path}")
    return match.group(1).strip()


def skill_sources(profile, base):
    items = list(profile.get("skills", []))
    excluded = set(profile.get("exclude_names", []))
    for root in profile.get("skill_roots", []):
        directory = selected_path(root["path"], base)
        for path in sorted(directory.glob("*/SKILL.md")):
            if metadata(path) not in excluded:
                items.append({"path": str(path), "name": metadata(path)})
    selected = {}
    for item in items:
        path = selected_path(item["path"], base)
        if path.name != "SKILL.md" or not path.is_file():
            raise KitError("Selected skill must be a SKILL.md")
        name = item.get("name") or metadata(path)
        if name in excluded:
            continue
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise KitError(f"Invalid portable skill name: {name}")
        destination = item.get("destination", name)
        relative(destination)
        signature = manifest_files(path.parent)
        if name in selected:
            old = selected[name]
            if old["signature"] != signature:
                preference = profile.get("prefer", {}).get(name)
                if not preference:
                    raise KitError(f"Conflicting skill resources: {name}")
                wanted = selected_path(preference, base)
                if wanted not in (path, old["path"]):
                    raise KitError(f"Invalid skill preference: {name}")
                if wanted == old["path"]:
                    continue
            else:
                continue
        selected[name] = {"path": path, "name": name, "destination": destination,
                          "signature": signature, "original_name": metadata(path),
                          "origin": item.get("origin", "explicit-source")}
    destinations = [i["destination"] for i in selected.values()]
    if len(set(destinations)) != len(destinations):
        raise KitError("Conflicting destination paths")
    for a in destinations:
        for b in destinations:
            if a != b and relative(a) in relative(b).parents:
                raise KitError("Nested skill destinations conflict")
    return selected


def dependency_target(target, selected):
    if not isinstance(target, str) or not re.fullmatch(r"[a-z0-9]+(?:[-:][a-z0-9]+)*", target):
        raise KitError("Invalid skill dependency name")
    if target in selected:
        return target
    matches = [name for name, item in selected.items()
               if item["original_name"] == target or item["origin"].split("@", 1)[0] == target]
    if len(matches) > 1:
        raise KitError(f"Ambiguous skill dependency: {target}")
    return matches[0] if matches else None


def dependencies(selected):
    edges = []
    for name, item in selected.items():
        path = item["path"].parent / "skill-dependencies.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for kind in ("required_skills", "optional_skills"):
            for dep in data.get(kind, []):
                target = dep["name"]
                resolved = dependency_target(target, selected)
                present = resolved is not None
                edges.append({"skill": name, "dependency": target, "resolved": resolved,
                              "required": kind == "required_skills", "present": present})
                if kind == "required_skills" and not present:
                    raise KitError(f"Missing required skill: {name} -> {target}")
    return edges


def complete_dependencies(selected, roots):
    while True:
        missing = set()
        for item in selected.values():
            path = item["path"].parent / "skill-dependencies.json"
            if path.is_file():
                missing.update(d["name"] for d in json.loads(path.read_text()).get("required_skills", [])
                               if dependency_target(d["name"], selected) is None)
        if not missing:
            return selected
        for name in sorted(missing):
            matches = [root / name / "SKILL.md" for root in roots if (root / name / "SKILL.md").is_file()]
            if not matches:
                raise KitError(f"Missing required skill: {name}")
            signatures = [manifest_files(p.parent) for p in matches]
            if any(s != signatures[0] for s in signatures[1:]):
                raise KitError(f"Conflicting required skill: {name}")
            path = matches[0].resolve()
            selected[name] = {"path": path, "name": name, "destination": name,
                              "signature": signatures[0], "original_name": metadata(path), "origin": "required-dependency"}


def copy_selected(source, target, selection=None):
    source = source.resolve(strict=True)
    entries = manifest_files(source)
    if selection is not None:
        entries = {key: entries[key] for key in selection}
    for name, entry in entries.items():
        src = source / relative(name)
        data = read_relative(source, name)
        validate_input_file(src, data)
        if digest(data) != entry["sha256"]:
            raise KitError(f"Changed or secret-bearing selected input: {name}")
        dst = target / relative(name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and (not dst.is_file() or dst.read_bytes() != data):
            raise KitError(f"Conflicting bundle component: {name}")
        dst.write_bytes(data)
        dst.chmod(entry["mode"])
    if selection is None and manifest_files(source) != entries:
        raise KitError("Source changed during copy")
    for name, entry in entries.items():
        src = source / relative(name)
        if digest(read_relative(source, name)) != entry["sha256"]:
            raise KitError(f"Source changed during snapshot: {name}")
    return entries


def canonical_standard(repo, payload, instructions="", settings=None):
    spec = importlib.util.spec_from_file_location("portable_standard_installer", repo / "scripts/install.py")
    if spec is None or spec.loader is None:
        raise KitError("Cannot load canonical standards")
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    for role, description in installer.role_descriptions().items():
        (payload / "agents" / f"{role}.toml").write_text(installer.routing.render_agent(role, description))
    settings = settings or {}
    if set(settings) - {"model", "model_reasoning_effort"} or any(not isinstance(v, str) for v in settings.values()):
        raise KitError("Only model and reasoning effort may be imported from host settings")
    config = "".join(f"{key} = {json.dumps(value)}\n" for key, value in settings.items())
    (payload / "config.toml").write_text(installer.config_with_block(config))
    (payload / "AGENTS.md").write_text(installer.agents_with_policy(instructions))


def audit_paths(payload):
    found = []
    pattern = re.compile(r"(?:/home/[A-Za-z0-9_.-]+|/mnt/[a-z]/Users/[A-Za-z0-9_.-]+)[^\s\"'`<>)]*")
    for path in sorted(payload.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".sh"}:
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                for value in pattern.findall(line):
                    found.append({"file": path.relative_to(payload).as_posix(), "line": number, "path": value})
    return found


def build(profile_path, output, repo):
    profile_path = Path(profile_path).resolve(strict=True)
    repo = Path(repo).resolve(strict=True)
    output = Path(output).absolute()
    output = output.parent.resolve(strict=True) / output.name
    if output.exists() or output.is_symlink():
        raise KitError("Build output already exists")
    profile = json.loads(profile_path.read_text())
    profile_digest = digest(read_file(profile_path))
    if profile.get("schema_version") != 1:
        raise KitError("Unsupported source profile")
    selected = skill_sources(profile, profile_path.parent)
    roots = [selected_path(p, profile_path.parent) for p in profile.get("dependency_roots", [])]
    if profile.get("include_native_skill_creator"):
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        if (home / "skills/.system").is_dir():
            roots.append((home / "skills/.system").resolve())
    selected = complete_dependencies(selected, roots)
    if not selected:
        raise KitError("Empty skill selection")
    edges = dependencies(selected)
    runtime = selected_path(profile.get("runtime", str(repo / "agent-graph-runtime")), profile_path.parent)
    inputs = [repo, runtime, profile_path, *[i["path"].parent for i in selected.values()]]
    for tree in [*profile.get("support", []), *profile.get("support_files", []), *profile.get("knowledge", [])]:
        inputs.append(selected_path(tree["path"], profile_path.parent))
    instructions_path = selected_path(profile["instructions"], profile_path.parent) if profile.get("instructions") else None
    if instructions_path:
        inputs.append(instructions_path)
    for source in inputs:
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise KitError("Build output overlaps source")
    source_identity = {str(path): manifest_files(path) if path.is_dir() else digest(read_file(path)) for path in inputs}
    output.mkdir()
    try:
        payload = output / "payload"
        for name in ("skills", "agents", "agent-graph-runtime", "knowledge"):
            (payload / name).mkdir(parents=True)
        skills = []
        for name, item in sorted(selected.items()):
            target = payload / "skills" / relative(item["destination"])
            copy_selected(item["path"].parent, target)
            path = target / "SKILL.md"
            if name != item["original_name"]:
                text = path.read_text()
                path.write_text(re.sub(r"(?m)^name:.*$", "name: " + name, text, count=1))
            skills.append({"name": name, "original_name": item["original_name"], "destination": item["destination"],
                           "source": str(item["path"]), "origin": item["origin"], "source_files": item["signature"]})
        copy_selected(runtime, payload / "agent-graph-runtime")
        instructions = read_file(instructions_path).decode() if instructions_path else ""
        if instructions_path:
            validate_input_file(instructions_path, instructions.encode())
        canonical_standard(repo, payload, instructions, profile.get("settings"))
        for tree in profile.get("support", []):
            source = selected_path(tree["path"], profile_path.parent)
            copy_selected(source, payload / relative(tree["destination"]))
        for item in profile.get("support_files", []):
            source = selected_path(item["path"], profile_path.parent)
            target = payload / relative(item["destination"])
            data = read_file(source)
            validate_input_file(source, data)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
            target.chmod(0o644)
        for tree in profile.get("knowledge", []):
            source = selected_path(tree["path"], profile_path.parent)
            copy_selected(source, payload / "knowledge" / relative(tree["name"]), tree.get("files"))
        aliases = {}
        for name, item in selected.items():
            native = item["origin"].split("@", 1)[0]
            if ":" in native and native != name:
                aliases[native] = name
        for item in selected.values():
            path = payload / "skills" / relative(item["destination"]) / "SKILL.md"
            body = path.read_text()
            for native, projected in sorted(aliases.items(), key=lambda p: -len(p[0])):
                body = re.sub(r"(?<![\w:-])" + re.escape(native) + r"(?![\w:-])", projected, body)
            path.write_text(body)
        (payload / "knowledge" / "kit-invocations.json").write_text(json.dumps(aliases, ensure_ascii=False, indent=2) + "\n")
        bootstrap = {}
        for name in BOOTSTRAP:
            src = repo / "scripts" / name
            data = src.read_bytes()
            dst = output / name
            dst.write_bytes(data)
            dst.chmod(0o644)
            bootstrap[name] = {"sha256": digest(data), "bytes": len(data), "mode": 0o644}
        git = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
        lock = {"schema_version": 1, "files": manifest_files(payload), "bootstrap": bootstrap,
                "source_commit": git.stdout.strip() if git.returncode == 0 else None,
                "source_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
                "source_tree_sha256": digest(canonical(source_identity[str(repo)])),
                "skills": skills, "dependencies": edges, "external_paths": audit_paths(payload),
                "requirements": profile.get("requirements", []), "host_capabilities": profile.get("host_capabilities", []),
                "mcp": "deferred", "profile_sha256": profile_digest, "invocation_aliases": aliases,
                "dependency_files": [name for name in manifest_files(payload) if Path(name).name in
                                     {"package.json", "package-lock.json", "requirements.txt", "pyproject.toml", "uv.lock", "Cargo.toml"}]}
        for path in inputs:
            found = manifest_files(path) if path.is_dir() else digest(read_file(path))
            if found != source_identity[str(path)]:
                raise KitError(f"Source changed during build: {path}")
        if digest(read_file(profile_path)) != profile_digest:
            raise KitError("Source profile changed during build")
        lock["id"] = bundle_id(lock)
        (output / "manifest.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n")
        verify_bundle(output)
        return {"status": "built", "bundle": str(output), "id": lock["id"], "skills": len(skills),
                "bytes": sum(v["bytes"] for v in lock["files"].values()), "external_path_mentions": len(lock["external_paths"])}
    except BaseException:
        raise
