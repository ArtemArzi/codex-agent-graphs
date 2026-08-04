---
name: research
description: Run fast, adaptive, evidence-backed research with native Codex tools, installed skills, MCP/apps, optional durable tracking, and bounded multi-agent depth. Use when the user asks to research, investigate, compare, verify current facts, survey a field, or produce a cited decision-ready answer; use a skill-only root loop by default and admit the graph only for deep, resumable, persistent, or independently verified work.
---

# Research

Host invocation: `$research` in Codex, `/cag:research` in Claude Code.

Use one native Codex research loop. Add the graph only when durable state or
independent verification closes a real need. Do not turn planning, searching,
evidence capture, reconciliation, or drafting into separate graph nodes.

## Plain-language user updates

Write every progress and final message in the user's language and in plain
words. First say what was found or what is blocked, then what it means for the
question or decision, and finally what happens next. Do not expose the research
controller's internal log as the explanation.

Required order: result → impact → next step.

Use terms such as `controller`, `root`, `scout`, `receipt`, `digest`,
`checkpoint`, `gate`, `verification` and `recovery` only when the exact internal
name helps the user act or verify something; explain it on first use. Put hashes,
artifact names and protocol details in an optional `Technical details:` block
after the plain explanation. Keep ordinary progress to one short paragraph.

## Choose the execution tier

- `skill-only` — default for a normal question that fits one session. Search,
  open sources, synthesize and answer directly. Do not initialize the
  controller and do not create `research.json` or a run directory.
- `tracked` — use the controller when the work may cross sessions, must produce
  a persistent report, needs a durable source ledger/handoff, or the user
  explicitly asks to track or resume it.
- `verified` — tracked research plus `research_verifier` when material claims
  are high-risk, contradictory, weakly supported, due-diligence grade, or the
  user explicitly requests independent verification.

## Core contract

- Start with one root agent and a bounded initial evidence set. `fast` and
  `deep` are controller depths only after `tracked` or `verified` is admitted.
- Read only the installed skills relevant to the question. Discover MCP when
  the question needs current external evidence, provider data, library
  documentation or a live system. Local-file analysis can record
  `mcp:not-applicable:<reason>` in tracked mode without a ritual lookup.
- Keep normal research read-only except for ignored run state and the requested report.
- Prefer primary and authoritative sources. Open sources; do not treat search snippets as evidence.
- Put citations next to material factual claims and separate source claims, inference, contradiction, and unknowns.
- Expand sources only while coverage is incomplete. Stop when enough evidence exists for an honest answer; source checkpoints and hard limits are not quotas.
- Do not ask the user to approve ordinary search, source selection, safe fallbacks, or internal delegation.

Read [routing.md](references/routing.md) for depth and capability selection. Read [source-policy.md](references/source-policy.md) and [control-artifact.md](references/control-artifact.md) before writing `research.json`. Read [roles.md](references/roles.md) only when delegation or independent verification is justified.

## Run skill-only research

Understand the decision, use applicable sources and capabilities, stop when
coverage is sufficient, and answer with citations next to material claims.
Keep no graph artifacts. Escalate to `tracked` before context loss or when a
durable report becomes part of the requested outcome.

## Start or resume tracked research

```bash
python3 scripts/research_graph.py init --question "<question>" --workspace "<workspace>" --output "<report.md>"
python3 scripts/research_graph.py ready --run "<run-directory>"
```

Use `--depth deep` only when the user explicitly asks for deep, exhaustive,
due-diligence, or independent work. Otherwise keep `--depth auto`.

The runner stores ignored, resumable state under `<workspace>/.agent-graphs/research-runs/`. `ready` returns the current durable node and the applicable source, scout, and soft-time bounds.

## Execute `work`

Perform the complete research task natively inside one root turn:

1. Understand the decision and freshness need without creating a separate intake artifact.
2. When external, provider, library or live context matters, inspect exposed
   `mcp__*` tools/resources and make one relevant MCP call before a general
   native-web path. For local-only evidence, skip discovery and record
   `mcp:not-applicable:<reason>`.
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
- In tracked runs record exactly one MCP status: `mcp:<server>` after relevant
  use, `mcp:fallback:<reason>` after a relevant server fails, or
  `mcp:not-applicable:<reason>` for local-only evidence.

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

After successful completion, preserve the requested report at its canonical
output path and compact only the terminal run through
`<HARNESS_HOME>/agent-graph-runtime/artifact_lifecycle.py compact --root
<workspace> --run <run-directory>` (harness home: `~/.codex` under Codex,
`${CLAUDE_PLUGIN_ROOT}` under the Claude Code plugin). Never compact a
running or blocked run.
Artifact pruning remains a separate dry-run-first command and is not a graph
node or hook.
