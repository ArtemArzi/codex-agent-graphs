# Evidence matrix for release readiness

Use for a release-level audit or when summarizing materially different checks.
A small scoped audit can use a few rows; do not create a second quality policy.
Project requirements define intended behavior; observations establish only what
was actually checked. Record unknown requirements rather than choosing them for
an owner. Prefer concise, user-language descriptions over test terminology.

## Each material row

| Requirement / why it matters | Required for this scope? | Method, environment and version | Observed result and evidence | Status | Missing check / next trigger |
| --- | --- | --- | --- | --- | --- |
| One observable requirement | Required, nonblocking or unknown, with basis | What actually ran/read and on which candidate | Actual observation, dated command/CI/report/source reference | See below | Remaining action and when it is needed |

A method is not a status. Name whether evidence is code/config inspection, a
local automated check, integration test, deployed-browser/HTTP observation,
provider-confirmed result or human/specialist review. These can complement each
other; none automatically proves the rest. Keep the command and full receipt in
the owning report/CI; link to them rather than pasting bulky or sensitive logs.

Statuses:
- **PASS:** the stated criterion is supported for the stated scope/environment.
- **FAIL:** applicable evidence contradicts the expected outcome.
- **NOT CHECKED:** needed evidence is absent, stale, skipped or for another scope.
- **BLOCKED:** a check could not finish due to access, environment or another
  prerequisite; identify the obstacle. This is not automatically a product defect.
- **NOT APPLICABLE:** the requirement does not apply, with a scope-based reason.
  Lack of evidence or access is never a reason for this status.

For mixed evidence split the criterion or keep the unresolved portion explicit.
A missing required check prevents claiming readiness. An unknown requirement
that could change release acceptance stays unresolved; it does not silently
become nonblocking. Nonblocking risks need their real impact and, when necessary,
recorded owner acceptance; do not manufacture approval or a person's role.

## Choose by the product and change

| Risk | Useful evidence when applicable | Insufficient by itself |
| --- | --- | --- |
| Access to another user's data | Positive and negative role/tenant scenarios through the real enforcement boundary | Login works; middleware name found |
| Lost or duplicated writes | Stored result, retries/concurrency and transaction behavior | Button success message; happy-path unit test |
| External delivery | Matching provider receipt and final record in the relevant environment | Mocked API success; request merely sent |
| Recovery | Restore/rollback rehearsal and observed usable data/service against agreed targets | Backup schedule; recovery document exists |
| Load | Measured workload, errors, latency and saturation against project targets | Fast local page; invented user-count limit |
| UI and accessibility | Critical journeys, error/empty/denied states on applicable viewports and assistive checks | Build passes; screenshot of one happy state |
| Public web delivery | Authorized live URL behavior, indexability/redirects/assets where required | Configuration file exists; assuming private pages need indexing |
| AI actions and costs | Task outcomes, allowed tools, failure cases and budgets in representative evals | Fluent response; one model run; unmeasured confidence score |

Apply only relevant rows. Defer expensive integration, restore or load checks to
the agreed environment/release boundary, preserving their impact on readiness.
Specialist/legal review is a separate evidence source when required; do not copy
jurisdiction-specific claims from a dated checklist as established current law.

## Small hypothetical example

For a release that requires tenant isolation and verified recovery:
- Tenant isolation: PASS in staging on candidate R, two-account integration test,
  receipt attached. This supports staging isolation for the exercised paths.
- Recovery: NOT CHECKED; a backup schedule exists but no restore was observed.
- Payments: NOT APPLICABLE; this product does not accept payments.

Conclusion: readiness is not established because required recovery evidence is
missing. Next step: the authorized restore rehearsal in a test environment, or
resolve the missing environment/authority first. Do not report a measured outage
or declare a safe public pilot from those facts.

## Origin of the adaptation

The method/applicability distinction was informed by the reviewed snapshot of
[web-audit's checklist](https://github.com/haraldalder-vibemogger/web-audit/blob/6359ae321861c1575f5ed77afef301f53fc5267d/reference/checklist.md).
This is an independently written adaptation for the existing production-audit
workflow, not a port of its scripts, questionnaire or legal references.
