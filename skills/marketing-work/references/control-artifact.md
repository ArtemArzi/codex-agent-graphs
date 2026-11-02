# Optional evidence control

Read project instructions, the company's current brief and the existing task or
canonical output first. The model chooses the marketing work, sources, stage,
specialists and useful checks. This controller only binds local evidence and
completion. It does not send, publish, spend, schedule, fetch data or handle
credentials. It supplies no marketing targets or business-rule defaults.

Use `skill-only` by default: perform the skill directly and create no run.
Admit `tracked` only for resumability, durable evidence or an explicit request.
Admit `verified` when an independent review of the exact candidate is needed.
Inherited host acceptance still applies inside `work` at every tier. Required
plan/result acceptors remain distinct from the root and from one another when
host policy requires it. The controller does not select a model, spawn agents,
enforce native dispatch or prove a reviewer's identity. The root must inspect
the real review evidence; a declared role alone is insufficient.

## Existing owners and files

Keep the company brief, task, campaign or other canonical result in its existing
project location. A run is not another brand CRM, backlog or content queue.
Use canonical root-relative regular-file paths, with no repeated separators,
trailing separators, symlinks or traversal. Different roles must refer to
physically distinct files: a hardlink cannot substitute for separate evidence.
This separation is checked again on resume and completion. Sources,
the canonical output and evidence must live outside `.agent-graphs`. Inputs
cannot also be the output. Work evidence is separate from input/output; review
evidence is separate from all work evidence. Files bound as evidence must stay
immutable; write a new evidence file for an additional observation.

Run material lives only in
`.agent-graphs/marketing-work-runs/<run-id>/`: `state.json`, immutable
`work-0.json`, optional `verification-0.json`, at most one repaired pair with
suffix `1`, and `FINAL.json`. Receipts bind company, exact objective, root, run,
mode, tier, graph version/digest, controller digest, input paths/digests, output
path and exact candidate digest. They contain references and check evidence,
not a second marketing plan. `state.output` identifies the canonical document
for the shared artifact lifecycle. Running state is resumable and retained;
completed raw state may be compacted by that shared lifecycle. This controller
contains no pruning, cleanup hook or retention timer.

## Commands

Run from any directory; replace `SCRIPT` with the installed
`marketing-work/scripts/marketing_graph.py` path and `PROJECT` with the project
root. The ordinary skill-only route invokes none of these commands.

```sh
python3 SCRIPT init --root PROJECT --run campaign-next-step --tier tracked \
  --company 'Brand A' --objective 'Choose the next useful acquisition test' \
  --input company/brief.md --output company/current-task.md
python3 SCRIPT ready --root PROJECT --run campaign-next-step
python3 SCRIPT resume --root PROJECT --run campaign-next-step
```

`init` refuses an existing run and never writes the canonical output, even if it
already exists. The model edits that document through its existing owner. Both
`ready` and `resume` validate state, sources and receipts without writing. Their
JSON result names the next command and, after work, exact work/output hashes.

After actual work and proportionate checks, supply a separate evidence file:

```sh
python3 SCRIPT work --root PROJECT --run campaign-next-step \
  --author root-session --evidence company/evidence/checks.md \
  --capability 'mcp:not-applicable:local-company-sources'
python3 SCRIPT complete --root PROJECT --run campaign-next-step
```

Record actual relevant skills/MCP receipts using repeated `--capability`.
For local-only work, use `mcp:not-applicable:<reason>` rather than discovering
tools ritualistically. Capability strings reference model-owned evidence; the
controller cannot attest a tool call. Work requires at least one `mcp:` entry.

For `--tier verified`, or `work --verify` on a tracked run, review is required.
Give the independent reviewer the canonical input, exact work receipt, candidate
and checks. Preserve its real result in a separate review evidence file. Supply
the exact two hashes returned by `work` or `ready`:

```sh
python3 SCRIPT verify --root PROJECT --run campaign-next-step \
  --reviewer independent-session --role block_reviewer --verdict accept \
  --reason 'The source evidence supports this bounded next step' \
  --work-sha WORK_SHA256 --output-sha OUTPUT_SHA256 \
  --evidence company/evidence/review.md
python3 SCRIPT complete --root PROJECT --run campaign-next-step
```

Choose the role required by the current host policy. The graph's ordinary
conditional reviewer is `block_reviewer`; an appropriate whole-result acceptor
may supply the receipt when the complete outcome requires it. No review is
manufactured for the tracked happy path. Neither route proves publication,
delivery, human use, sales or business effect.

## Refusal and bounded repair

A `reject` verdict returns to `work` once. Preserve the rejected evidence,
correct the canonical document, provide a new evidence file with different
content, and call `work --first-false-assumption '...'`. Both changed candidate
and new evidence are required. Then obtain a review of the new exact candidate.
A second rejection records `phase=exhausted`, retaining `status=running`; no
work, acceptance or completion transition is available. This is stricter than
the shared two-iteration no-new-evidence ceiling: an unchanged retry is refused
immediately, without creating a receipt or resetting a budget. The fixed
controller permits two reviews and one repair; it has no unlimited override.
Host agent concurrency, duplicate-scope guards and policy acceptance remain
root-owned operations inside work, not controller-attested facts.

Changed bound sources/objective/company require reconciliation with the task
owner; do not rewrite state or create another run to reset failed budgets.
Changed output after a work receipt, changed graph/controller, altered receipts,
unknown schema/identity, extra run files, symlinks and conflicting writers all
fail closed. Completed resume rechecks the final artifact as well. The state
checksum detects accidental edits; it is not a signature against an authorized
filesystem writer. Atomic state replacement and exclusive lock files protect
cooperating controller writers. They are not a lock on a human editor of the
canonical document. Recheck the result before any external action.

For protocol problems, allow one bounded diagnosis/repair. After that, preserve
state and pending reviews, degrade control and continue authorized marketing
work through its existing document owner. Do not claim controller completion.
An interrupted write may leave an unreferenced receipt or `.state.tmp`; a crash
may leave `.lock`. The controller refuses these rather than stealing ownership
or deleting evidence. Reconcile writers and artifacts before an explicit repair.
No existing marketing graph state predates graph `marketing-work` v1.0.0 and
state schema 1. Unknown or changed identities have no automatic migration.
