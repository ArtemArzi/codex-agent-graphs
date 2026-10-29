# Critical business flows

Read when a task changes a consequential sequence, shared state, permissions,
money, an external effect, or recovery across boundaries. Read only the relevant
branches. Ordinary isolated changes with adequate checks need no flow inventory.
Project requirements and authority remain binding; examples are references.

## Choose the owning stage

- **Project Start:** identify relevant actors, state/data owners, boundaries,
  invariants, failure expectations and unknown business decisions. Put them in
  existing domain, architecture and quality owners. Maintenance covers changed
  areas; this reference adds no graph role, required filename or bootstrap gate.
- **Task Delivery:** map the affected requirement to existing or missing checks,
  their environment and done criterion. Reuse settled rules. A local change does
  not restart Project Start; missing consequential rules block only dependent work.
- **Verification:** run the selected checks on the actual candidate. Observe the
  result and absence of forbidden effects, not just a response code or mock call.
- **Release:** reuse valid evidence and perform the project-required smoke,
  compatibility and recovery checks through the existing deployment owner.
  This reference grants no live-payment, load-test or release authority.

## Select relevant processes

| Surface | Questions that change design or verification |
| --- | --- |
| Identity, roles and organizations | Who can act on which object, tenant and fields? Can another identity read or mutate it? What happens after a role/session change? |
| CRM and approval workflows | Which transitions and actors are allowed? What remains durable after rejection, concurrent editing, cancellation or restart? |
| Money, checkout and fulfilment | Who owns price, quantity, currency and rounding? Which order/version is paid? How are a payment attempt, provider outcome, delivery and refund related? |
| Imports, exports and bulk changes | Which schema and identity rules apply? What happens on duplicates, invalid rows, partial failure, retry and another tenant's data? |
| Background jobs and integrations | Where is durable intent? How is a repeat identified? What does timeout leave unknown? How are late/out-of-order results, retry and compensation handled? |
| Data/schema and release | Which existing records and callers must remain compatible? How are migration, interrupted release, restore and pending external effects reconciled? |

For an important affected flow, capture the smallest useful mapping in its
existing owner, for example:

`actor/object -> entry -> state owner -> invariant -> failure/abuse -> check/environment -> evidence or gap`

An entry might state: a manager can advance only their organization's approved
request; a duplicate command must not repeat the notification. The project's
accepted rule supplies the actual identity, transition and repeat semantics.
Do not invent rules, a new mandatory register or a complete test suite to fill it.

## Payment and purchase example

These are scenario candidates, not universal states or a provider integration.

| Scenario | Observable requirement to establish from the project |
| --- | --- |
| Account/cart/checkout/payment/delivery | Correct actor and order, agreed price/currency, confirmed outcome and permitted fulfilment |
| Foreign object or tenant | Rejection plus absence of unauthorized reads, writes and external effects |
| Changed quantity, price, discount or order version | Server-authoritative rules and agreed snapshot/repricing behavior, including a change while payment is pending |
| Duplicate request or retry after timeout | Stable business-operation identity; no unintended second charge, reservation or delivery |
| Untrusted notification | Authenticity by the actual provider contract, plus merchant, payment/order, amount, currency and relevant status validation |
| Duplicate, late or reordered events | Durable deduplication/state handling; no repeated effect or impermissible rollback |
| Provider success with lost response or failed local write | Resolve the uncertain external outcome and reconcile durable state without blindly repeating the effect |
| Last item, one-time coupon or balance under concurrency | Check and modification share the required atomic boundary; final amounts/counts and rejection effects satisfy the contract |
| Refund, cancellation or fulfilment retry | Ownership, permitted amount/quantity, state and audit trail stay correct after failure and repeat |
| Automated registration, reservation or payment attempts | Agreed business limits resist the relevant misuse while legitimate users retain a working path |

A browser success redirect does not establish payment. A new SDK-generated
idempotency key on every retry does not establish one business operation.
Provider signatures, status queries and sender checks differ; use current
documentation for the selected provider rather than a foreign sample's header.
A local DB transaction does not undo an already completed external charge.

Identify the harmful business behavior before choosing anti-abuse controls.
API-valid automation can still consume stock, reservations, quotas or bonuses.
Test the actual flow and an allowed client, not only one IP threshold or CAPTCHA.
Keep card testing, stress and fault experiments in a suitable authorized test
environment. This reference supplies no account, provider or production access.

## Pick evidence with an honest boundary

- Domain/component checks: allowed and rejected transitions, calculations,
  object ownership and repeat semantics through relevant public interfaces.
- Real adapter/DB checks: actual query/serialization, constraints, transaction
  isolation, restart and concurrency on the target engine/version when material.
  A stand-in proves only its own behavior. Preserve applicable real-path checks.
- Provider sandbox/contract checks: the real adapter and actual provider's test
  states. A fixture returning `paid` proves neither a charge nor callback security.
- E2E: a real application entry and observable user/backend result. Controlled
  simulated notifications and provider-sandbox events must be labelled separately.
- UAT: the process owner accepts business behavior and exceptions; an automated
  browser path can support this decision, but does not itself record acceptance.
- Release/recovery: project-owned compatibility, migration, smoke and restore
  checks. Tests, deployment, provider effects and human acceptance remain separate.

For asynchronous results use a bounded wait for the relevant observable state.
For a race establish the intended interleaving on independent sessions/connections;
a fixed sleep or two promises alone may not exercise the conflicting operations.
For a stale-response or delayed-error test, establish that the relevant request
started and its delayed result actually arrived before asserting that the result
was rejected. An early assertion can pass before the adverse event occurs.
A skipped DB test is not evidence that the corresponding DB property holds.
Assertions must run on a fixture that reaches the intended branch.

Use [legacy-and-invariants.md](legacy-and-invariants.md) for independent
properties, shrinking/replay and discriminating mutation checks. Consult only
the useful entries in [reference-implementations.md](reference-implementations.md)
when an implementation example would resolve a concrete design or test question.

## Shared guidance and repository-local skills

Keep reusable questions and evidence limits here. The project owns its actors,
tenant/data boundaries, states, units/rounding, provider, reserve/expiry/refund
rules, operation keys, native commands and release/recovery policy.
Place those facts in existing canonical documents and link them from the plan.

Create a repository-local skill only when repeated preparation/execution benefits
from it. It may explain fixtures, target DB/sandbox setup, replay, commands and
how to inspect evidence, while linking the owning requirements. It must not
duplicate business truth, start a second controller, add unconditional tooling
or imply permission for live effects. With a missing companion, use the known
project contract and report the exact unverified portion rather than install it.
