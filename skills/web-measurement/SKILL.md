---
name: web-measurement
description: "Use when connecting or verifying Google Search Console, GA4, Yandex Webmaster or Metrika, diagnosing missing or duplicate website events, or checking conversion evidence and consent."
metadata:
  version: "0.1.0"
---

# Web Measurement

Establish the named site's search/measurement identity and observed data. Search
engines and analytics are independent choices: Google does not require GA4,
Yandex does not require Metrika, and one working service proves nothing about another.

Read current project instructions, measurement/quality owner and task decisions.
Select only requested services/environments and material missing information.
For setup or authorised repair, use existing implementation/config owners;
read-only audit does not grant account, verification, goal or access changes.
Honor existing authority without asking again for already authorised work.

Read [accounts-and-signals.md](references/accounts-and-signals.md) for identity,
least-needed roles and the script/network/account/report evidence ladder. Record
the reached level separately for each service. A tag, HTTP 2xx or a test event
is not proof of report conversion, accepted lead or indexing.

Read [events-and-consent.md](references/events-and-consent.md) when preparing or
checking pageviews, conversions, environment suppression or consent. Keep one
owner for each pageview/event; receipt-confirmed acceptance is a stricter project
conversion boundary than DOM submit. Tracker failure must not downgrade an
accepted request. No personal fields, free text, receipt/key or unintended URL
parameters in analytics or exported diagnostic evidence.

Use the shared [evidence contract](../website-standards/references/evidence.md)
when reporting/reusing checks. If that companion is unavailable, use the current
project quality format and disclose the missing reference; do not install it or
invent a PASS. Keep native implementation/release/operate ownership and one
existing handoff. Request unavailable credentials through the normal human login
flow; never ask for passwords, tokens, cookies or copied browser profiles.

Finish in the user's language: exact site/environment/services, what was observed,
which level is unverified, practical consequence and next permitted check.
Separate published/crawlable/indexed/impressions/clicks/events/accepted records/
manager action/effect. Read [sources.md](references/sources.md) when guidance or
roles need refreshing; current account state cannot come from dated documentation.
