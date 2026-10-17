---
name: deployment
description: Prepare a project's deployment documents, native commands and CI/CD, or release and verify an exact candidate through its existing deployment path. Use for deployment preparation, an authorized release, or resuming an interrupted rollout; adapt checks including E2E to project requirements and environments.
---

# Deployment

Use [workflow.yaml](workflow.yaml) as the agent-readable prepare/release/resume
route. It describes milestones and conditions, not a new graph or a generic YAML
shell executor. Native project scripts/CI own execution and release state.

## Start from the project

Read nearest AGENTS.md, docs map, architecture/engineering/quality/deployment
owners, current Git and the existing task/release handoff. Preserve dirty work
and other operators. Identify source, artifact, operator version, target and native
operation separately. Existing decisions/current source outrank old receipts;
previous local PASS does not establish today's installed state.

When another independent task may share the target, source or release contract,
use available `chat-coordination` to establish current owners and dependencies.
Without its tools, preserve known work and isolate preparation. A reply or intent
never replaces native lock/CAS, release authority or journal reconciliation;
different repos/worktrees can still mutate the same service.

- **Prepare**: “готовимся к деплою”, first pipeline setup or a changed deployment
  contract. Inspect the existing path, choose the actual profile, update one
  owning runbook, prepare reversible local commands/CI and verify in isolation.
  This ordinary local work is included; do not ask again for each file. Buying
  resources, secrets provisioning, push/dispatch, DNS, activation and other
  external effects still require applicable authority.
- **Release**: use an already prepared path and exact candidate. Select the
  native lane, reuse valid evidence through its owner, run required missing work,
  invoke authorized native publication/activation and verify actual state.
- **Resume**: inspect the native journal/status, exact target/current and pending
  operation before continuing. An uncertain mutation is not safe to replay.

## Adaptive checks and project mapping

Read [checks-and-evidence.md](references/checks-and-evidence.md) when selecting,
running or reusing tests. Test kind is a project label; E2E, unit, integration,
accessibility, security, migration, performance, AI evals and manual acceptance
share the requirement/subject/environment/dependency model. Do not add or run
every category automatically. Follow project gates even if a generic profile
looks cheaper. Unknown impact widens investigation, not silent omission.

Read [check-placement.md](references/check-placement.md) when preparing or changing
local/CI execution. A pipeline can run locally, on a chosen runner or across both.
Choose one authoritative execution for each required check and candidate; share
native commands and verify transferable evidence instead of repeating full suites.
Preserve any separately required trust, platform, artifact and live checks.

Use native contracts directly when they supply adequate command/evidence mapping.
When useful, adapt [the template](assets/project.template.json) using
[project-contract.md](references/project-contract.md); reference existing owners
instead of duplicating their policy. Resolve helpers against THIS installed skill:

```text
python3 <skill-dir>/scripts/deployment.py validate --contract CONTRACT --project-root REPO
python3 <skill-dir>/scripts/deployment.py plan --contract CONTRACT --project-root REPO --context CONTEXT
```

The standard-library helper validates inputs and plans required checks; it never
executes commands, authorizes a release or creates a second journal. Exit 0 means
valid planning only. Potential reuse is `verify_reuse`, requiring the native
verifier on original evidence; supplied JSON cannot make a check PASS.

For an existing deployment read only the relevant [profile notes](references/native-profiles.md).
Five Sites/Jaguar mappings are read-only rehearsal examples, not replacement
pipelines or full readiness proof.

When changing a container build or real test dependency, read
[container and integration guidance](references/native-profiles.md#container-builds-and-real-test-dependencies)
for readiness, ownership and actual assertions; preserve native checks and scope.

When building/releasing container images or addressing image/cache accumulation,
read [image-lifecycle.md](references/image-lifecycle.md). Check local and target
storage separately, preserve native retention/recovery, perform authorized
selective cleanup and record the disk result or pending gap with the release.

## Execution, failure and completion

Read [operations-and-recovery.md](references/operations-and-recovery.md) before
external operations or resuming. Use native locks/CAS/admission/attestation,
preserve expiry and data compatibility, and promote the exact tested artifact.
A changed build-time profile creates a different static artifact. Do not cancel
an in-progress production mutation blindly or reset native budgets.

Repair check failures and invalidate dependent evidence; retain unaffected valid
work according to native policy. Missing mandatory evidence is not success.
Two attempts without new evidence stop the failing approach.

Prepare completes with a usable checked local pipeline/owning documents and
explicit missing target/authority prerequisites. Release completes only after
native reconciliation and fresh required identity/health/public-user-path proof.
Published image, queued content, HTTP 200 or helper exit 0 are intermediate.
Code rollback never implies DB/Sheets restoration or reversal of sent effects.

## Compatibility and human report

Use [handoff.md](references/handoff.md) with Project Start, Task Delivery or
Production Audit. Keep one quality owner and native journal. A skill switch does
not restart intake, invalidate unchanged evidence or add a review cycle. Inherit
host review/routing policy; this skill mandates no models/agents. Required
independent acceptance remains required where applicable.

Task Delivery may arrive through Software Factory: take the root's integrated,
reviewed candidate and combined evidence, not separate leaf PASS labels. Prepare
can run before implementation finishes when the release path needs work; it does
not approve that future candidate. After technical release verification, use the
bounded Product Care continuation in [handoff.md](references/handoff.md) when
application/effect belongs to the requested outcome. Release proof and product
effect remain separate; the handoff creates no automatic reads or schedule.

Tell the user plainly what is ready/released, where, what was actually checked,
the current outcome and any necessary action. Link technical subjects/receipts.
Distinguish local checks, deployment, provider delivery and human acceptance.
For a blocked external action, finish independent preparation and name exactly
the missing authority or evidence.
