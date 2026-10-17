# Technical maintenance of an existing product

Read for a code/data/dependency or recovery question about a running product.
Use the current Review, Diagnose or Follow-up pass; this is a technical lens,
not another lifecycle or a required audit of every module.

## Follow one useful path

Establish the actual source, built artifact, installed release and environment
through the existing runbook/evidence. They may differ. Trace one important
user operation through its entry point, responsible modules, persisted state,
worker/provider and result visible to its recipient. A healthy process or a
saved row establishes only its own part of that path.

Use permitted current evidence and relevant change history. Check the actual
callers and state owner before calling a module misplaced. Repeated scattered
changes or hard-to-test combined behavior can justify the available
`improve-codebase-architecture` survey; a clear local defect can go directly
to Task Delivery. Size and edit frequency alone do not justify refactoring.

Select the affected lens, not the entire list:

- **Data and background work:** inspect transaction boundaries, constraints,
  duplicate/concurrent processing and pending/failed work. Use accepted business
  invariants. Queries, indexes and capacity need the real workload and measured
  problem; do not infer a schema defect from a generic checklist.
- **Dependencies and configuration:** compare the relevant installed and pinned
  versions/configuration. For an actual upgrade, use official version-specific
  compatibility/migration guidance through Task Delivery and Deployment.
  An unfamiliar version is not evidence that it is unsupported.
- **Recovery:** read the existing backup/restore/rollback procedure and its
  resource, lease and dependency prerequisites before a permitted drill.
  A backup file does not establish restored data, relations or compatibility
  with queued work. Keep restore execution and its invariants with that owner.
- **External effects:** distinguish saved intent, attempted delivery, accepted
  provider receipt and the recipient's useful result. An uncertain send needs
  reconciliation under the native procedure, not an automatic replay.
  For lead intake, use available `reliable-leads` rather than rebuild its rules.

For a real failure, state the observed symptom, the first unsupported
assumption and the smallest observation that separates explanations. Keep the
immediate cause, unknown upstream cause and mitigation distinct. Missing access
or telemetry is unknown coverage, not evidence of health.

## Preserve the useful engineering continuation

A temporary fix should be visible to the next affected change, not buried in a
chat. Use the existing incident/runbook to record what it changes, why it is
temporary, the known owner or ownership gap, removal/review condition, relevant
compatibility constraint, and the user-path check after removal. A pinned
endpoint may also pin an old image; an ordinary restart need not remove either.
Do not invent an expiry, assignment or scheduled reminder.

For example: the bot process is running but cannot reach its provider; the
operator has a temporary endpoint override and a confirmed user reply.
That establishes recovery for the observed route, not the upstream network
root cause or the safety of keeping the override forever. On the next release,
read its removal condition and effective image before proposing a change.
If evidence already covers the question and no useful action remains, report
that bounded no-op.

Return one actionable finding, chosen task or justified no-op with its evidence,
unknowns and next condition in the existing owner. Existing authorization governs
whether implementation continues; this lens grants no probes, repairs, database
reads, upgrades or sends. It creates no monitoring schedule.

This reference is an independent synthesis of observed maintenance episodes.
[Google SRE monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
informs symptom/cause separation; the
[Workbook postmortem chapter](https://sre.google/workbook/postmortem-culture/)
informs actionable follow-through. Neither supplies project targets or authority.
