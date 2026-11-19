# Adaptive routing

## Default execution: skill-only

Use one root agent without controller state for a normal one-session answer;
required policy acceptors and separately useful bounded branches may still run
inside `work`.
The source checkpoints below are proportionality guidance, not a requirement to
create a tracked run. Admit the controller only for resumability, a persistent
report/source ledger, durable handoff or explicit tracking. An inherited policy
may still require independent plan/result acceptors on the skill-only route;
those are operations inside `work`, not a reason to create controller state.

## Tracked depth default: fast

Use one root agent, usually 4-6 opened sources, no discovery fan-out agents,
and no independent verifier without the inherited policy or a concrete signal.
When the host policy calls for review, complete it outside the fast controller
and keep the evidence in the report, handoff or root task record. An ordinary
report review uses `block_reviewer`. Only complex engineering or material risk
requires independent acceptance of both plan and result. The fast receipt uses
`research.json.agents=[]`, `verification="self"` and outcome `succeeded`.
Expand toward 10 only when coverage finds a gap.
Treat every source checkpoint as a decision point, the maximum as a hard ceiling,
and the time value as a soft stop; none is a quota to consume.

The root may use any relevant installed skill or exposed tool. Capability use does not change the graph topology.

## Select capabilities

| Need | Preferred capability | Fallback |
|---|---|---|
| Current web facts or focused discovery | Tavily or Firecrawl Search for domain and freshness filters, Exa for semantic discovery | native web search |
| Public page with a known URL | Firecrawl Local scrape | existing extraction MCP or hidden Playwright for a public interactive page |
| Known section of a site | Firecrawl Local map for candidate URLs, then scrape selected URLs or bound a crawl by path and page count | sitemap or internal links, then a supported extractor |
| Thorough multi-source investigation | `deep-research`, only in deep mode | scouts plus native web tools |
| Official technical documentation | provider-specific MCP, then Context7 | official websites, local docs, native web, then `curl` |
| Scholarly evidence | `literature-review` and original papers | academic search plus primary papers |
| Market or company decision | `market-research` plus Exa/company sources | filings, first-party data, reputable analysis |
| Repository or local-product truth | local files, tests, CLI help, MCP for the live system | report the unavailable proof path |

When the question needs external, provider, library or live context, inspect
exact MCP/tool names and call the best relevant server before a native external
path. Record success as `mcp:<server>`. If a relevant server fails, record
`mcp:fallback:<reason>` and continue safely. For local-file evidence record
`mcp:not-applicable:<reason>` in tracked mode without discovery.

## Collect public web sources

1. Use the owning provider for primary data where available. For open-web
   discovery on a focused question, start with one search tool chosen by
   query fit. For several independent questions use the parallel route
   below. Deduplicate and rank candidate URLs by relevance,
   authority and freshness before requesting page bodies.
2. Inspect the live tool catalog for a distinct local connection, such as
   `firecrawl_local`. Use its scrape tool for selected public URLs. For larger
   known URL lists, the Firecrawl Local v2 API supports
   `POST /v2/batch/scrape` and polling `GET /v2/batch/scrape/{id}`. Use a
   trusted, already configured local endpoint when available and authorized.
   If only per-URL MCP scrape is exposed, use bounded groups or the supported
   extractor. Map lists URLs. Use it to pick pages, or crawl a known section
   with explicit path, depth and page bounds.
3. Pilot a small representative group, then expand based on what it returns.
   Start with Markdown and request links or browser rendering when needed.
   Use bounded concurrency and increase it only while useful content arrives
   and host resources allow it. Chrome can materially raise memory usage.
   Save reusable source bodies under the existing task owner when the task
   needs them. Pass relevant excerpts and source URLs to synthesis. Existing
   evidence checkpoints and tracked citation ceilings still apply.
4. Confirm each selected result contains the needed material. Check the
   target site's status, title and body for empty output, login, bot checks
   or rate limiting. Count a page as collected only if the needed content
   is present. Use hidden Playwright for ordinary public JavaScript
   interactions when the page needs it. When a site explicitly limits
   access, record the observed limit and look for an authorized first-party
   API, export or alternate source. Follow the established manual browser
   handoff when the task calls for user login or CAPTCHA. Report the gap
   if access remains unavailable.

A Local installation can forward search to Firecrawl Cloud. A bundled
search-and-scrape request goes through the search backend in that setup.
Use separate discovery and direct local scrape calls. When page retrieval
must stay local, verify the endpoint disables cloud page fallback (for
example with `FIRECRAWL_CLOUD=search` or `off`), and check returned source
metadata when present. Local formats and fallback depend on the installed
version and configuration. Verify them against the active endpoint and the
[Firecrawl Local documentation](https://docs.firecrawl.dev/quickstarts/firecrawl-local).

## Search and collect in parallel

Use this route for an explicitly broad research request or several
independent evidence questions. Make one initial parallel search wave by
assigning each query a distinct angle and source class. Examples include
official capabilities, independent implementations or evaluations, and
reported failures. Use the owning provider for primary records. Use Tavily
or Firecrawl Search for domain and date filters, Exa for semantic discovery,
and native search where its region, recency or index covers an actual gap.
Use multiple relevant providers on the first wave when their questions are
independent. Send follow-up queries only for gaps and contradictions.

Make Firecrawl Local the main collector for eligible public URLs. Merge
search results and deduplicate by URL and equivalent document, while
preserving query parameters that change content. Start downloading vetted
URLs as they arrive. Use bounded Local batch jobs for known URL groups and
a path-limited crawl for a relevant site section. Base total and per-origin
concurrency on a representative pilot and observed responses. A batch-wide
concurrency limit alone does not set per-origin limits across jobs. Pause or
reduce requests to an origin that limits access. Use the collection route
above for failures and browser-only pages.

For a reusable or large collection, save successful page bodies with their
requested URL, resolved URL when available, retrieval time and status under
the existing task owner. Track coverage by question and retain unresolved
failures. Read in groups by question. Extract evidence and quotations with
their source locations. Confirm material or disputed claims in the original
pages. When exhaustive reading is requested, track which documents were
actually reviewed and report the unread or unavailable ones. Reuse relevant
saved documents with a freshness check.

Report conclusions with the primary or corroborating sources that support
them. A downloaded collection provides candidate material, and any source
used as evidence follows the existing citation contract and tracked limits.
Keep the existing deep-mode delegation and review rules below.

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
- explicit request for deep or exhaustive source coverage, due diligence, or a separate investigation that requires new evidence.
- recommendation likely to cause substantial cost, time, or irreversible action;
- material contradiction among credible sources;
- unavailable primary evidence for a decision-critical claim.

Weak signals:

- two or more genuinely independent research branches;
- current comparison across several products, markets, jurisdictions, or datasets;
- a decision-relevant gap remains after the adaptive fast path has used the evidence needed up to its 10-source ceiling;
- low confidence in a key conclusion;
- more than one material assumption is required.

A request to review an existing report selects a reviewer under the host policy. Escalate collection depth when the requested investigation or an evidence gap calls for it.

Record the controlling signal briefly in `reason`. Continue using evidence already collected; do not restart the research.

## Delegate inside deep work

- Use one scout per independent branch, up to three in parallel.
- Use the planner only when the branches cannot be bounded directly by the root.
- Use the synthesizer only for material conflicts, large evidence packets, or a final report whose scope exceeds a clean root synthesis.
- Prefer parallel tool calls before spawning agents when source lookups alone are independent.

## Request independent verification

Without an inherited review policy, use the deep tracked controller's
`verification="independent"` and `work` outcome `verify` for these signals:

- high-stakes consequence;
- material contradiction remains or was resolved by judgment;
- key recommendation relies on indirect or low-confidence evidence;
- the user requests independent verification;
- a consequential report contains several material claims across independent branches.

A well-supported, low-risk deep report can finish with a root check when the
host policy permits it. Under the inherited policy, ordinary report reviews use
`block_reviewer`. Use the deep verifier node when the applicable whole-report
acceptor matches the controller contract. Keep a native verdict outside the
controller when its role is unsupported, and preserve outstanding controller
obligations as described in [the skill](../SKILL.md#inherited-routing-and-acceptance-policy).

## Stop

Finish with explicit residual gaps when more search is unlikely to change the decision. Never reopen work only to improve style, collect redundant sources, or exhaust a checkpoint or maximum.
