# Codex Agent Graphs

Canonical Git repository for three user-facing Codex workflows:

- `project-start`: project foundation plus an operational documentation-maintenance route.
- `research`: adaptive native research with a fast default and conditional deep/multi-agent verification.
- `task-delivery`: staged implementation and verification.

The user sees three skills. Internal graph roles live under `agents/` and do not become additional skills.

## Why a skill plus code

The skill is the Codex-native entry point and carries the operating instructions. The Python runner stores only durable graph state, enforces transitions and budgets, hashes artifacts, and makes runs resumable. Codex performs the semantic work with native skills, tools and optional subagents; the runner does not call a model API directly.

Research v2 uses three durable states: `work -> optional verify -> complete`. Planning, capability selection, search, evidence capture, reconciliation and drafting stay inside one native root-agent work loop. Fast mode uses no internal agents. Exa, Deep Research and domain skills are loaded only when relevant; planner, scouts, synthesizer and verifier are conditional capabilities rather than mandatory stages.

Project Start v3 follows the same model-first shape for both bootstrap and documentation maintenance: `work -> optional verify -> complete`. One root agent owns research and documentation edits; up to two read-only explorers and one independent verifier are conditional. Deterministic code keeps path safety, exact document deltas, decisions, retries, receipts, state compatibility and SHA-256 integrity.

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

Codex loads custom-agent configuration at session start. Open a new CLI session or a new Desktop task after installation. The Project Start verifier and four Research roles are available conditionally; the Project Start auditor and curator remain installed only so active v2 runs can finish.

## Project Start routes

`skills/project-start/graph.json` is the versioned contract for one user-facing graph with two modes:

- `bootstrap`: one native work loop prepares business, foundation, quality, plan and agent context, then hands implementation to Task Delivery;
- `maintenance`: one native work loop classifies the exact documentation delta as no-change, factual or semantic and updates only what is needed.

Installed Matt-style and domain skills remain available through the capability registry but are selected by the root model only when relevant. Native Codex remains the orchestrator. Sandcastle may be selected as later execution infrastructure, but it is not nested as a second graph owner.

Task Delivery completion creates a durable `maintenance-required` obligation, so the next task cannot begin until Project Start returns to `operational` or requests a real semantic decision. Root and nested `AGENTS.md` files are canonical maintenance inputs. Stable modules may receive inherited local context maps; hooks may only trigger an audit, never author or approve those instructions. Active v2 maintenance runs use the frozen legacy graph; every new run uses `scripts/project_graph.py`.

## Validate

```bash
python3 scripts/check_all.py
```

Format and configuration references: [Codex skills](https://learn.chatgpt.com/docs/customization/overview#skills) and [Codex `config.toml`](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).
