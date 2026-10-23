# Product-specific access and observations

Source review: 2026-10-23. Refresh the selected provider's linked documentation
before applying a configuration. Controls and report availability change; these
notes are not the site's observed account state or a universal robots template.

| Product | What to distinguish | Relevant check |
| --- | --- | --- |
| ChatGPT Search | `OAI-SearchBot` is for search; `GPTBot` is for possible model training; `ChatGPT-User` handles user-initiated access and does not determine Search inclusion | Check the intended search directive and genuine-request access against current published IP information. Search can be allowed while training is disallowed. A user fetch is not evidence of autonomous discovery. [OpenAI](https://developers.openai.com/api/docs/bots) |
| Google AI Overviews / AI Mode | Google Search eligibility and generative-AI participation controls; the separate Gemini app is another surface | Check search indexing/preview controls and actual Search Console generative-AI include/exclude/inherit value when accessible. Inspect inheritance at the relevant property. Do not assume a default is the current value. [Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [control](https://support.google.com/webmasters/answer/16908024) |
| Alice / Yandex | Search quality, access to AI-answer use and the exact Alice surface/mode | Apply current Yandex guidance, including `YandexAdditional` / `YandexAdditionalBot` controls where relevant; do not infer Google-equivalent robots semantics. Compare factual answers and cited pages in the chosen surface. [Quality](https://yandex.ru/support/webmaster/ru/epos), [controls](https://yandex.ru/support/webmaster/ru/adding-site/indexing-prohibition) |
| Claude with web search | `Claude-SearchBot`, `Claude-User`, and `ClaudeBot` have search, user-fetch and training roles respectively | Check the intended role, not a blanket "allow all AI" rule. A conversation without web search does not measure current web-search visibility. [Anthropic](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler) |
| Perplexity | `PerplexityBot` is for search, not foundation-model training; `Perplexity-User` handles user-initiated fetches | Check current directives/IPs and actual access. User-initiated fetching generally ignores robots.txt according to its documentation; robots is not private-data protection. [Perplexity](https://docs.perplexity.ai/docs/resources/perplexity-crawlers) |
| Microsoft / Bing AI surfaces | Bing's observed index and AI Performance data versus other products' responses | Use available AI Performance citation/pages/grounding-query reports; Topics Portfolio is a beta requiring sufficient data. Report scope and missing coverage, rather than extrapolating to every AI system. [Bing](https://blogs.bing.com/webmaster/2026/10/introducing-topics-portfolio-beta-in-ai-performance/) |

Inspect robots, meta/X-Robots directives and hosting/CDN/WAF observations in
context. Verify real crawlers using provider-supported identity checks or
verified-bot facilities, not a matching user-agent string alone. Do not disable
the site's protection wholesale or allow training as a prerequisite to citations.
Private material needs access control regardless of bot policy.

Report availability honestly. When connected read-only tools do not expose a
setting, use an authorised native view/export or leave it unverified. Do not use
browser login as evidence of a service account's rights. Do not change controls
just to complete an audit.

Google now documents a separate generative AI performance report linked from its
control help page. Use the report if available for the actual property; do not
assert that all Google AI reporting is inseparable from ordinary web reporting.
API exports, consumer UI answers and provider aggregate reports may cover
different queries, users and periods. Record that distinction before comparing.

Exa Search and Firecrawl Search find candidate URLs; their extraction tools can
read known URLs. Record response/cache dates and extraction mode when available.
They are optional diagnostic paths, not mandatory paid dependencies or proof of
native consumer-product visibility. A failure or exhausted quota leaves that
path untested; use an available equivalent without concealing the substitution.
