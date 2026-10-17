# Factory reference delta — 2026-10-17

Read-only research packet for the root implementer. No source/project changes, installs, external code execution, or chat-to-chat messages. One recommendation survives comparison with the existing Factory; the other candidate areas are already substantially covered.

## Source basis and pins

Owning GitHub MCP `get_file_contents` and `list_commits` read repository sources. Latest main observed:

- ZazenCodes: `555467c365e6750278efba09349369109f62f65f`, committed 2026-10-07 15:27:07Z.
- OpenAI Symphony: `be10a1b79df723d6d7612b5651c8522704dafb2e`, committed 2026-09-15 22:12:07Z. SPEC labels itself **Draft v1**, not a released conformance guarantee.

Five decisive source files/pages were read (directory listings and commit metadata are navigation):

1. [Upstream Factory skill](https://github.com/zazencodes/zazencodes-season-3/blob/555467c365e6750278efba09349369109f62f65f/src/software-factory-claude-code/.claude/skills/factory/SKILL.md), sections Build check, Review round N, Merge, /factory rework. The orchestrator reads explicit output artifacts, waits for the entire review round before repair, then distinguishes merge success from cleanup failure. Rework reads existing history and starts another explicit round.
2. [Upstream builder](https://github.com/zazencodes/zazencodes-season-3/blob/555467c365e6750278efba09349369109f62f65f/src/software-factory-claude-code/.claude/agents/builder.md), Read first, Commit, Write build.md. Builder must verify its assigned branch, read prior rework/build/review history, commit explicit paths, preserve earlier-round log, and identify environmental/business blocking causes.
3. [Upstream approver](https://github.com/zazencodes/zazencodes-season-3/blob/555467c365e6750278efba09349369109f62f65f/src/software-factory-claude-code/.claude/agents/approver.md), Decide. Approval requires convincing evidence for all acceptance criteria, one independent spot-check, final reviews and conflict check; upstream approval itself authorizes automatic local main merge.
4. [Symphony SPEC](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/SPEC.md), sections 7.4, 8.4–8.5, 9.2–9.3, 12.3, 14.3, Appendix A.2–A.3. It reconciles live state before dispatch and checks both claimed/running identity, refreshes eligibility before retry, reuses preserved workspaces, does not assume sessions survive restart, and calls cross-host re-execution after side effects a new attempt rather than invisible failover. Appendix A warns against duplicate execution from confusing host startup and in-workspace failures.
5. [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), published 2025-11-26; sections Incremental progress, Getting up to speed, Testing. Fresh sessions recover from git history plus progress artifacts and run a basic user-flow check before extending work. Evidence is their web-app experiment, not proof of this Factory's behavior or a general multi-agent superiority result.

No Agent Mail/Gas Town branches repeated. No implementation was copied or executed.

## Confirmed local coverage

Compared actual local `skills/software-factory/SKILL.md`, `references/routing-and-context.md`, `references/readiness-and-checks.md`, `references/helper-usage.md`, and the relevant `scripts/factory.py` status/verify implementation at root-provided base `f55f7d76b1fa1e2045d3bf51a68528da08b3db32`.

- Routing/context lines 151–162 already demand explicit acknowledgement, reject timeout-as-completion, avoid duplicate owners, distinguish `send_message` from `followup_task`, and deny durable session restart guarantees.
- Routing/context lines 175–191 already demand actual diff/commit/check acceptance, combined product checks, required review, freeze/repackaging after contract drift, and inspecting Git/packets after interruption.
- Readiness lines 35–68 already cover canonical-runner discovery, import/build origin, environment capability probes, unchanged-case discrimination, failed/interrupted evidence, and exact candidate/environment binding.
- Helper `status` checks observed current source/job/candidate state against saved verification. `verify` integrates exact clean owned commits in a separate retained worktree. Its `check` and `fresh` remain separate from task approval/completion.

Therefore environment-origin probes, combined acceptance, exact-SHA freshness, review joins, and simple non-duplicate-owner guidance should not be reintroduced as new features.

## One actionable improvement: reconcile the completed work before replaying a lost turn

**Gap (inference from comparison):** the current interruption instructions say to inspect state, but do not give a decision for the important case where the leaf committed or an authorized integration completed and the final message never arrived. A caller can still interpret a lost turn as missing work and unnecessarily repeat implementation/integration. The code helper is not defective for this; its evidence is available, but the human/agent procedure needs to use it explicitly.

**Narrow edit location:** expand `references/routing-and-context.md` under Join, changes and interruptions, replacing/extending its two general interruption sentences. Add a short SKILL pointer only if needed for discovery. Do not change helper schemas, add a scheduler, or add task state files.

Proposed text:

> Before a follow-up or replacement after interruption, reconcile the existing task record, exact assignment/base, actual native agent state when available, worktree HEAD/dirty state, retained result/check artifacts, and any already performed integration. Record the observed result and the next unfinished obligation in the existing task record. A missing final message does not undo a committed result, and a worker exit does not prove acceptance.
>
> If the original owner is active or its state is unknown, preserve ownership and continue independent work; do not dispatch another writer for the same mutable scope. If its committed result exists, inspect the diff and resume only missing checks, review or authorized integration. If only partial dirty work exists, preserve it and continue with the same available owner. If that owner is unavailable, establish that no prior writer remains active before explicitly transferring the unfinished scope with current state and evidence. If baseline/contract changed, keep the old result as evidence and issue updated context before dependent work. Never replay a potentially external or non-idempotent action solely because its response was lost; first inspect the owning system's actual result and use its existing retry/recovery rules. Factory does not grant missing authority or guarantee durable restart.

This is a procedural adaptation of source reconciliation, not an attribution that upstream implements the same Codex protocol. It complements the accepted inter-chat coordination design with an intra-task recovery decision.

## Testable scenarios

Documentation scenario checks are proportionate; helper code changes/tests are unnecessary unless the implementation scope actually expands.

1. **Commit succeeded, final reply lost:** assigned leaf HEAD contains owned changes at accepted base, clean tree, no live writer. Expected: root accepts the candidate only after diff/check inspection; continues missing review/integration, does not rebuild the same slice.
2. **Follow-up response delayed, owner active/unknown:** expected: no duplicate writer; independent work can proceed; no stale lock deletion or automatic ownership takeover.
3. **Dirty partial work, unavailable old owner:** expected: preserve bytes; transfer only after prior writing activity is established absent, with fresh context. Unknown activity remains a blocked dependent operation, not permission to replace.
4. **Authorized integration succeeded, acknowledgement lost:** actual target/history proves integration already happened. Expected: no second integration or repeated side effect; verify outstanding postcondition and report actual state.
5. **Context/base changed during interruption:** expected: retain previous commit and old verification, mark affected evidence stale, repack/recheck only affected obligations before dependent use.
6. **Environment smoke fails on unchanged base:** expected: existing readiness procedure applies; preserve failure and repair environment or surface missing capability. Do not add a new retry engine or relax the check.

## Source disagreements and limits

- Upstream has mandatory spec/builder/four-reviewer/approver roles and automatic main merge/cleanup; our Factory deliberately preserves root implementation, existing task ownership, policy-based reviews, two-writer limits, and actual user authority. Do **not** import that chain, merge authority, auto-cleanup or its fixed resume count.
- Symphony is an autonomous tracker-backed scheduler with state claims, retry timers and startup cleanup. Borrow reconcile-before-retry and stable work identity as a reasoning rule only. Do **not** add a global registry/controller, polling, automatic retries, automatic cleanup or assume native Codex sessions are restartable.
- Anthropic's progress-file and feature-list pattern overlaps existing task records/accepted requirements. Reuse those owners; do not add `claude-progress.txt`, `feature_list.json`, mandatory initializer agents or an unconditional browser smoke on non-web work. It explicitly leaves generalization and single-versus-multi-agent superiority open.
- This packet establishes source-based guidance and a local procedural gap. It does not prove live chat coordination, interruption recovery, deployment, speed or cost savings.

## Memory provenance

Used MEMORY.md:1050–1087 for orientation to prior Factory adaptation and non-duplication; current local/source inspection takes precedence. Relevant rollout ID: `01a124e5-b11e-7080-a531-9ad6618700dc`. No memory writes.
