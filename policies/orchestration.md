# Global Codex Orchestration Policy

## When delegation helps

- Work locally by default. A small, sequential or tightly coupled task rarely benefits from another agent.
- Before each spawn, identify a bounded result and why independent work or review is worth the startup, context and integration cost. Keep this justification in the dispatch; do not create a separate artifact for it.
- Use an explorer for one unclear execution path, a researcher for one current external question, a worker for an independently owned implementation unit, and a reviewer for material uncertainty or risk. A file, plan heading, slice, model name or available slot is not a reason to spawn.
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

- Preserve the configured role model and effort. Exploration/research use Terra High; worker/task_worker use Astra Low; reviewer/task_result_reviewer/block_reviewer/task_plan_reviewer use Astra High. Other specialized roles retain their configured models.
- Ultra is reserved for the user-facing root; never override a child to Ultra.
- Explicitly set agent_type and fork_turns for every spawn. Default fork_turns to none and provide a self-contained task.
- Use 1–3 recent turns only when essential context is risky to restate. Never use a full-history fork from an Ultra root; it inherits the parent's model and reasoning level.

## Ownership and lifecycle

- Root owns orchestration, semantic judgment, integration and final acceptance. Children are leaf workers; keep agents.max_depth = 1.
- A scope is objective + owned subsystem/artifact + expected output + acceptance. Give each independent scope a new task name and fresh context.
- Reuse followup_task only for correction, clarification or verification of the same scope. Do not repurpose a finished agent for another slice to hide new work from a counter.
- A timeout is not failure or completion. Wait, check status or narrow a same-scope follow-up; do not duplicate the assignment.
- Close completed agents when supported. Otherwise treat them as terminal and do not repurpose them. If open-thread capacity is exhausted, continue locally.
- Read-only role settings describe intent when the host inherits the parent's permissions. Use a read-only parent for enforced read-only review when available; every dispatched reviewer must still remain read-only.

## Review proportional to risk

- Use one independent reviewer for an ordinary review, focused on counterexamples, actual behavior and decisive evidence. Do not add a review layer merely because more than one file or subsystem changed.
- Deep/multi-agent review is for an explicit user request, or a concrete high-risk case where independent review blocks will address different failure modes. Explain the additional coverage before spawning.
- For deep review, map at most four coherent non-overlapping blocks plus one whole-system reviewer. Run them against the same candidate; they do not review one another. Do not create a reviewer per file or a review-of-review chain.
- Wait for all required reviews and reconcile the strongest claims against the artifact. Retry a transiently failed review once in the same scope; if unavailable, cover what can be covered locally and state the independence gap without calling the deep review complete.
- After a correction, request only targeted same-scope verification. Re-run broad checks only when the changed evidence or remaining risk warrants it.
