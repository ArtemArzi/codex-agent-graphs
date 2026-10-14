# Review and diagnosis

## Choose the question and readers

Start with the user's focus and the last unresolved decisions. Prefer a small
number of relevant reads; do not sweep all history, logs, repositories, or skills.
For each important source establish what it covers, when it was collected, and
whether reading/probing it has side effects or material load.

Possible lenses, selected by applicability:

- Availability and critical path: permitted external probes, sanitized errors,
  latency, queue age, provider state, dependency failures.
- Repeated operations: support episodes, manual retries, waiting, workarounds,
  unfinished handoffs, storage/quota/cost pressure, maintenance evidence.
- People's work: completed and abandoned scenarios, reach, return use, help
  required, acceptance by the actual recipient, and quality of the result.
- Sustainability: supported dependencies, recurring effort, recovery readiness,
  or whether unused complexity should be simplified or retired.

Use existing definitions and tolerances. A static site need not have payment or
tenant checks; an internal document workflow need not have server telemetry.
Backup existence/freshness is distinct from verified restore. A restore drill,
new instrumentation, provider retry, or alert configuration is separate work
through its owner and applicable authorization.

## Validate the observation

Check event meaning and collection changes, partial periods, comparable cohorts,
actual exposure, environment, traffic exclusions, and source freshness. A report
with no events may mean no traffic, broken collection, an incomplete read, or a
real absence. Retention/rotation may have removed the relevant logs.

Distinguish one user episode from several events or messages about it. Increased
support can reflect friction; reduced support can reflect abandonment. A faster
component may leave end-to-end waiting unchanged or shift effort to another role.
Do not infer motivation from an event sequence or cause from release timing.

## Investigate a concrete signal

Describe the observed failure and affected path before choosing a fix. Locate
the first unsupported assumption: goal/requirement, process, data/measurement,
interface, implementation, dependency, or evidence collection.

Compare plausible explanations and choose the smallest permitted observation
that separates them. Check existing runbooks, source, framework mechanisms and
primary documentation as needed. A provider or agent diagnosis is a hypothesis
until its decisive evidence is verified. A recurring failure without new evidence
calls for changing the approach, not repeating a workaround indefinitely.

If an active material incident is established, use its response owner and
runbook. Preserve service/data boundaries and authorized actions; avoid restarting
healthy unrelated components or retrying an uncertain external effect. If that
authority or reader is missing, prepare the actionable evidence and name the
specific dependent gap while continuing other permitted investigation.

## Triage without building an orphan backlog

Look for an existing task/incident about the same episode or cause. Add meaningful
new evidence or changed consequences to that owner; do not create a second queue.
Rank impact/reach, repetition, confidence and the next step's cost/reversibility.
Unknown frequency or loss remains unknown. Avoid invented financial estimates.

Choose one of: keep current behavior; observe a named gap; diagnose; hand off a
specific task/incident; propose a small experiment or process change. A new
feature is only one possible response. Defer with a concrete reconsideration
condition; prune or retune repeatedly ignored/noisy findings.

An ordinary no-op needs successful, sufficient readings for its stated scope.
Keep unchanged non-actionable results quiet according to the user's notification
intent. A failed reader requires an explicit coverage gap, not a reassuring no-op.
The user-facing result can be short even when the evidence record is detailed.
