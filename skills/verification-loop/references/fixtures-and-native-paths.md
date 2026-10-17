# Isolated fixtures and early platform feedback

Read when tests share persistent resources or a feature depends on a platform's
own editor, router, serializer, migration mechanism or lifecycle. Keep it local
to the affected scenario; a simple wording check needs no new harness.

## Own setup and cleanup

Identify the fixture-owned database/schema, files, IDs, ports, roles, queues and
mutable options. Git worktrees alone do not isolate them. Prefer the existing
runner's isolation and lifecycle lock; avoid parallel writers to shared state.
Capture pre-existing options/roles that a test must temporarily change.
Cleanup removes only owned fixtures and restores those options under the same
ownership controls; a reset of the whole shared database is not cleanup.

Use the existing runner's run/owner identity and resource scope, including any
exclusive singleton. Record enough ownership before mutation to reconcile an
interrupted setup/teardown. After a crash, verify current values and ownership
before cleanup or restoration; do not overwrite another run's newer option or
free its active lease. Unique row prefixes do not isolate a shared homepage,
global role or port. Verify a failed-run cleanup/retry when changing this path.

Where suites share resources, declare their setup/teardown prerequisites or give
them isolated state. Verify standalone execution and relevant repeated/combined
execution. If order changes behavior, distinguish an intentional prerequisite
from contamination. A fixture that creates a second unique homepage can trip a
correct product guard; inspect state ownership rather than loosen that guard.
Retain failure evidence and rerun the affected scenario after cleanup.

## Exercise the native contract early

Before repeating a new pattern across many templates or modules, test one
representative vertical slice through the actual platform mechanism: create,
save, reopen and render, including a meaningful empty/error state.
For an editor, check both unfilled and populated content through its native
validation; a plausible HTML string may still be invalid stored block markup.
For a release proxy, use the actual request context rather than assume a direct
service has the same status/headers as the public edge.

Keep fast local assertions while developing; run the required broader suite at
its integration boundary. Moving a useful discriminating check earlier does
not remove project release gates. Distinguish a product failure from a locator,
test-order or environment failure, and preserve the intended behavior in either
repair.

Independent synthesis informed by
[Software Engineering at Google, testing](https://abseil.io/resources/swe-book/html/ch11.html):
test isolation and useful behavior evidence, adapted to the project's scale.
