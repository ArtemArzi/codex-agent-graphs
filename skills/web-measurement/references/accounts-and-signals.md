# Identity, access and observable signals

Record safe bindings before interpreting data: site protocol/host/path,
environment, provider/account/property/stream/counter and intended owner. Compare
the actual tag/request recipient with the project binding; never guess an ID or
use access to one account as permission for another.

| Service | Identity and audit access | Changes |
| --- | --- | --- |
| GSC | Domain vs exact URL-prefix property; Restricted for reports | Full for permitted actions; Owner for access/change-of-address functions. New verification/DNS/property actions need applicable authority |
| GA4 | Account/property/web stream/measurement ID; Viewer for data | Marketer for events/key events; Editor for property/stream, Administrator for access; check current provider role contract |
| Webmaster | Exact site/main address and verified owner; Просмотр | Редактирование for configuration; Владелец controls access |
| Metrika | Counter/site/environment, settings/goals; Просмотр | Аналитика can create goals; Редактирование changes settings/existing goals. Representative access is broader |

Access descriptions are a 2026-10-14 source snapshot. Refresh for the actual
operation; possession of a credential is neither scope nor user authority.

Evidence ladder, using the existing report:

1. **Installed:** expected code/ID is present in the exact artifact.
2. **Sent:** actual request to the expected recipient observed; sanitised payload.
3. **Account observed:** the event appears in the correct account/debug view.
4. **Report observed:** the event appears in the intended report with period,
   timezone, filters and processing delay stated.
5. **Operationally reconciled:** evidence relates to the authoritative accepted
   records/booking system, within permitted private or aggregate analysis.

Stages are not interchangeable. Missing access/delayed data means unverified,
not broken and not successful. Debug/test traffic can be filtered from reports;
do not force production events merely to make a dashboard non-empty. No report
count alone demonstrates causality or business effect.

GSC live URL inspection and the indexed version are different observations.
Webmaster/GSC availability does not establish indexing; submitted sitemap does
not guarantee crawling. Use the selected search provider's real URL result when
needed, separately from public HTTP/HTML checks owned by seo.
