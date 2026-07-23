# Graph evaluation contract

## Contents

- [Static checks](#static-checks)
- [Controller checks](#controller-checks)
- [Behavioral forward test](#behavioral-forward-test)
- [Release gate](#release-gate)

## Static checks

- `$skill-creator` quick validation passes.
- `graph_contract.py validate --require-work-policy` passes for a new or migrated graph.
- Every route contains only `work`, `verify`, `complete` unless an explicit tested exception is documented.
- Retry and verification-repair budgets are bounded.
- Work budgets and loop guards enforce the root-only fast path, need-based
  capabilities, independent agent scopes and two-iteration no-new-evidence stop.
- Adaptive execution declares whether the default is skill-only or tracked and
  keeps verified execution risk-triggered.
- `agents/openai.yaml` names the skill in `default_prompt`.
- No TODO, placeholder or hard-coded model remains.
- A fresh `$skill-creator` template fails graph scaffold until its TODOs and final metadata are resolved.
- One controller and at least one focused graph test exist.

## Controller checks

Test at least:

1. initialization creates canonical state and returns the next real command;
2. resume/status does not mutate evidence;
3. native happy path completes without unnecessary agents;
4. conditional verify binds to the exact candidate;
5. rejected verification has one bounded repair path;
6. invalid transition and exhausted retry fail closed;
7. artifact, graph or receipt tampering is rejected;
8. path traversal and unsafe ownership are rejected where files are mutated;
9. legacy active-run behavior matches the declared compatibility policy;
10. completion generates and rechecks the final artifact.
11. artifact inventory is read-only, compaction refuses unresolved state, and
    explicit pruning rejects symlinks, tampering, premature TTL and canonical
    outputs.

Add domain tests for permissions, source quality, implementation scope, external state or other material invariants.

## Behavioral forward test

Use a fresh agent and a disposable fixture. Ask it to use the installed graph skill on a realistic task. Do not reveal the expected internal route or prior diagnosis.

Observe:

- whether the skill triggers correctly;
- whether the root keeps semantic work native;
- whether agents are called only when useful;
- whether skills/MCP context is used when relevant and local-only work avoids
  ritual capability discovery;
- whether commands are executable from the installed path;
- whether the controller blocks a false completion;
- elapsed time and avoidable handoff overhead.
- agent starts, review starts, waits/handoffs, artifact count and compactions;
- duplicate scopes, evidence-free retries and unnecessary documentation follow-up.

Treat a partial run as partial coverage. Record the first untested transition rather than inferring success.

Compare representative tasks across `skill-only`, `tracked`, and the previous
full route with the same model, tools and acceptance criteria. A graph does not
pass merely because it is predictable: it must not add material wall time,
tokens or artifacts without closing a real risk or evidence gap.

## Release gate

Run focused tests, the shared artifact-lifecycle tests, the repository-wide
gate, installer plan/install/verify for every supported environment, and
`git diff --check`. Inspect the complete diff and preserve unrelated dirty
work. Commit only after all generated and installed copies match.
