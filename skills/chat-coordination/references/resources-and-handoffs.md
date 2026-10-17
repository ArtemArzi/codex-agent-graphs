# Resources and handoffs

Read for identity ambiguity, shared mutable state or integration. Keep only the
affected identities and links in the existing task/architecture/operations owner;
do not build a second project registry just to complete a task.

## Identify the intersection

| Subject | Useful identity and evidence |
| --- | --- |
| User task | Native host/thread ID, latest direct human outcome, owning plan and current assignment/attempt |
| Source checkout | Actual checkout and Git common-dir/worktree, accepted source commit, owned paths; preserve foreign dirty work |
| Shared contract | Owning API/schema/business rule, accepted version and affected consumers |
| Integration | Exact candidate commits, current target/base, owner of combining them and combined acceptance |
| Runtime | Actual host/account and service namespace, DB/schema, queue, Docker context/builder, mutable cache, output directory, port or browser profile |

Use native Git/OS/runbook facts to reconcile aliases, including symlinks and
Windows/WSL paths. A remote URL may connect clones without a shared filesystem;
equal CWD/projectId/title may connect unrelated work. Similar names alone are not
proof of either independence or identity. Do not inspect secrets or another
tenant's records to fill a map. Ask the owning environment only for relevant facts.

Stable project identities belong in the existing architecture/operations docs.
The current task records only its scope, version, dependency and next obligation.
Versions are evidence bindings, not permission tokens. A digest of a peer's text
does not prove its truth, currentness, human approval or enforceable ownership.

## Separate parallel work from exclusive changes

Independent authorized reads can share immutable inputs. Separate files need a
stable semantic contract as well: frontend/backend or two readers may still
disagree on one evolving API. Resolve that dependency before dependent writers.

Use separate worktrees/candidates for intersecting source edits; inspect the
actual source, branch, diff and dirty state. Worktrees do not isolate a DB,
credential, browser, port or mutable build directory. `git worktree lock` prevents
administrative removal/movement, not file edits or service mutations.

An intent note, ACK or advisory file reservation is cooperative information.
Two callers can both read "free" before either claims it. A helper lock protects
only the operations/participants that actually use it; per-workspace ownership
checks do not establish cross-workspace writer exclusion. Never advertise a
listing or skill as a hard lock.

If an affected operation needs exclusive ownership, use its existing isolation,
transaction, native lock/CAS or queue at the actual mutation boundary. Time-based
leases require the mutating path to reject an obsolete owner's generation after
takeover. TTL/PID/status alone cannot supply that protection across hosts. When
the mechanism is missing, prepare locally and leave the contested operation
pending; do not add an improvised registry and call it safe.

Do not hold a scarce mutable resource while waiting indefinitely on a second
dependency. Split the work or follow the project's accepted acquisition order.
Never resolve a dependency cycle by deleting another owner's lock.

## Handoff without taking over the other task

Agree only on the specific intersection: prerequisite, scope, current contract,
candidate and order of affected work. An agreed integrator owns combining these
authorized candidates, not both user outcomes or new external permissions.
Conflicting human business requirements return as a concrete decision to the
human; agent voting or start time cannot settle them.

Give a child only a suballocation of this task's area; it cannot create top-level
claims over another chat. Keep unresolved shared contracts out of dependent
packets. Accept actual commits/diffs/checks and combine the behavior, rather than
adding PASS labels from separate leaves.

Before integration, recheck source/target versions and foreign work. A prior PASS
on a different base is stale for affected behavior. Do not merge/push another
task, copy its active controller state or overwrite a shared branch merely
because both participants finished. Task Delivery, Project Start and native
deployment/recovery retain their existing contracts and acceptance policy.
