---
name: dev-policies
description: >-
  Load the repository-wide development policies (development recovery,
  large-codebase discovery) on demand. Use when planning recovery from
  spec/plan/implementation divergence or when exploring a large codebase,
  and whenever a graph skill references the global policies. Under Codex
  these policies are injected into ~/.codex/AGENTS.md by install.py; under
  the Claude Code plugin this skill is the delivery path.
---

# Dev Policies

Host invocation: `$dev-policies` in Codex, `/cag:dev-policies` in Claude Code.

Read the policy files and apply them to the current task. They live next to
this skill in the repository/plugin tree:

- `../../policies/development-recovery.md` — when spec, plan and
  implementation have diverged: how to localize evidence and recover without
  ceremony.
- `../../policies/large-codebase-discovery.md` — how to explore a large
  repository without flooding context: budgets, sampling, when to fan out
  read-only explorers.

Resolve the paths relative to this SKILL.md (under the Claude Code plugin the
skill root is `${CLAUDE_PLUGIN_ROOT}/skills/dev-policies`). Read both files
completely before advising; quote the applicable rule rather than
paraphrasing from memory. These policies are canonical repository content —
never edit them as part of applying them.
