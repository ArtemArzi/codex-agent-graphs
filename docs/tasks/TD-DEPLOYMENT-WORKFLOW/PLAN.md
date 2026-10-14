# Deployment YAML workflow: implementation plan

Date: 2026-10-14. Status: implemented, installed and independently accepted.
Plan acceptance: PLAN-DEPLOYMENT-YAML-20261014-PASS-84D6C1F9.
Original source: codex-agent-graphs main 5471689ab2378f5a2935a3c7d6e8ebd190ec123b.
Candidate: /tmp/deployment-skill-20261014-01a1387f/candidate.

## Outcome and authorization

Implement the user's Deployment skill with an agent-readable YAML workflow,
adaptive project checks including E2E, and compatible Project Start/Task Delivery
handoffs. User requests implementation plus deep independent review from multiple
sides. Sol roles only, no Astra. Research-only authorization is superseded for
skill implementation; production/project CI changes and remote push are excluded.
Prepare includes ordinary authorized reversible local configuration work.

Accepted research/design: RESERCH docs/research/2026-10-14-unified-deployment-standard.md
and deployment-contract-draft.md; research acceptance RESULT-DEPLOY-STANDARD-20261014-PASS-7F93C2A8.
This is a materially new implementation outcome requiring fresh plan/result
acceptance: cross-skill evidence, safety, installer and execution contracts.

## Architecture and ownership

- No new graph.json, graph controller, agents or schema/identity changes to old
  Project Start/Task Delivery runs. Use native Task Delivery with this durable
  plan and normal independent reviews; no controller solely to record receipts.
- workflow.yaml is read by the agent; its milestones route prepare/release/resume
  to native project owners. It is not an executable GitHub workflow and not a
  generic YAML shell interpreter. Project CI YAML remains owned by the project.
- A small standard-library Python helper validates a JSON project mapping and
  produces check plans/dependency ordering. It never executes commands, deploys,
  restores data, grants authority or owns a second release journal.
- Test kind is an arbitrary project label. Phase is source/artifact/environment/
  postdeploy/scheduled. Checks name their execution method, environment, prerequisites and
  required input bindings; profiles select project-approved check IDs. Prerequisite
  closure and phase ordering must be correct. E2E runs where its stack exists;
  it is not an unconditional duplicate before CI. No automatic affected-test
  omission or invented coverage thresholds.
- Check method is command or manual. Command checks reference an argv/cwd command
  ID; manual checks instead require an explicit acceptance/evidence owner and
  criterion reference. Manual acceptance is not synthesized from an exit code.
  Environment setup/readiness and artifact production may be explicit prerequisite
  check IDs in the dependency graph; checks separately bind source or artifact
  subject and named environment identity. Missing prerequisites/subjects remain
  visible blockers. A phase sort alone is insufficient; dependency closure and
  phase-consistent topological ordering are required.
- Existing quality document owns requirements, engineering/native scripts own
  commands, deployment runbook owns operational policy. Mapping references these
  owners; it does not create a competing requirement database.
- Evidence is bound to source/config/toolchain/environment/artifact/check recipe
  as applicable. Helper may identify a potential same-input reuse, but never
  skip a check or label release trusted from supplied JSON. Reuse requires the
  project's native verifier/attestation; live observations remain fresh.
- Native status/journal/locks/CAS and recovery remain project-owned. UNKNOWN
  requires reconciliation, compatible code rollback differs from DB restore.

## Owned paths

- skills/deployment/: SKILL.md, workflow.yaml, agents/openai.yaml, focused
  references, one project-mapping template and Five Sites/Jaguar examples,
  scripts/deployment.py and behavioral unit tests.
- skills/project-start/SKILL.md + references/quality-and-intake.md: short optional
  deployment route and test-phase/environment handoff. No mandatory coverage role.
- skills/task-delivery/SKILL.md + references/testing-and-review.md: preserve
  arbitrary check IDs/types, phases/prerequisites/subjects/actual evidence and
  deferred requirements in existing task summary/handoff. No runtime/schema edits.
- skills/production-audit/SKILL.md: narrow shared-owner/readback link only.
- scripts/install.py: add deployment to existing SKILLS list only.
- scripts/check_all.py: compile helper and run its nested test suite.
- tests/test_install.py: new-tree install/helper/idempotence/settings-preservation.
- README.md, README.ru.md and this task's PLAN/HANDOFF: discoverability and honest
  validation/delivery boundaries.

No unrelated skills/policies/config/models/roles/hooks, existing graph definitions,
secrets, projects' source/CI or production writes. Children are leaves; at most two
writers, normally root-only implementation. Discovery joined: one explorer
confirmed source clean, existing consumer seams and 31 WSL/30 Desktop trees in sync.

## Steps

1. Freeze precise helper/mapping contract; fresh task_plan_reviewer acceptance.
2. Scaffold deployment through system skill-creator, author concise skill/YAML,
   phase-aware check and evidence references, usable template/native examples.
3. Implement read-only helper and tests for real planning/invalidation boundaries.
4. Add narrow consumer integration and installer/test wiring; preserve graph bytes.
5. Run focused checks, generic skill validation and full scripts/check_all.py once
   integrated. Read-only conformance rehearsals for Five Sites/Jaguar examples.
6. Deep review: two non-overlapping block reviews (helper/evidence/test edge cases;
   consumer/install compatibility), one independent fresh-agent behavioral forward
   test on disposable fixtures; reconcile, targeted revalidation as necessary.
7. DIFFERENT fresh task_result_reviewer whole-result acceptance, with original
   request, plan, diff and all evidence. No missing check is PASS.
   This is candidate acceptance for safe delivery, not installed-outcome completion.
8. Deliver exact owned paths to canonical source with before-image/CAS checks and
   backups using sandbox escalation after a reviewable accepted candidate exists.
   No force/push/commit required. If source drift exists, preserve and reconcile.
9. Make skill usable through existing skills-only installer in WSL/Desktop only
   if fresh plan shows exactly intended new/consumer skill trees differ and all
   other maintained trees/runtime are in sync. This operation preserves config,
   models, roles, profiles, policies and credentials. Snapshot hashes/protected
   surfaces, preflight -> backup/transaction -> exact readback -> repeat idempotence.
   Installer has no per-skill selector; unexpected drift blocks installation of
   unrelated changes, not task implementation. Report any permission/review block.
10. Send the SAME task_result_reviewer a targeted delivery packet: canonical and
    dual-home exact manifest readbacks, protected-surface hashes, installer verify
    and repeat idempotence outcomes. Complete only after that delivery revalidation;
    do not open another acceptance pair or claim unavailable installation passed.

## Acceptance and failure oracles

- YAML clearly expresses conditional prepare/release/resume, authority/external
  action boundaries, native evidence/readback and failure outcomes; no graph added.
- Arbitrary unit/integration/E2E/a11y/security/migration/eval/manual/project checks
  can be configured without changing helper code; correct dependency closure and
  phase ordering; missing IDs/cycles/backward dependencies rejected.
- Phase is a release milestone independent of named environment. Test both
  source-phase E2E depending on source-phase local-stack setup and artifact/staged
  E2E depending on artifact production and staging readiness.
- Malformed/duplicate-key JSON, bool-as-int versions, unsafe relative paths,
  symlink owners/cwd, unknown fields, empty/invalid command IDs are rejected.
- A supplied PASS, stale/future timestamp, changed environment/artifact/recipe,
  missing required binding, failed/skipped required check cannot silently skip work
  or yield a release PASS. Native verification is an explicit next action.
- Mapping/plan creation has no subprocess execution or external writes; timeout,
  lost context, rollback and live verification rules exercised by fresh-agent
  fixture scenarios rather than pretending a planner is a production executor.
- Existing graph identities, schemas and tests stay unchanged/passing. Installation
  includes all new files and helper, preserves protected settings, supports two
  homes, readback and idempotence. No unrelated drift is overwritten.
- No app deployment/E2E/provider success or measured deployment acceleration claimed.

## Verification and recovery

Use Python unittest for helper behavior, native fixture/CLI tests and installer.
Use system quick_validate.py for skill metadata, existing repository check_all.py
for compatibility. YAML is agent-readable; validate it through the available YAML
validator when present, without introducing a production/runtime dependency.
No tests that merely mirror prose. Fresh-agent results must show actual actions
and outputs in disposable workspaces. Two no-new-evidence attempts stop the loop;
contract contradiction triggers development-recovery, routine defects repair in
place. Stop only affected external operation on missing authority/safety/data
decision, continue authorized preparation. Keep all failed evidence.

## Completion: 2026-10-14

All ten steps completed. Candidate acceptance:
RESULT-DEPLOYMENT-CANDIDATE-20261014-PASS-BC4072D9. The same independent whole-result
reviewer accepted actual canonical/dual-home delivery:
RESULT-DEPLOYMENT-INSTALLED-20261014-PASS-91F6A3D8. No outstanding repair items.

Canonical delivery applied 26 exact approved paths without deletions; WSL/Desktop
installation changed only deployment, project-start, task-delivery and
production-audit (88 files per home). Native verifier returned ok for both homes;
repeat install was in-sync; protected settings and aliases were preserved.
Source remains uncommitted; no project CI/production operation was performed.

Accepted candidate manifest SHA-256:
68b2ba5a04cf9b49f81a381cd612ed1b361182c428550a2891e31f9d9954c7b1.
It records the candidate before this factual PLAN/HANDOFF completion update;
skill code, consumer instructions and installed files remain accepted and unchanged.

See [HANDOFF.md](HANDOFF.md) and the durable
[result report](/home/artem/projects/RESERCH/docs/research/2026-10-14-deployment-implementation-result.md).
