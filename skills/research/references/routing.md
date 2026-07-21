# Adaptive routing

## Default: fast

Use one root agent, usually 4-6 opened sources, no internal agents, and no independent verifier. Expand toward 10 only when the coverage check below finds a concrete gap. Treat every source checkpoint as a decision point, the maximum as a hard ceiling, and the time value as a soft stop; none is a quota to consume.

The root may use any relevant installed skill or exposed tool. Capability use does not change the graph topology.

## Select capabilities

| Need | Preferred capability | Fallback |
|---|---|---|
| Current web facts or focused discovery | Exa, Tavily, or Firecrawl MCP | native web search or browser |
| Thorough multi-source investigation | `deep-research`, only in deep mode | scouts plus native web tools |
| Official technical documentation | provider-specific MCP, then Context7 | official websites, local docs, native web, then `curl` |
| Scholarly evidence | `literature-review` and original papers | academic search plus primary papers |
| Market or company decision | `market-research` plus Exa/company sources | filings, first-party data, reputable analysis |
| Repository or local-product truth | local files, tests, CLI help, MCP for the live system | report the unavailable proof path |

Inspect exact MCP/tool names at runtime and call the best relevant server before a native external path. Record success as `mcp:<server>`. If no relevant server succeeds, record `mcp:fallback:<reason>` and use the next safe path; do not fail the research merely because a preferred server is absent. Never use fallback as a reason to ignore an exposed relevant MCP.

## Expand by coverage, not count

Keep source expansion inside the native `work` loop; do not add graph nodes or intermediate artifacts.

- In fast mode, inspect coverage after roughly 4, 6, and at most 10 cited sources.
- In deep mode, inspect coverage around 10 and 20 sources. Continue beyond 20 only for a genuinely broad or high-stakes topic; 40 is an emergency hard ceiling.
- Stop at any checkpoint when all material sub-questions are answered, key claims have appropriate primary or independent support, contradictions are resolved or exposed, source classes are sufficiently diverse, and the latest batch adds little decision-relevant evidence.
- Continue only for an unanswered material sub-question, weak or indirect key evidence, unresolved contradiction, missing stakeholder/source class, low confidence that affects the conclusion, or a latest batch that still changes the answer materially.
- When the hard ceiling or soft time bound arrives first, finish with explicit residual gaps. Narrowing the claim is preferable to collecting redundant sources.

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
- a decision-relevant gap remains after the adaptive fast path has used the evidence needed up to its 10-source ceiling;
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

Finish with explicit residual gaps when more search is unlikely to change the decision. Never reopen work only to improve style, collect redundant sources, or exhaust a checkpoint or maximum.
