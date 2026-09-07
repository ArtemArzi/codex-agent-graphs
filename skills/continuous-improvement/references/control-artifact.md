# Continuous Improvement control artifact

`improvement.json` is the immutable receipt for one bounded repository pass. It records evidence and handoff identity, not chain-of-thought.

## Work receipt

```json
{
  "schema_version": 1,
  "run_id": "16 hex",
  "mode": "full",
  "focus": "User question or scan focus.",
  "disposition": "delivered",
  "confidence": "high",
  "capabilities": ["rg", "project-test", "mcp:not-applicable:local-signal-only"],
  "agents": [],
  "scan": {
    "sources_checked": ["failing tests", "recent changes"],
    "no_candidate_reason": null
  },
  "candidate": {
    "candidate_id": "short-stable-id",
    "title": "Observable defect",
    "source_kind": "failing-test",
    "risk": "low",
    "protected_domains": [],
    "benefit": {
      "affected": "Users of the affected operation",
      "consequence": "The operation produces the reproduced incorrect result",
      "frequency": "Every matching input; production frequency is unknown",
      "effort": "small",
      "why_now": "The current failing check proves a bounded defect with a focused repair"
    },
    "evidence": [{"kind": "command", "reference": "python -m unittest ...", "observation": "fails before the fix"}],
    "reproduction_commands": ["python -m unittest ..."],
    "acceptance": ["The regression test passes without weakening the contract."],
    "scope": ["src/module.py", "tests/test_module.py"]
  },
  "issue": null,
  "task_delivery": {
    "run_dir": ".agent-graphs/task-delivery-runs/<id>",
    "state_sha256": "64 hex",
    "task_sha256": "64 hex",
    "handoff_sha256": "64 hex",
    "changed_paths": ["src/module.py", "tests/test_module.py"],
    "tests": [{"command": "python -m unittest ...", "status": "passed", "exit_code": 0}]
  },
  "git": {
    "branch": "codex/continuous-improvement-<run-id>",
    "commit": "40 or 64 hex"
  },
  "residual_risks": []
}
```

## Dispositions

- `no-op`: `candidate`, `issue`, `task_delivery` and `git` are null. `scan.no_candidate_reason` is substantive. Repository content must match the initialized baseline.
- `issue-ready`: candidate evidence and an `issue` object with `title`, `body` and `reason` are required. No Task Delivery receipt or commit is allowed. Repository content must match baseline.
- `delivered`: allowed only in `full`; candidate risk is `low`, protected domains are empty and source kind is allowlisted. Graph 1.2 additionally requires `benefit.effort=small`. A completed Task Delivery v3 run, exact handoff, tests, changed paths and one non-default-branch commit are required.

Graph 1.2 requires `candidate.benefit` for `issue-ready` and `delivered`.
`affected`, `consequence`, `frequency` and `why_now` are substantive statements
grounded in the available evidence; unknown frequency is valid when explicit.
`effort` is `small`, `medium` or `large`; medium/large work may be issue-ready.
This is a short selection rationale, not a numeric score or a claim that the
controller proves business value. Legacy 1.0/1.1 receipts keep their old contract.

Every receipt contains exactly one MCP capability: `mcp:<server>` after
relevant use, `mcp:fallback:<reason>` after a relevant server fails, or
`mcp:not-applicable:<reason>` for a local-only signal. The verifier binds
`work_sha256` and, for delivered work, the exact Task Delivery and commit
identities.

## Verification receipt

```json
{
  "schema_version": 1,
  "run_id": "16 hex",
  "reviewer_role": "improvement_verifier",
  "reviewer_receipt": "/root/improvement_verify",
  "verdict": "pass",
  "work_sha256": "64 hex",
  "checked_claims": ["candidate evidence and risk boundary"],
  "residual_risks": [],
  "repair_list": []
}
```

`reject` requires a non-empty repair list. One repair may replace `improvement.json`; a second rejection blocks the run.

## Completion

`complete` rechecks the current graph, baseline, immutable work/verification receipts, Task Delivery completion and exact commit. It writes `IMPROVEMENT.md` inside the run directory with the final disposition, evidence summary, changed paths/tests when delivered, and residual risks.

## History and reuse

`history --root <repo> --limit 10` reads a bounded set of recent run summaries
(maximum 20). It does not create a run, change a baseline, restore archives or
write a cache. Valid completed raw runs provide historical candidate findings
and exact artifact references/hashes. Output truncation is explicit; open the
referenced verified receipt only when more detail is needed.

Compaction retains raw files until explicit pruning, so those runs remain
readable. A known final receipt whose raw run has been pruned is reported as
unavailable for evidence reuse; this command does not extract its archive.
Corrupt or incomplete runs are not treated as valid evidence. Retention and a
bounded result set mean history is not an exhaustive index of all past work.

History guides model judgment; it never automatically skips a new scan or
authorizes a change. Match the prior finding to the current scope and symptom,
not just its label. Revisit a finding for changed relevant code, refreshed
external signal or a concrete new observation. Record the reason in existing
`scan.sources_checked`, `scan.no_candidate_reason` or `candidate.benefit.why_now`.
An unresolved issue-ready finding may proceed into an authorized full repair
after confirming it still applies; reuse its investigation instead of
suppressing the repair merely because the evidence was seen before.
Neither a matching repository digest nor an old passing test proves current
external state, current acceptance or continued authorization.

Reuse the candidate's reproduction, evidence references, acceptance, scope and
benefit in the existing Task Delivery plan. Carry prior receipt paths/hashes as
historical sources; Task Delivery creates its own current plan and baseline.
Do not reuse an old completion receipt for a new repair or launch a second
discovery agent merely because control moves between the two skills.
