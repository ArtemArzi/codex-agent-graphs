# Deployment contract

Reuse an existing good runbook. Fill from observed source, accepted requirements
and actual commands; unknown facts stay unknown.

## Owners and units

Link architecture/quality/engineering owners and optional mapping. Describe actual
static/web/worker/data/proxy/cloud units, dependencies and compatibility.

## Environments and authority

Name targets and allowed actions. Private endpoints/secret version refs stay in
established private mapping. Separate provisioning/publish/activation/data restore.

## Checks and CI/CD

Link required check IDs/commands, profile/runner/milestone/subject/environment,
prerequisites and evidence owner. Include applicable E2E/manual/periodic checks,
reuse/invalidation and deferred gaps. Do not copy the whole quality policy.

Choose local, hosted or hybrid execution per check; reuse native entrypoints.
Fill this view with required checks only, linking their existing definitions:

| Check ID / trigger | Authoritative location / environment | Original evidence / native verifier | Work still needed elsewhere / reason | Measured cost |
| --- | --- | --- | --- | --- |

Document how a local result is accepted for the exact final candidate, and the
approved fallback when trust, inputs or local capacity are insufficient. Preserve
independently required checks; explain intentional repeats. Record cold/warm/cache
state and resource limits when measuring. GitHub execution is optional.

## Artifact and release

Document source/operator/toolchain/config/artifact identity, authoritative build/
check/publish commands, native lock/CAS/admission/switch/readback and retention.

## Failure, interruption and recovery

Name the native journal/status. Explain pre/post-switch failure, UNKNOWN,
idempotent continuation, compatible code rollback and separate data recovery.
Include new-data/old-version compatibility and applicable isolated failure rehearsal.
Define bounded postdeploy observation, safe activity and error/resource criteria;
name what remains unverified when traffic or evidence is insufficient.

## Evidence and remaining gaps

Link actual rehearsal results/limits. Local checks, live release, provider delivery
and human acceptance have separate status. Name next action and material unknowns.
