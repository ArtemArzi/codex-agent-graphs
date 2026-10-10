# Routing, dependencies and context packets

Read before delegating through Software Factory. Keep the decision and results in
the existing task record; do not introduce a mandatory graph or ceremony.

## Check independence

| Observed condition | Route or adjustment |
| --- | --- |
| One small fix or edits that must be understood together | Ordinary Task Delivery; root implements |
| B needs A's code, schema or interface decision | Complete and check A first; then B |
| Different files implement the same unsettled business rule or API | Root resolves the shared contract before parallel work |
| Independent modules with stable inputs/outputs and separate files | Two writing leaves can work in parallel |
| Same file, dependency lockfile, generated output, shared directory/file path | One owner writes it; move shared work before/after the parallel phase |
| Shared database, queue, account, mutable cache, port, build folder or browser session | Isolate it or serialize the conflicting operations; worktrees alone are insufficient |
| Runtime/environment paths still point at the original checkout | Verify import/build/runtime origin before tests; use read-only dependencies only when appropriate |
| Main has unrelated changes | Preserve them; use an authorized clean clone/base. Do not stash/clean or silently treat dirty changes as accepted requirements |
| High-risk changes, missing authority or unresolved business behavior | Follow Task Delivery and inherited acceptance policy; extra workers do not resolve these gaps |
| An isolated part is too small to repay setup and integration | Root does it directly; a stage name is not a reason for an agent |

File disjointness is necessary for two writers, but it does not prove semantic
independence. Name the shared interfaces and one combined acceptance check.
For example, two report readers can be implemented independently only after the
input schema, status meanings, comparability rule and CLI errors are agreed.
Frontend and backend often need an API contract first, even in separate files.

More parts do not mean more simultaneous writers. For four implementation
parts, identify dependency waves and keep at most two writers active. Independent
parts beyond the first pair can use a separate workspace after capacity frees;
dependent parts start from the previous checked candidate in a NEW workspace.
Pass the exact accepted commit and choose its branch as `--base` in a clean
experimental checkout; do not move main or reuse a baseline-bound workspace.
Root owns the final combined checks across waves. If independent review is
required before dependent execution by the task's risk/plan, finish it first.

With four total agents, obey the inherited justification and capacity rules.
Read-only work must have its own useful question; no duplicate explorers and
no speculative review of code that does not yet exist. A review applies only
to the inspected commit and must be revalidated for affected later changes.

## Pack context before dispatch

The reference factory passes job/worktree/branch paths, then the builder reads
`spec.md` and later round findings; its reviewer reads the same spec, `build.md`
and the branch diff. Sources: [builder](https://github.com/zazencodes/zazencodes-season-3/blob/main/src/software-factory-claude-code/.claude/agents/builder.md),
[code reviewer](https://github.com/zazencodes/zazencodes-season-3/blob/main/src/software-factory-claude-code/.claude/agents/reviewer-code.md).
Preserve this explicit file-based context without introducing a second owning
specification beside Task Delivery. Reuse the project's existing accepted task
record/specification; reference its relevant part in each leaf's packet.

| Artifact | Owner and consumers | When |
| --- | --- | --- |
| Common accepted task/contract in existing record | Root maintains; affected leaves and reviewer read | Before dependent work; changes require notification/repackaging |
| Per-job brief with context snapshot | Root/helper prepare; assigned leaf reads; root inspects | Before dispatch, never silently replace it under an active leaf |
| Code and local commits | Assigned writing leaf, exact worktree/owned files | During its slice; other leaves do not consume unfinished edits |
| Leaf result message | Leaf returns to root; root records decisive evidence in existing record | Before integration; identifies commit and actual checks |
| Integrated candidate and combined check evidence | Root assembles; independent reviewer reads | After required slices finish, bound to exact commit |
| Review verdict/findings | Read-only reviewer returns; root routes corrections to owner | Before completion, then affected checks/review repeat after repairs |

Role handoff is data, not conversational memory. A research leaf gets a specific
question, relevant sources, known facts, exclusions and expected evidence. A
reviewer gets the original intended outcome, accepted contract, base/candidate
SHAs, paths, diff, actual test evidence and explicit exclusions; use a fresh
context without the author's conclusions as its verdict. Its allowed result is
findings or a supported verdict, never code changes. Use the configured native
agent roles and `fork_turns="none"`; preserve their configured model settings.

Write one compact Markdown packet per writing job in an authorized scratch or
task location, and pass its path to `prepare --context`. The helper supplies
absolute worktree, branch, base SHA, owned files and objective. Add only the
information that changes this leaf's work:

```markdown
## Required outcome
What observable behavior this part must deliver; what counts as done.

## Shared contract and boundaries
Inputs, outputs, status/error meanings and stable interfaces.
Which root-approved decisions apply; what this part must not decide or change.
Dependencies already satisfied and the exact accepted revision/artifact.

## Facts and sources
Relevant project AGENTS/documentation map, owning specification, symbols and tests.
Use absolute paths or paths relative to the assigned worktree, with the intended
revision when relevant. Include decisive excerpts if a source is outside that
revision; distinguish facts from assumptions and unresolved questions.

## Ownership and exclusions
Exact owned files (also passed via --owns), shared files owned by root,
other parts' interfaces, forbidden external actions.

## Verification
Commands, expected observable results and failure cases, CWD/environment needs.
Which checks are this leaf's and which combined checks root will run.
Shared resources: database/test-data scope, ports/browser sessions, generated
outputs and caches, where applicable; who owns and can mutate each one.

## Return to root
Status, commit SHA, changed files, tests/commands/results, assumptions, limits,
and any unresolved dependency or required scope change.
```

Do not invent accepted decisions to fill the template. If an unresolved decision
changes the implementation contract, resolve it before starting that dependent
leaf; use an independent research leaf only when it repays the handoff.
The packet is a task-specific projection, not a copy of the whole chat, repo or
model reasoning. Include source facts and relevant failed attempts; exclude
credentials, customer payloads, unrelated history and active TD/PS state files.
Named paths do not grant new permissions. The helper snapshots supplied text;
it does not sanitize secrets, verify its truth or enforce agent permissions.

An agent cannot assume it sees root's conversation or a sibling's memory.
Require the leaf to read its brief and actual sources, report contradictions,
and avoid guessing missing shared contracts. Never use mutable sibling files
as the only reference for intended behavior. Root communicates interface changes
to affected leaves and pauses/repackages dependent slices when needed.

## Communication and tool availability

Before relying on delegation, inspect the actual tool registry for native agent
creation, messaging, waiting and continuation. Do not assume another host or a
previous chat exposes the same tools. When unavailable, preserve the work and
use ordinary/sequential root execution if authorized; state the missing check.

Root can send a bounded update with `agents.send_message`; an active leaf can
reply to root or a named sibling. Use exact returned agent IDs or canonical task
paths, not guessed nicknames. Receipt of a message is proved by an acknowledgment
with its task/change identifier, not merely a successful send call. Messages may
arrive at model/tool boundaries; do not treat a timeout as failure or completion.
Do not retry by spawning a duplicate owner when a response is delayed.

`send_message` does not start another turn on a completed/idle agent. Use
`agents.followup_task` for bounded continuation or correction of the same scope.
Inspect current state before resuming after interruption; this is not a durable
restart guarantee after process loss. An invalid target is a routing failure to
resolve from the registry, not permission to create another owner automatically.

Peer exchange can clarify facts, but root still owns shared contracts, scope
changes and integration. A changed interface or ownership boundary needs root's
decision and an updated packet for every affected leaf. Do not silently accept
a sibling message as a revised requirement or consume its unfinished files.

A native child, a Git worktree/branch and a separate user-owned Codex chat are
different objects. Use native children for this task's subtasks. Create a new
user-owned chat only on explicit user request and only if the host exposes the
relevant thread tools; never claim root-to-root chat coordination from a child
messaging test. No new user chat is needed just to prepare another Git job.

## Join, changes and interruptions

Accept each completed slice by its actual diff, owned paths, commit and relevant
checks; an agent's claim alone is not evidence. Keep one final combined product
check even if individual checks and Git merge pass. Wait for every required
review, following the inherited whole-task threshold without duplicating it per
file. Deployment, paid calls and main integration retain their own authority.

If a contract, baseline or assigned scope changes during execution, stop the
affected slice, preserve its work and issue updated context tied to the new
decision. Do not let old assumptions become accepted just because code exists.
On interruption, inspect current Git state and retained packets/evidence before
resuming; a timeout is neither a failed implementation nor a completed task.
With no available agent capacity, do useful independent work locally rather
than duplicate an assignment. No automatic resume engine is supplied by this
bundle. Installation, four-agent execution, tracked TD→PS and speed/cost savings
remain unverified until separately exercised.
