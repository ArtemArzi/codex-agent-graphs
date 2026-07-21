# Agent Graphs Repository

This repository is the canonical source for the user's global Codex workflows.

- Keep `skills/project-start` and `skills/task-delivery` backward compatible unless a migration is explicitly planned.
- Keep `skills/agent-graph-builder` as the shared non-runtime graph creation contract. It must layer on `$skill-creator`, validate all operational graphs and never become another user-work graph.
- Treat `skills/research/graph.json` as a versioned execution contract.
- Treat `skills/project-start/graph.json` as the shared bootstrap/maintenance execution contract; keep both routes compatible with state schema v2.
- Keep `skills/development-recovery` independent of every graph. Its managed global policy may trigger the skill, but it must not add graph nodes, mandatory agents or a runtime state machine.
- Keep large-codebase discovery as a compact managed global policy. Reuse native `explorer`/`researcher`, Task Delivery explorers and Research; do not add a duplicate skill, graph or custom role.
- Treat every root or nested `AGENTS.md` as canonical Project Start context; module files inherit the nearest parent and hooks may only trigger audits.
- Keep graph execution deterministic: agents do judgment work; scripts own state transitions, receipts, bounds, and integrity checks.
- Use only Python standard-library dependencies in install and graph runtime scripts.
- Never silently overwrite installed skill or global-policy drift. Back up first, then verify hashes.
- Support both WSL CLI and Codex Desktop skill roots.
- Subagents are leaf workers. Graph orchestration stays in the root agent.

Before committing, run `python3 scripts/check_all.py`.
