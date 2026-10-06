# Resume or explicitly restart an unfinished Task Delivery run

Resume compatible v3 state with the current `task_graph.py`; schema v2 uses
[the legacy runner](legacy-v2-resume.md). Ordinary loaders remain exact-identity
and evidence checks. An unsupported graph identity is not permission to edit
its version/hash or manufacture an acceptance receipt.

When the owner authorizes replacement of an unfinished saved **v3** instance:

```bash
python3 scripts/task_graph.py restart --run /absolute/repo/.agent-graphs/task-delivery-runs/<run-id> --reason 'Owner requested replacement of this unfinished instance' --acknowledge-incomplete
```

The reason and acknowledgement may use already recorded owner authorization;
replacement does not answer unresolved business decisions. An optional
`--successor-task-id <new-id>` selects the new identity. Otherwise it is stable
for this exact old run. Repeat the exact command after interruption, including
the same reason and optional ID. Do not use ordinary init/recover to bypass a
pending `.agent-graphs/restart-task-delivery.json` or
`.agent-graphs/restart-project-start.json` transfer.

Restart structurally validates the root, run, index owner, baseline, supported
mode/profile, plain contained files, scope selection and decision answers.
It rejects completed runs, v2/unknown schemas, ambiguous ownership/selection,
pending Project Start obligations, collisions, symlinks and active locks. A
new graph identity may replace an unknown old identity only through this
explicit lifecycle operation; old evidence is never executed or certified.

Before retirement it prepares the complete current successor and captures the
source run/index/plan bytes. Old code, documents, plan, receipts and graph
identity remain preserved. `plan` becomes a new plan run; `implement/full`
becomes a new full run with the same intended outcome, profile and scope. The
copied candidate may move its single scope block into its hashed region; the
original is unchanged. Historical review prose grants no acceptance: the new
index has no checkpoints and every node has no old receipts. Current source
and document hashes form the fresh baseline, so preserved pre-restart edits
are not silently counted as new accepted implementation evidence.

Resolved decision answers are retained verbatim, with original scope/source
and lineage. Rejected reviewer repair lists and prior verification requirements
remain mandatory, also through another restart. The successor's
`restart_inheritance` names `restart-constraints.json` and its SHA-256. Both
fresh `task.json` and `verification.json` must include:

```json
{
  "restart_constraints": {
    "sha256": "<restart_inheritance.sha256>",
    "decisions": ["<exact decision objects from restart-constraints.json>"],
    "repair_requirements": ["<each rejected repair requirement in order>"]
  }
}
```

The `decisions` array contains the actual objects, not string placeholders.
Fresh work and review must assess these constraints and name them exactly;
a copied field is evidence binding, not a replacement for the review. Scope
changes still require the existing authorized amendment route. Inherited
verification cannot become a self-verified success.

A durable marker and staged operation hold repository admission throughout the
transfer. Every target must equal its exact preimage or planned postimage;
staged bytes, old receipts, plan, baseline and current source basis are checked
before continuation. External edits or tampering stop transfer without being
overwritten. The old run records `retired` with explicit successor linkage;
this is unfinished retirement, never successful completion. Marker completion
allows ordinary work again. A completed marker may be replaced by a later
restart; the per-run completed marker retains earlier idempotent requests.

If safe restart cannot be admitted, preserve all state and record the concrete
blocker and next step in the existing handoff. Make at most one bounded
controller repair, then continue authorized native work without claiming
controller completion or clearing decisions/obligations. Never recover by
rewriting old identity, removing useful code/docs or weakening evidence.
