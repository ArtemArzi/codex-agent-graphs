# Persistent effects and recovery

Keep accepted intake, delivery projection, notification and manager visibility
separate. Telegram/email are normally notifications, not the only working ledger.
Choose required destinations and a manager role/working queue explicitly.

Own storage: use the existing DB's transaction/constraints, durable volume and
documented commit settings. Django atomic/on_commit is not proof of disk flush;
on_commit can wake a worker, but a persisted intent and independent scan close
the commit→enqueue crash window. PostgreSQL asynchronous commit and SQLite
journal/synchronous/filesystem settings change guarantees. Check actual versions;
Postgres select_for_update cannot be assumed to work on SQLite.

Keep durable pending/leased/retry_wait/delivered/needs_operator state, attempts,
next attempt, safe error class, lease ownership/expiry, payload version and
provider reference. Recovery of expired lease considers whether an external
effect may already have happened; do not blindly resend every expired job.
Finite budget exhaustion preserves lead/job with an actionable alert/owner.

One chosen retry layer coordinates SDK/proxy/worker retries. Use connect/request
timeouts, finite attempts/time, backoff+jitter and documented Retry-After/provider
hints. Values depend on measured latency and tolerated delay, including cold
connection/deploy behavior. Validation/auth failures need repair/review. A 5xx,
timeout or connection loss does not prove the side effect absent.

| Destination capability | Ambiguous outcome |
| --- | --- |
| Documented idempotency/payload semantics | Retry same operation under that bounded contract |
| Query/reconcile by immutable business ID | Verify intended record and fields before safe continuation |
| No reliable dedup/readback | Operator review or explicit policy permitting a possible duplicate; no exactly-once promise |

Validate provider business response and destination, not transport status alone.
Telegram sendMessage needs ok/result/message_id and correct route; its examined
API has no established client dedup key. After ambiguous send/lease, preserve
accepted lead and choose review/reconciliation or an authorised possible duplicate.
Sheets/CRM delivery preserves immutable identity and manual manager fields.
Search-before-append alone has a race; use serialisation/uniqueness or conflict
reconciliation as the adapter supports. Manual replay is audited with previous
business identity/payload, actor and possible earlier effect, not a new lead.

Monitor acceptance/rejection counts, age/count of pending/retry/manual work,
delivery latency, last successful scan, storage capacity and backup/restore
freshness. Safe codes/IDs only; no raw request/provider payload, contacts or keys.
An alert for Telegram/DB failure needs a channel not wholly dependent on the
failed component. Assign response ownership/thresholds; do not invent them.

Guarantee bounds: accepted work can survive configured process/deploy failures
while durable storage remains intact. Outbox does not survive loss of its only
storage by itself. Agree RPO (allowed data-loss window) and RTO (restore time),
backup outside the failure domain, monitor it and measure isolated restore.
Restore intake, consent, keys and intents consistently; old backup may forget
completed external effects or deletion state, requiring reconciliation/tombstones.
Code rollback does not restore data or reverse sent messages. Existing accepted
jobs must remain processable across schema/config changes and code rollback.

Optional retry libraries such as Tenacity help bounded in-process calls only;
they do not provide persistence, scheduling, idempotency or an outbox. Prefer
native mechanisms already present before adding dependencies.
