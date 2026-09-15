# Architecture contract delivery evidence

## Scope and baseline

User approved the six-step plan and WSL installation on 2026-09-14.
Plan acceptor: `/root/two_skills_architecture_plan`, receipt
`plan-accept-two-skills-architecture-20260914-b7f3c9`.
Initial worktree was clean. Installer plan confirmed both installed skills and
roles matched source; only an unrelated top-level model_reasoning_effort setting
differed from installer output. That setting is preserved, not printed here.

## Active paths and implementation decisions

- Project Start 3.5 uses root-authored canonical role documents; active initialize
  does not copy the legacy FOUNDATION/PLAN templates. Updated SKILL and
  documentation/maintenance contracts therefore own the active behavior.
- ENGINEERING.md is an explicitly referenced fallback guide, and NESTED-AGENTS.md
  supports module instructions; these two templates were updated.
- Task Delivery 3.9 creates plans through task_graph.py::plan_template, now with
  Architecture conformity inside the reviewed plan markers. Legacy plan templates
  and released graph identities/schemas remain unchanged.
- Existing engineering_standard binding checks path/hash and plan reference.
  Explicit foundation/other documents use existing must_read packet snapshots.
  Reading, semantic conformity and arbitrary-document freshness are checked by
  agents; the runner is not claimed to prove those properties.
- Task worker, native worker, plan/result acceptors and project documentation
  verifier now have explicit architecture duties. Claude role projections were
  regenerated from TOML with existing model-routing settings unchanged.
- Runtime discovery: `/root/architecture_runtime_seams`, read-only, confirmed
  active paths and the distinction between semantic and integrity guarantees.

## Executed checks

- `python3 -m unittest skills/task-delivery/scripts/test_task_graph.py -q`:
  99 passed, including explicit architecture packet hashes, missing must-read
  rejection and changed-guide -> degraded old run -> fresh reviewed continuation.
  The continuation fixture models the result of semantic maintenance; real
  Project Start decision/maintenance lifecycle is covered by its own suite.
- `python3 -m unittest discover -s tests -p test_architecture_contract.py -v`:
  7 passed. Correct public-interface implementation passes; three forms of private
  import fail despite identical output; wrong behavior fails despite legal import.
  Scoped installation, concurrent target drift rejection, symlinked-parent
  rejection and exact rollback after injected failure are covered in temporary homes.
- `python3 scripts/check_all.py`: exit 0, all workflow checks passed, including
  Project Start bootstrap/maintenance/adversarial and legacy compatibility checks,
  generated-role parity, validators and Task Delivery tests.
- Full-suite log after the installer parent-validation repair was retained in the
  task's temporary verification workspace and ended with
  `All workflow checks passed.`.
- `git diff --check`: exit 0.

## Behavioral fixture evidence

Fixture: `tests/fixtures/architecture-contract/` with accepted A1/E1/E2,
public payment interface, pending notification feature and executable `check.py`.

Fresh plan acceptor `/root/architecture_plan_negative_smoke` rejected private
payment-storage access and bypassing check.py. Corrected public-interface plan
was accepted: `plan-negative-smoke-corrected-20260914-b9e63d72`.
It correctly found no need for external architecture research for this task.

Fresh worker `/root/architecture_worker_smoke` read all explicit fixture documents
and candidate instructions, implemented only the temporary notification module
using payments.public, and ran check.py successfully. Root independently read
the actual implementation and reran check.py: PASS.

Project Start semantic smoke `/root/project_architecture_docs_smoke` read candidate
contracts and fixtures. For the hypothetical new CSV automation it chose one
stdlib process, self-contained docs and honestly planned/review-only checks;
unavailable playbook did not block clear work or produce invented sources. For
hypothetical unauthorized private import it preserved A1/E1/E2 and classified the
observed divergence as factual documentation, not a permitted rule change.
This is a read-only scenario evaluation, not a claim to have executed a new real
bootstrap or changed the fixture. Actual bootstrap/maintenance state transitions
are covered by the Project Start runner suite (65 tests passed separately).

Whole source candidate accepted by `/root/architecture_contract_result`:
`architecture-source-20260914-4b3d91e7`. The reviewer independently ran the seven
focused tests, inspected active generation and reconciled the behavioral findings.

## Scoped installation and rollback

`install_update.py` is task-specific and calls existing installer replacement,
backup and manifest helpers for exactly two skills and five role files. It never
writes config.toml, global policies, unrelated skills or other hosts. A prepare
receipt binds source and installed manifests; intervening drift rejects apply.
An injected installation failure restores exact prior targets and preserves the
rejected candidate under the backup directory, without deleting either version.

Prepared WSL installation receipt was retained in the task's temporary
verification workspace.
Scoped apply: PASS. Backup:
`<CODEX_HOME>/backups/agent-graphs/<timestamped-backup>`.
Scoped verify: PASS for both skills and all five roles; config hash unchanged.
Independent backup comparison: all seven saved targets exactly match the prepared
before-manifest. Loading installed task_graph.py and generating a new plan
confirmed Architecture conformity lies inside reviewed markers: PASS.

Fresh installed-file scenario and whole-result completion receipt are retained in
the Task Delivery run. This validates reading installed guidance in fresh context;
it does not assert that this already-running parent session reloaded cached roles.

## Limits

No mass migration of existing project docs or new runtime schema/graph gates.
The fixture's AST check covers static payment-internal imports, not every possible
dynamic data-access or event coupling. Human/model review remains necessary for
semantic rules. Behavioral scenarios are evidence for those cases, not a guarantee
that every future agent will comply.
