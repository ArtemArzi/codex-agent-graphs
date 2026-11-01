from __future__ import annotations

import json
import asyncio
import os
import re
import shutil
import tempfile
import tomllib
from pathlib import Path

from portable_bundle import KitError, metadata, relative, read_file, SECRET


def catalog_entries(catalog):
    data = catalog
    if "skills" in data and isinstance(data["skills"], dict):
        data = data["skills"]
    data = data.get("result", data)
    groups = data.get("data", [])
    if not groups:
        raise KitError("Native catalog has no cwd groups")
    selected = {}
    errors = []
    for group in groups:
        errors.extend(group.get("errors", []))
        for skill in group.get("skills", []):
            if skill.get("enabled"):
                path = Path(skill["path"]).resolve(strict=True)
                selected[(skill["name"], str(path))] = {**skill, "path": str(path)}
    if errors:
        raise KitError("Native catalog reported discovery errors")
    return list(selected.values())


def profile_from_catalog(catalog_path, output, repo, knowledge_path=None, knowledge_policy=None):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise KitError("Source profile output already exists")
    catalog = catalog_path if isinstance(catalog_path, dict) else json.loads(read_file(Path(catalog_path)))
    entries = catalog_entries(catalog)
    profile = {"schema_version": 1, "skills": [], "skill_roots": [{"path": str(Path(repo).resolve() / "skills")}],
               "support": [], "support_files": [], "knowledge": [], "requirements": [{"name": "python", "minimum": "3.12"}],
               "host_capabilities": [], "include_native_skill_creator": True}
    namespaces = {}
    portable_names = {}
    groups = catalog.get("result", catalog).get("data", [])
    profile["exclude_names"] = sorted({metadata(Path(s["path"])) for group in groups for s in group.get("skills", [])
                                        if s.get("enabled") is False and not s.get("pluginId")
                                        and Path(s["path"]).is_file()})
    home = Path(catalog["home"]) if catalog.get("home") else None
    if home:
        if (home / "AGENTS.md").is_file():
            profile["instructions"] = str(home / "AGENTS.md")
        if (home / "config.toml").is_file():
            config = tomllib.loads(read_file((home / "config.toml").resolve(strict=True)).decode())
            profile["settings"] = {key: config[key] for key in ("model", "model_reasoning_effort") if key in config}
    for entry in entries:
        path = Path(entry["path"])
        original = metadata(path)
        plugin = entry.get("pluginId")
        native = entry["name"]
        if not plugin and (Path(repo) / "skills" / original / "SKILL.md").is_file():
            continue
        name = re.sub(r"[^a-z0-9-]+", "-", native.lower()).strip("-")
        name = re.sub("-+", "-", name)
        if name in portable_names and portable_names[name] != str(path):
            raise KitError(f"Native names collide after portable projection: {name}")
        portable_names[name] = str(path)
        destination = name
        if plugin and "skills" in path.parts:
            source_root = next((parent for parent in path.parents if parent.name == "skills"), None)
            if source_root is not None:
                namespace = re.sub(r"[^a-z0-9-]+", "-", plugin.lower()).strip("-")
                destination = "plugins/" + namespace + "/skills/" + path.parent.relative_to(source_root).as_posix()
                namespaces[namespace] = source_root.parent
        relative(destination)
        profile["skills"].append({"name": name, "path": str(path), "destination": destination,
                                  "origin": native + ("@" + plugin if plugin else "")})
        if plugin and any(word in plugin for word in ("primary-runtime", "bundled", "codex-security")):
            profile["host_capabilities"].append({"skill": name, "provider": plugin,
                                                 "status": "requires-host-capability", "automatic_install": False})
    for namespace, root in sorted(namespaces.items()):
        for name in ("scripts", "references", "assets", "rules"):
            if (root / name).is_dir():
                profile["support"].append({"path": str(root / name), "destination": "skills/plugins/" + namespace + "/" + name})
        for name in ("LICENSE", "LICENSE.md", "NOTICE", "package.json", "package-lock.json", "pyproject.toml", "uv.lock"):
            if (root / name).is_file():
                profile["support_files"].append({"path": str(root / name), "destination": "skills/plugins/" + namespace + "/" + name})
    if knowledge_path:
        root = Path(knowledge_path).resolve(strict=True)
        if knowledge_policy:
            policy = json.loads(Path(knowledge_policy).read_text())
            parent = Path(knowledge_policy).resolve().parents[1]
            files = []
            for value in policy["files"]:
                source = (parent / relative(value)).resolve()
                if source.is_file() and source.is_relative_to(root):
                    files.append(source.relative_to(root).as_posix())
            if not files:
                raise KitError("No selected knowledge files")
            profile["knowledge"].append({"name": "work", "path": str(root), "files": files})
        else:
            profile["knowledge"].append({"name": "selected", "path": str(root)})
    output.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(profile, ensure_ascii=False, indent=2) + "\n").encode()
    if SECRET.search(data):
        raise KitError("Source profile contains a secret-like value")
    with output.open("xb") as stream:
        stream.write(data)
    output.chmod(0o600)
    return {"status": "profile-created", "profile": str(output), "native_selected": len(entries),
            "additional_skills": len(profile["skills"]), "canonical_new_skills": "automatic",
            "namespace_projection": "plugin names become unique hyphenated user skills", "mcp": "deferred"}


async def native_catalog(home, cwd, executable=None):
    home = Path(home).resolve(strict=True)
    cwd = Path(cwd).resolve(strict=True)
    executable = str(executable or shutil.which("codex") or "")
    if not executable:
        raise KitError("Codex executable unavailable; supply --codex")
    config_path = home / "config.toml"
    config_source = config_path.resolve() if config_path.is_file() else None
    config_bytes = read_file(config_source) if config_source else None
    config = tomllib.loads(config_bytes.decode()) if config_bytes else {}
    argv = [executable, "app-server", "--stdio", "-c", "features.apps=false", "-c", "features.hooks=false",
            "-c", "analytics.enabled=false"]
    for name in config.get("mcp_servers", {}):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise KitError("Unsupported MCP identifier; native capture refused")
        argv.extend(["-c", f"mcp_servers.{name}.enabled=false"])
    environment = {key: value for key, value in os.environ.items()
                   if not any(word in key.upper() for word in ("TOKEN", "SECRET", "API_KEY", "CODEX_", "OPENAI_", "PROXY"))}
    with tempfile.TemporaryDirectory(prefix="portable-catalog-") as scratch:
        environment.update(CODEX_HOME=str(home), CODEX_SQLITE_HOME=scratch, RUST_LOG="off")
        process = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE,
                                                      stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                                                      env=environment, limit=16 * 1024 * 1024)
        async def request(message, expected):
            process.stdin.write((json.dumps(message) + "\n").encode())
            await process.stdin.drain()
            while True:
                line = await process.stdout.readline()
                if not line:
                    raise KitError("Native catalog process ended before response")
                value = json.loads(line)
                if value.get("id") == expected:
                    if "error" in value:
                        raise KitError("Native catalog request failed")
                    return value
        try:
            async with asyncio.timeout(90):
                await request({"id": 1, "method": "initialize", "params": {
                    "clientInfo": {"name": "portable-kit", "version": "1"}, "capabilities": {}}}, 1)
                process.stdin.write(b'{"method":"initialized","params":{}}\n')
                await process.stdin.drain()
                response = await request({"id": 2, "method": "skills/list", "params": {"cwds": [str(cwd)]}}, 2)
                catalog_entries(response)
                return {"home": str(home), "result": response["result"]}
        except TimeoutError as exc:
            raise KitError("Native catalog timed out; no model or MCP calls were requested") from exc
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 5)
                except TimeoutError:
                    process.kill()
                    await process.wait()
            after_source = config_path.resolve() if config_path.is_file() else None
            after = read_file(after_source) if after_source else None
            if after != config_bytes or after_source != config_source:
                raise KitError("Host configuration changed during capture; inspect before continuing")


def capture(home, cwd, output, repo, knowledge_path=None, knowledge_policy=None, executable=None):
    catalog = asyncio.run(native_catalog(home, cwd, executable))
    return profile_from_catalog(catalog, output, repo, knowledge_path, knowledge_policy)
