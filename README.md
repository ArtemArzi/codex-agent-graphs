# Codex Agent Graphs

Canonical Git repository for three user-facing graph workflows, one graph-building meta-skill, one global recovery capability and one global discovery policy:

- `project-start`: project foundation plus an operational documentation-maintenance route.
- `research`: adaptive native research with a fast default and conditional deep/multi-agent verification.
- `task-delivery`: staged implementation and verification.
- `agent-graph-builder`: creates and validates new graph-backed skills against the shared model-first contract, layered on the system `skill-creator`.
- `development-recovery`: non-graph recovery when implementation evidence diverges from an accepted specification or plan.
- `large-codebase-discovery`: a managed global `AGENTS.md` policy that delegates bounded repository research and joins all required evidence before a plan or specification.

The three operational graph skills remain independent. `agent-graph-builder` is a non-runtime meta-skill: it invokes the system `$skill-creator` for generic skill scaffolding, then adds the common graph contract, controller boundaries and tests. `development-recovery` is a small implicitly invokable skill activated by a managed global `AGENTS.md` invariant; it has no `graph.json`, graph state or custom agents. Large-codebase discovery deliberately adds no skill: it reuses Codex's generic `explorer`/`researcher`, Task Delivery's explorers and `$research`, then enforces a join before planning. Internal graph roles live under `agents/` and do not become additional skills.

## Why a skill plus code

The skill is the Codex-native entry point and carries the operating instructions. The Python runner stores only durable graph state, enforces transitions and budgets, hashes artifacts, and makes runs resumable. Codex performs the semantic work with native skills, tools and optional subagents; the runner does not call a model API directly.

Research v2 uses three durable states: `work -> optional verify -> complete`. Planning, capability selection, search, evidence capture, reconciliation and drafting stay inside one native root-agent work loop. Fast mode uses no internal agents. MCP discovery and relevant MCP use are required inside `work`; Exa, Deep Research and domain skills, planner, scouts, synthesizer and verifier remain conditional capabilities rather than mandatory stages.

Project Start v3 follows the same model-first shape for both bootstrap and documentation maintenance: `work -> optional verify -> complete`. One root agent owns research and documentation edits; up to two read-only explorers and one independent verifier are conditional. Deterministic code keeps path safety, exact document deltas, decisions, retries, receipts, state compatibility and SHA-256 integrity.

All three graphs use one MCP-first policy without adding a node: discover the current MCP surface, call the provider-specific server or Context7/research/service MCP that fits the question, then use native web/browser and finally `curl` only as fallbacks. Every new work receipt records `mcp:<server>` or an explicit `mcp:fallback:<reason>`.

New graph-backed skills should be created through `agent-graph-builder`. Its validator enforces the shared `work → optional verify → complete` topology, bounded retries, MCP receipts, environment-selected agent roles, controller/test presence and the separation between model judgment and deterministic state. Existing Project Start, Research and Task Delivery all pass this contract.

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

The installer copies files instead of creating cross-filesystem symlinks. It also installs bounded development-recovery and large-codebase-discovery blocks into each environment's global `AGENTS.md`. Existing skills, configuration and global instructions are backed up before replacement; unrelated `AGENTS.md` content is preserved.

Codex loads skills, global instructions and custom-agent configuration at session start. Open a new CLI session or a new Desktop task after installation. The Project Start verifier and four Research roles are available conditionally; the Project Start auditor and curator remain installed only so active v2 runs can finish.

## Project Start routes

`skills/project-start/graph.json` is the versioned contract for one user-facing graph with two modes:

- `bootstrap`: one native work loop normalizes the documentation map, domain context, business, foundation, codebase, quality, plan, skill contract and agent context, then hands implementation to Task Delivery;
- `maintenance`: one native work loop classifies the exact documentation delta as no-change, factual or semantic and updates only what is needed.

Bootstrap applies `setup-matt-pocock-skills`, `domain-modeling` and `codebase-design` inside the same work loop; maintenance selects them only for the changed documentation layer. Native Codex remains the orchestrator. Sandcastle may be selected as later execution infrastructure, but it is not nested as a second graph owner.

Task Delivery completion creates a durable `maintenance-required` obligation, so the next task cannot begin until Project Start returns to `operational` or requests a real semantic decision. Root and nested `AGENTS.md` files are canonical maintenance inputs. Stable modules may receive inherited local context maps; hooks may only trigger an audit, never author or approve those instructions. Active v2 maintenance runs use the frozen legacy graph; every new run uses `scripts/project_graph.py`.

## Validate

```bash
python3 scripts/check_all.py
```

Format and configuration references: [Codex skills](https://learn.chatgpt.com/docs/customization/overview#skills) and [Codex `config.toml`](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).
