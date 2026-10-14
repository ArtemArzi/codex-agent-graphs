# Choose a contour and define acceptance

| Contour | Suitable when | Required boundary |
| --- | --- | --- |
| Native/managed inbox | Ready platform is sufficient for the workflow | Documented provider acceptance; inbox/manager ACL, quota/spam/export/retention. Physical durability/idempotency not claimed without proof |
| Existing CRM | CRM already owns people/intake/working queue | Commit in current models/tenant services; restoreable required effects without another lifecycle authority |
| Durable intake + projections | Working destination is external and controlled retry/recovery is needed | Committed intake plus delivery intents, bounded recovery and observable manager path |

Compare these options before designing. Public pricing/docs are not contractual
SLA/RPO evidence. Read current quotas: provider retention can coexist with no
notification or usable manager access. A stricter commit-before-ACK requirement
remains unverified if a hosted provider cannot establish that boundary.

Own backend protocol, adapted to existing versioned interfaces:

- Create a random scoped submission key for one intentional operation. It is
  not phone/email; two intentional requests from one person are valid.
- Validate fields, consent/version, size and abuse limits without silently
  dropping valid users. Use market-appropriate phone rules/autofill/accessibility.
- Uniqueness plus transaction decides concurrent duplicates. Persist intake,
  consent evidence and required delivery intents together; an existing persisted
  event can be the intent if claim/recovery semantics are defined. Only return
  accepted after successful commit under the configured storage guarantee.
- Same key + same canonical payload returns the original receipt; changed
  payload conflicts without overwriting or adding effects. Retention/dedup
  window must cover supported late retries, coordinated with privacy deletion.
- Validate status and receipt schema/operation binding, not merely response.ok.
  Use expected origin/contract; proxy HTML200 or malformed success is unknown.
  Receipt exposes only necessary safe identity/status/time/version.

UI: idle → pending → accepted / rejected / retryable / unknown. Pending has a
bounded wait and recoverable controls. Explicit rejection explains correction;
unknown means no confirmed result, not “definitely not sent”. Keep input and
the same operation key for unchanged retry. After unknown, editing fields must
not silently send a second operation; reconcile previous outcome or explain the
new intention/possible earlier acceptance. Success does not promise a call or
read receipt. Analytics failure cannot reverse accepted state.

Status lookup, if needed, uses a protected opaque capability/auth and limits;
never a public phone lookup. Keep keys/receipts out of URL/analytics. Persistent
browser keys, if needed, have a minimal lifetime/cleanup and no contact fields.
Storage denial needs a tested memory-only degradation (explicit reload limit)
or a usable alternative, not an invisible disabled form. Reload/closed tab before
commit is not a completed send. Unload/beacon is not a guaranteed fallback.

Do not collect unsent contacts on blur by default. Payload remains in memory of
the open form; local/sessionStorage and IndexedDB still have XSS/shared-device
and retention consequences. Delayed automatic submission requires a separately
agreed consent/intent/expiry model. No recovery of a closed unfinished form is
promised unless that requirement and mechanism are explicitly accepted.
