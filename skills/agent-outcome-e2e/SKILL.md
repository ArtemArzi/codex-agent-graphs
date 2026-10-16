---
name: agent-outcome-e2e
description: Verify an integrated agent task through its real input channel, model, tools, durable state and observable result, including policy constraints and failure recovery. Use for agent end-to-end readiness or effect verification; reuse existing eval and browser/API runners.
metadata:
  version: "0.1.0"
---

# Agent outcome E2E

Establish what the agent actually did for the user. A plausible final answer,
successful tool call, passing unit suite or second agent's approval alone cannot
establish the whole task. This skill selects and audits integrated evidence;
it is not a new runner, release controller or generic eval framework.

## Bind the scenario

Read relevant requirements, quality rules, active candidate and existing tests.
Use [case-contract.md](references/case-contract.md) to define the initial state,
supported alternatives, required outcome, critical constraints, independent
evidence, environment and budget. Reuse the project's eval owner and approved
criteria. Resolve material ambiguity before dependent scoring; do not change
expected behavior to make the candidate pass.

Map the actual path: input event/channel → model and harness → tools → state
and effect → user-visible result. An agent producing a document or choosing a
legitimate no-op has an outcome too; a CRM write is not mandatory for all agents.

## Choose and run the necessary layers

Use existing native unit/integration, eval-harness, e2e/API/browser or provider
test capabilities as appropriate. Missing optional runners do not authorize
installation. Preserve the project's established browser mode and release owner.

Distinguish scripted decisions and replay from a real model independently choosing
actions. Freeze relevant model/provider/settings, harness, tools, corpus, fixtures
and clock; record any difference from the release target. Isolate independent
trials without resetting state midway through a conversation that tests continuity.
Readiness/setup failures remain visible and cannot silently become agent failures
or excluded successes.

Use [effects-and-faults.md](references/effects-and-faults.md) for identities,
authorization, duplicates, concurrency, cancellation, restart and uncertain
effects. Introduce faults only in an authorized controlled environment. Record
that each injected fault actually reached the tested path. A nontriggered fault
does not prove recovery.

## Inspect outcome and constrained trajectory

Verify the exact target, durable fields/artifact, required delivery and absence of
unintended effects through independent readback. Check necessary consent, ownership
and ordering constraints, including prohibited attempts where the contract covers
them. Do not prescribe one complete sequence of harmless reads when alternatives
are valid. Check the full user-visible result, including intermediate publications
when the channel emits several messages.

Use deterministic checks for exact properties. Use a calibrated model/human rubric
for meaning or usefulness that those checks cannot establish. Test the verifier
with a valid result, a valid alternative, a realistic defect and missing/corrupt
evidence as applicable. A critical violation is not offset by tone or average
success. Keep hidden truth and verifier access outside the evaluated agent's reach.

## Report bounded conclusions

Use [results-and-sources.md](references/results-and-sources.md) for aggregation
and classification. Preserve raw observations with the exact configuration,
criterion decisions and relevant effect evidence; redact secrets, unnecessary
personal data and hidden reasoning. Report PASS, FAIL, INCONCLUSIVE, INVALID or
NOT RUN as supported. Show infrastructure/verifier exclusions and denominators.

Separate local adapter, provider sandbox, live delivery, human acceptance and
business effect. Required missing evidence prevents an overall PASS. Explain
what remains unverified and the next authorized check. Apply host review policy
to the complete outcome, not a new reviewer for every trace or phase.
