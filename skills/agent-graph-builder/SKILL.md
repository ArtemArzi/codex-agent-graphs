---
name: agent-graph-builder
description: Create, refactor, or standardize Codex-native agent graph skills with a shared model-first contract, deterministic state controller, bounded optional agents, receipts, compatibility, and adversarial tests. Use when a user asks to create an agent graph, turn a repeated workflow into a graph-backed skill, align several graph skills to one contract, or audit whether a proposed graph is too complex. Always layer this skill on the system $skill-creator rather than recreating generic skill scaffolding.
---

# Agent Graph Builder

Host invocation: `$agent-graph-builder` in Codex, `/cag:agent-graph-builder` in Claude Code.

Create a skill-backed control graph that constrains evidence and lifecycle while leaving semantic work to the model.

## Task context and collaboration

Apply the inherited “Collaboration and useful questions” policy when designing a workflow. Generated skills must inherit the host's collaboration policy and add only domain-specific intake and acceptance guidance. Keep small tasks lightweight, preserve decisions across skill switches and support explicit no-question instructions within existing authority. Do not embed a mandatory interview or duplicate the global policy in every generated skill.

## Plain-language user updates

Make every operational graph explain its work in the user's language and in
plain words. User-facing progress and final messages must lead with what
changed, what it means for the task, and what happens next. They must not read
like the controller's internal log.

Required order: result → impact → next step.

Require a `Plain-language user updates` section in every operational graph
skill. Internal terms such as `controller`, `root`, `worker`, `packet`,
`receipt`, `digest`, `checkpoint`, `gate`, `authority`, `control-degrade` and
`recovery route` may appear only when the user needs the exact identifier to
act or verify something; translate and explain it on first use. Put hashes, exact
artifact names and protocol details in an optional `Technical details:` block
after the plain explanation. Keep ordinary progress to one short paragraph.

## Inherited routing and acceptance policy

The effective user-level policy is the sole authority for models, effort and
review thresholds. Root owns decisions and integration; auxiliary agents receive
fresh bounded context and remain leaves. Default to native skill-only execution.

Trivial chat and wording stay root-only. Simple engineering gets one independent
`block_reviewer` result review; ordinary non-engineering artifact reviews also
use `block_reviewer`. Only complex engineering or concrete material risk requires
a fresh whole-plan `task_plan_reviewer` before execution and a different fresh
workflow-specific whole-result acceptor afterwards. A substantive label, long
document, skill switch or review request alone does not trigger this pair.
Honor explicit review scope without inflating it. Do not split risky work to
evade the threshold. Same-outcome repairs reuse valid evidence and the assigned
reviewer; reassess material changes. Finish all required checks and reconcile
findings before claiming acceptance. Root self-review is not independent review.

These reviews are operations inside `work`, not new graph nodes. Prefer native
review before admitting a controller. If a released controller demands an
acceptance-role receipt below the threshold and has no supported auxiliary
completion route, degrade controller execution and preserve state and pending
obligations. Continue authorized work with the required `block_reviewer` verdict
in the existing handoff. Never relabel its role, alter identity/schema, clear
pending obligations or claim controller completion. Protocol mismatch does not
raise the review threshold. Nested skills reuse valid same-scope evidence.

## Mandatory dependency

1. Invoke `$skill-creator` and read its complete `SKILL.md` before creating or restructuring a graph skill.
2. Use its `init_skill.py`, frontmatter rules, progressive-disclosure guidance, `agents/openai.yaml` generator and `quick_validate.py` for the generic skill layer.
3. Apply this skill only to the graph-specific layer: `graph.json`, controller, durable artifacts, agent routing and graph tests.
4. If `$skill-creator` is unavailable, stop before scaffolding and report the missing dependency. Do not recreate it from memory.

The machine-readable dependency is `skill-dependencies.json`. Do not move the dependency into `agents/openai.yaml`; that format currently declares MCP tools, not other skills.

## Decide whether a graph is justified

Create a graph only for a repeated workflow that benefits from durable state,
resumability, bounded repair, evidence handoffs or bounded independent review
when the workflow needs it. Keep a normal skill or prompt when the work is local,
one-shot or safely handled by model judgment alone; required policy acceptance
does not by itself justify a controller.

Do not create one graph per task. Prefer a small stable family of graphs with modes or profiles inside the existing `work` loop.

## Build the graph

1. Inspect the target repository, nearest `AGENTS.md`, existing skills, controllers, tests and installer. Preserve dirty user work and active-run compatibility.
2. Write the behavioral contract before controller code: trigger, modes, artifacts, evidence, stop decisions, verification conditions, completion truth, adaptive `execution_policy` and the bounded `work_policy`.
3. For a new skill, initialize the generic folder with `$skill-creator`, replace every generated TODO and generate the final `agents/openai.yaml`. Only then optionally run:

```bash
python3 scripts/graph_contract.py scaffold \
  --skill-dir <path/to/new-skill> \
  --mode <mode> --work-artifact <receipt.json> \
  --complete-artifact <result.md> --verifier-role <role>
```

The scaffold refuses to overwrite existing graph or control-artifact files. It does not invent the domain controller.

4. Keep the default control topology `work → optional verify → complete`.
   `optional verify` describes only controller admission; an inherited policy may
   require plan/result acceptors inside `work` even when that node is skipped.
   Planning, research, capability selection, implementation and synthesis
   normally stay inside `work`; they are not graph nodes merely because they
   occur in sequence.
5. Declare a code-first control boundary. Domain work reads project instructions, architecture, source and tests before controller detail. Protocol failure gets one bounded repair, then degrades control without blocking authorized domain work. Only authority, semantic contract, safety, data or external-state boundaries may interrupt the user; degraded control may refuse verified completion.
6. Keep task state separate from controller health. When resumability matters, provide one compact suspend checkpoint and allow unrelated unfinished tasks to proceed independently; do not model suspension, compaction or task switching as graph nodes.
7. Put judgment in the root model. Put path safety, state transitions, retry bounds, immutable receipts, SHA-256 binding, compatibility and completion checks in standard-library code.
8. Apply [efficiency-contract.md](references/efficiency-contract.md). Start
   root-only for domain work; admit required policy acceptors as the explicit
   independent-review exception, and admit other agents only for a concrete
   independent evidence gap. Stop duplicate scopes and no-new-evidence retries
   at their declared budgets. An explicit user override must remain finite.
9. Declare `execution_policy`: `skill-only` does not initialize durable state;
   `tracked` and `verified` describe controller admission and its supported
   receipts. Neither tier can suppress a host-policy acceptance operation, and
   `verified` remains the graph path for an exact-candidate controller review.
   A graph whose core purpose is durable lifecycle may expose only `tracked` and
   `verified`; do not invent a fake quick path.
10. Make domain agents conditional capabilities, not mandatory graph stages.
    Root owns final synthesis and truth; subagents may return bounded independent
    discovery, preparation, implementation or synthesis packets and remain leaf
    workers. Host-policy acceptors are mandatory operations when the policy
    applies, but are not new graph nodes. Never hard-code model names in the
    graph skill.
    A request for stages or slices is not a request for subagents. New work_policy v2 graphs cap concurrency and no-progress retries, not total useful starts over a long task. At host capacity, continue permitted local work and keep missing independent verification explicit.
11. Route applicable installed skills and relevant MCP context inside `work`. Discover MCP only when the task can benefit from external, provider, library or live-system context. Record an actual receipt, a checked fallback or `mcp:not-applicable:<reason>` for local-only work; never add a separate MCP node.
12. Version `graph.json` and the durable state schema. Pin active runs to the graph identity and add an explicit compatibility or migration path before changing a released contract.
13. Classify run material by [artifact-lifecycle.md](references/artifact-lifecycle.md). Canonical outputs remain project history; active state remains resumable; safely terminal raw state uses the shared runtime for verified compaction and explicit TTL pruning. Do not add a cleanup node or destructive hook.
14. Read [graph-contract.md](references/graph-contract.md) while designing fields and [evaluation.md](references/evaluation.md) before claiming completion.

## Validate

Run both layers:

```bash
python3 <skill-creator>/scripts/quick_validate.py <graph-skill>
python3 scripts/graph_contract.py validate \
  --skill-dir <graph-skill> --require-work-policy
```

Then run the graph's focused controller tests and the repository-wide gate. Forward-test a complex new graph from a fresh agent against a disposable fixture; provide the skill and task, not the intended answer.

Do not call the graph complete until the real controller has exercised init/resume, happy path, conditional verify, bounded failure or retry, tamper rejection, compatibility and final artifact generation.

## Completion contract

Return:

- why a graph was justified;
- route and mode summary;
- deterministic versus model-owned responsibilities;
- optional agents and capability routing;
- fast path, admission rules, budgets and loop guards;
- skill-only, tracked and verified routing plus the controller admission signal;
- state, receipt and compatibility contract;
- artifact retention, compaction and cleanup impact;
- exact validation commands and results;
- installation or migration impact;
- residual risks.

If the graph became longer only to make prose explicit, simplify it before handoff.
