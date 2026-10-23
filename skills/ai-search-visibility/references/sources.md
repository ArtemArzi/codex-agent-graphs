# Sources and adaptation decisions

Reviewed 2026-10-23. Refresh current first-party documentation when acting on a
provider rule. Sources establish guidance, not this site's actual visibility.

## Primary sources

- Google: [generative AI optimisation](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide),
  [AI Search features](https://developers.google.com/search/docs/appearance/ai-features),
  [participation control and report pointer](https://support.google.com/webmasters/answer/16908024).
- OpenAI: [crawler roles](https://developers.openai.com/api/docs/bots).
- Anthropic: [crawler roles and controls](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler).
- Yandex: [search/Alice quality](https://yandex.ru/support/webmaster/ru/epos),
  [AI-answer restrictions](https://yandex.ru/support/webmaster/ru/adding-site/indexing-prohibition).
- Perplexity: [crawlers and user fetchers](https://docs.perplexity.ai/docs/resources/perplexity-crawlers).
- Bing: [AI Performance / Topics Portfolio beta](https://blogs.bing.com/webmaster/2026/10/introducing-topics-portfolio-beta-in-ai-performance/).
- Optional diagnostic tools: [Exa search](https://exa.ai/docs/search/quickstart),
  [Exa contents](https://exa.ai/docs/reference/get-contents),
  [Firecrawl search](https://docs.firecrawl.dev/features/search),
  [Firecrawl scrape](https://docs.firecrawl.dev/features/scrape).

## External skills considered

This is an independently authored skill. External instructions/scripts were not
copied or installed; links credit design comparisons, not authority over this
skill or the user's environment. No dependency on their tools, templates or
licensing/configuration files is introduced.

- [imergea/SEOGEO entrypoint](https://github.com/imergea/SEOGEO/blob/main/SKILL.md),
  version stated 1.8.5, Git blob `084bfedf91032a96524b7ef79dcff30fb9862f90`;
  [GEO reference](https://github.com/imergea/SEOGEO/blob/main/references/ai-search-geo.md),
  Git blob `470fbc7ff0f986a242b7ea3bbb04506489461830`. Useful ideas: conditional
  topical references, evidence tied to actionable fixes, product-specific
  diagnosis. Not adopted: universal weighted GEO score, fixed passage lengths,
  blanket training-bot allowances, categorical "AI never executes JS", automatic
  Wikipedia/Wikidata presence, or numerical uplift claims without direct evidence.
- [SE Ranking page-level GEO](https://github.com/seranking/seo-skills/blob/main/skills/seo-geo/SKILL.md),
  reviewed 2026-10-23. Useful ideas: inspect actual citation results for a page's
  questions, compare cited sources and preserve the underlying observations.
  Not adopted: mandatory SE Ranking/Firecrawl costs, Claude-only tool names,
  default US market, required protocol files, or claimed universal citation
  benefits from markup/licensing files. Raw HTML can be inspected with any
  suitable available tool; Markdown extraction alone cannot prove schema absence.

Project research informed the distinction between finding, extracting, freshness,
citations and business outcomes. Company identities, prices, source recordings
and account state remain in their owning client project. The skill carries only
the reusable method; a local case is not universal evidence of effectiveness.
