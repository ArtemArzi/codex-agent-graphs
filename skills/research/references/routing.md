# Adaptive routing

## Default: fast

Use one root agent, usually 2-4 opened sources, no internal agents, and no independent verifier. Treat the fast limits in `graph.json` as ceilings and the time value as a soft stop, not a quota to consume.

The root may use any relevant installed skill or exposed tool. Capability use does not change the graph topology.

## Select capabilities

| Need | Preferred capability | Fallback |
|---|---|---|
| Current web facts or focused discovery | `exa-search` when its MCP tools are exposed | native web search or browser |
| Thorough multi-source investigation | `deep-research`, only in deep mode | scouts plus native web tools |
| Official technical documentation | `documentation-lookup`, `openai-docs`, or product-specific docs | official websites and local docs |
| Scholarly evidence | `literature-review` and original papers | academic search plus primary papers |
| Market or company decision | `market-research` plus Exa/company sources | filings, first-party data, reputable analysis |
| Repository or local-product truth | local files, tests, CLI help, MCP for the live system | report the unavailable proof path |

Inspect exact MCP/tool names at runtime. Do not fail because a preferred skill, model, or connector is absent; use the next safe path and record material use in `capabilities` or a decision-relevant absence in `gaps`.

## Escalate to deep

Switch from fast to deep for one strong signal or two weak signals.

Strong signals:

- medical, legal, financial, security, safety, or compliance consequence;
- explicit request for deep, exhaustive, due-diligence, or independent research;
- recommendation likely to cause substantial cost, time, or irreversible action;
- material contradiction among credible sources;
- unavailable primary evidence for a decision-critical claim.

Weak signals:

- two or more genuinely independent research branches;
- current comparison across several products, markets, jurisdictions, or datasets;
- a decision-relevant gap remains after the normal fast source budget;
- low confidence in a key conclusion;
- more than one material assumption is required.

Record the controlling signal briefly in `reason`. Continue using evidence already collected; do not restart the research.

## Delegate inside deep work

- Use one scout per independent branch, up to three in parallel.
- Use the planner only when the branches cannot be bounded directly by the root.
- Use the synthesizer only for material conflicts, large evidence packets, or a final report whose scope exceeds a clean root synthesis.
- Prefer parallel tool calls before spawning agents when source lookups alone are independent.

## Request independent verification

Set `verification` to `independent` and record `work` with outcome `verify` when any of these apply:

- high-stakes consequence;
- material contradiction remains or was resolved by judgment;
- key recommendation relies on indirect or low-confidence evidence;
- the user requests independent verification;
- a consequential report contains several material claims across independent branches.

Do not request independent verification merely because a report is long. A deep multi-source answer may still complete with root self-check when its primary evidence is direct, consistent, and low-risk.

## Stop

Finish with explicit residual gaps when more search is unlikely to change the decision. Never reopen work only to improve style, collect redundant sources, or exhaust a numerical budget.
