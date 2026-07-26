# Shared artifact lifecycle

## Contents

- [Artifact classes](#artifact-classes)
- [Lifecycle](#lifecycle)
- [Commands](#commands)
- [Retention and safety](#retention-and-safety)
- [Compatibility](#compatibility)

## Artifact classes

Classify artifacts by usefulness, not by their current directory.

1. **Canonical project history**: accepted plans, specifications, handoffs,
   reports, decisions and maintained project documentation. Keep these in their
   owning project path. Graph cleanup never deletes them.
2. **Active resumability state**: state, baselines, slice packets, receipts,
   checkpoints, intermediate verification and recovery evidence. Keep the full
   set while a run is active, blocked, awaiting implementation, undecidable or
   otherwise unresolved.
3. **Terminal raw evidence**: the internal run material after a safe terminal
   completion. Compact it into one verified archive plus a small permanent
   receipt, then delete only through the explicit retention command.

The permanent receipt lives at:

```text
.agent-graphs/history/<graph-id>/<run-id>/FINAL.json
```

The temporary archive lives at:

```text
.agent-graphs/archives/<graph-id>/<run-id>.tar.gz
```

## Lifecycle

Artifact handling is a post-completion operation, not a graph node:

```text
work -> optional verify -> complete
                              |
                              v
                 compact -> explicit TTL prune
```

`compact` must publish the archive only after it has:

- resolved an exact supported managed run path without symlinks;
- verified terminal state and compatibility holds;
- hashed every raw file;
- created a path-safe deterministic archive;
- read the archive back and matched every member to the manifest;
- preserved terminal outputs that exist only inside the raw run;
- atomically written `FINAL.json`.

It leaves the raw run intact. Cleanup remains a separate explicit operation.

## Commands

The installer places the shared standard-library runtime at
`<HARNESS_HOME>/agent-graph-runtime/artifact_lifecycle.py` (`~/.codex` under
the Codex installer, `${CLAUDE_PLUGIN_ROOT}` under the Claude Code plugin).
In the source repository the same relative directory exists at the
repository root.

```bash
python3 <artifact-lifecycle.py> inventory --root <project>

python3 <artifact-lifecycle.py> compact \
  --root <project> --run <managed-run-directory>

python3 <artifact-lifecycle.py> prune --root <project>

python3 <artifact-lifecycle.py> prune --root <project> --apply
```

`inventory`, `compact`, and default `prune` do not remove data. `prune` without
`--apply` is always a dry-run.

## Retention and safety

The default successful policy is:

- raw unpacked run: 7 days after completion;
- compressed archive: 30 days after completion;
- permanent `FINAL.json` and canonical project outputs: no automatic expiry.

Repositories may override the day counts through
`.agent-graphs/retention.json` using schema version 1. Archive retention must
not be shorter than raw retention.

```json
{
  "schema_version": 1,
  "completed": {"raw_days": 7, "archive_days": 30},
  "superseded": {
    "raw_days": 7,
    "archive_days": 30,
    "require_successor": true
  }
}
```

Fail closed:

- never compact or prune active, blocked or awaiting-implementation state;
- never follow a symlink;
- never accept an unknown managed root or status;
- never prune when raw state, archive or manifest changed after compaction;
- never prune a superseded run until its recorded successor exists and is
  completed;
- never trigger deletion from a hook or from `complete`;
- always retain `FINAL.json` and write a GC receipt for applied cleanup.

## Compatibility

Current graph controllers and state schemas do not change. Operational skills
call the shared lifecycle after their normal completion gate. Active legacy
Task Delivery state under `.codex/task-delivery` remains discoverable:

- `running`, `blocked`, and `awaiting_implementation` stay intact;
- safely completed task state may be compacted explicitly;
- new graph runs continue to use `.agent-graphs`;
- no existing run is silently migrated or deleted.
