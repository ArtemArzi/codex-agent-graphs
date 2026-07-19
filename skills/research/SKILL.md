---
name: research
description: Run an autonomous, evidence-backed agent graph for questions that require source discovery, current external research, comparison, contradiction handling, or a cited decision-ready report. Use when the user asks to research, investigate, compare sources, verify current facts, survey a field, or produce a rigorous answer without step-by-step supervision.
---

# Research Graph

Run research as a bounded graph, not an open-ended agent loop. The root agent owns the run. Internal agents are leaf workers with non-overlapping assignments.

## Operating contract

- Do not ask the user to approve normal research steps. Make reversible assumptions, record them, and continue.
- Keep research read-only except for local run state and the requested report.
- Discover relevant skills, MCP servers, apps, web search, local files, and official documentation before planning. Inspect only capabilities likely to matter.
- Prefer primary and authoritative sources. For technical claims, use official docs or original papers. For current claims, verify freshness live.
- Separate confirmed facts, source claims, contradictions, inference, and unknowns.
- Never fabricate a citation. Put citations next to the claims they support.
- If a preferred capability is unavailable, use the next safe source path automatically. Stop only when no safe path can meet the evidence threshold.

Read [source-policy.md](references/source-policy.md) for evidence rules and [roles.md](references/roles.md) before dispatching internal agents.

## Start or resume

Use the bundled runner from this skill directory:

```bash
python3 scripts/research_graph.py init --question "<question>" --workspace "<workspace>" --output "<report.md>"
python3 scripts/research_graph.py status --run "<run-directory>"
python3 scripts/research_graph.py ready --run "<run-directory>"
```

`init` is idempotent for the same question, workspace, and output. The run lives under `<workspace>/.agent-graphs/research-runs/` and can be resumed by either CLI or Desktop without writing to the protected `.codex/` directory.

## Execute ready nodes

Always ask the runner for the ready node. Complete it, save its artifact inside the run directory, then record the receipt:

```bash
python3 scripts/research_graph.py record --run "<run-directory>" --node "<node>" --artifact "<artifact>" --outcome succeeded
```

Allowed branch outcomes:

- `gap_check`: `succeeded` or `needs-more`.
- `verify`: `succeeded` or `rejected`.
- Other nodes: `succeeded` or `failed`.

The runner bounds additional collection and synthesis repair cycles. Never bypass a transition or edit `state.json` by hand.

If a node fails because a source or capability is unavailable, choose a safe fallback and reopen it without asking the user:

```bash
python3 scripts/research_graph.py retry --run "<run-directory>" --reason "<fallback and correction>"
```

Retries are bounded by the graph contract. A verifier rejection uses its separate synthesis-repair bound and cannot be reopened through `retry`.

## Graph nodes

1. `intake`: normalize the question, scope, assumptions, audience, output, and freshness needs.
2. `capability_discovery`: inventory only relevant local sources, skills, MCP/apps, web, and official-doc paths; record fallbacks.
3. `plan`: use `research_planner` when available. Produce 1-3 non-overlapping branches, source targets, and stop conditions.
4. `collect`: dispatch up to three `research_scout` agents in parallel when useful. Use one agent for a narrow question. Do not duplicate branches.
5. `evidence`: merge findings into the evidence ledger. Deduplicate sources and preserve source-to-claim links.
6. `reconcile`: use `research_synthesizer` for material conflicts; otherwise reconcile in the root.
7. `gap_check`: test the ledger against the plan. Return `needs-more` only for a concrete decision-relevant gap.
8. `synthesize`: create the report from the ledger, preferably with `research_synthesizer` for complex work.
9. `verify`: independently audit with `research_verifier`. On `rejected`, record a repair list; the graph returns to synthesis within its bound.
10. `complete`: run the mechanical report check and deliver the report plus residual limitations.

If custom graph agents are not installed in the current session, route planner/scout work to `researcher`, synthesis to the strongest available model, and verification to `reviewer`. If multi-agent tools are unavailable, execute the same nodes serially in the root; preserve all gates.

## Agent dispatch contract

Every internal agent receives:

- exact branch objective and exclusions;
- must-read local paths or source classes;
- freshness cutoff and evidence standard;
- artifact schema from `references/source-policy.md`;
- instruction to remain leaf-only and read-only;
- explicit completion and failure criteria.

The root waits for all dispatched branches, integrates each result once, and closes completed agents when supported.

## Completion gate

Before final delivery:

```bash
python3 scripts/research_graph.py check-report --run "<run-directory>"
python3 scripts/research_graph.py complete --run "<run-directory>"
```

Completion requires a successful verifier receipt, a readable report, a non-empty evidence ledger, valid artifact hashes, claim-adjacent citations for material factual claims, and explicit residual gaps. A low-confidence but honest result may complete; an unsupported confident result may not.
