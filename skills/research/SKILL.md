---
name: research
description: Run fast, adaptive, evidence-backed research with native Codex tools, installed skills, MCP/apps, and optional multi-agent depth. Use when the user asks to research, investigate, compare, verify current facts, survey a field, or produce a cited decision-ready answer; start with one native agent and automatically deepen only for real complexity or risk.
---

# Research

Use the graph as a small control layer around one native Codex research loop. Do not turn planning, searching, evidence capture, reconciliation, or drafting into separate graph nodes.

## Core contract

- Start with the root agent in `fast` mode unless the user explicitly requests deep work or a strong escalation signal is already present.
- Read only the installed skills relevant to the question. MCP discovery and relevant MCP use are mandatory inside `work`; Exa, Deep Research, domain skills, apps, browser search, and local files remain adaptive capabilities, not graph stages.
- Keep normal research read-only except for ignored run state and the requested report.
- Prefer primary and authoritative sources. Open sources; do not treat search snippets as evidence.
- Put citations next to material factual claims and separate source claims, inference, contradiction, and unknowns.
- Expand sources only while coverage is incomplete. Stop when enough evidence exists for an honest answer; source checkpoints and hard limits are not quotas.
- Do not ask the user to approve ordinary search, source selection, safe fallbacks, or internal delegation.

Read [routing.md](references/routing.md) for depth and capability selection. Read [source-policy.md](references/source-policy.md) and [control-artifact.md](references/control-artifact.md) before writing `research.json`. Read [roles.md](references/roles.md) only when delegation or independent verification is justified.

## Start or resume

```bash
python3 scripts/research_graph.py init --question "<question>" --workspace "<workspace>" --output "<report.md>"
python3 scripts/research_graph.py ready --run "<run-directory>"
```

Use `--depth deep` only when the user explicitly asks for deep, exhaustive, due-diligence, or independent work. Otherwise keep the default `--depth auto` and let evidence trigger escalation.

The runner stores ignored, resumable state under `<workspace>/.agent-graphs/research-runs/`. `ready` returns the current durable node and the applicable source, scout, and soft-time bounds.

## Execute `work`

Perform the complete research task natively inside one root turn:

1. Understand the decision and freshness need without creating a separate intake artifact.
2. Inspect exposed `mcp__*` tools/resources and make one relevant MCP call before a general native-web path. Prefer a provider-specific MCP, Context7 for official library documentation, a research MCP such as Exa/Tavily/Firecrawl, or the service MCP that owns the requested data. Do not substitute `curl` while a suitable MCP is available.
3. Search and open an initial evidence set, then test coverage before crossing each source checkpoint in `ready`. Continue only for an unanswered sub-question, weak material claim, unresolved contradiction, missing source class, or meaningful new evidence in the latest batch. If every relevant MCP is unavailable or fails, continue automatically through native web/browser and finally `curl`, and record the reason.
4. Compare evidence and write the final report directly to the requested output path. Stop early when the latest batch is redundant and remaining gaps are unlikely to change the answer.
5. Write one small `research.json` containing mode, reason, used capabilities, optional agents, cited sources, confidence, gaps, and verification decision.
6. Record one durable work receipt.

For a normal answer:

```bash
python3 scripts/research_graph.py record --run "<run-directory>" --node work --artifact "<research.json>" --outcome succeeded
```

For an answer that needs independent semantic verification:

```bash
python3 scripts/research_graph.py record --run "<run-directory>" --node work --artifact "<research.json>" --outcome verify
```

Use `failed` only when no safe source or capability path can meet the minimum evidence contract. Reopen a failed node with a concrete fallback:

```bash
python3 scripts/research_graph.py retry --run "<run-directory>" --reason "<fallback and correction>"
```

## Use capabilities natively

- Use the owning provider MCP first: OpenAI Developer Docs for OpenAI, GitHub for repository truth, Linear/Notion for their workspace data, Playwright for live browser state, and comparable service-specific servers when exposed.
- Use Context7 before general web search for version-sensitive official library or framework documentation.
- Use Exa, Tavily, Firecrawl, or another research MCP for focused discovery, code context, companies, or people.
- Use `deep-research` only after deep routing; never import a broad source target into fast mode or treat the deep 40-source emergency ceiling as a goal.
- Use official documentation skills for version-sensitive technical claims.
- Use domain skills such as market research or literature review when the question actually belongs to that domain.
- Record each successful server as `mcp:<server>` in `capabilities`. Only when no relevant MCP succeeds, record one `mcp:fallback:<reason>` and fall back automatically to native web search, browser, local files, or `curl`. A fallback receipt is not permission to skip MCP discovery.

## Use multiple agents only on evidence

Keep zero internal agents in fast mode. In deep mode, dispatch at most three `research_scout` agents for genuinely independent branches. Use the planner only when decomposition itself is unstable, and the synthesizer only for material conflicts or evidence too large for the root to reconcile cleanly.

Keep every internal agent leaf-only, read-only, bounded to one branch, and responsible for a compact evidence packet. Integrate each result once. Never create one agent per source.

## Verify conditionally

Use `research_verifier` only for the signals in [routing.md](references/routing.md). Give it the report, compact ledger, exact claims to check, and a strict instruction not to expand the research.

On rejection, repair only the listed claims and run one delta verification. The graph permits one repair by default; a second full audit is intentionally unavailable.

## Complete

```bash
python3 scripts/research_graph.py check-report --run "<run-directory>"
python3 scripts/research_graph.py complete --run "<run-directory>"
```

The deterministic gate checks receipt and report hashes, the small control artifact, source-to-report citation identity, mode/agent bounds, and conditional verifier completion. It does not inspect reasoning or repeat semantic research.
