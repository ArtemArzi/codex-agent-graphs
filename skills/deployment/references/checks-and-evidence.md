# Adaptive checks, including E2E

Start with the project's quality owner and exact engineering/native commands.
Separate a requirement, existence of a test and an observed run. Preserve native
full suites and financial/security/migration gates. A profile cannot authorize
skipping required work. Test labels are descriptive, not a fixed enum.

| Milestone | Typical work | Prerequisites |
| --- | --- | --- |
| Source | Unit/types/lint/contracts, source-based local-stack E2E, AI evals | Exact source/toolchain/fixtures; stack readiness when needed |
| Artifact | Packaging smoke, bundle/browser checks | Exact artifact/config; production/build receipts |
| Environment | Staging integration/E2E, routing/workers | Authorized running candidate environment and compatible data |
| Postdeploy | Fresh version/health/public path/readback | Actual activated target; writes only if specifically authorized |
| Scheduled | Load, restore drills, periodic security/long tests | Their own scope, environment and trigger/freshness policy |

Milestones are not environment types. A local E2E may run in source phase after
local DB/browser setup; staged E2E may consume an artifact. Dependencies describe
actual order. Keep custom test types and native aggregate suites. Manual acceptance
names criterion/owner; AI cannot manufacture approval from a tool exit code.

During development run affected checks; at release use the project-required
profile. Do not run every category after each edit or repeat unchanged full suites
in local/CI by habit. Each required check has an authoritative runner, environment,
subject and outcome. Packaging smoke and unit tests often prove different things.
For placement and transferable local results, use [check-placement.md](check-placement.md).
Select tests by the changed mechanism: config/rules, imports and background jobs
can need bounded resource/adverse-input checks even when no app-code file changed.
This does not add a load test to every release.

Keep the first failure and each retry result. Passing after retry is flaky/retried
evidence, not an unqualified clean PASS; the native quality policy determines
whether it can satisfy a required check. Retry only safe bounded test work, not
the whole mutating deployment. Quarantine needs explicit project policy, owner,
repair deadline and compensating coverage; required evidence cannot vanish.

Record check ID, original command/receipt, runner/trust, applicable source/operator/
toolchain/config/data/environment/artifact identities, time and actual result,
required skips/gaps. Safe version references suffice; never raw secrets/hashes.

Native owner decides reuse. A helper match needs verification of original evidence
and current policy. Supplied `passed`, a digest or old environment observation
does not establish trust. Changed subjects/validator/policy/toolchain/config/data
invalidate dependent evidence. Unknown closure widens checking; caches are not PASS.

Disruptive/provider-write tests require their agreed scope. Mock delivery tests
do not establish real delivery. Missing target access stays a gap; local E2E is
not production proof. Postdeploy readback is always fresh. Keep this mapping in
the existing task/handoff, not a second quality registry.
