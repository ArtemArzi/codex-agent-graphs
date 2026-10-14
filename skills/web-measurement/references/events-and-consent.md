# Events, environments and consent

Map business meaning before tagging: CTA click, form start, validation failure,
accepted intake, delivered projection, booking started/confirmed and sale are
different facts. Keep existing event names if sound; adapters should not create
another taxonomy merely to use this skill.

Successful lead conversion follows a validated acceptance receipt from the
chosen intake contract, never a click, DOM submit, generic response.ok or an
email/Telegram send. For provider inbox, do not label undocumented durability
as established. Existing reliable-leads/project owner defines acceptance.
No PII/lead IDs/submission keys in analytics. Use aggregate/private reconciliation
instead of exporting operational records into trackers.

Choose one pageview owner: native automatic tagging or manual routing. In GA4,
send_page_view:false disables config pageview, not history-based Enhanced
Measurement. Manual SPA routing must also handle that setting. Check initial
load, navigation, back/forward and reload after route/title updates; inspect
duplicate GTM/direct/native integrations. For Metrika, check SPA hit/reachGoal
ownership against the actual implementation and current documentation.

Test errors, accepted replay, timeout/unknown, repeated click, analytics blocked
and tracker exceptions. No accepted goal on rejection/unknown. At-most-once
emission in tested browser/replay cases is a bounded objective, not universal
exactly-once analytics. A browser missing due to consent/adblock is not a lost
CRM lead. Server operational counts remain authoritative for accepted records.

Separate production/test bindings. Preview must not silently pollute production
reports. Use authorised debugger/test environment; live test events are external
effects. Check chosen recipient/goal and actual account observation, not script
presence alone. Record processing delays/filters rather than repeated blind probes.

Consent policy is a project input, dependent on market and approved basis. Do
not universally add a banner or infer legal compliance. Check default/accept/
reject/change/reload as applicable; Google defaults precede measurement commands,
and Consent Mode does not store the user's choice itself. Reject/blocked tracker
states must not prevent form acceptance. Inspect recordings/autocapture too:
PII in fields, URL/title/referrer/UTM/free text must not leak through them.
Data redaction is a fallback, not permission to send personal data; hashes of
phone/email are not automatically anonymous or allowed.
