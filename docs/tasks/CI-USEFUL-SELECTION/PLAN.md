# Continuous Improvement: useful selection and evidence reuse

Status: COMPLETE

## Accepted outcome

Improve CI usefulness, prevent repeated discovery without fresh evidence, and reuse findings in Task Delivery. Preserve one candidate per pass, no-op, low-risk delivery, clean baseline, exact commit and no automatic publication. User additionally authorized pushing this change and the preceding local delegation commit to GitHub. Research remains unchanged.

## Research basis

Baseline main e330cab; clean working tree. Live origin/main dfcf4dc, so the previous delegation change is local-only. WSL/Desktop installation parity was verified earlier in this conversation.

CI1.1 has candidate evidence but no benefit rationale or read-only prior-run summaries. Root selects candidates; code owns identity, evidence and completion. Read-only seam exploration confirms TD3.9 must keep its own current baseline/plan/tests/handoff. Existing CI delivered test synthesizes TD-shaped receipts rather than exercising the actual TD controller. Artifact lifecycle compact preserves raw runs until explicit pruning and copies the result Markdown; Markdown alone does not contain sufficient reusable provenance.

## Implementation contract

- Release CI1.2 with pinned exact CI1.1 identity and unchanged legacy receipt requirements. Keep graph nodes and modes, limits on candidate count, risk and changes. Use shared work_policy v2 with bounded concurrency, no arbitrary cumulative start cap.
- Require candidate benefit fields for 1.2: affected, consequence, frequency, effort and why_now. These are evidence-backed model judgments, not an invented numeric score or proof of business value. Unknown frequency is valid when explicitly stated. Delivery must justify bounded effort; audit can report larger unresolved work.
- Add a read-only bounded history command (default10, max20). Read verified completed raw runs, return concise evidence and exact receipt references; never mutate, restore archives, or treat same local content as proof that external signals are unchanged. Clearly report corrupt/unavailable history. Compacted runs whose raw artifacts remain are supported. If raw runs were pruned, report known final receipt IDs as unavailable for reuse; archive extraction is deliberately outside this slice.
- Read this history before candidate discovery. Avoid repeated investigation of unchanged facts; re-open findings only for changed relevant code, refreshed signal or specific new evidence. Record this reasoning in existing scan sources/no-op reason or candidate why_now, no separate database.
- Pass current reproduction, evidence paths, affected scope, acceptance and benefit in the existing TD plan. TD rechecks relevance and current constraints but does not repeat already evidenced stable searches; its own baseline/tests/receipt remain mandatory.
- Preserve user changes, active legacy runs and installed drift/backups. No new roles, graph stages, schedules or autonomous pushes.

## Verification

Focused history tests (read-only, changed code, tamper, bounded output, symlink, partial/pruned results), benefit and legacy tests; real TD3.9 delivery integration, one fresh disposable behavior exercise and independent review. Full check_all, installer plan/install/verify WSL+Desktop, git diff check, logical commit and authorized fast-forward push with remote SHA verification. Report untested behavior and no measured savings claim.


## Verification findings and corrections

- Real TD3.9 integration now executes a failing regression, applies the bounded source fix, executes the passing check, runs actual TD completion, creates one real local commit, then runs CI completion and both artifact compactions. History reads the resulting actual lifecycle receipt. This replaces synthetic-only seam confidence; the old isolated fixture remains useful for focused guards.
- Independent review reproduced a FIFO FINAL.json blocking history and a legacy1.1 optional-benefit field causing false rejection of valid old completion Markdown. Fixed ordinary-file validation and version-aware rendering; regression coverage retains tamper checks.
- Fresh behavior used a previous audit finding, reproduced its current failure, fixed only the private helper and created a real local commit. TD accepted a lowercase task ID but CI rejected it due to a duplicated stricter regex. The first false assumption was CI's interoperability validator, not the task or its accepted result. One bounded repair aligns new1.2 with TD's exact ID contract; legacy remains unchanged. The same fixture/run/TD receipts/commit are preserved for closure, without renaming the task or repeating implementation.
- The behavioral second pass produced no-op after current checks; no extra improvement, worker, network lookup or product change was invented. No time/token savings are claimed. Same-scope review and corrected fixture closure passed; publication is the final authorized operation below.


## Accepted result

- Independent final review: PASS. Reviewer reproduced the fixed FIFO and actual old-runtime1.1 rendering cases and verified exact task-ID compatibility without relaxing legacy behavior.
- `python3 scripts/check_all.py`: PASS after all runtime corrections. Focused CI suite: 25 tests; actual TD3.9 integration: 1 test. Skill validation, shared contract, artifact lifecycle, packaging and installer checks passed in the full gate.
- Fresh installed-skill behavior: seed audit `9879093f55b444fa` -> full repair `f0099757a0d7d0d8` -> second no-op `8455964bdde8cbb2`. TD `ee7deedf289272c7`, local fixture commit `cfde89f72779b51ba2dbc528b338f86a0405bb40`. Existing tests went 1 FAIL/1 PASS -> 2 PASS; follow-up closure reused the same immutable work SHA `c3f239b4f08a27d616f9bb2badc39df9bfcdb1332c1e75e3c9d8e187adaa4da9` with no new code, tests or commits. All three results now appear as usable historical evidence. The prior no-op report retains its then-accurate warning about the unfinished first pass; it was not rewritten.
- Root inspected the actual TD plan: historical receipt path/SHA, current reproduction, affected users, frequency uncertainty, small effort and authorization rationale all transferred into its research basis. No additional agents or MCP/network discovery occurred inside the trial. This is one successful scenario, not a benchmark of general selection quality or savings.
- `install --all` and independent `verify --all`: PASS for WSL and Desktop, no parity issues. Only the Continuous Improvement skill changed in this installation. Backups under each Codex home: WSL `backups/agent-graphs/20260907-223427-668554-401669`; Desktop `backups/agent-graphs/20260907-223427-752231-401669`.
- New tasks load CI1.2; no app restart or product deployment was performed. Research and the other graph versions remain unchanged. Raw-pruned history remains explicitly unavailable for reuse; no archive restore was added.
- User-authorized publication: this change plus prior local delegation commit `e330cab` to origin/main, using a normal fast-forward push and post-push remote SHA verification.
