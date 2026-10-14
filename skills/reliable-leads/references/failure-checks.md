# Select observable adverse checks

These are criteria to choose from, not proof any project already passes. Use
existing native fixtures and quality requirements, not a new universal test
runner. Required checks stay unknown/not_run without permitted evidence.

| Failure | Expected observable outcome |
| --- | --- |
| Invalid field/consent | Accessible correction, retained current input, no accepted goal/effects; server validates independently |
| False abuse rejection | Test real formats, autofill, keyboard, shared IP/CAPTCHA outage; visible recovery and safe counters, no fake success |
| Concurrent same operation | One intake/intent per required sink and same receipt under key scope/window |
| Same key changed payload | Explicit conflict; no overwrite/new job or silent key regeneration |
| Lost ACK after commit | UI unknown; unchanged same-key replay finds original receipt |
| HTML200/malformed receipt | No accepted/goal; recoverable unknown |
| DB down/full/lock timeout | No ACK without proven commit, no half intake/intent; safe error/unknown and independent signal |
| Storage denied/reload/close | Usable known degradation; no guaranteed unsent recovery. After commit delivery is browser-independent |
| Kill commit→enqueue/claim/send/mark | Persisted work discovered; expired leases classified, ambiguous external effects not blindly repeated |
| Provider outage/429/auth/5xx | Correct operation-specific class, bounded delay/budget, observable backlog/manual route |
| Side effect done, response lost | Reconciliation/dedup where supported; explicit review/duplicate policy elsewhere |
| Budget exhausted | Lead/job retained; owner/alert/manual replay with stable identity |
| Manager edits projection | Retry/reconciliation preserves status/comment and other manual fields |
| Managed quota/spam/retention | Manager access/export/reprocess and expiry are checked, not only provider storage |
| Deploy/schema change | Existing accepted jobs remain drainable; precise version/config identity |
| Backup/restore | Consistent intake/consent/key/intents, measured RPO/RTO; reconcile previously delivered effects |
| Tracker blocked/error | Acceptance path independent; conversion only after valid receipt |
| Missing manager ACL/alert failure | Distinguish delivered record from usable working queue and actual processing |

Isolation: fake recipients, artificial data, separate storage/test clock, no
production credentials. Allow only necessary local intake/fake-sink network;
their POST carries synthetic fields/key and necessary delivery fields. Prevent
unrelated egress and PII/payload/keys in analytics, URLs, logs/exported captures;
sanitise saved reports. Synthetic data is not permission to build a leaking
production analytics schema. External/provider-write tests need their own scope.

Count different populations: loss of confirmed accepted records, delayed
projection/notification, explicit pre-accept rejection and unfinished submission.
Browser analytics blocked by consent/adblock is not a complete denominator.
Use fixture truth/DB audit or permitted private reconciliation for guarantees.
No finite synthetic trial proves a universal probability of losslessness.
