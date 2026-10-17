---
name: agent-project-design
description: Design or adopt a customer-facing or internal AI agent from a concrete process, defining its behavior, authority, state, tools and outcome checks. Routes the agent lifecycle; ordinary software tasks or isolated prompt wording do not require the full route.
metadata:
  version: "0.1.0"
---

# Agent project design

Turn the requested process into a bounded agent capability with observable
success. This is the entrypoint for the agent lifecycle pack, not another
implementation workflow, graph or default team of agents.

Read nearest project instructions, the documentation map, relevant requirements,
current implementation and task state. Start at the requested stage. Preserve
accepted decisions and existing work. Ask only about consequential unknowns;
continue authorized independent work while an answer is pending. Use the user's
language and explain choices through the process they affect.

## Establish the agent boundary

Identify the user, process owner, trigger, present alternative and expected
result. Prefer ordinary deterministic automation when the path is known; add
model decisions for ambiguity or unstructured inputs. One narrow-tool agent is
a useful starting candidate. Multiple agents, RAG, durable workflows and long-term
memory need a task-specific reason, not a mandatory place in a diagram.

Use [agent-contract.md](references/agent-contract.md) for a new or materially
changed capability. Record the applicable decisions in existing owners; a small
task can use one compact section. Separate required behavior, implementation
proposal, observation and unknown. Do not invent policies, budgets or authority.

Use [harness-and-tools.md](references/harness-and-tools.md) when choosing the
model loop, context assembly, tools, runtime or integrations. Check current
official documentation against the selected version when implementation depends
on an API. Choose libraries only after the contract; benchmark scores alone do
not select a product stack.

## Route the affected work

| Need | Owner when available |
| --- | --- |
| Business process, buyer, alternatives, value | Existing business-work / business-hypothesis-check and project facts |
| Project foundation and implementation | Existing Project Start / Task Delivery or native project process |
| Action space and failure diagnosis | agent-harness-construction / agent-introspection-debugging |
| Persistent facts or preferences | Pack companion agent-memory-lifecycle |
| Nondeterministic evaluation | Existing eval-harness; pack agent-outcome-e2e for the integrated result |
| Working user path and external effects | Pack companion agent-outcome-e2e with native runners |
| Release and operation | Existing Deployment / production-audit / Product Care / incident owner |
| Pilot, acceptance, handover and offer | Pack companion agent-commercial-delivery |

Discover companions by their exact name in the active catalog or this pack's
single `skills/<name>` source. Read only the needed branch. Missing optional
skills do not authorize installation and do not block work that native project
owners and these references can perform. Report a missing capability when it
prevents the requested result; never fabricate execution.

Distinguish skills used by the developer from skills loaded by the shipped
agent. For a runtime skill, check its trigger, actual loading, interaction with
tool descriptions and effect on outcomes. Instructions are not enforcement of
permissions or mandatory transaction conditions.

## Close the requested stage

Deliver the concrete contract, candidate or evidence appropriate to the request,
with unresolved decisions and the next dependent step. Implementation, release,
provider delivery, human acceptance, sale, adoption and business effect are
different observations. Apply the active host review policy; no phase in this
skill creates a fresh acceptance ceremony by itself. A future follow-up note
does not register a schedule or authorize customer contact.
