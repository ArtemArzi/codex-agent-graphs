# Execute a prepared project

Read when the user supplies project documentation and asks Factory to implement
the system, or when resuming that execution after a human step or interruption.
Use the existing execute route and Task Delivery. A board, factory interview,
new progress registry or remote runner is not a prerequisite for local work.

## Keep the accepted outcome visible

Read the accepted requirements, architecture, quality/acceptance document and
current task owner before choosing ready work. Check relevant prerequisites;
settled product decisions do not need another interview. Resolve a missing
business decision before its dependent work, while continuing independent parts.
Use Task Delivery's full implementation path when the request covers plan to
code. Apply the host's review threshold; this reference adds no fixed reviewer
chain or approval between ordinary engineering stages.

Keep requirement-to-check coverage in the existing quality/task owner. For each
affected outcome distinguish implementation, observed verification and any
pending human/provider condition. Reuse project check IDs and original evidence.
Do not create a second feature list or change requirements/test meaning to make
the candidate pass. The final result must account for the accepted project scope,
including combined behavior, rather than only the last finished slice.

## Prepare a usable human step

When an actual prerequisite needs the user, first complete the authorized work
that can be prepared and checked without it. Record in the existing task owner:

- what is ready and its bounded check results;
- the exact remaining action and its purpose, including the approved account,
  configuration location or credential mechanism when known;
- how the result will be checked and the exact next unfinished operation.

Use the approved secret-entry mechanism; task text, logs, screenshots and source
control are not secret stores. Ask for no secret value in chat. Missing authority
remains missing; an instruction to continue does not prove a provider action or
successful authentication. A local/mock check does not verify the external path.
Pause only dependent work and retain partial results honestly. In an unattended
run, save the wait and end; after the human answer use durable task context.
An interactive native chat can continue in its supported way.

## Continue from observed state

Before continuation, reconcile the existing task, accepted contract, actual
revision/dirty state, prior writer activity and original check/result evidence.
See [routing-and-context.md](routing-and-context.md#join-changes-and-interruptions)
for ownership, lost responses and already-applied effects. A fresh context must
read those sources; it cannot assume the previous conversation survived.
Continue the next unfinished obligation rather than reinitializing the project.

When code, environment or relevant evidence changed, run a short project-native
check of the affected previously working path before stacking dependent work.
Select that check from the quality document and observed change. Reuse valid
unchanged checks; a new session alone does not require another full suite.
Record invalidated evidence and repair a real regression before dependent work.
Never import another root's live TD/PS state or treat replayed chat as authority.
The skill does not automatically restart a stopped process or supply persistence
for an external runner.

## Recognize an unproductive loop

Judge progress by new observations that narrow the problem or satisfy the
accepted outcome. Another command, rephrased plan or repeated identical failure
is not itself progress. Follow the existing development-recovery trigger after
two consecutive attempts without new evidence; preserve the failing result and
choose a bounded changed approach. Do not reset counters by creating a new run,
weaken the check or add a worker to repeat the same unresolved assignment.
Legitimate repeated checks with changed code or new evidence are different.
Automatic loop detection and enforced cost limits require a real runner; this
instruction does not add either mechanism or change the host's actual limits.

## Close the whole requested outcome

Read back the integrated candidate, applicable acceptance checks and required
independent review. State what is implemented, what was actually verified, what
awaits a human/external prerequisite and what has been accepted or released.
A worker exit, helper PASS, commit or screenshot alone is not whole-project
completion. Keep deployment under its existing authority and project gates.

For author validation, exercise a small prepared project through implementation,
an actual recorded human pause, fresh-context continuation and combined checks.
Use synthetic operator input. Add relevant failure branches such as a duplicate
continuation or interrupted/stale evidence; assess behavior and preserved effects,
not keyword matches. Such an exercise is bounded local evidence, not proof of
cloud recovery, provider delivery, general speed gains or every future project.

Patterns informed by [Anthropic's long-running coding example](https://github.com/anthropics/claude-quickstarts/blob/1a18c340ca42b9137d991637afe867bdcf70a9ce/autonomous-coding/prompts/coding_prompt.md),
[OpenHands persistence](https://github.com/OpenHands/software-agent-sdk/blob/641e161178cb934f38afcbe603125950611d1668/examples/01_standalone_sdk/10_persistence.py),
[pending actions](https://github.com/OpenHands/software-agent-sdk/blob/641e161178cb934f38afcbe603125950611d1668/examples/01_standalone_sdk/04_confirmation_mode_example.py)
and [Symphony retry tests](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/test/symphony_elixir/core_test.exs#L1141).
These are references; their framework, permissions, fixed feature counts and
separate progress files are not imported. No upstream implementation is copied.
