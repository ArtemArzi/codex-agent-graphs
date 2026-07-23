# Work efficiency contract

The graph is a control boundary around model judgment, not a checklist engine.
Every new or materially refactored graph declares `work_policy` in `graph.json`.

## Fast path

- Start root-only. A skill, MCP call, subagent or reviewer must close a concrete
  evidence gap; availability alone is not a reason to invoke it.
- Choose the cheapest execution tier that preserves the needed guarantee:
  `skill-only` for bounded one-session work, `tracked` for resumability or
  durable evidence, and `verified` only for material risk or uncertainty.
- Do not initialize a controller merely to record that a small local task
  happened. Do not bypass a controller when interrupted state, scope/baseline
  binding or a durable handoff is part of the requested outcome.
- Discover MCP capabilities only when the task involves current external
  evidence, provider data, library documentation or a live system. Record
  `mcp:not-applicable:<reason>` for local-only work instead of performing a
  ritual lookup.
- Keep planning, research, implementation and synthesis inside `work`. They do
  not become nodes or mandatory handoffs merely because they happen in order.
- Emit progress on a state change, blocker or meaningful new evidence. Waiting,
  rereading and restating the plan are not graph transitions.
- Open documentation follow-up only when the candidate creates factual or
  semantic documentation impact.

## Admission rules

Start an agent only when its bounded scope is independent enough to save root
context or wall time. Do not duplicate a live or completed scope. A same-scope
retry must identify new evidence or a new discriminating check.

Start independent review only when risk, uncertainty, an explicit user request
or a release gate needs a counterexample search. One reviewer is the default.
Parallel block review is an explicit deep-review mode, not an automatic response
to task size.

An explicit user request may raise a normal budget, but the run must record the
finite override. It never disables integrity, evidence or stop guards.

## Bounded repair

Before repair, name the first false assumption in the specification, plan,
implementation or verification. Stop at the declared repair budget. Stop sooner
when two consecutive iterations create no new evidence.

The common budgets cap agent starts, review starts, repair cycles,
no-new-evidence iterations and logical receipts per work unit. Domain graphs may
choose lower values and may add bounded domain limits, but must not remove the
common guards.
