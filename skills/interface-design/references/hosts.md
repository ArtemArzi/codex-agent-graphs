# Host adapters

The method and bundled relative resources are shared by Codex and Claude Code.
Resolve `scripts/...` and `references/...` against this skill's installed directory,
even when the current working directory is a project elsewhere.

| Host/channel | Entry | Discovery and execution |
|---|---|---|
| Codex | `$interface-design`, `$interface-performance` | Current enabled skill catalog and effective Codex configuration |
| Claude native | `/interface-design`, `/interface-performance` | Personal `<claude-home>/skills`, current Claude catalog and permissions |
| Claude cag plugin | `/cag:interface-design`, `/cag:interface-performance` | Enabled cag plugin's skill catalog and plugin permissions |

Choose native or plugin delivery for this pack. The native installer checks its
known native roots, not all plugin caches; it does not automatically detect a
second copy provided by an enabled plugin. Do not install/enable both copies.
Do not disable a whole plugin just to resolve a duplicate without authorization.

Optional capability names in dependencies.json express roles, not universal
commands. Find the enabled equivalent in the current host catalog. Plugin names
may differ between hosts. Missing capabilities use the bundled methods and native
project tools where sufficient; preserve the exact missing check when they are
not. Never invent an OpenAI tool or Codex subagent in Claude, or the reverse.
Provider role/model selection belongs to the active host policy. This pack has
no mandatory subagents, graph runtime, paid API or controller dependency.

`scripts/capabilities.py` is an optional **Codex** snapshot checker. Its TOML
`--config` inputs are Codex configuration, not Claude settings. It does not inspect
Claude JSON, plugin caches or runtime tools, and its output is not Claude
activation evidence. In Claude, use the supplied current catalog and effective
Claude settings/permissions directly. File presence alone never proves activation.

The native UX pack uses the shared CAG installer transaction but owns only its
two skill directories. It does not join the engineering `claude-native.json`
ownership record, change native roles/runtime, or edit settings, credentials,
models, MCP configuration, AGENTS.md or CLAUDE.md. Keep installed private edits;
on drift compare source and local copies before a separately authorized update.
