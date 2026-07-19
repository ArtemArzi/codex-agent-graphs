# Internal roles

These roles are implementation details of the Research graph, not user-facing skills.

| Role | Preferred profile | Job | Fallback |
|---|---|---|---|
| Planner | `research_planner` / GPT-5.6 Terra high | decomposition, evidence standard, gap analysis | `researcher` |
| Scout | `research_scout` / GPT-5.6 Terra high | branch-specific discovery and evidence capture | `researcher` |
| Synthesizer | `research_synthesizer` / GPT-5.6 Sol high | contradiction resolution and draft | root strongest model |
| Verifier | `research_verifier` / GPT-5.6 Sol max | independent claim and citation audit | `reviewer` |

Use model profiles as preferences, not as a reason to fail a run. If a named model is unavailable, choose the strongest available model suited to that role while preserving independent verification.

One narrow question should normally use one scout. Use two or three only when branches are genuinely independent and parallel work reduces elapsed time. Never create a scout per source.
