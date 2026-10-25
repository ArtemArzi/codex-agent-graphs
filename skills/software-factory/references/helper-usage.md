# Worktree helper

Use the absolute path to `scripts/factory.py` inside this skill as HELPER.
Python 3.10+ and Git are sufficient; there are no package dependencies.
Copying this skill folder is sufficient for the helper. The canonical
repository path is `skills/software-factory/scripts/factory.py`.

Choose a clean authorized checkout at the selected base branch. If the original
checkout is dirty, preserve it and use an authorized clean clone/base. Keep the
workspace outside the repository, with separate job ownership for exact files.

```sh
python3 "$HELPER" prepare --repo /absolute/clean-repo   --base experiment/task-base --workspace /absolute/workspace   --job summary --owns src/summary.py --owns tests/test_summary.py   --objective 'Implement the accepted summary contract' --context /absolute/summary.md
python3 "$HELPER" status --workspace /absolute/workspace
python3 "$HELPER" verify --workspace /absolute/workspace --timeout 180 --   python3 /absolute/run_combined_checks.py
```

Repeat prepare for at most two implementation jobs per workspace. Defaults to
base `main` when --base is absent; choose the intended base explicitly for real
experiments. Ownership cannot overlap, including parent/child paths.
Prepare snapshots a nonempty UTF-8 context file in the generated brief and
records its SHA256; root must inspect its meaning and source references.
Minimal legacy briefs without --context do not satisfy the full packet contract.

Prepare does not launch agents. Root dispatches native leaves with exact absolute
job CWD/brief and the routing/context instructions. Leaves test and commit only
owned files. Branches retain the compatible `pilot/<workspace-id>/...` namespace;
that historical prefix does not change their isolation or the skill name.

Verify requires committed clean jobs and an unchanged clean source at the bound
base. It checks changed-path ownership and merges exact job commits into an
integration branch/worktree. Repeating the same exact jobs/base reuses that
unchanged clean candidate but runs the supplied check argv again. Each attempt
has its own original log and receipt under `workspace/evidence`; `verification.json`
points to the latest attempt. Dirty, stale, active or merge-error candidates are
retained and cannot be silently replaced by another copy of the same inputs.
The combined command must verify its actual import/build origin and isolate
mutable resources. Existing read-only dependencies may be shared deliberately.
Before a costly verify, probe that command and its required environment on a
small existing case as described in [readiness-and-checks.md](readiness-and-checks.md).
Use the project's canonical runner; Factory's captured exit/log do not prove
that it discovered tests or that all required acceptance checks ran.

Status reports observed SHA/branch/dirty state and whether saved verification is
fresh. Freshness is not approval, permissions enforcement or runtime isolation.
The helper never installs skills, merges source/main, pushes or deploys. Locks
serialize helper calls only; they do not prove an external writer has stopped.
Changing the baseline requires a new workspace rather than reusing stale verification.

## Managed storage and completion

New preparations journal allocation intent in `workspace.json` before Git creates
any branch/worktree. An unchanged reservation with both path and branch absent
can retry the same `prepare` or `verify`. Partial paths, branches, registrations
and foreign files are retained visibly. A ready job cannot be prepared again.
These records are local helper state, not a second task controller.

Existing workspaces without the new storage marker are legacy resources. Status
can still read them, but storage mutations refuse them; creating a marker manually
does not establish ownership. Nothing here authorizes legacy cleanup.

The default lifecycle is `retain`. For a task whose existing authority includes
releasing its own disposable preparation, root declares that scope at the first
prepare and assigns the actual writer identity:

```sh
python3 "$HELPER" prepare --repo /absolute/clean-repo --base main   --workspace /absolute/workspace --job summary --owns src/summary.py   --objective 'Implement the accepted summary contract' --context /absolute/summary.md   --authority TASK-ID --lifecycle ephemeral --owner summary-writer
python3 "$HELPER" storage --workspace /absolute/workspace
```

Lifecycle and authority remain bound to that workspace. They are caller declarations,
not new permission grants. `storage` performs a read-only report without acquiring a
lock or creating files. It lists reserved/active/terminal/closed resources, owner,
eligibility and reasons for retaining each checkout. It does not scan or clean
unrelated repositories, dependency stores or shared caches.

Root joins every child and other known writer before finishing a job. Stop using
the checkout after this handoff. Matching owner/task declarations are required;
an active clean checkout is insufficient. Root uses the normal result and retention
decision from its owning task, with no new human Git choices:

```sh
python3 "$HELPER" finish --workspace /absolute/workspace --resource job:summary   --owner summary-writer --authority TASK-ID --writers-joined --outcome terminal
python3 "$HELPER" close --workspace /absolute/workspace --resource job:summary   --authority TASK-ID
python3 "$HELPER" close --workspace /absolute/workspace --resource job:summary   --authority TASK-ID --apply
```

`close` is a dry-run unless `--apply` is supplied. `finish` can also record an
explicitly cancelled job with `--outcome cancelled`. It cannot clear an unfinished,
error or stale integration. Such resources remain available for recovery.

For a foreground check known to leave no background writers, root can include
`verify --writers-joined` before `--`. A completed pass/fail then marks its helper
owner joined. Otherwise the result contains `resource` and `owner`; after joining
all writers, root can use the same `finish` command with those returned values.
A timeout, crash, stale result or merge failure remains active and retained. PID
liveness and the helper lock are never treated as proof of a finished writer.
External tools or raw writers are not isolated by this protocol.

Before a new integration allocation, eligible earlier terminal ephemeral integration
checkouts close automatically. The default cap is two unclosed managed integration
candidates per workspace, including failed reservations. New UUIDs do not bypass
it. At the cap, creation stops and reports the retained paths and reasons. The cap
has no CLI override; use the existing task's recovery/retention decision rather than
editing the manifest or moving to a new workspace merely to evade it.

Closing verifies canonical source/common-dir/workspace/worktree/admin identities,
exact registration/branch/base, terminal ownership, clean tracked/index/untracked/
ignored state and complete evidence outside the checkout. Useful ignored files,
unfinished Git operations/locks, unfamiliar admin data, worktree-specific refs,
reflog-only commits, uncommitted commit-message drafts and changed identities retain
the resource. A complete failed-check receipt and globally anchored recovery branch
can qualify; failed merges cannot. Before removal, known Git-admin bytes are archived
with readback in `workspace/evidence`, then identity/state/evidence are rechecked.
Native `git worktree remove EXACT_PATH` performs removal without force or prune.
All branch refs and their commits, job briefs, attempt receipts/logs and admin archives
remain available. Branches are never deleted automatically. Failed or uncertain
closure reports retention; do not manually remove a path to make a check pass.
