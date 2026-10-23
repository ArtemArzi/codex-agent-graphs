# Adaptive technical SEO

Choose Google, Yandex or both from business market/goal. Do not infer that all
sites need multiple languages, a region setting or every analytics service.

| Common check | Observable contract |
| --- | --- |
| Route inventory | Public canonical, redirect, removed, private/preview intent per URL |
| HTTP/content | Correct status and meaningful indexable content; unknown route real 404/410 rather than 200-shell soft404 |
| robots/noindex | Intended crawl access; noindex readable by robot, not hidden behind disallow. robots is not access control |
| Sitemap | Real parseable XML, absolute intended canonical URLs; no redirect/noindex errors or fabricated lastmod; sending is not indexing |
| Canonical/duplicates | Consistent target that is accessible and matches content; inspect host/slash/query variants. Canonical is a signal, not forced selection |
| Redirect/migration | Preserve URLs by default; necessary changes direct old→new, no loops/chains, links/canonical/sitemap updated |
| JS/content | Meaning/links/metadata available without click/login; compare source and rendered DOM/resources/deep links. SSR/prerender when useful, not compulsory stack |
| Language/region | Actual lang/content, only real variants; hreflang self/reciprocal/absolute links where applicable |
| Schema | Valid supported type matches visible truthful content; syntax/rich-result eligibility/actual display separate |
| Performance | Critical mobile path works; fixed-condition lab regression and real-user data separate; media/font load and layout measured |

Staging should use access control where secrecy is needed; public noindex only
for nonsecret previews. Before release check production origin/directives and
no staging restrictions. Respect existing Deployment owner and scope of effects.

| Profile | Additional evidence |
| --- | --- |
| Google | Exact GSC property; indexed vs live inspection, selected canonical; currently supported rich-result types; CWV lab/field distinction |
| Yandex | Exact Webmaster site/main address; actual business geo need and regional moderation; current JS-render setting; Clean-param only for demonstrated nonsemantic parameters |
| Both | Common URL contract plus independent observations in each service; no result transfer between search engines |

Google technical eligibility is not a guarantee. Google site-move guidance
recommends redirects for at least a year; Change of Address concerns domain/
subdomain changes, not ordinary path moves. Confirm current migration guidance
and the project's longer compatibility requirements before changing old URLs.

Yandex's specialised JS rendering beta page contradicts a categorical older
redesign statement; do not assert that Yandex never renders JS. Use current
specialised docs and test actual content. Inconsistent setting names/examples
must not be copied untested. Region is not language. Detailed Yandex hreflang/
schema support requires provider-specific refresh, not assumed Google equivalence.

Google CWV guidance at source review: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 using
field assessment; one lab run is not field evidence. Treat targets/budgets as
applicable engineering criteria, not promises of ranking or universal Yandex gates.

## Error pages and removed routes

Request a fresh nonexistent nested URL directly and inspect both the HTTP status
and visible page. A page saying "not found" with `200` is a soft-404 candidate;
a separate `/404` route does not prove the fallback works. Unknown routes normally
return `404`; deliberately removed content without a replacement may use `410`.
The error template should explain the situation in the site's language and offer
ordinary working links to home and relevant sections. Check readability, keyboard
access and narrow mobile layout when changing it. A correct error page supports
navigation and indexing hygiene, not a promised ranking boost.

For a moved page use the reviewed permanent redirect to its actual replacement.
Do not blanket-redirect missing URLs to home or fabricate a canonical replacement.
Remove broken internal links and error URLs from sitemap; retain historical URL
evidence for the migration owner. Check the deployed fallback when release is
authorised: a development-server response does not prove CDN/hosting behaviour.

## CMS changes and freshness

When CMS publication or a template is affected, check a representative draft,
publication, correction and removal through the real project mechanism. Verify
the resulting source/rendered facts, links, metadata and sitemap, including cache
invalidation where applicable. Use an isolated test surface or already authorised
test material; an audit is not permission to create public posts. Report repository,
preview and live observations separately. Keep one source for shared prices and
contacts; changing a database field alone does not prove every public copy updated.
