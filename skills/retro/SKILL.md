---
name: retro
description: Review a specific coding session or recurring environment, tool, or navigation failure and propose evidence-backed improvements without applying them.
---

Conduct a bounded, read-only retrospective. Use this skill when the user requests one or when real repeated environment, tool, or navigation failures justify examining the cause. A routine successful session, one transient error, or a large instructions file alone does not warrant a retrospective.

## Scope and sources

Use the specified session or problem; otherwise use the current conversation and its observed failures. Identify the affected task, repeated symptom, available evidence, and first unsupported assumption. Read only relevant logs, commands, project guidance, and configuration. If evidence is missing, report the limit; do not search unrelated sessions, secrets, or the entire machine to fill it.

Compare the failure with existing mechanisms before proposing changes. Inspect the project's current check commands and CI configuration when an automated check is relevant. A check that already exists but is unwired or failing is a different finding from a missing check. Separate a demonstrated cause from a hypothesis, and prefer the smallest improvement that addresses the actual failure.

## Improvement candidates

Choose only categories supported by the observed session:

- **Navigation:** a precise pointer for information that was repeatedly difficult to locate, or clarification of a hidden dependency. Link the existing owner instead of duplicating its contents.
- **Automated checks:** a deterministic check for a reproduced mechanical mistake. Use the existing language and check system; compare lint, typing, tests, hooks, and CI according to the actual gap. Absence of a hook alone does not establish a problem.
- **Coding standards:** clarify a judgment-based rule when the session shows ambiguity or a missed requirement. Mechanical patterns may be better enforced by an existing linter; cost and false positives still matter.
- **Instruction placement:** remove or relocate demonstrated stale or conflicting guidance while preserving essential constraints and examples. Instruction length alone is not evidence of irrelevance.
- **Tool economy:** reduce repeated high-cost calls or unnecessary output without losing diagnostic evidence.
- **Information access:** propose a scoped source such as development logs or read-only service access when unavailable evidence caused the failure. Availability and authorization remain separate questions.

For proposed agent-facing wording, consult an available `writing-for-agents` skill through native Codex discovery when its guidance helps. Do not call a Claude `Skill` tool or install dependencies as part of this review.

## Result and boundaries

Return a short prioritized set of findings, each connecting the observed symptom, source evidence (file, symbol, command, or log excerpt), likely cause and confidence, proposed change, and how to verify it. Report no supported findings when that is what the evidence establishes. Use the user's language and the existing owning report or handoff when one exists.

Recommendations do not authorize implementation. This retrospective does not mutate global instructions, skills, memory, configuration, access controls, hooks, or CI. Carry out any later implementation only within separately established authorization and the host's review policy. Do not assume every task uses separate implementation and review agents; required reviews follow the host policy, and implementation still needs relevant standards.
