# Harness, tools and runtime

Trace one input through context assembly, model calls, tool execution, persistence
and delivery to the user. For an existing agent, inspect that path before adding
prompt layers. Treat model behavior, harness defects, environment failures and
grader errors as different hypotheses until evidence distinguishes them.

Choose tools with clear target identities, preconditions and outcomes. Use the
project's schemas and result conventions; do not replace every API response with
a new universal envelope. Return enough observation to distinguish a valid empty
result, failure, unfinished search and unknown effect. Validate arguments and
authorization outside model instructions. Apply business constraints at the
boundary that performs the action.

For effectful tools, define stable operation identity, concurrency/duplicate
behavior, the evidence for completion and reconciliation after an uncertain
response. A request ID or checkpoint alone does not make an effect exactly once.
Read-only retries and write retries need different contracts. Cancellation of
generation, rollback of an action and cancellation of a business object differ.

Keep context selective. Separate instructions, retrieved data, conversation state
and authoritative live facts. Trace hidden summarization/repair/fallback calls
and their budgets when present. Preserve required state and permissions outside
free-form compaction. Minimize overlapping tool meanings and duplicated context.

Compare alternatives only when the choice matters: direct function calls versus
a framework; one agent versus a fixed workflow or multiple agents; local storage
versus a shared durable service; lexical versus vector/hybrid retrieval. Explain
failure/recovery, cost and maintenance implications against the actual workload.
Do not infer scale requirements solely from user count.

Runtime-specific skills are optional adapters: Deep Agents/LangGraph memory,
OpenAI agent tooling, LangSmith traces/evaluation, Harbor task packaging or other
supported implementations. Confirm installed versions and official examples.
No adapter silently activates a provider, exports traces, installs dependencies
or expands permissions.

Observe task/run/turn/tool/effect linkage as relevant, with source/candidate
versions, latency, costs and public outcomes. Retain useful evidence without
secrets, unnecessary personal data or hidden model reasoning. Define an operator
and actionable failure signal; a log file alone is not a tested alert.

Methodological sources: [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
for simple composable patterns and
[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
for selecting and maintaining useful context. These are engineering guidance,
not evidence that a chosen implementation works.
