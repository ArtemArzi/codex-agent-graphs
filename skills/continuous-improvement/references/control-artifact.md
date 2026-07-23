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
- `delivered`: allowed only in `full`; candidate risk is `low`, protected domains are empty and source kind is allowlisted. A completed Task Delivery v3 run, exact handoff, tests, changed paths and one non-default-branch commit are required.

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
