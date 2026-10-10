---
name: software-factory
description: Coordinate optional Codex worktree-based delivery with Task Delivery, choosing ordinary, sequential or parallel work from actual dependencies. Use when the user requests Software Factory or isolated parallel development.
---

# Software Factory

Preserve installed Task Delivery, Project Start, model routing and user
authorization. This workflow uses native Codex agents and needs no dashboard.
Use the available Task Delivery skill; if unavailable, report the missing
dependency without installing or claiming that its workflow ran.
For worktree operations, read [helper-usage.md](references/helper-usage.md).
The transferable helper is `scripts/factory.py`, resolved against THIS skill
directory, not the target project CWD. It requires Python 3.10+ and Git.

Before delegation, read [routing-and-context.md](references/routing-and-context.md).
Check native tool availability; use explicit message acknowledgments for changed
instructions and bounded follow-up turns for completed leaves, as described there.
Choose from actual dependencies and shared resources, not the number of files:

- **Ordinary:** small, tightly coupled or already understood work. Root uses
  Task Delivery directly without jobs, extra agents or worktrees just for stages.
- **Sequential:** one part needs another's code or an unresolved shared contract.
  Establish and check that prerequisite first. Root can do the whole chain;
  delegate a later part only if the handoff has a concrete benefit.
- **Parallel:** substantial independent parts with stable interfaces, disjoint
  owned files and isolated mutable resources. Start only the parts whose
  prerequisites are satisfied. Mixed work can use sequential preparation,
  parallel implementation, then sequential integration.

Explain the chosen route and its reason briefly, and record it in the existing
task record. An explicit request to test parallelism permits extra overhead,
not shared-state races or missing prerequisites. Reassess when new dependencies
appear; fewer active agents or a sequential fallback is a valid result.

Root owns the common task, contract and integration. Preserve Task Delivery's
review/risk routing; Software Factory does not lower its acceptance threshold or force
a separate controller for each leaf. Use quick when appropriate; tracked/verified
only for their actual purpose. Project Start remains responsible for required
canonical-document maintenance.

Usually use zero to two useful children. Four concurrent agents require explicit
deep parallel work and four genuinely independent scopes under the inherited
policy and host capacity; never launch four merely to fill slots. There are at
most two simultaneous writers. Other useful agents may research independent
questions or review an already frozen candidate; they cannot approve unfinished
or subsequently changed code. The helper supports two implementation jobs per
workspace; read-only roles do not need fake Git jobs. More writing parts run in
waves from checked prerequisites, using a new workspace/base for dependent waves.

For each writing leaf, root prepares a compact self-contained context packet
using the linked reference. Pass it through `factory.py prepare --context FILE`;
the helper embeds a snapshot in the job brief with a source-content hash.
Old calls without this option remain supported, but their minimal brief is not
a complete task packet. The hash records the supplied text, not correctness or
approval; root checks the actual packet and sources before dispatch.

Prepare creates a branch/worktree and brief; it does not launch an agent. Send
the exact absolute CWD and brief, require the leaf to read them and the relevant
project instructions, test, and commit only owned files. Leaves do not delegate.
Do not send the entire chat or another agent's private reasoning. Each leaf
returns its commit, changed files, commands/results, assumptions and remaining
limits. Root reads the actual diff and reconciles these with the common contract.

Git worktrees isolate files, not permissions. Native agents share the host and
can accidentally write elsewhere; root must inspect the actual diffs and the
unchanged source. An agent report or passing test is not independent approval.
Reviews follow the active user policy; do not force a fixed seven-agent chain.

Use `status` for observed progress. Run `verify` with the project's real check
argv; it merges exact clean candidates into a separate integration worktree and
retains failures. Inspect and review the combined behavior. Recheck source,
job and integration SHAs and dirty state immediately before any authorized
manual integration. The helper never pushes or applies to source/main. Locks
coordinate helper calls only; no claim of protection against external Git edits.
After integration, the old baseline-bound verification is stale by design.
Do not start dependent work from a sibling's uncommitted edits. If a leaf needs
more scope or a contract decision, stop that slice and let root resolve it;
unaffected independent work may continue. Preserve failures and completed work.

If tracked TD/PS is selected later, finish each run and any required PS
maintenance in its own job root. Never copy active runtime state or import a
sibling receipt into main. Reconcile main's own document snapshot after merging
canonical documentation. The retained native experiment demonstrates quick delivery only;
tracked TD/PS needs its own end-to-end validation.

Keep branches, worktrees and evidence until the user authorizes integration or
cleanup. Installation, push, main integration and deployment follow the actual
task authorization; the helper never performs them. Preserve existing defaults
and do not clean up automatically.
