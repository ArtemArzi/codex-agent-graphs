# Optional internal roles

The root agent owns `work`. Internal roles are callable capabilities inside deep work, not mandatory graph nodes.

| Role | Preferred profile | Use only when | Fallback |
|---|---|---|---|
| Planner | `research_planner` / GPT-5.6 Terra high | decomposition itself is unstable | root |
| Scout | `research_scout` / GPT-5.6 Terra high | an independent branch benefits from parallel search | root or parallel tool calls |
| Synthesizer | `research_synthesizer` / GPT-5.6 Sol high | conflicts or evidence volume exceed a clean root synthesis | root strongest model |
| Verifier | `research_verifier` / GPT-5.6 Sol max | routing requires independent semantic verification | reviewer |

Use zero internal agents in fast mode. In deep mode, use at most three scouts and at most one planner or synthesizer when its job cannot be performed cheaply in the root. Every internal agent remains leaf-only, read-only, and bounded to the supplied objective and sources.

The verifier must not restart research. Give it the exact report, compact ledger, report SHA-256, escalation reasons, and material claims. On repair, reuse the same verifier for a delta check of the repair list.
