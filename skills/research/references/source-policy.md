# Evidence and source policy

## Evidence ledger

Store `evidence.json` as an object with an `items` array. Each item contains:

```json
{
  "claim_id": "C-001",
  "claim": "Concise factual proposition",
  "stance": "supports",
  "source_url": "https://example.com/original",
  "source_title": "Source title",
  "publisher": "Publisher or author",
  "published_at": "2026-01-10 or unknown",
  "accessed_at": "2026-07-19",
  "source_class": "primary",
  "paraphrase": "What the source establishes",
  "confidence": "high",
  "branch": "market",
  "notes": "Limits, contradiction, or inference boundary"
}
```

Allowed `stance`: `supports`, `contradicts`, `context`. Allowed `source_class`: `primary`, `authoritative-secondary`, `secondary`, `community`. Allowed confidence: `high`, `medium`, `low`.

## Source ordering

1. Original specifications, official documentation, first-party data, laws, standards, filings, and original papers.
2. Reputable analysis that links to primary evidence.
3. Independent reporting for context and cross-checking.
4. Community discussion only for discovery, operational experience, or explicitly attributed opinion.

For version-sensitive claims, record the version or date. For current facts, verify live during the run. A search-result snippet is not evidence; open the source.

## Contradictions

Do not collapse disagreements into a false average. Record both claims, compare authority, recency, directness, methodology, and independence, then state whether the conflict is resolved, provisionally resolved, or unresolved.

## Verification artifact

Store `verification.json` as an object with:

- `verdict`: `pass` for an accepted report or `reject` for a report requiring repair;
- `checked_claims`: either a positive integer count or a non-empty array of claim-level checks;
- `residual_risks`: an array, empty only when no material risk remains;
- `repair_list`: required as an array when the verdict is `reject`.

Finish the file completely before recording the `verify` node. Do not edit a recorded verifier artifact; correct it while the node is still ready, or use the graph's bounded rejection branch.

## Report contract

The report must include:

- direct answer or executive summary;
- method and scope;
- findings with claim-adjacent links;
- contradictions and how they were handled;
- implications or recommendation when requested;
- assumptions, confidence, and residual gaps.
