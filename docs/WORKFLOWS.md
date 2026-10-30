# Workflow guide

[Repository](../README.md) · [Documentation map](README.md) · [Installation](INSTALLATION.md)

This guide describes workflow ownership and the optional control layer.
Current skill instructions and project requirements govern a real task.

## Critical flows and engineering references

[Critical business flows](../skills/verification-loop/references/critical-business-flows.md)
is the shared conditional guide. Project Start identifies affected actors,
invariants and owners; Task Delivery selects the changed scenarios; verification
establishes actual outcomes; deployment retains release/recovery ownership.
Existing projects enter at the needed stage rather than repeat bootstrap.
Read only useful branches and [reference examples](../skills/verification-loop/references/reference-implementations.md).
Project documents own business rules and exact commands. A repo-local skill may
help repeated preparation/execution without becoming a second specification.
The managed engineering policy permits a better justified and verified
alternative to an example while preserving binding contracts and authority.

## Application readiness

For whole-application handoff/release readiness, Task Delivery and Factory route
the integrated candidate and existing QUALITY/evidence to
[Production Audit](../skills/production-audit/SKILL.md). Its
[conditional profiles](../skills/production-audit/references/readiness-profiles.md)
select checks during implementation, on the candidate and after release.
[Web measurements](../skills/production-audit/references/web-measurements.md)
distinguish lab/field performance, accessibility and actual public delivery.
A required-now defect blocks readiness; absent required evidence leaves it
unestablished. Deployment retains actual release authority and its native journal.
Ordinary small changes do not acquire a full application audit or new controller.

## Engineering lifecycle

| Stage | Owner | Evidence or output |
| --- | --- | --- |
| Understand and prepare the project | [Project Start](../skills/project-start/SKILL.md) | Preserved project context, domain, architecture, engineering/quality guidance and a plan |
| Resolve an evidence gap | [Research](../skills/research/SKILL.md) | Sources, findings, uncertainty and a recommendation |
| Understand an unclear product or idea | [Grill Me](../skills/grill-me/SKILL.md) through Grilling | Adaptive question rounds, settled decisions and explicit consequential unknowns |
| Implement a bounded task | [Task Delivery](../skills/task-delivery/SKILL.md) | Candidate change, applicable tests/review and handoff |
| Coordinate independent jobs | [Software Factory](../skills/software-factory/SKILL.md) | Context packets, isolated worktrees where useful and integrated verification |
| Prepare, release or resume | [Deployment](../skills/deployment/SKILL.md) | Project-native commands, exact candidate, target readback and recovery route |
| Observe real operation | [Product Care](../skills/product-care/SKILL.md) | Diagnosis, an evidence-backed next action or no change; follow-up where authorized |
| Find one useful improvement | [Continuous Improvement](../skills/continuous-improvement/SKILL.md) | One justified candidate, issue-ready result or honest no-op; implementation belongs to Task Delivery |

Project Start supports new and inherited repositories, plus focused maintenance
after delivery. Useful existing documents remain authoritative; the foundation
covers their semantic roles instead of forcing every project into one filename
layout. Task Delivery can record a maintenance obligation when project context
must be updated after implementation.

Software Factory chooses ordinary, sequential or parallel work by dependency.
Workers receive bounded context; branches and worktrees isolate Git changes.
Ports, databases, browser sessions and external effects still need their own
ownership. The integrated candidate receives combined checks and the review
required by the host policy. See [Software Factory details](SOFTWARE_FACTORY.ru.md).

Deployment uses its `workflow.yaml` as a prepare/release/resume guide. Native
project scripts, CI and release state remain the execution owners. Product Care
can return a problem to business, CRM, implementation or release without
creating a second task system or a scheduled monitor automatically.

## Business, CRM and agent ownership

- **[Business Model](../products/business-model/README.md)** extends the existing
  business-work entry with model design, delivery economics and process-to-product.
  It accepts either opportunity search or recurring client work. Russia is its
  default target when none is selected; foreign cases are references, not local
  validation. Existing research, NMT, marketing, hypothesis checking and engineering
  owners remain optional companions. A bounded technical experiment may precede
  broader validation. Delivery/use/support observations return to the same model.

- **[Business Automation](../products/business-automation/README.md)** owns the
  business context, process, selected improvement, adoption and effect. NMT
  companions cover segment, value proposition, requirements and go-to-market
  when those questions matter.
- **[CRM Business Pack](../products/crm-business-pack/README.md)** translates an
  agreed process into Bitrix24/amoCRM models, configuration and integrations.
  A process problem returns to the process owner; a custom code component goes
  through the engineering workflow and comes back to a CRM scenario check.
- **[Agent Lifecycle](../products/agent-lifecycle/README.md)** owns the agent
  contract and routes harness/tools, memory when necessary, outcome checks and
  pilot/handover. Developer skills and skills actually loaded by a shipped agent
  are different surfaces. The pack does not require every agent to use RAG,
  multiple agents, long-term memory or a particular provider.

A repository package supplies reusable guidance. Access to a CRM, model API or
other provider must already be available and authorized for the actual task.
The packs do not provision accounts or install every mentioned tool.

## Skills and graph controllers

The root agent owns planning, implementation, synthesis and final judgment.
Optional leaf helpers handle bounded work. Small Python controllers own
mechanical transitions, retry bounds, paths, receipts and digests; they never
call a model API or replace semantic work.

```text
skill-only  → direct root-agent work without a durable controller run
tracked     → durable scope/baseline, state, evidence and resumable handoff
verified    → tracked execution with exact-candidate independent verification
```

Current host review policy applies in every tier. A skill-only task can still
require independent review. A tier name alone neither grants authority nor
proves the result.

Four workflows have operational graph contracts:

| Workflow | Modes | Contract |
| --- | --- | --- |
| Project Start | `bootstrap`, `maintenance`, automatic selection | [graph.json](../skills/project-start/graph.json) |
| Research | Bounded fast/deep work; skill-only by default | [graph.json](../skills/research/graph.json) |
| Task Delivery | Tracked `plan`, `implement`, `full`; ordinary quick work stays native | [graph.json](../skills/task-delivery/graph.json) |
| Continuous Improvement | `audit` or `full`, one candidate maximum | [graph.json](../skills/continuous-improvement/graph.json) |

Admitted controllers share `work → optional verify → complete`. Deployment,
Software Factory and the product packs do not add operational graphs.
Controller health and task health are distinct: protocol trouble gets bounded
repair/degradation while preserving pending checks. It is never evidence that
the implementation passed or that an unfinished controller completed.

## Supporting capabilities

| Capability | Role |
| --- | --- |
| [Chat Coordination](../skills/chat-coordination/SKILL.md) | Conditional discovery and authorized fact exchange between independent user tasks; resource guards stay with native owners |
| [Agent Graph Builder](../skills/agent-graph-builder/SKILL.md) | Graph-specific structure on top of the system `skill-creator`; for recurring work that genuinely needs a graph |
| [Development Recovery](../skills/development-recovery/SKILL.md) | Resolve divergence among specification, plan, implementation and evidence; independent of every graph |
| [Domain Modeling](../skills/domain-modeling/SKILL.md) and [Codebase Design](../skills/codebase-design/SKILL.md) | Bundled companions for domain and architecture reasoning |
| [Grill with Docs](../skills/grill-with-docs/SKILL.md) | The same interview plus agreed terms and durable decisions in existing project documents |
| [Improve Codebase Architecture](../skills/improve-codebase-architecture/SKILL.md) | On-demand survey of actual change friction, candidate tradeoffs and a scoped handoff |
| [Website Standards](../skills/website-standards/SKILL.md) | Technical site quality, SEO, measurement and reliable leads through existing owners |
| [SEO](../skills/seo/SKILL.md) | Technical/editorial SEO, useful 404 pages, internal links and relevant local/external search presence |
| [AI Search Visibility](../skills/ai-search-visibility/SKILL.md) | Product-specific discovery, factual accuracy and citation evidence; reuse SEO without a mandatory second audit |
| [Interface Clarity](../skills/interface-clarity/SKILL.md) | Text and placement supporting the visitor's next decision, with distinct expert, human-comprehension and behavioural evidence |
| [Writing for Agents](../skills/writing-for-agents/SKILL.md), [Grilling](../skills/grilling/SKILL.md), [PR](../skills/pr/SKILL.md) and [Retro](../skills/retro/SKILL.md) | Conditional help with instructions, open decisions, change descriptions and learning |
| Large-codebase discovery policy | Bounded read-only discovery using existing roles; no separate graph |

The system `skill-creator` is needed when Graph Builder scaffolds or restructures
a skill. `setup-matt-pocock-skills` is an optional external companion.
Project Start includes an [architecture playbook](../skills/project-start/references/architecture-playbook.md)
and an engineering-standard fallback; check actual availability rather than
assuming every skill mentioned in a reference ships in this repository.

The [Matt companion guide](MATT_POCOCK_COMPANIONS_2026-10-02.md) records sources
and adaptation. Grilling uses short rounds without limiting total discovery
depth; a clear edit needs no full interview. Diagnostic feedback loops and
requirements/standards review are integrated into existing references rather
than installed as competing pipelines. See the
[development pipeline](DEVELOPMENT_PIPELINE.ru.md) for the complete ownership map.

## Model routing and independent review

[policies/model-routing.toml](../policies/model-routing.toml) is the canonical
source for role models, reasoning levels and compatible profiles. Full setup
projects it into role files and managed host guidance. The configured root
default is Sol 6.1/Max; valid manual effort remains owned by each home.

Ordinary auxiliaries and bounded reviews use Sol 6.1/Medium. Implementation
workers, synthesis and focused risk review use their configured High roles.
Complex engineering or concrete material risk needs a fresh whole-plan
acceptor and a different whole-result acceptor at Sol 6.1/High. Trivial work
stays with the root; simple engineering gets one auxiliary result review;
ordinary non-engineering reviews stay auxiliary. The host threshold overrides
blanket workflow defaults.

`deep_reviewer` is the sole Astra role, reserved for exceptionally complex
outcomes, unresolved material uncertainty or explicit deep review. Stage
switches and routine corrections reuse valid review at the same outcome scope.
Role files define behavior; actual sandbox/tool settings determine enforcement.
See [installation scopes](INSTALLATION.md) before changing routing or profiles.

## MCP, apps and external systems

The repository provides no MCP server of its own. Workflows discover available
apps/MCP when a task needs external data, current documentation or a live system,
preferring the provider that owns the data. A tracked capability receipt records
`mcp:<server>`, a checked fallback, or a local-only not-applicable reason.
An installed skill does not grant external write authority or provider access.

Claude Code has a real [plugin distribution](INSTALLATION.md#claude-code-distribution)
in this repository. It uses a separate update channel from Codex; plugin
packaging and provider parity are separate from successful project execution.

## Artifact lifecycle and history

Plans, reports, decisions, handoffs and maintained docs remain at their project
paths. Active, blocked or awaiting-implementation run state stays intact.
After safe terminal completion, the shared runtime can create a verified archive
and a permanent compact receipt:

```text
.agent-graphs/history/<graph>/<run>/FINAL.json
.agent-graphs/archives/<graph>/<run>.tar.gz
```

Inventory and compaction do not delete raw state. Pruning defaults to a dry run;
`--apply` rechecks archives/manifests, avoids symlink traversal and never deletes
canonical outputs. Successful raw state has a seven-day default retention and
its archive thirty days, configurable in `.agent-graphs/retention.json`.

Historical research and task evidence explain decisions, but are not current
contracts or today's verification. Start from [the documentation map](README.md)
and use current source plus fresh observations for a real task.
