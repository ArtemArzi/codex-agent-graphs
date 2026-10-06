---
name: agentic-engineering
description: Operate as an agentic engineer using eval-first execution, decomposition, and cost-aware model routing.
metadata:
  origin: ECC
---

# Agentic Engineering

Use this skill for engineering workflows where AI agents perform most implementation work and humans enforce quality and risk controls.

## Operating Principles

1. Define completion criteria before execution.
2. Decompose work into agent-sized units.
3. Route model tiers by task complexity.
4. Measure with evals and regression checks.

## Eval-First Loop

1. Define capability eval and regression eval.
2. Run baseline and capture failure signatures.
3. Execute implementation.
4. Re-run evals and compare deltas.

## Task Decomposition

Prefer small independently verifiable units when decomposition helps; fifteen minutes is a sizing hint, not a delegation requirement:
- each unit should be independently verifiable
- each unit should have a single dominant risk
- each unit should expose a clear done condition

## Model Routing

Use the host's configured roles and preserve the user's manual root effort.
Default to root execution. Simple engineering gets its configured bounded
result review; whole-plan/result acceptance is reserved for complex engineering
or material risk. Do not select vendors, upgrade models or spawn agents from
this skill's examples. Delegate only when an independent block repays handoff.

## Session Strategy

- Continue session for closely-coupled units.
- Keep the current session and valid acceptance across phase transitions. Start a new session only when requested or necessary, with a durable handoff.
- Compact after milestone completion, not during active debugging.

## Review Focus for AI-Generated Code

Prioritize:
- invariants and edge cases
- error boundaries
- security and auth assumptions
- hidden coupling and rollout risk

Do not waste review cycles on style-only disagreements when automated format/lint already enforce style.

## Cost Discipline

Track per task:
- model
- token estimate
- retries
- wall-clock time
- success/failure

Resolve failed assumptions with new evidence. A failure does not authorize a model change; use configured host escalation rules.
