# Research control artifact

For a tracked run, write one compact `research.json` in the run directory. It is a receipt for controller routing and evidence, not a research transcript. Skill-only work does not create this artifact.

Minimum form:

```json
{
  "schema_version": 2,
  "mode": "fast",
  "reason": "Why this depth is proportionate.",
  "capabilities": ["mcp:not-applicable:local-evidence-only"],
  "agents": [],
  "sources": [
    "https://example.com/primary-source"
  ],
  "verification": "self",
  "confidence": "high",
  "gaps": []
}
```

Rules:

- `mode` is `fast` or `deep` and must respect the requested depth and source/agent bounds.
- `capabilities` records actual tools and exactly one MCP status:
  `mcp:<server>`, `mcp:fallback:<reason>`, or
  `mcp:not-applicable:<reason>`.
- `agents` contains only the supported internal discovery roles actually used:
  `research_planner`, `research_scout`, and `research_synthesizer`, in deep mode.
  Fast mode always records `[]`. Never put plan/result acceptors in this field.
- `sources` is an array of cited URL strings or absolute local-file paths. Put
  source titles and the claims they support in the report's citations, not
  objects in this array. Search snippets are not sources.
- `verification` describes the controller branch: use `self` with outcome
  `succeeded` in fast mode; use `independent` with outcome `verify` only in deep
  mode when using its supported verifier node. It does not record native
  host-policy acceptance performed outside that node.
- `confidence` is `high`, `medium` or `low`; unresolved material uncertainty belongs in `gaps`.

The runner binds this artifact and the report by SHA-256, checks source-to-report citation identity and preserves immutable node receipts. The verifier and completion gate must use the exact current report rather than a summary.

Required native plan/result acceptance remains mandatory in both depths. Keep
its reviewer identities, verdicts, receipts and exact reviewed scope/report
references in the existing report, handoff or root task record, outside this
controller artifact. In fast mode complete the native reviews before recording
`succeeded`; do not switch to deep only to encode those reviews. A `self` value
in this legacy controller field does not replace or waive independent acceptance.
