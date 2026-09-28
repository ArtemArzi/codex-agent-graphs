# Work efficiency contract

The graph is a control boundary around model judgment, not a checklist engine.
Every new or materially refactored graph declares `work_policy` in `graph.json`.

## Code-first control boundary

- Project instructions, architecture, source code, tests and runtime evidence come
  before controller artifacts. The graph controls boundaries and completion; it
  is never the primary work product.
- Separate domain/task state from controller health. A digest, marker, receipt,
  schema, reviewer budget, run partition or checkpoint mismatch gets at most one
  bounded repair. If it persists, mark control degraded and continue authorized
  domain work. Degraded control may block a verified completion claim, not
  implementation, tests or a skill-only handoff.
- Interrupt the user only for missing authority, semantic contract ambiguity,
  security/data/external-state risk or a destructive choice. Technical controller
  compatibility is not a human decision.
- Support independent unfinished tasks with a compact suspend checkpoint:
  canonical input digest, current objective, changed paths, accepted evidence and
  resume hint. Suspension and host compaction are lifecycle operations, not graph
  nodes.
- An explicit user instruction to disable a graph disables its controller for
  that task. Do not reactivate it through recovery or another skill.

## Fast path

- Start root-only for domain work. A skill, MCP call, subagent or non-required
  reviewer must close a concrete evidence gap; availability alone is not a
  reason to invoke it. An inherited policy-required plan/result acceptor is an
  explicit independent-acceptance exception.
- Choose the cheapest execution tier that preserves the needed guarantee:
  `skill-only` for bounded one-session work, `tracked` for resumability or
  durable evidence, and `verified` for material risk, uncertainty or a
  controller-level independent-review requirement. Host-policy reviews may run
  inside skill-only without controller state.
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

Start an agent only when its independent result or necessary counterexample
search is worth startup, context transfer and integration cost. State this
briefly in the dispatch, not a new artifact. A stage or slice is not an agent.
Do not duplicate a live or completed scope. A same-scope retry must identify
new evidence or a new discriminating check.

Start independent review when the inherited host policy, an explicit review
request or a real release requirement calls for it. Apply the host threshold:
one `block_reviewer` result review for simple engineering, and `block_reviewer`
for ordinary non-engineering artifact reviews. A whole-plan acceptor and a
different whole-result acceptor are required only for complex engineering or
concrete material risk. Trivial work stays root-only. Finish all required checks
before acceptance; same-outcome corrections reuse the assigned reviewer.
Without host policy, keep review proportional to actual risk and requested scope.
A controller receipt incompatibility does not justify a larger review route;
follow the entrypoint's compatibility rule without changing receipt identities.

An explicit user request may raise a normal budget, but the run must record the
finite override. It never disables integrity, evidence or stop guards.

## Bounded repair

Before repair, name the first false assumption in the specification, plan,
implementation or verification. Stop at the declared repair budget. Stop sooner
when two consecutive iterations create no new evidence.

For work_policy schema 2, max_agent_starts is null: cumulative starts are an
overhead signal, not a task-stop condition. Cap concurrent agents instead (0–2
normally, respecting the host). Other budgets still bound repeated review,
repair, no-new-evidence iterations and receipts per work unit. Released schema 1
graphs retain their original limits; do not reinterpret active receipts.

Host limits are not reset by creating another run. When delegation is unavailable,
continue authorized domain work as root. Preserve required independent checks
as unmet rather than manufacturing verification or asking about internal counters.
