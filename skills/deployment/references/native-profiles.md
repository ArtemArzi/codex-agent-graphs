# Native profiles and adding a project

Examples are mapping/navigation aids checked against local source on 2026-10-14.
They are not installed project configuration, executed tests or release authority.
Read fresh project instructions/runbook before use.

## Five Sites

Use [five-sites.example.json](../assets/five-sites.example.json) for read-only
shape/path rehearsal. Existing release:preflight/release:verify aggregate checks
and snapshots. Preserve Node24/ABI, cohort/profile, exact approvals/CSP, native
artifact/rollback packet, admission/backup, lock, source/public/LIVE acceptance.
Verify requires candidate/output/browser arguments from its runbook before execution;
the example locates its owner, not a full release command.

Code and signed-content/post lanes differ; server_local is not automatically
GitHub-owned. Preserve native same-operation reuse. No cross-release PASS cache,
shorter-profile omission or duplicate generic E2E job is implied.

## Jaguar CRM

Use [jaguar-crm.example.json](../assets/jaguar-crm.example.json). Preserve 17-stage
local full PostgreSQL/frontend/browser/real-stack, exact receipt, maintainer
attestation and separate publication/production. release:verify requires original
receipt/native arguments; it cannot verify a helper-normalized claim by itself.

The workflow builds one linux/amd64 image, smokes it and pushes that same image.
Web/worker/migrate/PWA identity and financial/data compatibility remain native.
Code rollback is compatibility-first; DB restoration separate. Read-only examples
do not establish installed digest/schema/flags/backups/provider delivery.

## Static/content/cloud and new projects

Adapt [project.template.json](../assets/project.template.json) and
[DEPLOYMENT.template.md](../assets/DEPLOYMENT.template.md) only when no good owner
exists. Replace illustrative commands with observed real ones or implement/test
missing ones under prepare; never execute a universal npm recipe from a template.
Static config belongs in artifact identity; publishers may protect runtime/data
and require CAS; cloud scripts need saved version/deployment/settings/triggers.

For a material platform/tool choice, inspect current primary docs and existing
solutions before custom machinery. Separate initial provisioning/DNS/TLS from
ordinary releases. GitHub/BuildKit, Kamal or managed statics are project options,
not global requirements. Record version/reason/migration/maintenance implications
in the owning project document.

## Container builds and real test dependencies

Read this section when the changed path uses Docker/Compose or needs a real
database/queue for integration proof. Prefer the existing native Bench/Compose
or test setup. Use available docker-patterns and current official docs for the
project's versions; Testcontainers is an option only when isolation pays for a
new dependency. No universal Docker migration or runner installation follows.

Resolve readiness by the required service condition, not an arbitrary sleep.
Isolate test data, mapped ports, caches/build outputs and resource ownership;
register cleanup for resources this run creates, including failure paths. Do
not run global prune or remove another operator's volumes. A missing runtime
leaves mandatory integration proof pending; skipped tests cannot supply it.

For a changed Dockerfile/Compose setup, select relevant assertions from the
project: build context, cache and build-secret handling, runtime user, supported
target, size/resource limits if required, and smoke of the resulting artifact.
Use an owned unique local tag where appropriate. Prefer a quiet config validation
which does not print resolved environment values. Pull/build/start can have
side effects and need the applicable authority and available runtime.

A helper that builds then prints image size/user only reports observations; its
exit zero does not enforce non-root, a size limit, absence of secrets or working
application behavior. Bind assertions to project requirements and actual checks.
Preserve build-once/promotion and fresh target proof under native policy.

Design ideas: [Docker build guidance](https://github.com/docker/skills/blob/f79172733725e2fd236343ee7b963c446ed85d09/skills/docker-build-strategies/SKILL.md),
[Compose guidance](https://github.com/docker/skills/blob/f79172733725e2fd236343ee7b963c446ed85d09/skills/docker-compose-patterns/SKILL.md),
and [Testcontainers examples](https://github.com/testcontainers/claude-skills/tree/5263fe47160c3ef187b93de4b21d2d7380bce12e/plugins/testcontainers/skills).
These are sources for an original synthesis, not imported scripts or a substitute
for current version-specific docs. The inspected skills snapshot has Go/.NET;
choose a language-compatible SDK/reference for other stacks.
