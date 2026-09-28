# Internal research roles

The root agent owns `work`. Internal roles are callable capabilities inside
research, not mandatory graph nodes. The inherited user-level routing policy is
the only authority for model and effort; this reference names roles, not model
profiles.

| Role | Dispatch role | Use when | Fallback |
|---|---|---|---|
| Planner | `research_planner` | decomposition itself is unstable | root |
| Scout | `research_scout` | an independent branch benefits from parallel search | root or parallel tool calls |
| Synthesizer | `research_synthesizer` | conflicts or evidence volume exceed a clean root synthesis | root |
| Ordinary review | `block_reviewer` | ordinary non-engineering report/plan or bounded block review | report missing independent evidence if required |
| Whole acceptor | `research_verifier` | global complex-engineering/material-risk threshold requires whole-report acceptance | never substitute self-check for required acceptance |

Use zero discovery/fan-out agents in fast mode. A required verifier or plan
acceptor is not optional discovery fan-out and never belongs in
`research.json.agents`. Native acceptance receipts remain in the report,
handoff or root task record. In deep mode, use at most three
scouts and at most one planner or synthesizer when its job cannot be performed
inside a clean root synthesis. Every internal agent remains leaf-only,
read-only, and bounded to the supplied objective and sources.

The verifier must not restart research. Give it the exact report, compact ledger,
report SHA-256, escalation reasons, and material claims/source set so it can
accept the whole artifact. On same-scope repair, reuse the same verifier for a
delta check of the repair list; materially new scope gets a fresh assignment.
