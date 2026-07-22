# Continuous Improvement graph

Status: READY
Task ID: TD-CONTINUOUS-IMPROVEMENT

<!-- task-delivery:plan:start -->
## Outcome

A validated, installable Continuous Improvement graph selects one evidence-backed low-risk repository problem, safely hands accepted work to Task Delivery, and completes with a no-op, issue-ready, or draft-PR-ready receipt.

## Research basis

- Internal: existing graph contract, installer, Task Delivery controller and tests were inspected. All operational graphs use `work -> optional verify -> complete`; installed copies are managed by `scripts/install.py` and checked by `scripts/check_all.py`.
- External: the prior decision pass checked official GitHub Agentic Workflows, GitHub coding-agent guidance, OpenAI Codex, Anthropic agent design, and SWE-agent. The implementation follows their shared pattern: bounded candidate discovery, environmental evidence, sandboxed delivery, stopping conditions, and reviewable PR output.
- Capabilities: `$agent-graph-builder`, required `$skill-creator`, `$task-delivery`, local Git/Python tests, and `mcp:fallback:local-controller-implementation` after MCP discovery found no external data dependency for this code change.

## Acceptance

- `continuous-improvement` is a valid Codex skill with generated UI metadata, schema-v2 graph, standard-library controller, control-artifact reference and focused tests.
- Default `full` and optional `audit` share only `work`, conditional `verify`, and `complete`.
- One run selects at most one evidence-backed candidate and finishes as `no-op`, `issue-ready`, or `delivered`.
- `audit` cannot deliver code. `delivered` requires a completed Task Delivery receipt, a low-risk candidate, bounded changed paths, an isolated non-default branch and one exact commit.
- High-risk/protected work fails closed to `issue-ready`; direct merge, deployment and push-to-main are outside the graph.
- Optional verifier binds to the exact immutable candidate receipt; one rejected verification repair is allowed.
- The installer manages the new skill and verifier for WSL CLI and Desktop without overwriting unrelated drift.
- Focused tests, shared graph validation, repository-wide validation, installer plan/install/verify and a fresh-agent disposable forward test pass.

## Implementation plan

1. Scaffold `continuous-improvement` through `$skill-creator`, then apply the Agent Graph Builder contract and concise operating instructions.
2. Implement the deterministic controller for safe paths, clean/full preflight, state and graph identity, bounded dispositions, Task Delivery receipt binding, verification repair, commit validation and final `IMPROVEMENT.md`.
3. Add one leaf-only `improvement_verifier` and wire the skill/role into installation and repository validation.
4. Add adversarial controller tests for no-op, issue-ready, delivered handoff, audit restrictions, protected paths, tampering, retry bounds, compatibility identity and completion.
5. Run focused, shared, repository-wide, install and fresh-agent checks; inspect the complete diff without touching the concurrent README change or pre-existing task artifacts.

## Tests

- `python3 skills/continuous-improvement/scripts/test_continuous_improvement_graph.py`
- `python3 <skill-creator>/scripts/quick_validate.py skills/continuous-improvement`
- `python3 skills/agent-graph-builder/scripts/graph_contract.py validate --skill-dir skills/continuous-improvement`
- `python3 scripts/check_all.py`
- `python3 scripts/install.py plan --all`
- `python3 scripts/install.py install --all`
- `python3 scripts/install.py verify --all`
- `git diff --check`
- Fresh `task_worker` forward test against a disposable Git fixture.

## Stop conditions

- Stop rather than widening the graph if the controller would need to duplicate Task Delivery planning, implementation or review internals.
- Stop if installation would overwrite unmanaged agent configuration or installed drift without the existing backup flow.
- Do not edit or include the concurrently modified `README.md`, pre-existing `.codex/`, or `docs/tasks/TD-README-PUBLIC/` artifacts.
- Do not authorize automatic merge, deployment, protected-domain changes or direct commits on the default branch.

## Scope

<!-- task-delivery:scope
skills/continuous-improvement/
agents/improvement_verifier.toml
scripts/install.py
scripts/check_all.py
tests/test_install.py
-->
<!-- task-delivery:plan:end -->

## Plan review

Self-review PASS for `standard`: the plan preserves the three-node contract, delegates one bounded controller/test slice, keeps semantic selection in the model, and leaves implementation/review ownership in Task Delivery.

## Delivery result

PENDING
