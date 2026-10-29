# Existing delivery task

Status: implementation pending.

Improve normalized purchase-event processing and its regression checks using
the existing handler.py entry. A completed order grants one entitlement in the
observable grants list. The handler receives events after the external adapter
has normalized them; that adapter is outside this exercise.

Accepted requirements:

- Only an event for the order's account may change that order or create a grant.
- Repeating one event and a distinct paid event for an already-paid order must
  not grant the entitlement twice.
- A later pending event must not downgrade a confirmed order.
- Keep the existing unknown-order and forbidden responses; a duplicate may
  return status duplicate. New valid paid events still apply normally.
- No new queue, DB, provider or architecture workflow is needed for this task.

Use this plan as the state owner. Add concise actual results and meaningful
unverified portions here after implementation; do not create a second plan.
