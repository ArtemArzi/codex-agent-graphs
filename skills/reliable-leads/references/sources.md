# Primary sources and applicability

Reviewed 2026-10-14. Refresh provider terms/features and actual runtime versions
before selection. No vendor code, framework or retry library is bundled.

- Native forms: Netlify [submissions](https://docs.netlify.com/manage/forms/submissions/),
  [billing](https://docs.netlify.com/manage/forms/usage-and-billing/),
  [spam filters](https://docs.netlify.com/manage/forms/spam-filters/).
  Inbox/export is useful; honeypot/reCAPTCHA rejects may not appear in spam.
  Do not infer physical ACK durability, idempotency or free hosting from these docs.
- Formspree [plans](https://formspree.io/plans),
  [over-limit](https://help.formspree.io/articles/form-and-project-settings/over-limit-submissions),
  [double submissions](https://help.formspree.io/articles/troubleshooting/delay-on-submit-or-double-submissions),
  [webhooks](https://help.formspree.io/articles/plugins/webhooks).
  Snapshot: over-limit retained but access/delivery restricted until reprocess;
  retention continues. Webhook receiver must tolerate documented retries.
- [Django 5.2 transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/),
  [locking](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update),
  [PostgreSQL 18 WAL](https://www.postgresql.org/docs/18/runtime-config-wal.html),
  [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html),
  [backup API](https://www.sqlite.org/backup.html).
  Versioned documentation is not evidence of actual deployed configuration.
- AWS [idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/),
  [timeouts/retries/jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/),
  [Brandur staged job drain](https://www.brandur.org/job-drain): existing patterns
  and failure experience, not guarantees for local implementations. No snippets copied.
- [Telegram](https://core.telegram.org/bots/api#sendmessage),
  [retry parameters](https://core.telegram.org/bots/api#responseparameters),
  [OWASP browser storage](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html).
- Optional [Tenacity 9.2.0](https://github.com/jd/tenacity/releases/tag/9.2.0),
  commit a2af454, [Apache-2.0](https://github.com/jd/tenacity/blob/9.2.0/LICENSE):
  in-process bounded retry only; check compatibility/licence before adding.

No author attribution is used to justify this protocol. The remembered
“Красильщиков” source and claimed DB-on-error technique were not identified.
A nearby Krasinsky ASR episode about forms/early phone capture is not proof of
that attribution or a recommendation to collect unsubmitted contacts.
