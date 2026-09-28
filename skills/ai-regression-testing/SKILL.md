---
name: ai-regression-testing
description: Choose and strengthen behavioral regression tests for AI-assisted code changes and bug fixes, including new critical rules before their first incident. Use for test-impact analysis, regressions and mock/real-path gaps. Respect project requirements; do not replace task orchestration or nondeterministic agent evals.
metadata:
  origin: ECC
---

# AI Regression Testing

AI-written code and AI-written tests can share the same wrong assumption.
Ground checks in the requirement, a reproducer or an independent observable
outcome. Use this skill to decide what behavior to protect; verification-loop
can run and report the checks when that skill is available. Neither owns the
user's whole delivery process or model/delegation policy.

## Establish the test obligation

Read the relevant requirements, quality policy, affected execution path and
existing tests. Use the project's commands and fixtures; a missing quality file
is a documentation gap, not a reason to stop a bounded fix or create a framework.

Ask the owner only about an unknown behavior that materially changes correctness
or acceptance. Explain the consequence and offer an informed option in plain
language. Do not ask them to select a test framework. Use known answers from
context; with explicit no-questions instructions, continue with reversible
stated assumptions without inventing business decisions or new authority.

Prioritize according to impact, changed behavior and history:

- A discovered bug gets a focused reproducer when practical and meaningful.
- A new critical rule, permission boundary, persistence operation or retry path
  can need tests before any incident. Prior bugs are one signal, not a prerequisite.
- An existing correct test is reused unless behavior legitimately changed.
- A small low-risk reversible edit may need inspection or an existing check;
  do not create tests that only mirror the implementation or inflate counts.
- Use an established coverage threshold if the project has one; do not invent a
  universal quota. A percentage does not establish that critical cases are tested.

## Choose the smallest sufficient boundary

| Risk | Useful checks and timing |
| --- | --- |
| New/changed rule | Unit/component scenarios with valid, invalid and boundary inputs, added with the rule |
| Bug fix | Reproducer of the intended defect, then affected regression tests after the correction |
| API/database change | Contract/shape checks plus real test adapter/persistence checks for mapping, constraints and transactions |
| Permissions | Rejection and allowed access through the server boundary, with representative users/data |
| Repeated or concurrent action | Repeated requests and concurrent attempts at the affected transaction/queue boundary |
| Failure/restart | Interrupt the relevant test service or worker; verify persisted state and the agreed continuation/retry behavior |
| Load-sensitive change | Performance/load evidence using the agreed workload and threshold before relevant release or scale-up |
| Migration/restore | Compatibility and restoration in a suitable test environment before depending on the changed mechanism |
| UI workflow | Component checks plus critical E2E/error states where needed; verify affected visual/accessibility behavior |

Regression describes the purpose of rerunning checks; it is not a separate
level beside unit/integration/E2E. Add a check with the behavior it protects;
rerun it after changes affecting that behavior and at the project's release
boundary. Deferred load/restore/provider checks need a reason, next trigger and
an honest limitation on readiness, not a silent PASS.

## Prove the check can detect a defect

For a bug fix, where practical, observe failure on the broken behavior and
success after the fix. Otherwise use a known wrong fixture/version, a controlled
mutation in an isolated test workspace, or another independent observation.
Never damage live code/data to manufacture a failure. A missing dependency or
an unrelated compile error is not a reproduction of the business defect.

Keep input fixtures and expected outcomes tied to the requirement. Do not change
the expected value merely because the implementation disagrees. If intended
behavior is ambiguous, record the gap rather than teaching the test to agree.
If the check could not be shown to discriminate, report that evidence limitation.

## Mock and sandbox boundaries

Mocks help isolate behavior; they do not prove the real database query, migration,
authorization, transaction or provider delivery. A test of a sandbox response
proves only that path. To claim parity, exercise both relevant paths against the
same agreed contract; confirm that representative, nonempty fixtures ran.

For data changes, inspect persisted effects using a real test database/adapter
when that is the relevant boundary. For external providers, distinguish a mock,
a provider test environment and confirmed live delivery. Read
[regression-scenarios.md](references/regression-scenarios.md) for API mapping,
empty-fixture, restart and UI rollback examples when those risks apply.

## Run and communicate

Use the project's existing runner. Preserve the underlying command's exit code;
inspect intended test discovery and assertions. Distinguish a product failure,
a pre-existing failure and an unavailable environment. Do not install a runner,
create a slash command or force every project into a sandbox mode to fit this skill.

For substantial work tell the owner which behavior the check protects and why.
Report what passed, what failed, what was not run and what remains outside the
covered scenarios. Passing tests reduce specific regression risks; they never
guarantee that a defect cannot recur under different inputs or environments.
Stop broadening tests after the relevant evidence and required gates are met.
