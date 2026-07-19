# Codex Agent Graphs

Canonical Git repository for three user-facing Codex workflows:

- `project-start`: project foundation and durable documentation.
- `research`: autonomous, evidence-backed research graph.
- `task-delivery`: staged implementation and verification.

The user sees three skills. Internal graph roles live under `agents/` and do not become additional skills.

## Why a skill plus code

The skill is the Codex-native entry point and carries the operating instructions. The Python runner stores graph state, enforces transitions and retry bounds, hashes artifacts, and makes runs resumable. Codex performs the semantic work with native tools and subagents; the runner does not call a model API directly.

## Install

Preview changes:

```bash
python3 scripts/install.py plan
```

Install identical copies into WSL CLI and Desktop, including graph-only custom agents:

```bash
python3 scripts/install.py install --all
python3 scripts/install.py verify --all
```

The installer copies files instead of creating cross-filesystem symlinks. Existing installations and config files are backed up before replacement.

Codex loads custom-agent configuration at session start. Open a new CLI session or a new Desktop task after installation so the four Research roles appear in the agent-type schema.

## Validate

```bash
python3 scripts/check_all.py
```

Format and configuration references: [Codex skills](https://learn.chatgpt.com/docs/customization/overview#skills) and [Codex `config.toml`](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).
