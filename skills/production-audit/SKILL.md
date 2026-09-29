---
name: production-audit
description: Local-evidence production readiness audit for shipped apps, pre-launch reviews, post-merge checks, and "what breaks in prod?" questions without sending repo data to an external audit service.
metadata:
  origin: community
---

# Production Audit

Use this skill when the user asks whether an application is ready to ship, what
could break in production, or what must be fixed before a launch. This is a
maintainer-safe rewrite of the stale community production-audit idea: it keeps
the useful production-readiness lens and removes unpinned external execution and
third-party data sharing.

## When to Use

- The user asks "is this production-ready", "what would break in prod", "what
  did we miss", "audit this repo", or "ready to ship?"
- A feature was merged and needs a pre-deploy or post-merge risk pass.
- A public launch, demo, customer rollout, or investor walkthrough is close.
- CI is green but the user wants production risk, not only test status.
- A deployed URL, release branch, PR, or current checkout is available for
  evidence gathering.

## When Not to Use

- During active implementation when the right lens is line-level secure coding;
  use `security-review` first.
- For pure libraries, templates, docs-only repos, or scaffolds unless the user
  wants packaging/release readiness rather than application readiness.
- When the user asks for a formal compliance audit. This skill is engineering
  triage, not legal, financial, medical, or regulatory certification.
- When the only available evidence is a product idea with no repo, deployment,
  CI, or runtime surface.

## How It Works

Build the audit from local and user-authorized evidence. Do not run unpinned
remote code, upload repository contents to third-party services, or call
external scanners unless the user explicitly approves that specific tool and
data flow.

Use this order:

1. Establish the release surface.
2. Read recent changes and current branch state.
3. Inspect runtime, auth, data, payment, background-job, AI, and deployment
   boundaries that actually exist in the repo.
4. Check CI, tests, migrations, environment documentation, and rollback path.
5. Produce a short ship/block recommendation with specific fixes.

## Scope and applicable evidence

Before checks, read the project quality requirements and known decisions. Identify
which candidate/version, environment and user journeys the requested audit covers.
Ask only about missing information that changes the conclusion and cannot be
found in the project; explain its practical consequence. Respect an explicit
no-questions request, record material unknowns and continue independent checks.
Do not invent load limits, recovery targets or risk acceptance.

For release-level conclusions read [evidence-matrix.md](references/evidence-matrix.md).
Select applicable risks; a static site need not have payment or tenant tests.
Use permitted local checks and supplied evidence first. Restore drills, load
traffic, notifications and payment tests can mutate systems or incur costs;
perform them only in an authorized environment and scope. Otherwise record the
missing check and its next trigger. An audit request alone does not authorize
repairs, deployment or external actions.

## Evidence Checklist

Start with cheap, local signals:

```text
git status --short --branch
git log --oneline --decorate -20
git diff --stat origin/main...HEAD
```

Then inspect the project-specific surface:

- Package scripts, CI workflows, release scripts, Docker files, and deployment
  manifests.
- API routes, webhooks, auth middleware, background workers, cron jobs, and
  database migrations.
- Environment variable documentation and startup checks.
- Observability hooks, error reporting, logs, health checks, and dashboards.
- Rollback, seed, migration, and backfill instructions.
- E2E coverage for the user paths that matter most.

If a deployed URL is in scope, use browser or HTTP checks only within that
authorized target; redirects and related domains do not expand scope automatically.
Use only authorized test identities for credentialed checks.

## Risk Lenses

### Security And Auth

- Are public routes, API routes, and admin routes clearly separated?
- Are auth and authorization enforced server-side?
- Are secrets kept out of client bundles, logs, example output, and checked-in
  files?
- Are rate limits, CSRF protections, CORS policy, and upload validation present
  where the app needs them?
- Does the AI or agent surface defend against prompt injection, tool abuse, and
  untrusted content crossing into privileged actions?

### Data Integrity

- Do migrations run forward cleanly and have a rollback or recovery plan?
- Are destructive migrations, backfills, and data imports staged safely?
- Do database policies, grants, and service-role boundaries match the app's
  tenancy model?
- Are retries idempotent for writes, jobs, and webhook handlers?

### Payments And Webhooks

- Are webhook signatures verified before parsing trusted payload fields?
- Is each payment, subscription, or fulfillment webhook idempotent?
- Are replay, duplicate delivery, and out-of-order delivery handled?
- Are test-mode and live-mode credentials separated?

### Operations

- Can the app start from a clean checkout using documented commands?
- Are required environment variables named, validated, and fail-fast?
- Is there a health check that proves dependencies are reachable?
- Are deploy, rollback, and incident-owner paths documented?
- Are logs useful without leaking secrets or personal data?

### User Experience

- Are the launch-critical paths covered on desktop and mobile?
- Are forms usable on mobile without input zoom, layout overlap, or blocked
  submission states?
- Do loading, empty, error, and permission-denied states tell the user what
  happened?
- Is there a support or recovery path when a critical operation fails?

## Readiness decision

Report readiness for the named release and environment in the user's language.
Use one of these conclusions with its reason:
- **Blocked:** an observed defect violates a required release criterion.
- **Not established:** a required criterion lacks applicable evidence. State what
  check is missing and why release readiness cannot yet be claimed; missing
  evidence is not an observed product defect.
- **Ready within checked scope:** required criteria passed for this candidate
  and environment. List remaining nonblocking limits and any actual risk acceptance.

Do not average away a blocker. A small pilot is a separate scope with its own
criteria, not an automatic fallback for failed authorization or data integrity.
An audit conclusion does not authorize deployment, external writes or acceptance
of business risk. Keep an already authorized action distinct from a recommendation.

Avoid a numeric score by default. If explicitly requested, use an agreed rubric
and show this decision and the evidence matrix first; a number cannot override
failed or unverified required criteria. Without a rubric, explain the limitation
instead of inventing weights or a probability of safety.

## Owner-facing output

Lead with the decision, its scope and the most important reason in plain language.
Then show a compact [evidence matrix](references/evidence-matrix.md) for material
criteria. Do not duplicate every minor check in the user-facing summary.

Include:
- What must work and why it matters for this release.
- How it was checked, candidate/environment, result and evidence pointer.
- What remains unverified, the consequence and the next concrete check or fix.
- Which findings are actual blockers versus proposed improvements.

Use the existing project quality document for requirements and the existing
release/task report for observations. Preserve the project's owners of commands,
architecture and decisions. If no record exists, one scoped audit report suffices;
this skill does not require a new graph, checklist database or duplicate spec.

## Anti-patterns

- Treating green CI, a source-code marker or a numeric score as release proof.
- Calling a planned, skipped, blocked or mismatched-version check PASS.
- Copying secret values or raw matching credential lines into reports; use a
  redacted location and finding description instead.
- Running remote scanners, installing tools or uploading source/customer data
  without authorization for the particular tool and data flow.
- Trying extra domains, production writes, failover or restore drills merely
  because an audit checklist mentions them.
- Presenting legal reference checklists as current legal certification.
- Adding mandatory interviews, agents or all risk categories to every audit.

## See also

Use `verification-loop` for faithful command evidence, `security-review` for
focused implementation analysis, `deployment-patterns` for a release procedure,
and `e2e-testing` for applicable user-path checks. Select only capabilities needed
by the actual scope; this list is not a mandatory sequence.
