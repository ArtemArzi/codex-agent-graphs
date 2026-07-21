# Research control artifact

Write one compact `research.json` in the run directory. It is a receipt for routing and evidence, not a research transcript.

Minimum form:

```json
{
  "schema_version": 2,
  "mode": "fast",
  "reason": "Why this depth is proportionate.",
  "capabilities": ["mcp:provider-or-server"],
  "agents": [],
  "sources": [
    {
      "id": "source-1",
      "kind": "web",
      "url": "https://example.com/primary-source",
      "title": "Primary source",
      "claims": ["Material claim supported by this source"]
    }
  ],
  "verification": "self",
  "confidence": "high",
  "gaps": []
}
```

Rules:

- `mode` is `fast` or `deep` and must respect the requested depth and source/agent bounds.
- `capabilities` records actual tools and includes `mcp:<server>` or a checked `mcp:fallback:<reason>`.
- `agents` contains only roles actually used; fast mode keeps it empty.
- `sources` identifies each cited source and the report claims it supports. Search snippets are not sources.
- `verification` is `self` for direct completion or `independent` when the work outcome routes to `verify`.
- `confidence` is `high`, `medium` or `low`; unresolved material uncertainty belongs in `gaps`.

The runner binds this artifact and the report by SHA-256, checks source-to-report citation identity and preserves immutable node receipts. The verifier and completion gate must use the exact current report rather than a summary.
