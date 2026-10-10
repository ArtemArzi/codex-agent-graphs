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
base. It checks changed-path ownership, merges exact job commits into a new
integration branch/worktree, runs the explicit argv there and retains result/log.
The combined command must verify its actual import/build origin and isolate
mutable resources. Existing read-only dependencies may be shared deliberately.

Status reports observed SHA/branch/dirty state and whether saved verification is
fresh. Freshness is not approval, permissions enforcement or runtime isolation.
The helper never installs skills, merges source/main, pushes or deploys. Locks
serialize helper calls only. Preserve failed candidates and evidence; changing
the baseline requires a new workspace rather than reusing stale verification.
