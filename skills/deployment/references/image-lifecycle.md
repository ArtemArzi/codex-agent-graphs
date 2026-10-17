# Image and build-cache lifecycle

Read when preparing or releasing container images, or when image/cache storage
is the maintenance question. Put commands and retention decisions in the native
deployment/runbook owner. Cleanup is part of that outcome when authorized, not
a separate general skill, controller or automatic global prune.

## Account for each storage location

Check the actual local daemon/context, remote deployment host and relevant
builder separately. A remote Docker context can make a local command operate
on the server. Registry storage is another owner; removing a local image does
not delete its registry copy or the server's copy.

Include project-owned exported image/OCI bundles and release staging leftovers
when the native packaging path creates them. Their retention follows the same
active-operation/recovery owners; an archive is not disposable just by extension.

Use permitted read-only inventory, for example `docker system df -v`, image
references/IDs/digests and all container references, including stopped containers.
Inspect build-cache usage for the actual builder; each builder may have its own
cache. Record safe identity/usage fields, not environment values or credentials.
Check headroom before staging/building a new image and revisit owned leftovers
after verified activation or a failed build's reconciled cleanup.

## Decide what stays before choosing deletions

Apply the project's retention/recovery window, not a universal age or image
count. Retain the current release, active/staged builds and operations, required
compatible rollback artifacts and any image referenced by another service,
stopped container or operator. Read native journals/pins as well as Docker's
container references: a rollback image can be unreferenced by containers.
A local development host may need a different retained set from production.

For each candidate, identify its project/owner, immutable identity and references,
the reason it is obsolete, and whether removing it would break offline recovery.
A tag can move and a dangling image can still be named by a rollback journal.
An old-looking timestamp or Docker's reclaimable label is insufficient proof
that the image is disposable under the project's policy.
If retention is undocumented, prepare a small keep/remove set from the actual
release/recovery owners, preserving known necessary artifacts; resolve a material
recovery/authority ambiguity rather than inventing a loss tolerance.
No current or viable required rollback artifact is removed merely to hit a disk
target. Re-pulling is a recovery option only when the exact artifact's availability,
access and required network dependency meet the existing recovery contract.

## Clean selectively and recheck

Prefer an existing project-scoped cleanup command with an inspectable retained
set. Otherwise select exact obsolete references/identities and required filters;
check the installed tool's semantics. Immediately before deletion, re-read
identity/references and native operation/lock ownership. A changed tag, new
container/build, unknown owner or active lease requires recalculation.
On a shared daemon/builder, coordinate through its native exclusive maintenance
path; inventory alone is not a lock against concurrent changes.

Perform only deletions covered by current authority and host destructive-command
rules. Do not widen an image/cache request to volumes, backups, source trees,
all stopped containers, networks, other projects or registry history. Avoid
global system/image/builder prune as a default; broad unused-image pruning can
discard a required rollback with no container reference. Removing a conflicting
container or forcing an image deletion is not an automatic workaround.

Treat image retention and BuildKit cache separately. Use the actual builder's
existing bounded GC policy or authorized scoped cache cleanup, respecting active
builds and useful warm cache. Changing daemon/GC settings or creating a schedule
is separate configuration work, not implied by one cleanup.

Read back current/staged/retained rollback image availability, preserve valid
release checks and run another user-path smoke only if actual impact or new
evidence requires it. Then compare disk usage. Shared
layers mean summed image sizes are not bytes freed; removing a tag may reclaim
nothing. Record what was removed/kept, actual reclaimed space (or unknown) and
pending items in the existing release record. No eligible candidates is a
successful no-op; unavailable inventory/authority is pending cleanup, not PASS.
A cleanup failure after a successful release does not make that release disappear:
preserve its actual outcome and record the separate disk/maintenance consequence.

Sources checked 17 October 2026:
[Docker pruning](https://docs.docker.com/engine/manage-resources/pruning/),
[build-cache GC](https://docs.docker.com/build/cache/garbage-collection/),
[disk accounting](https://docs.docker.com/reference/cli/docker/system/df/).
These explain Docker mechanisms; the project owns its retention contract.
