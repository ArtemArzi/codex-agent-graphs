# Minimal control receipt

The model owns research reasoning. The runner records only enough information to
resume, bound optional discovery fan-out, and prove which report and sources
completed. An inherited user-level policy may require independent plan/result
acceptance even when no durable runner state is created.

## `research.json`

For a tracked run, write this small artifact after the report and required
native reviews are complete. Skill-only work does not create it:

```json
{
  "schema_version": 2,
  "mode": "fast",
  "reason": "default narrow research",
  "capabilities": ["exa-search", "mcp:exa"],
  "agents": [],
  "sources": [
    "https://example.com/first-party-source"
  ],
  "verification": "self",
  "confidence": "high",
  "gaps": []
}
```

Use only these required fields. Allowed modes are `fast` and `deep`; verification
is `self` or `independent`; confidence is `high`, `medium`, or `low`. This field
describes controller routing: fast mode uses `self`/outcome `succeeded` after
native policy acceptance, with that acceptance recorded separately. Only the
deep controller verifier route uses `independent`/outcome `verify`.

- `reason`: one short explanation for the chosen depth.
- `capabilities`: installed skills, MCP/apps, native tools, or local-source
  paths materially used. Include exactly one MCP status:
  `mcp:<server>` after relevant use, `mcp:fallback:<reason>` after a relevant
  path fails, or `mcp:not-applicable:<reason>` for local-only evidence.
- `agents`: only supported discovery roles used in deep mode
  (`research_planner`, `research_scout`, `research_synthesizer`); always `[]` in
  fast mode. Plan/result acceptors never belong in this controller field.
- `sources`: only sources actually cited in the report. Use HTTP(S) URLs or absolute readable local-file paths.
- `gaps`: only decision-relevant unknowns, not generic caveats.

Do not create a separate plan, capability inventory, claim ledger, collection artifact, reconciliation artifact, or draft receipt.
Keep required native acceptance identities and receipts in the existing report,
handoff or root task record; follow [control-artifact.md](control-artifact.md)
for the separate meaning of controller `agents` and `verification` fields.

## Source behavior

- Prefer primary and authoritative sources.
- Open web sources; snippets are discovery only.
- Use one direct primary source for a narrow authoritative fact when another source adds no value.
- Cross-check comparisons, contested facts, indirect evidence, and consequential recommendations.
- Put citations next to material factual claims and distinguish fact, attribution, inference, contradiction, and unknowns in the report itself.
- Treat source counts as adaptive bounds, not quality scores. Prefer a smaller set of direct, diverse evidence over redundant coverage.
- At each checkpoint, stop when all material sub-questions are covered and the latest batch adds little decision-relevant evidence. Continue only for a concrete coverage gap, and expose any gap that remains at the hard ceiling.

## Report

Write the answer directly to the requested output. Give the direct conclusion first, cite material facts, and state confidence or gaps only when they matter. Do not force a long methodology section onto a simple question.

## `verification.json`

Only for an existing deep controller verify node, the reviewer returns this
payload and the root writes it. Native policy acceptance outside that node
returns a verdict, unique receipt, checked claims and evidence references,
residual risks and repairs; it does not require `verification.json`:

```json
{
  "verdict": "pass",
  "report_sha256": "<sha256 of the exact report checked>",
  "checked_claims": 3,
  "residual_risks": []
}
```

Use verdict `reject` with a non-empty `repair_list` when repair is required. Check the complete assigned report against the request and sources, including material omissions and the depth reason. Do not broaden the research.
