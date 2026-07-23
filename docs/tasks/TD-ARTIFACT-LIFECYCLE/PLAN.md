# Task Delivery plan: shared artifact lifecycle

Status: COMPLETE

task-delivery:scope
- agent-graph-runtime/**
- docs/tasks/TD-ARTIFACT-LIFECYCLE/**
- skills/agent-graph-builder/**
- skills/continuous-improvement/SKILL.md
- skills/project-start/SKILL.md
- skills/research/SKILL.md
- skills/task-delivery/SKILL.md
- scripts/check_all.py
- scripts/install.py
- tests/test_install.py
- README.md

## Outcome

Give every graph one deterministic, repository-local artifact lifecycle without
adding graph nodes or relying on a destructive hook. Preserve canonical project
history, keep active and blocked state intact, compact completed raw runs into a
verified archive plus a small final receipt, and make deletion explicit,
retention-bound, observable, and fail-closed.

## Basis

- Canonical user documents under `docs/` remain project history.
- New graph state lives under `.agent-graphs`; `.codex/task-delivery` is a
  legacy/current task-state surface that must remain discoverable during
  migration.
- Local inspection found duplicate multi-megabyte baseline manifests and no
  shared retention or garbage-collection policy.
- External workflow systems separate terminal evidence from transient execution
  artifacts and apply explicit TTL only after a terminal state.
- The shared graph contract keeps lifecycle operations outside the
  `work -> optional verify -> complete` node topology.

## Acceptance

- A standard-library CLI inventories every supported graph run root and legacy
  Task Delivery state without following symlinks.
- `compact` accepts only safe terminal state, refuses active, blocked,
  awaiting-implementation, malformed, tampered, or unverified-superseded runs,
  and creates:
  - `.agent-graphs/history/<graph>/<run>/FINAL.json`;
  - `.agent-graphs/archives/<graph>/<run>.tar.gz`.
- Archive content is deterministic, manifest-bound, and verified before the
  final receipt is published.
- `prune` is dry-run by default. `--apply` removes only due, verified managed
  raw runs or archives and writes a GC receipt. It never deletes canonical
  outputs.
- Default successful retention is seven days for unpacked raw state and thirty
  days for the archive. Active and blocked state has no cleanup deadline.
- The installer copies and verifies the shared runtime in WSL and Desktop.
- Every operational skill routes terminal artifact handling to the shared CLI
  without adding a graph node or automatic hook.
- Legacy and graph controllers remain compatible because their state schemas and
  completion transitions are unchanged.

## Implementation

1. Add the shared runtime and adversarial tests for path safety, status
   classification, deterministic compaction, idempotency, tamper rejection,
   dry-run pruning, explicit apply, legacy inventory, and canonical-output
   preservation.
2. Add installer support and repository-wide validation.
3. Document the three artifact classes and the exact commands in Agent Graph
   Builder; keep operational skill additions short.
4. Update the public repository map and installation surface.
5. Run focused tests, the full repository gate, installer plan/verification
   against disposable homes, `git diff --check`, and a final diff review.

## Tests

- `python3 -m unittest tests/test_artifact_lifecycle.py -v`
- `python3 -m unittest tests/test_install.py -v`
- `python3 scripts/check_all.py`
- `python3 scripts/install.py plan --all`
- `git diff --check`

## Stop conditions

- Stop before any cleanup behavior that can operate outside the exact managed
  roots.
- Stop if active or awaiting-implementation Task Delivery state cannot be
  distinguished from safely terminal state.
- Stop rather than weakening symlink, hash, archive, successor, or retention
  checks.
- Do not run `prune --apply` against a real project during this task.

## Verification

- `python3 -m unittest tests/test_artifact_lifecycle.py -v`: PASS, 13 tests.
- `python3 -m unittest tests/test_install.py -v`: PASS, 14 tests.
- `python3 scripts/check_all.py`: PASS, including every skill validator, graph
  contract, controller suite and Project Start adversarial self-test.
- Disposable WSL and Desktop installation plus `verify --all`: PASS and
  `in-sync`, including `agent-graph-runtime`.
- Read-only inventory against AI Marketing and RESERCH: PASS; active, blocked,
  superseded-without-successor and incomplete legacy entries remained held.
- `git diff --check`: PASS.
- No real project was compacted or pruned. Live WSL/Desktop installations were
  intentionally left unchanged while other active agents still use the prior
  contract.
