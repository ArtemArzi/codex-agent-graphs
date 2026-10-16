# Define the capability

Use this attention map for the affected process, not a compulsory interview.
Reuse existing requirements and decisions. Label proposals and unknowns.

| Decision | Make it observable |
| --- | --- |
| Process and value | Who does what today; trigger, frequency, current time/cost/error and intended improvement |
| User and owner | Who requests, who approves, who owns data and who handles exceptions |
| Task boundary | Inputs, outputs, supported language/channel, exclusions and stop/handoff conditions |
| Decision boundary | Model interprets or proposes; deterministic code owns critical constraints and effects |
| Authority | Allowed reads, writes, recipients and identities; required consent; forbidden attempts |
| State | Business system of record, conversation state, durable preferences, knowledge and instructions |
| Tools | Preconditions, typed inputs, target identity, output meaning and verification source |
| Failure | No result, invalid input, denial, dependency failure, unknown outcome and bounded recovery |
| Quality | Allowed terminal states, critical failures, real-model scenarios, independent outcomes |
| Operation | Workload, latency/cost budget, observability, operator, restart and release recovery |

For each key promise, describe at least one meaningful way to observe success
and a relevant failure or boundary. Do not demand one exact wording or every
possible scenario. A documented capability is not an implemented one.

Model-held history and summaries are context, not a second independently mutable
business database. A client's preference is not permission to take an action.
Entity IDs identify targets; server-side ownership establishes authorization.

For a research agent, the result may be a sourced artifact. For a CRM agent,
it may be a correct entity and fields. For a background agent, a legitimate
no-op may be the right result. Define failure severity and handoff rather than
forcing every run to make a write.

Use profiles only for relevant differences: RAG/source grounding; sales/CRM
identity and agreements; booking/resources and confirmation; support/policy and
handoff; research/source coverage; developer/artifact behavior; background/admission
and budgets; multi-agent/ownership and joins. Ordinary UI/database engineering
remains with its existing owner.
