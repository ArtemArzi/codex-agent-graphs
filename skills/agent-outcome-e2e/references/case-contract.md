# Integrated case contract

Keep exact case truth in the existing eval/test owner, separate from runtime
instructions and reusable knowledge. Use only fields relevant to the promise.

| Field | Content |
| --- | --- |
| Requirement | User/process promise and owning specification |
| Input | Event/message, channel, actor, history and later turns |
| Environment | Initial business state, identity/permissions, knowledge/catalog versions, clock/timezone and dependencies |
| Candidate | Source/build identity, model/provider/settings, harness, tools and runtime configuration |
| Result | Allowed final state/artifact, required answer facts and legitimate alternatives |
| Constraints | Required approval/ownership/preconditions; forbidden attempts and collateral effects |
| Verifier | Independent database/API/artifact observations plus appropriate semantic rubric |
| Trials | State isolation/reset, variations versus identical repetitions, baseline, trial count and aggregation |
| Limits | Authorized environment and effect scope, cost/time limits, cancellation and stop conditions |
| Evidence | Raw public observations, source/run/effect linkage and missing-evidence behavior |

A representative case: a sales agent receives a synthetic lead, the customer
corrects the requested product, then agrees to the defined action. Observe the
right contact, current product and one intended CRM effect. Repeat delivery of
the same event, then interrupt the response after the possible write. Check
recovery using the same operation identity, absence of duplicate effects and
truthful user-visible completion. The business decides what constitutes agreement
and which CRM fields are required; do not invent those facts.

For consultation/RAG, check sufficient current sources, grounding of statements
and whether unrelated business state stayed unchanged. For a research/developer
agent, inspect the actual artifact and its observable behavior. For background
work, check admission, deduplication, no-op, budget and meaningful notification.

Replay or a scripted model proves wiring on supplied decisions. A real-model
case tests its own decisions in the chosen harness. A browser test proves only
the assertions and path it actually exercised. A provider test environment does
not automatically establish live delivery. Label these boundaries in every report.
