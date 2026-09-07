# Adaptive delegation and current model routing

Status: COMPLETE

## Accepted outcome

Delegate only when a bounded independent question, implementation unit, or risk review justifies startup and handoff. Preserve current installed Codex models in the canonical source. Work in slices does not itself require agents. A cumulative agent count does not block a valid long task; host restrictions still apply and unavailable independent checks are not reported as passed.

## Basis and scope

- Baseline main: dfcf4dc; remote parity and installed graph parity established in the preceding research.
- Evidence: docs/research/astra-graph-audit-2026-09-07.md.
- Own global orchestration policy/installer, Task Delivery graph/controller/instructions/tests, shared graph validation contracts, and three model role configs plus Claude projection compatibility.
- Preserve Project Start topology and legacy runs, optional discovery roles, independent critical review, immutable evidence, path ownership and bounded no-progress retries. Do not modify product repositories or hooks.

## Delivery

1. Sync the three already-installed model roles to Git; preserve Claude's existing effective model/effort with explicit tested projection.
2. Release Task Delivery 3.9 with adaptive cumulative delegation accounting, preserving pinned 3.8 behavior. Keep concurrency and no-progress guards, allow a positive slice estimate without an arbitrary six-slice ceiling, and distinguish stages from delegation.
3. Manage the global orchestration instructions from this repository; migrate only the recognized prior policy, back up installations, and preserve unrelated instructions/configuration.
4. Run focused adversarial/controller/install tests, fresh bounded behavioral checks, and independent review. Install verified changes in WSL/Desktop with backups; validate parity without restarting applications.

## Acceptance

- Small/root-only work has no mandatory worker or review; independent review remains risk-triggered.
- A task with more than eight useful sequential slices can retain receipts and complete; required reviews are still validated.
- Old 3.8 graph identity remains accepted with its old bounded behavior; unknown identities, stale scope and tampered evidence remain rejected.
- A planned slice estimate is not a task-stop trigger; repeated same-scope failures still stop the failing loop.
- Current worker/reviewer models survive installation and reinstallation; Claude output remains equivalent.
- Global rules retain bounded concurrency, leaf agents, fresh scoped context, no duplicate scopes and no review-of-review chains; no local seven-start stopping rule remains.
- Installation preserves user changes and confirms source/runtime parity. No push or deployment requested.

## Verification

Focused Python tests, installed skill validation, disposable fixture behavior and `python3 scripts/check_all.py`; independent review of the final cross-cutting changes. Report actual coverage and any host restrictions. No claim of measured token savings without a controlled comparison.


## Verification evidence — 2026-09-07

- Full `python3 scripts/check_all.py` passed again after the final admission wording correction, including installed skill validation and Claude projection checks.
- Focused suites: Task Delivery 96, installer 20, shared graph contract 13, Claude packaging 15 tests passed. These are controller/installation tests, not nine live agent starts.
- Nine accepted sequential slice fixtures complete beyond the planning estimate; premature completion remains rejected. A recoverable first result can continue beyond estimate 1; estimate 12 still stops two consecutive unsuccessful attempts.
- Independent Astra High reviewer passed the same four suites and 12 adversarial probes using the exact pinned 3.8 graph identity. The legacy asset is byte-identical to the previous release. One P2 admission ambiguity was found, corrected and independently rechecked: final PASS.
- Fresh Astra Low agent used the candidate installed in `/tmp/td39-forward-8lj5bozc/.codex` on a disposable two-stage duration formatter. Correct implementation, 5 final tests, no descendants, no network or MCP lookup. Installed init/record/complete/compact commands worked. It chose root-only tracked and created 10 control/documentation artifacts; this exposed ambiguous slice-to-tracked admission wording. The first plan write failed due to cwd, so the successful plan write occurred after the first code stage. No false pre-implementation plan-review claim is used as acceptance evidence.
- Corrected all three admission phrases: ordinary root-owned stages do not independently require tracked setup. This correction has static review coverage; no fresh post-correction skill-only rollout or controlled time/token comparison was performed. The leaf fixture cannot prove host-level delegation scheduling or skill discovery in a fresh root task.
- Installation plan preflight passed for WSL and Desktop. Both already-installed Astra role files match the candidate; unrelated TOML configuration is semantically unchanged. Managed skills and global policy are the intended updates.

- Live `install --all` and separate `verify --all` passed for `/home/artem/.codex` and `/mnt/c/Users/artem/.codex`, with no parity issues. Backups: WSL `backups/agent-graphs/20260907-220710-643898-261581`; Desktop `backups/agent-graphs/20260907-220710-769630-261581` (relative to each Codex home).
- No applications restarted; new tasks must load the new skill/policy context. Current host restrictions still apply. No push or product deployment performed.
