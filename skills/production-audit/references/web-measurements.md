# Browser performance, accessibility and public delivery

Read for an audit involving pages or browser interactions. Use the existing
interface-performance/interface-design/website-standards/seo capabilities when
available and relevant. The project's accepted UI, data and accessibility
contract remains binding; this reference is not a second specification.

## Measure the representative path

Select critical pages, states and interactions, including loading/error/empty/
denied states where applicable. Record the exact candidate, browser/device,
viewport, dataset, network and cold/warm cache. Inspect rendered behavior with
permitted tools rather than infer runtime success from HTML/source keywords.
Compare equivalent workloads and conditions before/after a change.

For frontend performance, inspect the main-content load, responsiveness and
layout stability, request waterfalls, images/fonts, JS and long interactions.
Prefer actual traces and project-pinned Lighthouse/CI or equivalent tooling.
Use concrete budgets/metrics from QUALITY; a smaller bundle or one high score
does not prove faster task completion or whole-application readiness.

Google's good field CWV thresholds are LCP <=2.5 seconds, INP <=200 milliseconds
and CLS <=0.1 at the 75th percentile. They are useful reference values, not
automatically accepted release limits for every product. Distinguish field
measurements from lab navigation results. TBT can help diagnose main-thread work
but is not a measured field INP. Scripted interaction data has its stated scope.
CrUX describes real Chrome traffic over a 28-day window and may lack samples.
For a new site, use agreed reproducible pre-launch lab checks and retain the
later field-data check/trigger; absence of field data is neither good CWV nor
an automatic blocker for a stage that does not require it.

## Exercise accessibility and compatibility

Use automation such as project-pinned axe for covered rules, plus applicable
keyboard navigation/focus, labels/errors, dialogs, zoom/reflow, reduced motion
and assistive scenarios. Inspect the project's supported browsers/viewports.
An automated pass, one screenshot or Chromium-only run does not establish all
browser support or WCAG conformance. Preserve incomplete/untested areas and
use knowledgeable human/expert evaluation for conclusions that require it.

When evaluating WCAG contrast, use the actual criterion/units: the large-text
exception refers to 18pt regular or 14pt bold, not 18px/14px. Verify computed
colors and context rather than apply a source example blindly. This is a
technical reference, not a declaration of legal compliance for a jurisdiction.

## Check the delivered surface

For public pages, check relevant HTTPS/redirect/status/assets/cache, canonical,
robots/sitemap and indexable content on the named allowed subject. Private
screens do not need public indexing; robots is not authentication. Technical
eligibility does not guarantee search indexing or rankings. A source/build check
does not replace actual published-URL checks after an authorized deploy.
Read-only browsing/crawling still stays inside the target and authority.

Inspect tool result structure and completeness. Exit 0 with an error field,
missing metrics or zero audited pages proves no successful measurement. Classify
setup/tool failures separately from observed performance or accessibility defects.
Use original evidence and the existing release/task owner; do not create another
report database, install globally, use npx to fetch new code or send private pages
to an external service without the authority for that tool and data flow.

Sources: [CWV thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds),
[lab and field](https://web.dev/articles/lab-and-field-data-differences),
[W3C evaluation](https://www.w3.org/WAI/test-evaluate/),
[contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) and
[Search technical requirements](https://developers.google.com/search/docs/essentials/technical).
The source ideas were checked alongside the pinned
[web-quality skills](https://github.com/addyosmani/web-quality-skills/tree/afa8da942115f2961fdbfa80807ea0b232ff6c00).
No upstream scripts, automatic schedules or blanket rules are imported.
