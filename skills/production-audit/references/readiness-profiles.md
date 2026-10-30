# Release readiness by product and stage

Read for whole-application delivery, pre-release readiness or an explicit
"what did we miss?" audit. Keep requirements in the project's existing QUALITY
owner and observations in its task/release report. This reference selects useful
checks; it adds no controller, tracker, scanner installation or fixed agent chain.

## Put checks at the useful boundary

| Stage | Existing owner | Useful work |
| --- | --- | --- |
| Foundation | Project Start | Establish critical journeys, data/access/integration boundaries, workload and recovery goals; mark material unknowns |
| Implementation | Task Delivery / Software Factory | Add checks with the affected behavior; run relevant regression/security/UI checks and measurements |
| Integrated candidate | Production Audit | Select applicable rows, reconcile current evidence and perform missing authorized checks; conclude readiness for this candidate/stage |
| Release | Deployment | Execute the authorized native path with the tested subject, prerequisites and recovery plan |
| Published environment | Deployment / existing operations owner | Verify actual version and safe critical path, then observe relevant user/runtime signals |

A small local fix keeps targeted checks. Use the whole readiness pass when the
requested outcome is an application ready for handoff/release, not for every
slice or document edit. Reuse the applicable review already required by host
policy. Missing optional companions do not authorize installation or invented
PASS; retain the exact missing capability and continue independent work.

## Select a profile, then adapt it

| Product | Select when relevant | Usually outside this profile |
| --- | --- | --- |
| Public site | Critical pages/forms, mobile/keyboard states, browser performance, public URL/indexability, permitted delivery path and redeploy/rollback | Tenant/payment/DB tests when those surfaces do not exist |
| CRM or stateful app | Roles/tenants, imports/exports, concurrent/retried writes, queues/integrations, representative data, migrations and usable recovery | Indexing private screens; treating robots as access control |
| Store/payments | App profile plus order/stock/payment invariants, trusted provider notifications, unknown outcomes, reconciliation/refunds and abuse limits | Real purchases, messages or refunds merely to satisfy the checklist |
| AI/agent extension | Representative outcome evals, allowed tools/data/effects and actual usage/limits | Treating every non-AI application as an agent system |

Profiles overlap. Record why a risk applies instead of demanding every row.
Use the project's critical-flow owners for concrete business/provider rules.
Security depth, expected traffic, acceptable data loss/downtime and spending are
project decisions; a reference example does not accept them for the user.

## Select evidence for the affected risk

- **Security and supply chain:** inspect the real enforcement boundary, positive
  and negative roles/object ownership, sensitive inputs, sessions and exposed
  data/secrets. Use available security-review/codex-security and project-pinned
  dependency, source or secret checks for their actual coverage. ASVS requirements
  can guide selection with versioned IDs. A passive scanner or dependency report
  does not establish business authorization or absence of all vulnerabilities.
- **Page/UI performance and accessibility:** for an HTML interface read
  [web-measurements.md](web-measurements.md). A fast backend is not evidence that
  the browser path is responsive, accessible or visually correct.
- **Capacity:** identify the operation mix, intensity/duration, dataset/cache,
  runner and environment differences. Record both requested and delivered load,
  dropped/unstarted iterations, latency distributions, errors and saturation.
  A closed-user loop can deliver less work as responses slow; choose an arrival
  model when the goal is a fixed incoming rate. Undelivered load leaves capacity
  unproven; investigate generator and service before assigning the cause.
- **Correctness under load/failure:** verify stored business outcomes, repeats,
  ordering, concurrency and queue/provider results, not only HTTP status/latency.
  Fast wrong data is a correctness failure. Use genuine stack boundaries where
  required; synthetic reports do not prove a live provider or target database.
- **Recovery:** where required, rehearse in a separate authorized location and
  verify usable restored data/service, loss and elapsed validation time against
  accepted goals. A backup schedule or completed restore job is insufficient.
  Code rollback does not reverse migrations, delivered messages or payments.
- **Operations:** check startup/config, dependencies, useful redacted errors,
  health and the existing response/rollback owner. After an authorized release,
  verify the actual subject and observe latency, traffic, errors, saturation and
  relevant worker backlog. An idle graph with no traffic proves little.

Use the evidence-matrix's PASS/FAIL/NOT CHECKED/BLOCKED/NOT APPLICABLE statuses.
Read the raw result as well as process exit: an error, zero executed audits,
incomplete data or skipped required subject is not PASS merely because JSON
output or a wrapper returned 0. Failure to run is not automatically a product
defect; missing access is not N/A. Report supplied/inspected evidence separately
from checks performed by this agent, including candidate and environment.

Required-now failures block the named readiness conclusion. A missing required-now
check leaves it not established. A later-stage check remains explicitly deferred
with its trigger; do not demand production field data before a first launch or
call that unavailable data a successful measurement. Revalidate affected evidence
when its code/artifact/environment changes; preserve valid unchanged results.
No numeric overall score can average away a required defect or evidence gap.

Active scans, load, restore and external writes require their actual allowed
target, data flow and environment. A profile adds no authority to run them.
Use existing project runners; do not copy unpinned remote scripts, add a schedule
or upload source/customer material merely because a tool appears in a reference.

Sources for the selection model: [OWASP ASVS](https://asvs.owasp.org/),
[k6 models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/),
[dropped iterations](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/dropped-iterations/),
[Google PRR](https://sre.google/sre-book/evolving-sre-engagement-model/) and
[recovery testing](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_backing_up_data_periodic_recovery_testing_data.html).
These inform checks, not mandatory vendors or an enterprise organization.
