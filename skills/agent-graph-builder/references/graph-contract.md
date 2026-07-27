# Shared agent graph contract

## Contents

- [Purpose](#purpose)
- [Skill package](#skill-package)
- [Control topology](#control-topology)
- [Ownership boundary](#ownership-boundary)
- [Artifacts and state](#artifacts-and-state)
- [Agents and capabilities](#agents-and-capabilities)
- [Work efficiency](#work-efficiency)
- [Execution tiers](#execution-tiers)
- [Modes and profiles](#modes-and-profiles)
- [Compatibility](#compatibility)
- [Lessons from the current graphs](#lessons-from-the-current-graphs)

## Purpose

An agent graph is a small control contract around a capable model. It exists to make lifecycle, evidence, retry and completion truth predictable. It is not a visual transcription of every cognitive step.

New graphs use schema version 2 and a versioned `graph_id`/`graph_version`. A single-route legacy shape may keep top-level `entry`, `terminal` and `nodes`; new graphs should use `routes`, even with one mode, so later mode additions do not require a structural migration.

## Skill package

```text
<graph-skill>/
├── SKILL.md
├── agents/openai.yaml
├── graph.json
├── scripts/<name>_graph.py
├── scripts/test_<name>_graph.py
├── references/control-artifact.md
└── optional focused references/assets
```

Create `SKILL.md` and UI metadata through `$skill-creator`. Keep `SKILL.md` short and route details to one-level references. Do not add README, changelog or installation guides inside the skill.

## Control topology

The default route is:

```text
work → complete
  └─ when evidence or risk requires independence → verify → complete
                                           reject → work
```

Every route contains exactly:

- `work`: root model owns discovery, applicable skills/MCP, planning, execution and candidate evidence;
- `verify`: a conditional independent role checks the exact immutable candidate;
- `complete`: root commits the durable completion artifact and state.

A user decision may pause `work`, but it does not need a permanent decision node. A slice packet, research branch, plan review or capability call is an operation inside `work` unless it has its own durable lifecycle across most runs.

Add a node only when it owns a distinct durable artifact, has independent transition/retry semantics, appears in most runs, and cannot remain a bounded operation inside `work`. Record the justification in the owning reference and tests.

### Code-first and control-late

The domain task and controller have separate health. Read project instructions,
architecture, source, tests and runtime evidence before control receipts. Give a
protocol mismatch one bounded repair; if it persists, degrade control and continue
authorized work. Degraded control can refuse verified completion, but cannot turn
a healthy implementation task into a user blocker. Only authority, semantic
contract, security, data, external state or destructive choices may interrupt the
user.

Unfinished tasks are independent. A tracked graph may write one compact suspend
checkpoint and later rehydrate from that checkpoint plus the repository. Suspend,
resume, host compaction and task switching remain lifecycle operations inside
`work`, never permanent nodes.

## Ownership boundary

The model owns:

- relevance, decomposition and proportionality;
- semantic research and synthesis;
- design and implementation decisions within authority;
- selection of applicable installed skills, MCP and bounded agents;
- user-facing explanation.

The deterministic controller owns:

- safe paths and state locking;
- graph and state versions;
- legal transitions and retry budgets;
- baseline manifests and exact changed paths;
- immutable receipts and SHA-256 identity;
- artifact schema checks;
- compatibility and tamper detection;
- completion truth.

Do not encode model reasoning as dozens of mandatory flags. Do not let model prose substitute for controller-verifiable evidence.

## Work efficiency

Every new or materially refactored graph declares the shared `work_policy`.
It makes the root-only fast path, need-based capability discovery, independent
agent admission, risk-based review, state-change-only progress, impact-gated
documentation and bounded user overrides machine-checkable.

Budgets bound agent starts, review starts, repair cycles, consecutive
no-new-evidence iterations and logical receipts per work unit. Loop guards reject
duplicate agent scopes, evidence-free retries and repairs that do not identify
the first false assumption. See
[efficiency-contract.md](efficiency-contract.md).

The validator still reads released graphs without `work_policy` for compatibility,
but `--require-work-policy` is the release gate for new or migrated graphs.

## Execution tiers

The skill is the interface; the controller is an admitted reliability layer.
Declare `execution_policy` with the shared tiers:

- `skill-only`: one root loop, no durable run and self-verification;
- `tracked`: controller state, baseline/scope/evidence and conditional review;
- `verified`: tracked execution plus required independent exact-candidate review.

Use `skill-only` only when the work is bounded to one session, reversible, clear
and does not need durable handoff. Admit `tracked` for resumability, multi-session
work, durable artifacts, baseline/scope binding or an explicit user request.
Admit `verified` for risk, uncertainty or an explicit independent-review request.

Project Start-like workflows whose purpose is a durable canonical foundation may
default to `tracked` and omit `skill-only`. Do not create an empty controller run
for ordinary work and do not pretend a self-review is independent verification.

## Artifacts and state

Each route defines one work artifact, one verification artifact and one completion artifact. The work artifact is a receipt, not a second plan or reasoning log.

At minimum bind:

- graph id, version and exact graph digest;
- run id, mode/profile and root;
- baseline or input identity;
- canonical plan/spec/source digests when relevant;
- chosen capabilities and agent receipts;
- tests or other observable verification;
- current node, attempts and bounded repair count;
- final artifact digest.

After terminal completion, apply the separate shared artifact lifecycle. Keep
canonical user outputs at their owning project paths, preserve unresolved raw
state, and compact safely terminal execution material into a verified archive
plus `FINAL.json`. Retention and garbage collection are post-completion
operations, never additional graph nodes. See
[artifact-lifecycle.md](artifact-lifecycle.md).

The verifier receives the exact work receipt and candidate digests. Completion rechecks current files rather than trusting the verifier or worker summary.

## Agents and capabilities

Root remains the sole graph orchestrator and synthesis owner. Use zero agents on the fast path. Add agents only for independent read-only discovery, a bounded implementation slice or independent review.

Agent requirements:

- exact objective, scope, exclusions, must-read evidence and acceptance;
- fresh context instead of the full root transcript;
- leaf-only topology;
- receipt tied to the assigned packet/candidate;
- no commits or external writes unless explicitly authorized;
- no hard-coded model names in the skill or graph contract.

Skills and MCP are capabilities inside `work`. Select only applicable skills and read their complete `SKILL.md`. Discover and call relevant MCP before generic fallbacks when external, provider, library or live-system context matters; local-only work records `mcp:not-applicable:<reason>`. Preserve receipts without loading every installed skill or creating a capability-selection graph node.

## Modes and profiles

Use modes when the same stable workflow has different terminal outcomes, such as plan-only, implement-only and full delivery. Use profiles when risk changes review depth or limits without changing the fundamental route. Execution tiers decide whether the controller or verifier is admitted at all; modes and profiles do not automatically justify extra agents.

Do not duplicate routes merely to restate identical nodes. Keep per-mode differences in artifacts, guards and conditional policies. Auto-routing should be explainable and explicit user commands should override heuristics where safe.

## Compatibility

Released graph state is an API. Before changing it:

1. compute and preserve the previous graph identity;
2. decide whether active runs may finish on the legacy controller, be read by the new controller, or require explicit migration;
3. reject unknown identities and silent reinterpretation;
4. add tests for the chosen path;
5. bump graph version for behavioral contract changes.

Never weaken current artifact checks merely to accept legacy state. Isolate compatibility logic.

## Lessons from the current graphs

- Project Start shows that bootstrap and maintenance can share one three-node topology while owning different documentation outcomes.
- Research shows that fast/deep search, source checkpoints and optional multi-agent branches belong inside `work`, not in ten permanent nodes.
- Task Delivery shows that plan/implement/full modes, risk profiles and delegated slices can remain operations and guards inside the same short route.

These are examples, not domain templates. Reuse the contract and adapt the artifacts.
