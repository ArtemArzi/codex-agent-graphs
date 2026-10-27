# Designing a factory

Use when designing recurring agent work or its move to remote execution. Start
from the user's problem and existing decisions. Keep accepted choices, observed
capabilities, proposals and unknowns distinct; ask only about remaining decisions
that materially change the design. A remote target can be designed before a
runner exists. Missing Task Delivery or Project Start does not block design-only
work: use the existing project documents and name the later handoff.

## Start with a useful loop

Choose one recurring problem, its intended result and what remains human.
Examples help only when the user needs them:

| Problem | Small initial loop |
| --- | --- |
| Ready tickets wait for implementation | A human labels one ticket; a remote run opens a draft PR with check results |
| Incoming reports are not understood | Explore one selected report, record evidence/questions, then stop or hand off an eligible task |
| PRs wait for feedback | A separate reviewer inspects an exact diff; bounded rework addresses findings |
| Technical debt keeps growing | Pick one agreed exception per day, tighten the existing check and propose one PR |

Reuse existing review, recovery and task owners. These examples do not create
schedules, grant merge authority or require a fixed chain of agents. When the
user already chose the loop, develop that loop rather than reopening selection.

## Map work to services

Use these distinctions when they help; keep established project terminology.
A **task** is a repeatable kind of work, a **trigger** starts it, a **run** is one
execution, and a **runner** is its execution environment. A run may contain more
than one agent session. Service roles can share one product or machine.

| Role | Design question |
| --- | --- |
| Ticket tracker | Where do humans and agents read work, decisions and questions? |
| Ticket source | What creates work, and how are duplicate reports reconciled? |
| Git host | Where are revisions, branches, PRs and reviews recorded? |
| Orchestrator | What accepts triggers, claims work, starts runs and records progress? |
| Runner | Where does code actually run, with what tools and isolation? |
| Observation | Where can the operator see outcome, errors, attempts and cost? |

Reuse known services. A product can fill several roles; runner/orchestrator logs
may provide enough observation. Research current capabilities and terms only
when selecting or validating a product; do not treat a vendor list as a durable
recommendation. Name a proposed product as proposed until accepted.

For each task, establish its trigger, inputs and permitted writes, completion
evidence, next action, human re-entry point and protection against competing
runs. For each ticket source, establish duplicate-report handling. One small
flow diagram or table is usually enough; do not create a second backlog.

## Remote execution contract

Resolve this contract for the affected loop before its remote implementation or
dispatch. In design-only work, unknown parts remain explicit open decisions.

- **Scope and environment:** identify the repository and allowed revision,
  task owner, runner and required tools. Choose local, remote or mixed execution
  from user intent and verified capabilities. A remote VPS is not automatically
  an isolated disposable environment: name checkout, process, data and network
  boundaries as needed. The local helper is not a remote dispatcher.
- **Durable state:** put work identity, decisions, current attempt and result
  references in the existing tracker/Git/orchestrator. Treat workspace files and
  session history as disposable execution context; remote continuation must be
  reconstructible without the original chat. Do not copy live TD/PS controller
  state or a sibling receipt between roots.
- **Claim and reconcile:** use the owning system's atomic claim/queue mechanism
  for the task and revision, not a chat acknowledgment or local worktree lock.
  Specify how duplicate trigger delivery is recognized and how an interrupted
  run is reconciled with actual commits, PRs, runner activity and pending writes.
  Unknown liveness is not permission for a second writer. Before retrying an
  external effect, read back its actual result; an absent response is not failure.
- **Human questions:** an unattended run records its question, evidence and next
  obligation, then finishes as waiting for a human. The answer can trigger a new
  run from durable context. Do not leave compute waiting indefinitely or assume
  a new run inherits chat memory. Interactive local work may keep its session.
- **Limits and recovery:** identify accepted limits for attempts, elapsed time,
  concurrent writers and spending, plus the operator's stop path. Unknown budgets
  stay unknown and block spending-dependent execution, not design preparation.
  Apply the host's writer/review limits; no remote profile bypasses them. Stop
  exhausted loops with a usable handoff. Recovery of the factory itself must not
  recursively trigger unbounded repair runs.
- **Access and effects:** establish runtime identity and the task's allowed
  repository, data, network and publication actions. Deliver credentials through
  the approved runtime mechanism, never task text or logs. Approval to design a
  factory does not authorize provisioning, purchases, schedules, push, merge or
  deployment. Reuse actual task authorization rather than asking again.
- **Evidence:** define what proves successful work and remote execution: runner
  identity, exact revision, actual commands/results and durable readback. Preserve
  failed attempts and unverified stages. A diagram, fixture or local PASS does not
  prove provider delivery, remote execution or production behavior.

## Introduce automation gradually

Start with one explicitly selected task or a throttled trigger. Use the project's
deterministic checks and independent review required by its active policy. For a
new unattended pilot, propose human PR review before merge unless the accepted
project policy already determines that boundary; do not rewrite global routing.
Turn recurring human findings into stronger checks or review guidance where
useful. Increase volume only after examining actual outcomes and failure handling.

The first pilot can be: human-selected ticket -> remote implementation -> checks
-> draft PR -> human decision, with any required independent review before merge.
Remote pilot verification should cover the normal path plus the relevant duplicate
trigger, interrupted run, lost response, human question and limit-stop cases.
Use synthetic data for preparation; an offline exercise is separate evidence
from a real remote run. Select cases by the loop's effects rather than a fixed quota.

## Finish and hand off

Keep the design in the existing architecture/operations document and its next
slice in the existing plan/tracker. If no project owner exists, provide a compact
proposal in chat or the requested document; do not force a new registry. Show:

- the current working path and its evidence;
- the target flow, service roles and human boundaries;
- accepted choices, proposals and remaining decisions;
- the smallest next slice, its checks and what remains unimplemented.

Project Start owns project-wide architecture maintenance when needed. Task
Delivery owns implementing a slice. Software Factory supplies flow/environment
choices and integration context; Deployment retains release ownership. Missing
skills are disclosed at the affected handoff without blocking a useful design.
Do not claim the target is operational until the actual runner and readback prove it.

Design language and small-loop examples are adapted from Matt Pocock's
[Software Factory draft PR #1316](https://github.com/mattpocock/skills/pull/1316),
inspected at [b59cab42](https://github.com/mattpocock/skills/tree/b59cab42bf1206e1363eafc37f71b21c3bcaa12f/skills/in-progress/software-factory).
This adaptation retains local execution and existing project owners; it does not
import the upstream remote-only constraint or its strict synonym rules.
