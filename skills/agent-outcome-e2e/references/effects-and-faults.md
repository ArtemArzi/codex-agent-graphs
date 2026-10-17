# Effects, retries and faults

Choose relevant cases across the affected path. Normal happy paths, requirement
boundaries and observed incidents all contribute; there is no universal quota.

| Condition | Independent observation |
| --- | --- |
| Ordinary success or valid no-op | Correct target/result; truthful answer; only permitted effects |
| Ambiguous or corrected request | Clarification or updated affected fields; unrelated conditions preserved |
| Denied/foreign/stale action | No unauthorized effect or data disclosure; attempted violation classified |
| Duplicate/out-of-order input | Product-defined identity/order behavior, without unintended repeated effects |
| Concurrent operations | Correct transaction/locking/conflict behavior through real test persistence |
| Timeout before send | Evidence of no send, or uncertainty explicitly retained |
| Response lost after possible write | Stable operation lookup/readback; no new-key retry that can duplicate the effect |
| Crash after effect before checkpoint | Durable state reconciled; user sees actual outcome after resume |
| Cancel before/after effect | Model cancellation and business cancellation/compensation are distinguished |
| Truncated/corrupt/schema tool or model result | Validated boundary, bounded failure/recovery and no fabricated success |
| Malicious retrieved instruction | Data remains data; forbidden action/recipient/owner change not accepted |
| Dependency failure, empty result, search limit | Failure/unfinished result not narrated as authoritative absence |
| Restart/compaction | Authoritative state and permissions recovered; no invented confirmation |
| Human handoff | Required information reaches the defined owner; handoff is not merely promised |

Before retrying an effect, distinguish known-not-executed, known-executed and
unknown. A durable pending intent and stable effect identity can support recovery;
the exact protocol belongs to the integration. Idempotency-key reuse requires
the provider's documented semantics. If no reliable lookup or safe retry exists,
retain uncertainty and escalate to the operation owner. Do not claim exactly-once
delivery from a request ID or an HTTP success code.

Model/API fault tests should record the chosen fault, injection point, trigger
evidence and resulting behavior. External-tool faults need their own fixtures and
effect readback. Never test destructive faults against production simply because
an E2E request names them. Use the user's existing scope; no blanket reapproval
of already authorized reversible checks.

Capture sufficient public messages, actual tool attempts/results and authoritative
effects. Check rejected attempts too when policy requires it: handler-only logs
may omit calls rejected by schema validation. An existing correct final record
cannot retrospectively authorize a forbidden path used to produce it.
