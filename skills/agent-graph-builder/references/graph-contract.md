# Shared agent graph contract

## Contents

- [Purpose](#purpose)
- [Skill package](#skill-package)
- [Control topology](#control-topology)
- [Ownership boundary](#ownership-boundary)
- [Artifacts and state](#artifacts-and-state)
- [Agents and capabilities](#agents-and-capabilities)
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

Skills and MCP are capabilities inside `work`. Select only applicable skills, read their complete `SKILL.md`, call relevant MCP before generic fallbacks, and preserve receipts. Do not load every installed skill or create a capability-selection graph node.

## Modes and profiles

Use modes when the same stable workflow has different terminal outcomes, such as plan-only, implement-only and full delivery. Use profiles when risk changes review depth or limits without changing the fundamental route.

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
