---
name: reliable-leads
description: "Use when building or checking website lead intake, handling duplicate or uncertain submissions, diagnosing missed notifications, or designing recovery of accepted requests across a CRM, form provider or delivery queue."
metadata:
  version: "0.1.0"
---

# Reliable Leads

Establish where a request becomes accepted and how accepted work reaches the
working system and manager. These are different boundaries; no absolute lossless
or external exactly-once promise follows from saving to a database.

Read the nearest project instructions, architecture/quality owner, actual form
and backend/provider path. Preserve the current system of record, tenant scope,
service facade and history. Do not create another lead model/database/queue
without a demonstrated gap and project decision.

## Choose the sufficient contour first

Read [acceptance-protocol.md](references/acceptance-protocol.md). Compare existing
native/managed inbox with the existing CRM/backend before choosing a mechanism:
ACK/storage proof, retry identity and payload binding, lost response, manager
access, export/retention, quota, privacy/processing location, cost and recovery.
Do not reject a ready provider just to build an outbox, or assume undocumented
provider guarantees. Unknown budget, retention, RPO/RTO remain explicit.

For an authorised implementation, use the existing task owner and native stack.
Audit scope alone allows no repairs, real leads, operator replay, fault injection
or data restore. Continue already authorised work without another approval ritual.

## Follow the complete request path

For own storage, success follows committed intake/consent and required delivery
intent. A persisted event plus reliable scanner may supply the outbox role;
on_commit alone does not. Validate accepted receipt, preserve one key for the
same operation, and handle unknown outcomes without pretending rejection.

Read [delivery-and-recovery.md](references/delivery-and-recovery.md) for leases,
bounded retries, ambiguous external effects, reconciliation and backup. Read
[failure-checks.md](references/failure-checks.md) to select adverse tests for the
actual contour. Use isolated synthetic data/fake recipients before any authorised
provider tests. Optional libraries are not persistent delivery guarantees.

Browser payload stays in the current form by default; background capture or
localStorage of contact data is not an automatic reliability feature. No PII,
submission keys, provider payload or secrets in analytics/public URLs/normal logs.

Report the proven acceptance boundary, delivery/visibility state, unknowns and
next action in the user's language. Use the shared
[evidence contract](../website-standards/references/evidence.md) and existing
quality/runbook format; missing companion reference is a disclosed gap, not an
installation trigger. [sources.md](references/sources.md) owns refresh pointers.
