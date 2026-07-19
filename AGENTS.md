# Agent Graphs Repository

This repository is the canonical source for the user's global Codex graph-skills.

- Keep `skills/project-start` and `skills/task-delivery` backward compatible unless a migration is explicitly planned.
- Treat `skills/research/graph.json` as a versioned execution contract.
- Keep graph execution deterministic: agents do judgment work; scripts own state transitions, receipts, bounds, and integrity checks.
- Use only Python standard-library dependencies in install and graph runtime scripts.
- Never silently overwrite installed skill drift. Back up first, then verify hashes.
- Support both WSL CLI and Codex Desktop skill roots.
- Subagents are leaf workers. Graph orchestration stays in the root agent.

Before committing, run `python3 scripts/check_all.py`.
