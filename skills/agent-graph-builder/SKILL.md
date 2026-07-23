---
name: agent-graph-builder
description: Create, refactor, or standardize Codex-native agent graph skills with a shared model-first contract, deterministic state controller, bounded optional agents, receipts, compatibility, and adversarial tests. Use when a user asks to create an agent graph, turn a repeated workflow into a graph-backed skill, align several graph skills to one contract, or audit whether a proposed graph is too complex. Always layer this skill on the system $skill-creator rather than recreating generic skill scaffolding.
---

# Agent Graph Builder

Create a skill-backed control graph that constrains evidence and lifecycle while leaving semantic work to the model.

## Mandatory dependency

1. Invoke `$skill-creator` and read its complete `SKILL.md` before creating or restructuring a graph skill.
2. Use its `init_skill.py`, frontmatter rules, progressive-disclosure guidance, `agents/openai.yaml` generator and `quick_validate.py` for the generic skill layer.
3. Apply this skill only to the graph-specific layer: `graph.json`, controller, durable artifacts, agent routing and graph tests.
4. If `$skill-creator` is unavailable, stop before scaffolding and report the missing dependency. Do not recreate it from memory.

The machine-readable dependency is `skill-dependencies.json`. Do not move the dependency into `agents/openai.yaml`; that format currently declares MCP tools, not other skills.

## Decide whether a graph is justified

Create a graph only for a repeated workflow that benefits from durable state, resumability, bounded repair, evidence handoffs or conditional independent review. Keep a normal skill or prompt when the work is local, one-shot or safely handled by model judgment alone.

Do not create one graph per task. Prefer a small stable family of graphs with modes or profiles inside the existing `work` loop.

## Build the graph

1. Inspect the target repository, nearest `AGENTS.md`, existing skills, controllers, tests and installer. Preserve dirty user work and active-run compatibility.
2. Write the behavioral contract before controller code: trigger, modes, artifacts, evidence, stop decisions, verification conditions and completion truth.
3. For a new skill, initialize the generic folder with `$skill-creator`, replace every generated TODO and generate the final `agents/openai.yaml`. Only then optionally run:

```bash
python3 scripts/graph_contract.py scaffold \
  --skill-dir <path/to/new-skill> \
  --mode <mode> --work-artifact <receipt.json> \
  --complete-artifact <result.md> --verifier-role <role>
```

The scaffold refuses to overwrite existing graph or control-artifact files. It does not invent the domain controller.

4. Keep the default control topology `work → optional verify → complete`. Planning, research, capability selection, implementation and synthesis normally stay inside `work`; they are not graph nodes merely because they occur in sequence.
5. Put judgment in the root model. Put path safety, state transitions, retry bounds, immutable receipts, SHA-256 binding, compatibility and completion checks in standard-library code.
6. Make agents conditional capabilities, not mandatory stages. Root owns synthesis and final truth; subagents receive bounded packets and remain leaf workers. Never hard-code model names in the graph skill.
7. Route installed skills and relevant MCP context inside `work`. Record actual capability receipts or an explicit checked fallback; never add a separate MCP node.
8. Version `graph.json` and the durable state schema. Pin active runs to the graph identity and add an explicit compatibility or migration path before changing a released contract.
9. Classify run material by [artifact-lifecycle.md](references/artifact-lifecycle.md). Canonical outputs remain project history; active state remains resumable; safely terminal raw state uses the shared runtime for verified compaction and explicit TTL pruning. Do not add a cleanup node or destructive hook.
10. Read [graph-contract.md](references/graph-contract.md) while designing fields and [evaluation.md](references/evaluation.md) before claiming completion.

## Validate

Run both layers:

```bash
python3 <skill-creator>/scripts/quick_validate.py <graph-skill>
python3 scripts/graph_contract.py validate --skill-dir <graph-skill>
```

Then run the graph's focused controller tests and the repository-wide gate. Forward-test a complex new graph from a fresh agent against a disposable fixture; provide the skill and task, not the intended answer.

Do not call the graph complete until the real controller has exercised init/resume, happy path, conditional verify, bounded failure or retry, tamper rejection, compatibility and final artifact generation.

## Completion contract

Return:

- why a graph was justified;
- route and mode summary;
- deterministic versus model-owned responsibilities;
- optional agents and capability routing;
- state, receipt and compatibility contract;
- artifact retention, compaction and cleanup impact;
- exact validation commands and results;
- installation or migration impact;
- residual risks.

If the graph became longer only to make prose explicit, simplify it before handoff.
