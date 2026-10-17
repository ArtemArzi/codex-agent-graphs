# Local and CI execution

Pipeline means the project's ordered checks/build/publication/deploy, not a
particular hosting service. Run it locally, on an isolated runner or in a hybrid
lane according to resources, target compatibility and the project's trust policy.
GitHub is optional; local is not automatically faster or production-equivalent.

## Assign work once

Use existing scripts, Make targets or package commands as the shared entrypoint.
Local and hosted wrappers call those commands rather than maintain separate test
recipes. Prefer the existing real-stack/Compose setup when appropriate; do not
introduce Dagger, Earthly, act or another platform without a demonstrated need.

In the existing runbook, map each required check ID to its trigger, authoritative
runner, source/artifact, environment/setup, evidence verifier and fallback. Link
measured duration when available. This is a runbook view of existing checks, not
new mapping-schema fields or a second registry. One runner per check/candidate is
the normal lane; independently required security/trust/platform checks retain
their purpose and explain any intentional repetition.

| Lane | Typical allocation | Completion condition |
| --- | --- | --- |
| Local | Full pre-activation pipeline in a project-compatible isolated environment | Native required results and permitted build/publish path; real target checks remain fresh |
| Hybrid | Heavy suite/E2E locally; hosted verification of accepted evidence, missing platform checks and publication | Native trust accepts local evidence for this candidate; final artifact is checked |
| Hosted | Heavy work on the chosen runner when local capacity, compatibility or trust is inadequate | Same native recipes and project-required coverage; local development checks need not duplicate the full release suite |

For hybrid, a cheap remote gate verifies evidence and does only missing or
independently necessary work. Source tests and smoke of a new production image
prove different things. Build once/promote the tested artifact where native
policy permits; a rebuilt artifact needs its own artifact checks even if source
tests remain valid. CI/CD and all pre-activation work may be local; GitHub is not
a mandatory handoff or publication step.

## Transfer evidence, not a green label

Run the project's release suite against its exact committed/frozen candidate,
with pinned relevant runtime/dependencies and isolated test data. Keep original
results/logs outside the candidate when their creation would change its identity.
Bind the receipt to the native source/tree, check policy/recipe, relevant config,
toolchain, environment/fixtures and artifact as applicable.

The native verifier must accept the original receipt, its inputs, completeness,
freshness and trusted issuer/runner under the project's established policy.
Maintainer attestation is a documented trust choice, not independent proof of
execution. A hash, a personal workstation or signed arbitrary PASS is insufficient.
Verifying in GitHub does not change the original check's environment or prove it
ran there. Untrusted contributor evidence needs the project-approved isolated
trusted-runner path; never expose production credentials or weaken branch rules.

If that trust bridge does not exist, keep required checks and name the gap; run
the suite on an adequate approved runner until a bridge is implemented/tested.
Changed final merge commit, recipe, dependency/config/environment inputs or
expired/incomplete evidence requires affected revalidation. Identical input alone
does not authorize dropping a project-required independent check.

`act` can debug supported workflow steps, but its [documented gaps](https://nektosact.com/not_supported.html) include
permissions, environments, concurrency and OIDC. It cannot alone validate the
hosted admission/security path. Use native local commands for test execution and
the real owner for platform-specific semantics.

## Measure before adding machinery

Separate queue/startup, dependency/environment setup, tests, artifact build,
transfer, verification and recovery/retries. Compare the same workload and record
cold/warm/cache state, CPU/RAM limits and critical path; summed parallel step times
are not elapsed release time. Cache reuse is distinct from new test execution.
Bound concurrency to available resources. Remove artificial ordering only where
there is no real dependency and resource capacity permits it. No universal timing
target or performance gain is promised; use observed project bottlenecks.

For whole-cycle claims include decision/approval waiting, staging, activation,
fresh public verification and any rollback, not only a successful test interval.
State the start/end boundary and failed attempts; compare the same release scope
and trust requirements. A synthetic/warm staging improvement does not establish
production downtime or end-to-end savings. Store timing with native evidence,
without introducing another telemetry platform for a single measurement.
