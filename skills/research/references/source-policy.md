# Minimal control receipt

The model owns research reasoning. The runner records only enough information to resume, bound optional fan-out, and prove which report and sources completed.

## `research.json`

Write this small artifact after the report is complete:

```json
{
  "schema_version": 2,
  "mode": "fast",
  "reason": "default narrow research",
  "capabilities": ["exa-search", "native-web"],
  "agents": [],
  "sources": [
    "https://example.com/first-party-source"
  ],
  "verification": "self",
  "confidence": "high",
  "gaps": []
}
```

Use only these required fields. Allowed modes are `fast` and `deep`; verification is `self` or `independent`; confidence is `high`, `medium`, or `low`.

- `reason`: one short explanation for the chosen depth.
- `capabilities`: installed skills, MCP/apps, native tools, or local-source paths materially used.
- `agents`: optional internal role names; keep empty in fast mode.
- `sources`: only sources actually cited in the report. Use HTTP(S) URLs or absolute readable local-file paths.
- `gaps`: only decision-relevant unknowns, not generic caveats.

Do not create a separate plan, capability inventory, claim ledger, collection artifact, reconciliation artifact, or draft receipt.

## Source behavior

- Prefer primary and authoritative sources.
- Open web sources; snippets are discovery only.
- Use one direct primary source for a narrow authoritative fact when another source adds no value.
- Cross-check comparisons, contested facts, indirect evidence, and consequential recommendations.
- Put citations next to material factual claims and distinguish fact, attribution, inference, contradiction, and unknowns in the report itself.
- Stop after enough evidence exists for an honest answer.

## Report

Write the answer directly to the requested output. Give the direct conclusion first, cite material facts, and state confidence or gaps only when they matter. Do not force a long methodology section onto a simple question.

## `verification.json`

When independent verification is required, write:

```json
{
  "verdict": "pass",
  "report_sha256": "<sha256 of the exact report checked>",
  "checked_claims": 3,
  "residual_risks": []
}
```

Use verdict `reject` with a non-empty `repair_list` when repair is required. Verify only material claims and the stated depth reason. Do not broaden the research.
