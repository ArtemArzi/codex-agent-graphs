# Global Codex Orchestration Policy

These instructions apply across projects unless a more specific instruction explicitly narrows them.

## Delegation decision

- Delegation is optional. Do the work locally when it is small, sequential, tightly coupled, or cheaper to complete directly.
- Available concurrency is capacity, not a target. Never fill slots merely because they are available.
- Delegate only bounded work that is independent enough to run concurrently or benefits from an independent review.
- Use 0-2 subagents for normal work and up to 3 in one wave without additional fan-out justification.
- Use 4-5 subagents in one wave only when every agent has a distinct non-overlapping scope, the work is substantial enough to justify startup cost, and parallel execution materially shortens the task.
- Use at most 5 active subagents at once and no more than 2 write-capable agents concurrently.
- Use at most 7 newly spawned subagents per user request. Exceed seven only when the user explicitly authorizes a higher numeric limit for that request.
- Do not create one agent per file, duplicate scopes, speculative backup agents, or review-of-review chains.

## Model policy

- Reserve Ultra for the user-facing root orchestrator.
- Never override a subagent to Ultra; use the configured role model and reasoning level.
- Route exploration and research to Terra High; worker and task_worker to Astra Low; reviewer, task_result_reviewer, block_reviewer, and task_plan_reviewer to Astra High. Keep other specialized roles on their configured models.
- Do not use `fork_turns = "all"` from an Ultra root because a full fork inherits Ultra and bypasses specialized role routing.

## Spawn contract

- Every spawn must explicitly set `agent_type` and `fork_turns`.
- Default to `fork_turns = "none"` and send a self-contained dispatch packet.
- Use `fork_turns = "1"` to `"3"` only when a small amount of recent conversation state is essential and risky to restate.
- Use `fork_turns = "all"` only for a true same-model continuation that requires the exact full history, cannot be expressed as a bounded dispatch packet, and does not violate the root-only Ultra policy.
- A dispatch packet should state the objective, scope and ownership, must-read paths or sources, known facts, acceptance criteria, verification, and expected output.

## Topology and lifecycle

- The root agent owns orchestration and final synthesis.
- Subagents are leaf workers and must never spawn descendants. Keep `agents.max_depth = 1` unless the global topology policy is deliberately redesigned.
- Maintain an internal count of newly spawned agents for the current user request.
- Count `spawn_agent` calls toward the seven-agent budget; `followup_task` reuse does not increment it.
- Treat a delegation scope as the combination of objective, owned artifact or subsystem, expected output, and acceptance criteria. Give each independent scope a fresh task name.
- Use `followup_task` only for correction, retry, clarification, or verification inside the same scope. A new task card, implementation slice, review block, artifact, or acceptance criterion requires a fresh `spawn_agent` with `fork_turns = "none"`, even when the `agent_type` is unchanged.
- After five new agents, prefer reuse only when the same-scope rule permits it. Never reuse an agent across scopes merely to conserve the spawn budget. After seven, continue serially unless the user explicitly raises the numeric limit.
- Do not redo delegated work merely because a wait operation timed out; wait again, inspect status, or narrow a follow-up first.
- After the root collects and integrates an agent's result, keep that agent open only while a same-scope follow-up is expected; otherwise stop or close it immediately when the available surface supports it.
- Before starting another independent scope, close completed agents from the previous scope. If explicit close is unavailable, treat those agents as terminal and never repurpose them; if the open-thread cap prevents a fresh spawn, continue serially in the root.

## Default routing

- `explorer`: read-only repository discovery and execution-path tracing.
- `researcher`: current external documentation and evidence-backed research.
- `worker`: bounded implementation, tests, and refactors.
- `reviewer`: whole-system architecture and cross-cutting final review on Astra High.
- `block_reviewer`: bounded read-only review of one explicitly assigned block on Astra High.
- `default`: bounded independent work that does not fit a specialist role.
- In Multi-Agent V2, per-role `sandbox_mode` is behavioral intent rather than a hard boundary because children inherit the parent runtime permission profile. Use a read-only parent session when read-only enforcement is required.

## Deep multi-review

- Use deep multi-review when the user explicitly requests deep, parallel, or multi-agent review, or when a material plan or implementation has at least two genuinely independent review blocks. Keep ordinary reviews on the single `reviewer` path.
- Size the review by the block map: two independent blocks use two block reviewers plus one whole-system reviewer; three use three plus one; four or more are grouped into at most four coherent blocks plus one whole-system reviewer. Never create one reviewer per file.
- Before spawning, map non-overlapping blocks by subsystem, contract, lifecycle, or risk surface. State why a 4-5 agent wave is justified when using that capacity.
- Spawn the whole-system `reviewer` and all `block_reviewer` agents in one wave. They review the same artifact independently from different scopes; they do not review one another.
- Give every reviewer a self-contained dispatch packet with the objective, exact scope, exclusions, must-read paths or sources, known facts, acceptance criteria, verification expectations, and required output format. Default `fork_turns` to `none`.
- Keep every review agent read-only and leaf-only. For a review-only turn, put the parent in read-only mode when the client supports it; a write-enabled parent can make the child role's `sandbox_mode` behavioral rather than a hard boundary. Block reviewers must stay inside their assigned block; the whole-system reviewer owns cross-block architecture, contracts, sequencing, lifecycle, security boundaries, and aggregate verification gaps.
- Wait for every requested reviewer. If a reviewer fails transiently, retry by reusing that agent once with a narrowed follow-up. If it cannot complete, the root covers the missing scope directly, reports the coverage gap and reduced confidence, and must not claim the deep review fully complete.
- The root agent verifies the strongest claims against the real artifact, removes duplicates, reconciles disagreements, and returns one severity-ordered synthesis with concrete evidence and residual risks.
- After corrections, reuse the same agents with `followup_task` for targeted verification when possible. Do not spawn a fresh review-of-review chain.
