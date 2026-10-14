# Visitor path and publication checks

Inspect actual states on representative mobile/desktop widths and keyboard;
select browsers/devices by project requirements. Use native tests, hidden browser
or available accessibility tools, not source regex alone. Automated a11y scans
do not establish full WCAG compliance.

| Surface | Observable behavior |
| --- | --- |
| Navigation/anchors | Correct destination, direct deep link and back/forward; sticky controls do not obscure target/focus |
| Contacts/CTA | Correct tel/mailto/messenger/booking target; opens the intended action, not an inert placeholder |
| Menus/dialogs | Open/close, Escape where appropriate, focus containment/return and scroll; no background interaction through modal |
| Form | Labels/autocomplete/inputmode, linked errors, first-invalid focus, pending/unknown/accepted, retained input on error; no loss when breakpoint changes |
| Mobile | Keyboard/zoom/viewport changes do not cover submit, error or essential controls; interactions work without hover |
| External widgets | Blocked script, timeout and unavailable provider give a usable action; opening a booking widget is not a booking |
| Errors | Real 404/appropriate HTTP status, safe request ID, useful recovery; no error disguised as a 200 success shell |
| HTTPS/config | Valid TLS, correct host, no mixed content or bundle secrets; necessary headers and auth/CORS/CSRF/limits follow actual architecture |
| Media/fonts | Required media loads; dimensions/fallback avoid blocking the task or severe shifts; slow-network state usable |
| Publication | Exact artifact/config is active at intended URL, fresh external readback and critical path through native release owner |

“Upper strip” does not identify a component. Inspect the visible controls and
overlay/focus behavior now; clarify actual type before deciding consent,
dismissal/persistence or notification semantics. Do not call it a cookie banner
or header without evidence, and do not redesign it to resolve ambiguity.

Keep live observations within authorised targets/redirects and account scope.
During manual login/input handoff follow the existing browser-mode owner and
stop agent actions; do not export/copy browser session state. Pageview alone may
emit real analytics: use fixture/staging suppression when the task excludes
those effects. Release verification does not automatically authorise lead sends.

References: [W3C notifications](https://www.w3.org/WAI/tutorials/forms/notifications/),
[WCAG focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).
