# Global Codex Orchestration Policy

## When delegation helps

- Follow the inherited Unified model routing and independent acceptance policy. The main agent owns decisions and integration; auxiliary roles perform bounded discovery, preparation, execution and focused checks. Direct local tool calls remain appropriate for trivial or tightly coupled integration steps.
- Before each spawn, identify a bounded result and why independent work or review is worth the startup, context and integration cost. Keep this justification in the dispatch; do not create a separate artifact for it.
- Use an explorer for one unclear execution path, a researcher for one current external question, a worker for an independently owned implementation unit, and an auxiliary focused reviewer for a narrow uncertainty. Whole acceptors cover the required acceptance boundaries. A file, plan heading, slice, model name or available slot alone is not a reason to spawn.
- A request to work in stages or slices does not require subagents. Respect an explicit request for delegation or independent review; otherwise select it by expected benefit.
- Do not duplicate a live or completed scope. While a child owns discovery, inspect only unassigned seams. Afterward, verify decisive claims and source files rather than repeat its whole search.
- Keep dispatch and results concise: objective, ownership/exclusions, relevant evidence, acceptance and expected output. Return findings and evidence, not a transcript or exhaustive file inventory. Expand only when a concrete missing fact requires it.

## Capacity and continuation

- Use 0–2 concurrent subagents for ordinary work. A third needs a distinct useful scope; 4–5 are reserved for explicitly deep parallel work whose independent scopes materially reduce completion time or improve necessary review.
- Never exceed five active subagents or two simultaneous writers; obey stricter host limits. Concurrency is capacity, not a target.
- Count starts, waits and retries to spot overhead. There is no local cumulative agent-start ceiling for an entire user task; each additional start still needs useful bounded work. Do not create a new run merely to reset a counter.
- At a host limit or unavailable delegation, continue authorized local work as root. Do not ask the user about technical counters, fabricate an independent review, or claim verified completion when a required review is unavailable. Report the precise remaining check and preserve a resumable handoff when it cannot be completed.
- If an agent twice produces no new evidence, stop that failing loop and change approach or continue locally. Do not repeatedly launch a larger-context successor for the same unexplained failure.

## Model and dispatch

- Preserve each configured role's model and effort from the shared routing policy. Whole-plan/result acceptors and auxiliary focused reviewers are different classes; use the matching role rather than overriding its model.
- Ultra is reserved for the user-facing root; never override a child to Ultra.
- Explicitly set agent_type and fork_turns="none" for every spawn and provide a self-contained task with direct evidence. Continue corrections with the same assigned reviewer instead of copying the parent's transcript into a new agent.

## Ownership and lifecycle

- Root owns orchestration, semantic judgment, integration and delivery after required independent acceptance. Children are leaf workers; keep agents.max_depth = 1.
- A scope is objective + owned subsystem/artifact + expected output + acceptance. Give each independent scope a new task name and fresh context.
- Reuse followup_task only for correction, clarification or verification of the same scope. Do not repurpose a finished agent for another slice to hide new work from a counter.
- A timeout is not failure or completion. Wait, check status or narrow a same-scope follow-up; do not duplicate the assignment.
- Close completed agents when supported. Otherwise treat them as terminal and do not repurpose them. If open-thread capacity is exhausted, continue locally.
- Read-only role settings describe intent when the host inherits the parent's permissions. Use a read-only parent for enforced read-only review when available; every dispatched reviewer must still remain read-only.

## Review proportional to risk

- Obtain the whole-plan and whole-result acceptances required by the shared policy. Add auxiliary focused reviewers for concrete narrow questions at either acceptance boundary; they supplement the whole acceptor and never substitute for it.
- Additional focused reviews cover distinct failure modes and may run beside the whole acceptor. Explain the useful coverage before spawning; a separate deep-review ceremony is not required by this user policy.
- For deep review, map at most four coherent non-overlapping blocks plus one whole-system reviewer. Run them against the same candidate; they do not review one another. Do not create a reviewer per file or a review-of-review chain.
- Wait for all required reviews and reconcile the strongest claims against the artifact. Retry a transiently failed review once in the same scope; if unavailable, cover what can be covered locally and state the independence gap without calling the deep review complete.
- After a correction, request only targeted same-scope verification. Re-run broad checks only when the changed evidence or remaining risk warrants it.
