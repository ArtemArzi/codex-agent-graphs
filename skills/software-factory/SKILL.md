---
name: software-factory
description: Design a software factory for recurring agent work and coordinate its tasks through Task Delivery. Use for Software Factory requests, remote-agent workflow design, or isolated sequential/parallel development.
---

# Software Factory

Help the user design and operate their own factory, including a gradual move
from local Codex work to remote execution. Preserve Project Start, Task Delivery,
model routing and task authorization. A skill describes work; it does not supply
a remote runner, event listener or scheduler.

## Choose the intent

- **Design:** the user wants to decide how recurring agent work should operate,
  choose infrastructure or move it remotely. Read [designing-a-factory.md](references/designing-a-factory.md).
  Produce an actionable design with current capabilities, target behavior and
  the next bounded implementation slice. Do not start execution merely because
  a design is complete.
- **Execute:** the user has a concrete task to perform. Use the execution guidance
  below and the available Task Delivery skill. Do not require a factory interview
  for a small task. If Task Delivery is unavailable, report that missing dependency
  and the work that can still be prepared; do not install it or claim it ran.

These are intents inside one skill, not mandatory lifecycle stages. A request
to design and implement may use both within its existing authorization. Read
only references needed for the selected work.

## Execution environment

Local, remote and mixed describe where work runs, independently of whether its
parts are ordinary, sequential or parallel. For remote/mixed execution, read the
[remote execution contract](references/designing-a-factory.md#remote-execution-contract)
and establish the actual runner, capabilities, durable state and authority before
dispatch. Native child creation runs where that host provides it; a remote URL,
worktree or MCP connection alone does not create remote agent execution.
The bundled helper provides local Git/worktree operations only. When remote
capability is missing, continue authorized design or local preparation, keep
remote execution pending and state the next concrete step. Do not silently
substitute local execution for a requested remote run.

## Execute a task

Enter from Task Delivery after decomposition, or on an explicit Factory request.
Use Project Start's accepted slice dependencies and architecture sections as
inputs, not a second specification. Before the chosen route is implemented,
read the [cycle handoff](references/routing-and-context.md#development-cycle-handoff).
The output is one root-owned integrated candidate with combined checks and
current review for Task Delivery/Deployment, not a separate release per job.
For worktree operations, read [helper-usage.md](references/helper-usage.md).
The transferable helper is `scripts/factory.py`, resolved against THIS skill
directory, not the target project CWD. It requires Python 3.10+ and Git.

Before assigning shared work, use available `chat-coordination` if another
independent user task can affect the source, contract or mutable environment.
Carry that task-level boundary into each child packet; a child receives only
this task's suballocation. Without the skill/tools, preserve known owners and
isolate preparation rather than assuming no other work exists. Ordinary isolated
work needs no chat scan. Factory jobs/workspace locks are not cross-chat claims.

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

Before a parallel writing wave or a costly combined check, use
[readiness-and-checks.md](references/readiness-and-checks.md) for the affected
path: shared prerequisites, delivery/update/recovery inventory when relevant,
and a small probe of the actual runner and environment. Reuse existing evidence;
ordinary small work does not acquire a release checklist or another controller.

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
Keep required instructions intact while selecting only relevant source excerpts
and verification details; the context reference explains how to avoid repeated
bulk reads without dropping inherited requirements.

Prepare creates a branch/worktree and brief; it does not launch an agent.
Start every admitted native leaf with a fresh context window and explicitly
set `fork_turns="none"` in Codex. A new independent job gets a new leaf;
same-job corrections can return to its existing leaf under the host policy.
Send the exact absolute CWD and brief, require the leaf to read them and the relevant
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
Report targeted checks, full checks and independent acceptance separately,
including failures or interrupted runs. Where timing is useful, distinguish
preparation, overlapping work, integration, verification and repair; overlap
alone does not establish a speed or cost saving.
Do not start dependent work from a sibling's uncommitted edits. If a leaf needs
more scope or a contract decision, stop that slice and let root resolve it;
unaffected independent work may continue. Preserve failures and completed work.

If tracked TD/PS is selected later, finish each run and any required PS
maintenance in its own job root. Never copy active runtime state or import a
sibling receipt into main. Reconcile main's own document snapshot after merging
canonical documentation. The retained native experiment demonstrates quick delivery only;
tracked TD/PS needs its own end-to-end validation.

Use the helper's storage lifecycle for new task-owned disposable workspaces:
prepare with the task authority, owner token and explicit `--lifecycle ephemeral`;
record these in the existing task. Default `retain` preserves legacy callers.
Join every writer before `verify --writers-joined` or finishing a resource.
Repeated unchanged verification reuses its candidate and runs a fresh check;
at capacity inspect `storage` and its retained reasons instead of allocating
another directory. A caller flag declares coordination and existing authority;
it grants neither permission nor proof that unknown writers have stopped.
After saving/readback of results and evidence, `finish` then inspect `close`
dry-run and apply only eligible owned resources through the helper. Branch refs
and receipts remain outside the checkout. Preserve dirty/ignored/admin data,
unfinished or changed resources, legacy copies and useful recovery state.
Installation, push, main integration, destructive shell and deployment retain
the actual task/host authorization. Never force, prune or delete branches to
make closure pass. See helper-usage.md for exact commands and limitations.
