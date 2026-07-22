# Task Delivery context-safe slices

Status: READY
Task ID: TD-TASK-DELIVERY-CONTEXT

<!-- task-delivery:plan:start -->
## Outcome

Task Delivery keeps the root coherent across sequential implementation slices,
requires proportionate test creation/update and staged execution, and handles
safe technical scope discoveries without invented human-approval ceremony.

## Research basis

- Internal: Task Delivery `3.3.0`, slice packet/receipt validation, graph tests,
  agent roles, compatibility identities, and the observed missing-scope blocker
  were inspected.
- External: `docs/research/task-delivery-context-checkpoint-research.md` records
  eight official or primary sources on Codex compact hooks, controller
  checkpoints, context engineering, selective/final E2E checks, bounded agent
  autonomy, and branch-based iteration.
- Capabilities: `$agent-graph-builder`, `$skill-creator`, `$task-delivery`,
  `$development-recovery`, `$research`, `$openai-docs`,
  `mcp:openaiDeveloperDocs`, native web, local Git, and Python tests.

## Acceptance

- The graph remains exactly `work -> optional verify -> complete` in `plan`,
  `implement`, and `full`; no context, test, or amendment graph node is added.
- `plan` remains implementation-free. `implement` and `full` may use sequential
  slices. A bounded `slice-accept` operation atomically validates an exact root
  acceptance artifact, stores its immutable digest, and writes the controller-
  owned context checkpoint. `slice-create` rejects a subsequent packet until
  `context-rehydrate` has validated and recorded the exact latest checkpoint
  digest; the new packet binds that digest.
- Checkpoints contain only verified compact state and immutable identities, not
  transcripts or reasoning logs. A host compact is optional; explicit
  rehydration works with or without it. For directory scope they expose the
  original `plan_scope` plus exact accepted paths instead of pretending to
  compute a complete remaining-file set.
- Slice packets declare test impact, fast slice checks, and deferred final
  checks. Workers reuse/update/add applicable unit, integration, and E2E tests,
  pass their assigned fast checks, and report deferred checks without falsely
  claiming they ran. Every check receives a deterministic `check_id` derived
  from canonical `command` plus `purpose`.
- Root acceptance independently replays at least one exact `slice_check` for
  every accepted slice and binds its `check_id`. Every successful `3.4` worker
  receipt must receive immutable root acceptance before another packet or final
  work. Delegated final changed paths must equal the exact union of accepted
  slice path provenance; there is no hidden root-integration exception. The
  controller unions deferred final checks from all accepted packets,
  deduplicates by `check_id`, rejects conflicting identities, and requires every
  exact command/purpose pair to appear passed in integrated `task.json.tests`
  before work may finish.
- A bounded scope-amend command records old/new plan identity, added paths,
  evidence, reason, authority, and review impact. The effective reviewed
  identity is an ordered chain: reviewed base plan digest followed by immutable
  amendment receipts whose `before_digest` equals the previous effective digest
  and whose `after_digest` equals the next one. Completion replays the entire
  chain. `root-technical` preserves the base review only when every declared
  semantic/risk impact is false; any other amendment is rejected as requiring a
  user decision and a new review/run. Root may autonomously approve only
  reversible technical paths that do not change outcome, acceptance,
  public/data/security/external-state semantics, or risk profile.
- Consequential scope changes still require a user decision and invalidate
  affected review evidence. No exact hash prompt is invented for routine
  technical scope completion.
- After a delegated candidate is rejected by the final verifier, the same
  three-node graph may issue exactly one additional repair packet bound to the
  rejected `work_sha256`. It passes the normal worker receipt, root acceptance,
  integrated final checks, and verifier again. A second repair packet, a second
  verifier reject, or an unsuccessful repair worker blocks the run. The two-
  packet normal-slice limit remains separate; a second unsuccessful normal
  packet also becomes an explicit terminal block rather than a dead end.
- An unsuccessful worker must preserve the pre-existing user baseline and leave
  no delta. It prepares a reversible patch/private pre-edit copy of only its
  owned edits; the controller verifies the manifest and never guesses
  provenance or automatically overwrites files.
- Active `3.3.0` runs retain their exact v1 slice/acceptance validation path;
  they do not silently receive checkpoint, amendment, or staged-test semantics.
  New behavior is versioned and tamper/path traversal failures remain closed.
- No global or installed hook is modified. WSL/Desktop installed copies remain
  unchanged until the branch passes focused tests, repository-wide validation,
  a fresh-agent forward test, and independent multi-review.

## Implementation plan

1. Version the Task Delivery graph and define compact checkpoint, rehydrate,
   staged-test, and bounded-amendment policies without changing graph topology.
2. Extend the controller with immutable `slice-accept`, context
   checkpoint/rehydrate, technical scope-amend, and one exact verifier-repair
   packet inside `work`, including compatibility, identity-chain, terminal
   failure, and path/risk guards.
3. Upgrade new slice packets/receipts to the staged-test contract while keeping
   legacy active-run behavior explicit and isolated.
4. Update the skill, slice/control references, worker and result-review roles so
   model-owned judgment and deterministic evidence boundaries agree.
5. Add positive, negative, tamper, compatibility, context, staged-test, and
   excessive-blocker regression tests; update the repository-wide static gate.
6. Run focused and full validation, forward-test from a fresh agent, then perform
   independent block and whole-system reviews and repair only proven findings.

## Tests

- `python3 -m unittest skills/task-delivery/scripts/test_task_graph.py -v`
- `python3 skills/task-delivery/scripts/test_task_delivery.py`
- `python3 skills/agent-graph-builder/scripts/graph_contract.py validate --skill-dir skills/task-delivery`
- `python3 /mnt/c/Users/artem/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/task-delivery`
- `python3 scripts/check_all.py`
- `git diff --check`
- Fresh-agent disposable forward test for two sequential slices, rehydrate,
  staged tests, one bounded technical scope amendment, and the verifier-repair
  transition.

## Rollback and compatibility

- Before installation, rollback is branch-local: abandon or revert this branch;
  installed WSL/Desktop `3.3.0` copies and active agents remain untouched.
- Installation is allowed only after verifying no active Task Delivery run will
  be stranded. The installer keeps its normal backup before replacing a managed
  copy.
- After activation, active `3.4.0` runs must finish with the `3.4.0` controller
  or a repair-forward compatible successor. Do not restore a `3.3.0` controller
  over them. To roll back defaults, first stop creating new runs, finish or
  explicitly migrate every active `3.4.0` run, then restore the backed-up
  `3.3.0` skill and verify both hosts.
- Active `3.3.0` runs opened before activation finish through the isolated v1
  slice contract in the new controller; their evidence gates are not weakened.

## Stop conditions

- Stop and use `$development-recovery` if preserving active `3.3.0` runs would
  require weakening current identity, path, scope, receipt, or test checks.
- Do not modify global/plugin hook caches or installed WSL/Desktop skill copies
  while this branch is under development.
- Do not make automatic scope amendments capable of changing product meaning,
  public contracts, security/data boundaries, migrations, external state, or
  the selected risk profile.
- Do not add a new graph node, transcript store, general memory subsystem,
  parallel write mode, or mandatory reviewer per slice.

## Scope

<!-- task-delivery:scope
docs/research/task-delivery-context-checkpoint-research.md
docs/tasks/TD-TASK-DELIVERY-CONTEXT/
skills/task-delivery/
agents/task_worker.toml
agents/task_result_reviewer.toml
scripts/check_all.py
-->
<!-- task-delivery:plan:end -->

## Plan review

Initial independent review REJECTED the underspecified intermediate acceptance,
plan-identity chain, exact staged-test matching, and post-activation rollback.
The frozen plan now defines `slice-accept`, checkpoint binding, ordered technical
amendments, deterministic check identities, deferred-check union, and active-run
rollback. Final delta review PASS:
`task_plan_reviewer:TD-TASK-DELIVERY-CONTEXT:delta-pass:9677f13cf2c0`.

## Delivery result

PASS. Task Delivery `3.4.0` preserves the three-node graph while adding
controller-owned acceptance/checkpoints, explicit rehydrate, staged tests,
bounded technical scope amendments, and one exact verifier-repair slice. Active
`3.3.0` runs remain version-gated, installed copies and global hooks were not
changed, and the observed amendment-hash ceremony is removed from the normal
technical recovery path.

Verification: focused `71/71`, legacy `44/44`, graph/skill validation,
repository-wide `scripts/check_all.py`, and `git diff --check` passed. Fresh-agent
CLI receipts `td34-frozen-forward-pass-208d0b08` and
`td34-scope-amend-forward-pass-208d0b08` completed the two-slice/checkpoint,
verifier-repair, scope-amend, verifier, complete, and HANDOFF lifecycles.
Independent result review PASS:
`task_result_reviewer:TD-TASK-DELIVERY-CONTEXT:whole-system-pass:9677f13cf2c0`.
