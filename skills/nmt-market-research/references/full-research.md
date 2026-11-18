# Full AJTBD / Next Move Theory market research

Adapted from Ivan Zamesin’s pinned public skill. See the [entrypoint](../SKILL.md)
for license, source and the supported routing rules. Use this reference when the
user needs the full evidence-backed report. The templates are examples of
detail and structure. Use the request’s language, geography, and existing
report owner.

Start from the existing product, assets and evidence. Confirm a missing premise
only when it changes the conclusion or the authorized research. Use the shared
[producer guidance](PRODUCER-CONTRACT.md) for evidence and validation, and the
[readability guidance](READABILITY-CONTRACT.md) for audience and report checks.
The active entrypoint governs intake, delegation and file delivery.

## Research order

1. Establish the product, market boundary, audience, existing assets and the
   decision at stake. The project context establishes accepted requirements and
   recorded observations. Assess customer claims individually for what their
   sources support.
2. Research market size and substitutes, then derive candidate segments.
   Use the canon sections linked from the entrypoint for the question at hand.
3. Compare segments, choose or narrow the first segment, assess differentiation
   and adjacent markets, then build the field-validation plan.
4. Assemble the report in its existing owner, or inline when requested.
   Use Markdown by default for saved output and self-contained HTML when
   requested. Preserve attribution, evidence links and the same report detail.

## How we pick the segment to compete for — four go/no-go questions (the selection screen)

Every segment — and every alternative market in the pivot pipeline — gets put through the same four go/no-go questions, the **selection screen**. They answer the core question: *which tasks of which segment should we compete for first?* Score each strong / medium / weak (bigger is better); a hard blocker on any one can rule the segment out on its own.

1. **Can we add value the customer notices?** Can we do the segment's main tasks with *added value they actually feel* versus their current way? The bigger and more perceptible the gap, the better.
2. **Can we earn our target margin?** Does the unit economics support the average margin we want per paying customer (price or budget, minus the cost to serve)?
3. **Can we create or capture demand?** Can we generate demand and reach these customers — and how big and accessible are the channels? Demand you can win lives in the count of customers who have hit a problem with their current tool and are ready to switch (their switching triggers); a big segment that's happily locked into a good-enough habit, whom you can't pry loose or reach, is not a market you can win, however big it looks.
4. **Is it big enough to scale?** Is there enough money in it — **customers × average yearly spend on this task (their job budget)** — to be worth competing for?

**Hard blocker (pass / FAIL).** Is there a legal/regulatory blocker that forbids operating, or a technology that is *impossible* (fusion-energy-class impossibility — not merely "hard to build"; a capable founder can build hard things)? A FAIL removes the segment regardless of the four answers.

Per segment block, render:

```markdown
#### Why this segment, scored (the selection screen)
| Question | Rating | One line |
|---|---|---|
| Can we add value they notice? | strong/medium/weak | {the value gap vs. the current way} |
| Can we earn our target margin? | strong/medium/weak | {unit-economics shape here} |
| Can we create or capture demand? | strong/medium/weak | {channels, reachability, how many are ready to switch} |
| Is it big enough to scale? | strong/medium/weak | {$ size = customers × yearly spend} |
| Any hard blocker? | pass / FAIL | {legal / impossible-tech check} |

**Compose to focus?** {Yes / on the edge / No} — {the binding constraint, one line}
```

The target segment is the one whose answers compose most in our favour **and** best fits the idea's assets.

---

## Job grammar (every Job, every time)

- Format: **When** {context + trigger + negative emotions before}, **I want to** {expected outcome} **with success criteria** {concrete, measurable criteria — plain text}, **in order to** {higher-level Job + positive emotions after}. The canon uses **"in order to,"** not "so that."
- The `I want to` clause names the **expected outcome** (the canon's primary Job element) — not just any verb. Each infinitive verb is one Job (split multi-verb statements into the hierarchy).
- **Name the level every time** — Big / Core / Small / Micro Job — and remember levels are **relative to our product's reach**, not absolute positions.
- **Core Jobs** = the highest-level Jobs the product performs fully. **Big Jobs** = motivation context one level above (not the segmentation root). **Number of Core Jobs is variable** — list as many as the segment performs.
- **Aha Moment** = the customer experiences a Core Job performed *better than the success criteria they expected*. Place it as early in the Critical Chain of Jobs as possible. Positioning promises only what the chain actually delivers (over-promising manufactures a Problem).
- In questions addressed to customers, use the everyday word **task**, never "Job."

---

## Mandatory disclaimers (top of the file, once — never repeated below)

> ⚠️ **Numerical disclaimer.** All numerical estimates are LLM-generated hypotheses. Each metric names its assumptions and carries a runnable verification path (see appendix); in Deep mode sizing is computed via 3 methods where real sources support it, and reconciled. Validate before any investment decision.
>
> ⚠️ **Hallucination disclaimer.** Everything in this document is generated by an LLM and may contain hallucinations in unknown places. For decisions with expensive consequences, run a full quantitative and qualitative research pass; do not act on this document alone.

Link external facts to the sources actually used. Mark missing sources as a gap in the verification checklist. Cite local evidence in a form the intended reader is authorized to access.

---

## Every claim carries its status — and every segment-level claim carries a count

Credibility is per claim, not per document. Two marks travel with each claim: **where it came from** and **how many sources say it**.

**Status — exactly one of three, on every claim in the report:**

- **Backed** — a quote, a document, or a measured figure sits behind it. Cite it (link per Rule 2; for a quote, name the file or the interview number).
- **Derived** — worked out from backed material. Say from what: *"derived from the 6 reviews that mention setup time."*
- **My hypothesis** — the model's inference with nothing behind it. Say so in the same sentence: *"my hypothesis — nothing in your material supports it yet."*

**Treat an uncorroborated estimate as the speaker’s estimate.** When a respondent, a sales rep, or the user says *"60–70% of deals go through tenders"*, it is written as **"per {role}, not a measured figure"** — and it stays out of the sizing inputs unless a document confirms it. If a figure has to lean on such an estimate, mark the whole figure as resting on one person's guess and give it a row in the risk table.

**Anything the model invented that no source mentions lives in one place only — a "Hypotheses to validate" list** (rendered in Section 5). A warranty, a guarantee, an integration, or a pricing model that appears nowhere in the material may not show up inside the segments, the differentiation, or the recommendation as though it were observed.

**Frequency — every segment-level or market-level claim carries a count and its source references.** Whenever the run aggregates from source material (interviews, sales calls, reviews, survey open-ends, the user's documents), the claim reads: *"said by 7 of 22 sources: #3, #7, #9, #11, #14, #18, #21."* No count, no segment-level claim.

- **One source is never a segment-level finding.** A claim resting on exactly one source goes to a separate **"Single signals — verify before acting"** list (rendered at the close of Section 2) with its quote and its source — and may not appear in the segment blocks, the differentiation, or the verdict.
- **A vivid quote is not evidence of size.** The most quotable line in the material never becomes "the segment's main problem" on its own; the main problem is the one with the highest count.
- **When the base is small, show the base.** *"3 of 4 interviews"* — never "most customers".

---

## Confidence scales to the input actually provided

The disclaimers at the top of the file are static. This one is computed from what the user really handed over, and it changes how the numbers are written. Grade the input before composing Layer 1:

- **Thin** — a product description only. No interviews, no analytics, no sales data, no reviews read.
- **Medium** — some real material (a few interviews or reviews, a pricing page, partial analytics), but nothing that covers the segments end to end.
- **Solid** — interviews or sales/usage data that actually cover the segments being claimed, plus external sources behind the sizing.

On **thin** input, three things are mandatory:

1. **A visible warning at the top of Layer 1**, in plain words: *"Thin input: I worked from your description only — no interviews, no analytics. Every number below is a ±{X} range, and every segment is a hypothesis, not a finding."* Give the honest X — with no data, market size is a ±3–5× range, not ±20%.
2. **Ranges instead of point numbers**, everywhere — sizing, segment sizes, yearly spend, shares. Write "$40–200M", not "$120M"; "roughly a third to two thirds", not "58%". A precise-looking number computed from nothing is exactly the failure that shipped a 4×-wrong market size with no warning attached.
3. **The three inputs that would raise accuracy most**, named concretely and ranked — *"8 interviews with {who}", "your last 12 months of deals with amounts", "the review pages of {competitor A, competitor B}"* — one line each on what it would sharpen.

On **medium** input, keep ranges for whatever the material doesn't cover and name what it does cover. On **solid** input, point numbers are allowed where a source backs them.

---

## Readability rules (the report is for a customer who doesn't know the methodology)

The report is **three reading depths in one file**, linked top-to-bottom like canon §-references. Most readers stop at Layer 1; doubters drop one level to see *how we got here*; experts read the bottom. The full template is in "Report structure" below. The rules that make it work:

- **Three layers, escalating depth — state each conclusion once per layer, never twice at the same depth.** Layer 1 = the answer (headline only). Layer 2 = the reasoning in plain language. Layer 3 = the full methodology work (tables, Job statements, selection screens). The old failure was risks appearing 3–4× at the *same* depth (one-pager → §4 options → §5 RAT). Now: a risk is a headline in L1, a plain sentence in L2, a full row in L3 — three depths, not three copies.
- **Drill-down links are mandatory.** Every Layer-1 claim that a skeptic could doubt carries a `▸` link to its Layer-2 anchor; every Layer-2 claim links to the Layer-3 section that derives it. Use Markdown anchors: write `[why narrow ▸](#l2-verdict)` and put `<a id="l2-verdict"></a>` above the target. This is what makes the simple layers *trustworthy* — the reader can always click through to the derivation.
- **Layer 1 = minimal jargon, plain words lead.** Lead every sentence in plain language a junior PM gets at a glance. A methodology term may appear **in parentheses** as a short plain gloss when it genuinely helps — but never *open* a sentence with a raw term, and keep jargon to a minimum. Short sentences — "explain it to a smart friend."
- **Layer 2 = plain language first, term glossed.** On first use, gloss a methodology term in 3–5 words in parentheses — e.g., *"the Big Job (the outcome the customer is really after)"*. Nested or repeated parenthetical glosses are fine — clarity beats purity. Explain terms locally. For reference the skill includes [glossary.md](glossary.md).
- **No internal methodology citations in Layers 1–2.** Never write "per b2b.md §6", "per Rule 14", or any canon file path in the readable layers.
- **Layer 3 may carry methodology citations — but fenced, not inline.** Put canon references in a collapsed **methodology trace** at the end of a subsection, styled out of the reading flow, e.g.:
  > <sub>**▸ methodology trace.** Segmentation root = similar Core Jobs + similar success criteria (`segmentation.md`, Rule 18); levels named product-relative (Rules 8, 20).</sub>
  Never break a sentence of report prose with `(b2b.md §7)`. Project-internal rule numbers (`AGENTS.md Rule 7`) never appear in any layer — they are for your reasoning, not the reader.
- **Disclaimers once.** The two-part disclaimer appears **once** (top of file), plus a one-line pointer in Layer 1. Do not repeat the full disclaimer block inside Layer 3. (Search the file before shipping — the disclaimer wording should hit at most twice.)
- **The zero-methodology reader test — every word in the report, tooltips included.** Someone who has never heard of this methodology must understand every sentence, every table header, and every tooltip. Explain it the way you would to a smart 8-year-old: everyday words, short sentences, no unexplained shorthand. No bare *TAM*, *SOM*, *RAT*, *WTP*, *UE*, *ICP*, *CAC*, *NPS*, *STT* — spell it out on first use or drop it. A tooltip that explains jargon with more jargon has failed: ✅ *"TAM — all the money everyone in the world spends on this problem in a year"* · ❌ *"TAM — total addressable market."*
- **Keep source links** for external facts (Rule 2).

**Enforcement gate (these kept getting skipped in real runs — check each before writing the file; full version in [readability guidance](READABILITY-CONTRACT.md)):**

- **Unique, resolving anchors.** Every `▸` drill-down link points to its own unique `<a id="…">` that exists **exactly once** in the file; no two links share a target. (The live failure was two Layer-1 links pointing at the same anchor.) Before shipping, list every `▸` target and confirm each resolves.
- **Inline-gloss opaque Layer-3 table headers.** A non-obvious column header carries a 3–6-word plain gloss right there — *"Job budget (what one customer spends a year on this)," "Ready to switch (how many have hit a problem and would move)," "Reachability (how easily you can get in front of them)."* Don't rely on the glossary file — a casual reader never opens it.
- **Segment depth across layers** (see Layer 2 / Layer 3 templates). The target segment is **partially described in Layer 2** (who they are, what they're trying to get done, what they care about most, why they'll switch) with a **brief strategic recommendation**; the other top candidate segments get a light touch in Layer 2; the **full Map of Segments at depth lives in Layer 3.**
- **Validation plan across layers** (see templates). Layer 1 touches it (the make-or-break risk + the next action). Layer 2 carries the **focused list — every risky assumption paired with how we'd check it.** Layer 3 carries the **detailed step-by-step validation plan per assumption, grounded in the canon (RAT).**

---

# Report structure — three layers in one file

Assemble the single output file as **three reading depths, linked top-to-bottom**:

- **Layer 1 — The Answer** (~1 page, zero methodology words): the verdict and the few things that matter, in plain language, each linking down to its reasoning. Forwardable to a co-founder who's never heard of the methodology.
- **Layer 2 — The Reasoning** (2–4 pages, plain language, terms glossed once): *how we got here* for each Layer-1 claim. Where trust is built; each claim links down to the full work.
- **Layer 3 — The Full Work** (the detailed report + appendix): the complete methodology — Map of Segments at depth, selection screens, competitor tables, action-RAT, pivot table, sizing appendix. For readers who want the audit trail.

Order in the file: top-of-file attribution + disclaimers (once) → **How to read this (the three levels)** → Layer 1 → Layer 2 → Layer 3. **Compute Layer 1 and Layer 2 LAST**, from the finished Layer-3 analysis.

## How to read this — the three levels

Emitted once, right after the disclaimers and before Layer 1, so the reader sees the structure and can jump to the depth they want. Keep the descriptions plain (no methodology words):

```markdown
## How to read this
**Level 1 below is the whole answer — one page.** Levels 2 and 3 are optional, there only if you want to check the work:
- **Level 1 — The Answer** (1 page, plain words): the verdict, who to sell to first, why, the make-or-break risk, what to do next, how big. **This is the complete answer — most readers stop here.** [jump ▸](#layer-1)
- **Level 2 — The Reasoning** (optional, plain language): how we reached each answer — the buyer in more detail, where we win, and every assumption with how to check it. [jump ▸](#layer-2)
- **Level 3 — The Full Work** (optional, the audit trail): the full market sizing *with a do-it-yourself re-check*, all segments at depth, competitors, the strategy, and the step-by-step plan to test each assumption. [jump ▸](#layer-3)
```

## Layer 1 — The Answer

```markdown
<a id="layer-1"></a>
# {Product} — what the research says
{date · {plain one-phrase market} · {country / region the research is about + the language those customers speak} · stage}

> ⚠️ These are hypotheses, not facts — [full disclaimer ▸](#disclaimers)

## The answer: {GO (to validation) / aim narrower / pivot — in plain words, e.g. "promising, but aim narrower"}
{2–4 short sentences. Plain words, no jargon. The single most important conclusion and the one binding constraint. The first time the verdict is "GO (to validation)", add the half-line gloss: "— worth the next step, which is checking it in the field, not building it yet."} [why this, not a clean yes ▸](#l2-verdict)

> **Validation debt:** this stands on **{N}** unvalidated assumptions — **{M}** of them fatal (would sink it if wrong). The fatal ones are the first things to check. [see them ▸](#l2-validation-debt)
> <sub>N = risky assumptions in the RAT table; M = those that kill it if wrong. A report on thin evidence has high debt — say so honestly (`PRODUCER-CONTRACT.md §4`).</sub>

> ⚠️ **Thin input.** {Emit this block only when the input graded *thin* — omit it entirely otherwise.} I worked from {what was given — e.g. your description only; no interviews, no analytics, no sales data}. So every number below is a **±{X} range**, and the segments are **hypotheses, not findings**. The three things that would sharpen this most: (1) {…}, (2) {…}, (3) {…}.

## Who to sell to
{The target segment in one plain sentence — who they are, not a methodology label.} [how we found this buyer ▸](#l2-buyer)

## Why they'd buy
{The value in one or two plain sentences — the concrete gain vs. their current way.} [the edge, in plain terms ▸](#l2-edge)

## The one thing that decides everything
{The single make-or-break risk, in plain words.} [the full risk list ▸](#l2-risks)

## Do this next
{One concrete next action.} [the action plan ▸](#l2-next)

## How big
{TAM/SAM/SOM in one plain line — each spelled out in everyday words, not as bare initials — plus whether size is the constraint. On thin input these are ranges, never point numbers.} [where these numbers come from ▸](#l2-sizing)
```

**Layer 1 rule: minimal jargon, plain words lead** — a methodology term may appear in parentheses as a plain gloss, but never opens a sentence; short, plain sentences ("explain it to a smart friend"). The make-or-break risk + the next action are Layer 1's light touch of the validation plan. Every line that a skeptic could doubt ends with a `▸` drill-down link.

## Layer 2 — The Reasoning

Use plain language and gloss methodology terms on first use. **No big tables** (prose + at most one small table); the full tables live in Layer 3. Each subsection carries an `<a id="…"></a>` anchor that Layer 1 links to, and links down to its Layer-3 section.

```markdown
---

<a id="layer-2"></a>
# How we got here — the reasoning

*Plain-language walk-through of the logic behind the answer above. The full methodology, tables, and sources are in the next layer. Explain any methodological term when it first matters.*

<a id="l2-input-risks"></a>
## What you told me — and the risks I see in it
*I checked which supplied materials establish an observation and which express a claim about customers or the market. These are the inputs the analysis leans on, and what I'd check before trusting each. (`PRODUCER-CONTRACT.md §3`.)* (Omit this block only if the user provided no claims or materials at all.)

| What you provided / claimed | How I treated it | The risk I see in it | How to check it fast |
|---|---|---|---|
| {claim or material, tagged data / observation / hunch} | {used as hypothesis in {where — wedge / segment / sizing}} | {the specific risk — e.g., "this is your stated value, not customer-validated; the real Job may differ"} | {the cheapest falsifying test} |

{If any wedge / segment / verdict rests primarily on an unvalidated input, say so here in one bold sentence and point to the matching RAT row.}

<a id="l2-verdict"></a>
## Why "{verdict}", not a clean yes
{How an idea is tested by walking a chain — market → buyable customer → real value → working economics → reachable. Name where the chain holds and where it breaks, in plain words. Why the verdict is what it is.} [full chain walk-through ▸](#l3-verdict)

<a id="l2-buyer"></a>
## The buyer, in a bit more detail
{A **partial profile of the target segment** — not the full Layer-3 work, but enough to picture them: who they are, the situation they're in, what they're trying to get done, what they care about most (their dominant success criteria, in plain words), and why they'd switch from their current way. Then **a brief strategic recommendation** — in 1–2 sentences, what to do about this segment (focus here / how to enter / what to lead with).}

{Then one short paragraph or 3-row table on the **other top candidate segments** — name each, one line on who they are and why they rank lower (later / slower / not buyable yet). Full detail on all segments is in Layer 3.} [the full segment map, all segments at depth ▸](#l3-segments)

<a id="l2-edge"></a>
## The edge, in plain terms
{What every existing option forces the customer to give up, and why ours doesn't — where we win, in plain words.} [the criteria-by-competitor matrix ▸](#l3-differentiation)

<a id="l2-validation-debt"></a>
<a id="l2-risks"></a>
## How we'd prove or kill this — every assumption and its check
{This is the heart of Layer 2. List **every risky assumption (hypothesis)** the whole case rests on — walked across the chain (market → buyer → value → economics → reach) — and pair each with **how we'd check it** in one plain sentence. Order by how-bad-if-wrong ÷ cost-to-check (riskiest, cheapest-to-falsify first). A compact two-column table is good here: *Assumption (in plain, falsifiable words) · How we'd find out fast.* This is the list the reader is meant to act on — the step-by-step "how" for each lives in Layer 3.} [the detailed step-by-step validation plan ▸](#l3-risks)

<a id="l2-next"></a>
## The plan, in order
{The next moves as a short numbered list, plain — which assumption to test first, second, third. One line on why this order (riskiest and cheapest-to-kill first). Don't build past the make-or-break check until it lands.} [the reasoning + full plan ▸](#l3-actions)

## If this market is too slow — where else this fits
{Pivot markets in one plain sentence each.} [ranked pivot options ▸](#l3-pivot)

<a id="l2-sizing"></a>
## What the sizing depends on
{State the strongest and weakest inputs, what the result covers and what is still unknown.} [calculations and re-checks ▸](#l3-sizing)
```

---

<a id="layer-3"></a>
# Layer 3 — The Full Work

The detailed report below is the audit trail (Sections 1–6 + appendix). Add an HTML anchor above each section heading so Layers 1–2 can link in: `<a id="l3-segments"></a>` before Section 2, `<a id="l3-differentiation"></a>` before Section 3, `<a id="l3-verdict"></a>` and `<a id="l3-pivot"></a>` before the relevant parts of Section 4, `<a id="l3-risks"></a>` before Section 5, `<a id="l3-actions"></a>` before its action plan, `<a id="l3-sizing"></a>` before the appendix and `<a id="disclaimers"></a>` before the opening uncertainty note. Keep methodology citations out of the prose — fence them in a `▸ methodology trace` line per the readability rules.

## Section 1 — Market snapshot

```markdown
## 1. Market snapshot ({Country})

**Overall buying goal:** {observed goal or explicit hypothesis}

| Metric | Estimate | How computed (1 line) |
|--------|----------|------------------------|
| TAM (global) | ~${X} | {linked methods and their reconciliation} |
| SAM ({Country}) | ~${Y} | {1 line} |
| SOM (1–2 yr) | ~${Z} | {1 line} |

**Landscape:** {new market / red ocean / blue ocean / niche}.
**Ambition vs. share:** target {revenue} → needs {Y%} of SAM → {✅ <10% / ⚠️ 10–30% / ❌ >30%}.
**Takeaway:** {1 sentence — is the market big enough, and what's the binding constraint instead?}

> Sizing assumptions and verification steps are in the Appendix.
```

**Sizing honesty rule.** Use bottom-up, top-down and comparable-market
methods where independent inputs support them. Explain disagreement and show
a range or a qualified estimate where inputs are missing. Treat a reused
input as shared evidence. Name any extrapolation, its conversion assumptions
and the sources. Size the market the user requested.

## Section 2 — Map of Segments (depth follows the verdict)

**Before emitting any segment, run the three segmentation anti-pattern checks** from the entrypoint and the segmentation canon: how they buy is not a segment · industry is not a segment when the Core Jobs and criteria match · every segment is defined by Core Jobs + success criteria + their priority order. A cut that fails a check is merged or justified, never shipped as-is.

Start with the comparison table, then expand each segment. **Depth follows the verdict:** ✅ target segments get the full block below; ⚠️ hold segments get a half block (recommendation line, persona, Core Jobs, selection screen — skip the full size tables and competitor tables); ❌ not-ours segments get **one paragraph only** — who they are, the one binding reason they're not ours, coverage if measured. Don't spend three pages on a segment the reader is told to ignore.

```markdown
<a id="l3-segments"></a>
## 2. Who's in this market — the segments (Map of Segments), with observed coverage

| Segment | $ size / yr | Job budget (yearly spend) | Ready to switch | Reachability | Verdict |
|---------|-------------|------------|-------------------|--------------|---------|
| {S1} | ~${} | ~${} | {how many have hit a problem & would move} | {channel} | ✅ focus |
| {S2} | … | … | … | … | ⚠️ hold |
| {Sn} | … | … | … | … | ❌ not ours |

Segments are grouped by similar Core Jobs + similar success criteria (not by vertical or demographics); the same vertical can split across segments when the Core Jobs and criteria differ. Ordered ✅ → ⚠️ → ❌.
```

Then, for each segment (✅ first, ⚠️ second, ❌ last), at the depth its verdict earns (full / half / one paragraph):

```markdown
### {S#} — {Name tied to Jobs and real criteria} {✅/⚠️/❌}

> **{I propose we focus on this segment because… / I'd hold off on this segment for now because… / This isn't our segment because…}** {1–2 sentences — how the selection screen's four answers compose, how many are ready to switch, the binding constraint}.
> **Coverage:** ~{X}% of total market customers.

#### Why this segment is attractive
{1 short paragraph — motivation, urgency, willingness to pay, reachability. Never use the word "pain".}

#### Persona
{ONE short paragraph telling the persona's story, then 3–5 inline causal-criteria bullets. The persona IS the criteria; demographics only as second-order correlates.}
- **{Causal criterion 1}** — cause: {1 line on how this produces buying behaviour / value / margin / acquisition}.
- **{Causal criterion 2}** — cause: {1 line}.
- **{Causal criterion 3}** — cause: {1 line}.

#### Core Jobs
Here's what they hire a product for, in the customer's own words:
1. **When** {context + trigger + negative emotions}, **I want to** {expected outcome} **with success criteria** {measurable, plain text}, **in order to** {Big Job + positive emotions}. — *{count + sources, e.g. "said by 7 of 22 sources: #3, #7, #9, #11, #14, #18, #21"}*
2. …

{When the run had source material, every Core Job and every success criterion above carries its count and source references; anything resting on a single source is not listed here — it goes to "Single signals" at the close of this section. When there was no source material, label the whole list **my hypothesis** and say what it was inferred from.}

#### Big Jobs (motivation context above the Core Jobs)
*Personal:* **I want to** {verb} {noun} **in order to** {life / status / identity outcome}.
*Business (B2B / hybrid):* **I want to** {verb} {noun} **in order to** {business outcome}.

### Segment size + Job budget
| Metric | Estimate |
|--------|----------|
| People / companies in segment | ~{N} |
| **What one customer spends on this problem per year (Job budget)** | **~${B}** |
| **Total money in segment per year** | **~${N×B}/yr** |
| **Share ready to switch** | **~{%} have hit a problem with their current tool and would move** |

> Sizing method + verification are in the Appendix.

[selection-screen table — see "How we pick the segment to compete for" above]

#### Direct competitors (Core Job level, in this segment)
| Competitor | Core Jobs covered | Main message / USP | Covers poorly (by success criteria) |
|------------|-------------------|--------------------|--------------------------------------|
| {[Name](url)} | … | … | … |

#### Indirect competitors (Big Job level — other ways customers close this Big Job)
| Way / solution | Big Job it closes | Why people use it | What it does poorly |
|----------------|-------------------|-------------------|---------------------|
| {do nothing / postpone} | … | … | … |
| {hire someone / agency} | … | … | … |

#### Who can do the whole job for them (turnkey, Big-Job-level players)
| Player | How they close the Big Job turnkey | Scaling capacity | Threat |
|--------|-------------------------------------|------------------|--------|
| … | … | … | low / medium / high |
```

Close Section 2 with three things: a short **cross-segment themes** block (4–7 patterns spanning segments, each with its count), the **Single signals** list below, and a one-line coverage-verification path (interview 6–8 past payers; if 30%+ don't fit, add a segment).

```markdown
### Single signals — verify before acting

One source said this and nobody else did. Interesting, not yet a finding — none of it fed the segments, the differentiation, or the verdict.

| Signal | Who said it | Their words | Why it could matter | Cheapest way to check |
|---|---|---|---|---|
| {the claim} | {source #7 / a review on {site} / the user} | "{verbatim}" | {one line} | {one line} |
```

(If the run had no source material at all, say so in one line instead of rendering an empty table.)

## Section 3 — Differentiation hypothesis (target segment)

```markdown
<a id="l3-differentiation"></a>
## 3. Differentiation hypothesis: target segment "{name}"

### Positioning (the Core Job → Big Job link — headline first)
> For **{segment with real criteria}**, who performs the Core Job **{Core Job}** in pursuit of the Big Job **{Big Job}**, **{Product}** delivers {value through the chosen mechanic} — so that {Big Job} is achieved {how exactly: faster / more reliably / without doing X / turnkey / with guarantee}.

### Why this segment
{1 paragraph — ROI × opportunity cost × selection-screen balance × fit with the idea's assets.}

### Matrix: success criteria × competitors
| Core Job success criterion | Direct 1 | Direct 2 | Indirect (Big-Job) | Hypothesis for us |
|----------------------------|----------|----------|--------------------|-------------------|
| {criterion} | ⚠️ | ❌ | ✅ | ✅ |

**Underserved criteria — where we win:** {1–3 success criteria all competitors close poorly — usually an *intersection*, not a single criterion}.

### Value-creation direction (one line, not a feature list)
**Mechanic direction:** {one of the published mechanics — `ajtbd-key-theses.md §22–§23` / `value-creation-mechanics.md`; the most powerful when applicable is *climb a level / kill a Job as a class*} — {how exactly the customer's life gets more energy-efficient, 1 sentence}.

> **What to build to deliver this — features, delivery format, cost, the Aha Moment — is `$nmt-craft-value-proposition`'s job.** It generates and filters the concrete ways to deliver this value across the whole mechanics catalog; don't anchor on a feature list invented here. This report stops at the underserved criteria (where you can win) + the mechanic direction.

### Threat from Big-Job-level players
{If turnkey Big-Job players with scaling potential exist — how serious, and partner-or-displace?}
```

## Section 4 — Strategic recommendation & pivot

```markdown
<a id="l3-verdict"></a>
## 4. Strategic recommendation & pivot options

### Verdict on the proposed segment + Jobs: GO (to validation) / NARROW / PIVOT
{Walk the RAT cause-and-effect chain — Market → Segment+Jobs → Value → Unit economics → Channels — and name the verdict + the binding constraint. **GO (to validation)** = the chain holds on the evidence so far → the next step is to validate it in the field, not to build; NARROW = it holds only for a sub-segment / sub-Job; PIVOT = an upstream link is broken and an alternative market scores better. Never write a bare "GO" — it reads as "build it now" (`PRODUCER-CONTRACT.md §4`).}

### Adjacent jobs you could capture next (Job switches within the segment)
{Using the target segment's Job Graph: which Previous Job or Next Job in the chain to capture; whether to climb to a higher Big Job (the most powerful mechanic); which sibling Small Jobs to add. "You're competing on Job X; the more valuable adjacent Job for this same segment is Y."}

<a id="l3-pivot"></a>
### Alternative Big-Job markets for your assets (ranked)
{Generated by the pivot pipeline from your technology, team expertise, and resources, scored on the same selection screen.}

| Alternative Big-Job market | Hypothesized segment + Core Jobs | Why your assets transfer | Selection-screen read (value · demand · margin · size×switch · risk-gate) | What changes vs. the original (channel · UE · build) | Confidence |
|---|---|---|---|---|---|
| {market} | {segment + Core Jobs hypothesis} | {tech / team / partners} | {strong/med/weak per factor; gate pass/FAIL} | {what's different} | high/med/low |

### Strategic options — top 3–5, ranked
{Compose the analysis into 3–5 concrete, ranked strategies the user could actually run. Draw from the full move space, not only "switch markets": stay and narrow to the strongest sub-segment; pivot to an alternative Big-Job market (from the table above); sequence markets (keep cash-flowing market A to fund entry into market B); change the business model or pricing; capture the Previous Job or Next Job in the chain; climb to a higher Big Job. Rank by expected return × confidence.}

| # | Strategy (one sentence) | Why it can win (the mechanism) | Main risk | First cheapest step to validate |
|---|---|---|---|---|
| 1 | {the recommended strategy} | {…} | {…} | {…} |
| 2 | … | … | … | … |

{Each strategy is a hypothesis with a validation step — not advice to follow blind. If a strategy rests on a user-provided claim from the claims ledger, name it: "stands on your input X — validate it first."}

### Suggested reruns
1. Rerun this skill on **{alternative Big-Job market}** — {why}.
2. Rerun with **{a narrower segment / different business model / different channel}** — {why}.
```

## Section 5 — Risks & next moves (action-first RAT)

```markdown
<a id="l3-risks"></a>
## 5. Risks & next moves

Walked across the package on the cause-and-effect chain (Market → Segment+Jobs → Value → Unit economics → Channels). Each assumption is in positive, falsifiable form and paired with the action to validate it. The goal is to *falsify cheaply* — to kill or pivot before the build, not to confirm.

| # | Risky assumption (positive form) | Why risky / cost if wrong | What to do to validate it (the action — cheapest falsifying test) |
|---|----------------------------------|---------------------------|--------------------------------------------------------------------|
| 1 | {top risk — usually the Segment-and-Jobs or WTP assumption} | {money / time / years} | {the concrete action} |
| 2 | … | … | … |
| 3 | … | … | … |
| 4 | … | … | … |
| 5 | … | … | … |

### Hypotheses to validate — my ideas, not yours and not the market's

Ideas that appear nowhere in your material or in the sources — I invented them. They are not findings, and nothing in the recommendation above rests on them. They're listed here so you can test the good ones.

| Hypothesis | What it came from | What would have to be true | Cheapest way to check |
|---|---|---|---|
| {e.g. "a 12-month replacement guarantee could unlock the cautious buyers"} | {my inference from {…}} | {…} | {…} |

<a id="l3-actions"></a>
### Action plan — the next moves, in priority order
1. **{Step 1}** — {the cheapest, highest-leverage falsification first}.
2. **{Step 2}** — {…}.
3. **{Step 3}** — {…}.
{Order by `(P(wrong) × cost-if-wrong) / cost-to-validate`. Segment-and-Jobs validation usually comes first.}

### Detailed validation plan — per assumption, step by step

This is the heart of Layer 3: for **each** risky assumption in the table above (at least the top 3–4), a concrete, canon-grounded plan to test it — so the reader can run it, not just read it. One block per assumption:

**Assumption {#}: {the assumption, in plain falsifiable words}**
- **Method (per canon):** {the right test for this kind of risk — e.g., AJTBD customer interviews on past behavior for a Segment-and-Jobs risk; a fake-door / landing-page smoke test or a priced letter-of-intent for a willingness-to-pay risk; a concierge / done-manually run for a value-delivery risk; a back-test against historical data for a prediction risk. Name why this method fits — RAT: test the riskiest, cheapest-to-falsify first; interview about real past Jobs, not hypotheticals.}
- **Steps:** {numbered, concrete — who to recruit and how many, what to ask or build, what to measure. Use *task*, never "Job", in any question put to a customer.}
- **Kill criterion:** {the specific result that falsifies the assumption — "if fewer than X of N behave this way, the assumption is dead and we {narrow / pivot / stop}." State the threshold up front so the test can't be rationalized away.}
- **Cost / time:** {the honest cost and rough timeline — no artificial "≤1 week" cap.}

> <sub>**▸ methodology trace.** Validate the riskiest assumption first, cheapest-to-falsify first; the goal is to kill or pivot before the build (`rat-key-theses.md`). Interview about real past tasks, not hypotheticals; recruit the people who actually performed the Job (`segmentation.md`).</sub>
```

## Section 6 — Verification checklist

Provide a checklist for rechecking the sizing assumptions, recruiting people
who recently performed the target task, checking segment coverage and running
the validation plan. Audit claim provenance and links. List sources still
needed and distinguish untested claims from observed results.

<a id="l3-sizing"></a>
## Appendix — market sizing, and how to re-check it yourself

Show the calculation, source, population filters and a way to challenge each
input. Separate independently measured inputs, analogs and assumptions.

### A. The calculations (what we did)

For **each** of TAM / SAM / SOM, and for **each segment's size + Job budget**, one compact block:

```markdown
**{Figure} = {result}**
- **Formula:** {the explicit arithmetic — e.g., SOM = reachable buyers × annual price × win-rate}.
- **Inputs (each with its assumption + source):**
  | Input | Value | Where it came from | Assumption / confidence |
  |---|---|---|---|
  | {e.g., # of mid-size plants in US+EU} | {n} | [{source}](https://…) | {how firm — observed / analog / guess} |
  | {annual price per customer} | {$} | {[user data] or [analog](https://…)} | {…} |
  | {win-rate in 1–2 yrs} | {%} | {benchmark / assumption} | {…} |
```

Use a compact table of available methods and linked input sources. Explain whether their ranges overlap. If they do not, show both estimates, investigate the drivers and state the likely range or open question.

### B. Re-check it yourself — step by step

For **SOM and each segment's size** (the numbers that drive the decision), a runnable recipe the reader can execute:

```markdown
**Re-check {SOM / segment size}:**
1. **Count the buyers.** Go to {named source + link}. Pull {the specific figure / filter to apply}. → you should land near {our input}.
   - *Where to look:* {pick the ones that fit the market} — official statistics ([U.S. Census / County Business Patterns](https://www.census.gov/programs-surveys/cbp.html), [Bureau of Labor Statistics](https://www.bls.gov/), [Eurostat](https://ec.europa.eu/eurostat), [data.gov](https://data.gov/)); industry analysts ([Statista](https://www.statista.com/), [IBISWorld](https://www.ibisworld.com/), Gartner/Forrester press releases); trade & industry associations for the vertical; company counts ([Crunchbase](https://www.crunchbase.com/), [LinkedIn](https://www.linkedin.com/) company/headcount filters, job-posting volume as a proxy for hiring/scale); public financials ([SEC EDGAR 10-Ks](https://www.sec.gov/edgar/searchedgar/companysearch), annual reports).
2. **Get the price.** {How to find what one buyer pays — competitor pricing pages, [G2](https://www.g2.com/) / [Capterra](https://www.capterra.com/) plan tiers, procurement records, the user's own quotes}. → compare to {our annual price}.
3. **Bound the win-rate (SOM only).** SOM is not the whole market — it is what you can realistically win in 1–2 years through the channels you actually have. Estimate it as {reachable-via-your-channels} × {a conversion benchmark for your motion — e.g., outbound/PLG/sales benchmarks from [OpenView](https://openviewpartners.com/), [First Round](https://review.firstround.com/), public SaaS benchmarks}. → compare to {our win-rate}.
4. **Redo the multiply** (step 1 × step 2 × step 3). **Confirm/break rule:** within ~30% of our number confirms the order of magnitude; off by >2× means an input is wrong — the table above shows which one to challenge first (the one tagged the weakest).
```

For **Job budget** (what one customer spends a year on this problem today): name where to verify it — the customer's current line items, competitor contract sizes, or interview data — and the one figure to ask for in a customer interview.

> Keep this section concrete and linked. A reader should be able to open the sources, redo the arithmetic in 20 minutes, and either trust our number or find exactly which input to push on. Full input breakdowns and divergence notes stay in-context, not dumped into the file.

---

## Methodology self-critic criteria (checked before the report ships)

Check evidence, method and the finished report.

1. **Segments = similar Core Jobs + similar success criteria** — not demographics, not Big Jobs, not industry.
2. **Real criteria are causes** (a behaviour / characteristic explaining how we create value, earn margin, or acquire), not paraphrased value or consequences.
3. **Selection screen applied** to every segment, and the focus pick justified on it.
4. **Switchability assessed** — the segment has triggered, unsatisfied customers willing to switch (the Problem is the trigger), not only habitual locked-in users.
5. **Jobs use the canon grammar** — `When … I want to {expected outcome} with success criteria … in order to …`; one expected outcome per Job; levels named and product-relative.
6. **Core vs Big distinguished** — Core = highest Jobs the product performs fully; Big = motivation above, not the segmentation root.
7. **Aha Moment placed** — where delivered value beats the customer's expected criteria; positioning promises only what the chain delivers.
8. **Competitors defined by Jobs, not categories** — direct on the Core Job; indirect on the Big Job, incl. do-nothing and non-obvious substitutes.
9. **Underserved criteria = an underserved success-criterion intersection** + a one-line published-mechanic direction — **no feature list** (features are `$nmt-craft-value-proposition`'s job).
10. **RAT walks the cause-and-effect chain**, each risk positive + falsifiable + paired with a validation action; riskiest-and-cheapest-to-falsify ordered first.
11. **Pivot markets evaluated on the same selection screen** against the extracted assets; existential-risk gate applied; each is a concrete Segment + Big-Job pair.
12. **User claims have evidence status** — every load-bearing user claim is tagged (data / observation / hunch); no verdict, target-segment pick, or strategy rests primarily on a single unverified user hunch without saying so; "I don't have this info" answers surface as explicit assumptions, not invented specifics.
13. **Strategic options are ranked hypotheses** — 3–5 options, each with a mechanism, a main risk, and a first cheapest validation step; none reads as consultant advice to follow blind.
14. **Every claim carries a status** — backed (cited) / derived (from what) / my hypothesis (said so). A number a person spoke is labelled *"per {role}, not a measured figure"* and is not used as a sizing input unless a document confirms it. Keep unsupported findings in the **Hypotheses to validate** list. Mark any resulting provisional recommendation clearly.
15. **Segment-level claims carry counts** — each says how many sources back it and which ones. Single-source items sit in **Single signals — verify before acting**, never in a segment block, the differentiation, or the verdict; no vivid quote was promoted into "the segment's main problem".
16. **Segmentation anti-patterns cleared** — no segment is a purchase channel; no B2B split by industry where the Core Jobs and success criteria coincide; every segment traces to Core Jobs + success criteria + priority order, or was merged.
17. **Confidence matches the input** — on thin input the Layer-1 thin-input warning is present, every number is a range, and the top-3 accuracy-raising inputs are named.
18. **The market is the user's market** — every competitor, channel, price anchor, regulation, and example comes from the market named in intake; any figure extrapolated from another market says so and is marked low confidence.
- [ ] Plain-language-led — every user-facing point leads in the reader's own words; methodology terms only in parentheses (never jargon-first); the methodology appendix / debug may stay in full terms.
- [ ] **Three layers present and correctly leveled** — Layer 1 (minimal jargon, plain words lead, terms only in parentheses), Layer 2 (plain reasoning, terms glossed), Layer 3 (the full work). No conclusion is repeated at the same depth across layers.
- [ ] **Drill-down links resolve and are unique** — every Layer-1 claim links to a real Layer-2 anchor; every Layer-2 claim links to a real Layer-3 anchor; every `#l...`/`#disclaimers` target exists **exactly once** and no two links share a target.
- [ ] **Segment depth across layers** — the target segment is partially profiled in Layer 2 (who · what they're getting done · what they care about · why they'd switch) + a brief strategic recommendation; other top segments touched in Layer 2; the full Map of Segments at depth is in Layer 3.
- [ ] **Validation plan across layers** — Layer 1 touches it; Layer 2 lists every risky assumption paired with how we'd check it; Layer 3 gives the detailed step-by-step plan per assumption (Method / Steps / Kill criterion / Cost), canon-grounded.
- [ ] **Opaque Layer-3 table headers carry an inline plain gloss** (Job budget, ready to switch, reachability, etc.) — and never use the non-canon term "switchable demand" in any rendered header or row.
- [ ] **Disclaimers once** — full two-part disclaimer at top only; Layer 1 has the one-line pointer; Section 6 does not repeat the block.
- [ ] **Citations fenced** — no canon path or `Rule N` inline in Layers 1–2 or in Layer-3 prose; any canon reference sits in a `▸ methodology trace` line.
- [ ] **Project context** — use the relevant authorized sources, with their provenance and evidence status.
- [ ] **Zero-methodology reader test passed** — no unexplained shorthand anywhere (TAM, SOM, RAT, WTP, UE, ICP, CAC); if HTML, every abbreviation and methodology term carries an `<abbr title="…">` plain gloss at first use plus the same gloss inline for phone readers.
- [ ] Step ledger ran — every pipeline stage checked off by name; any skip was declared, never silent.
- [ ] **Producer evidence checks** — name input risks and validation debt, show which evidence thresholds were reached or remain open, and pair the verdict with the first field test. If the user requests HTML, check local navigation and source links in the resulting file.

---

## Deep research pipeline

### Waves
```
Wave 1 (independent legs):  [1A] Market & Sizing · [1B] Competitors & Reviews mining ·
                    [P1] Asset Extraction → [P2] Market & Segment-Jobs Generation
Wave 2:             [2] Segments Synthesis & Self-Critic  (consumes 1A + 1B)
Wave 3 (independent legs):  [3] Strategy = Differentiation + action-RAT  (consumes 2 + 1A)
                    [P3] Pivot Evaluation & Ranking  (consumes P2 + 1A + 2)
Orchestrator:       assemble report → compute one-pager last → chat summary
```
(P1→P2 is a short internal sequence inside Wave 1; it only needs the idea + assets, so it overlaps the market research.)

### Research briefs

Use this brief for each leg. For any justified and authorized Codex dispatch, use `fork_turns="none"` and pass the decision, scope, settled context, source paths, exclusions and output explicitly:
> You work with Ivan Zamesin's AJTBD / Next Move Theory methodology. Use ONLY the Next Move Theory canon as the methodology source — do NOT use generic JTBD from the internet or prior training. Read the named canon sections needed by this leg. Resolve paths relative to the installed skill. Keep methodology citations and canon paths out of report prose — hold them in context (the orchestrator fences any that belong in Layer 3). Every named external source is a clickable Markdown link. Work in **the market the user named** — every competitor, channel, price anchor, regulation, and example comes from that market, never from the US or Russia by default. Mark every claim you return with its status: **backed** (a quote, document, or measured figure — cite it), **derived** (say from what), or **your hypothesis** (say so). Give every aggregate claim a count with source references — *"7 of 22 sources: #3, #7, …"*; a claim with exactly one source is returned in a separate *single signals* list, never as a finding. Any number a person merely said out loud is labelled *"per {role}, not a measured figure."* Return your full result in your final message — do not write any files.

**[1A] Market & Sizing.** Use the supplied product context and sources. Formulate and validate the market-level Big Job internally (in-context only). Compute TAM / SAM / SOM for **the market the user named**, each via up to three independent methods (top-down / bottom-up / analog). Where methods diverge, explain why and keep the remaining uncertainty visible. Compare to the user's ambition. If that market has thin public data, extrapolate openly — say from which market, by what ratio, and mark the figure low confidence; never silently size the US or the Russian market instead. Where the evidence is thin, return a range, not a point figure. Return, in your final message, the **compact** body (summary table + landscape + ambition + takeaway) and the **short** method tables + one-line verifications. ≤12 fetches.

**[1B] Competitors & Reviews mining.** Read the relevant Job and segmentation sections. Aim for 5–10 competitors where sources support that coverage (direct on the Core Job + Big-Job-level / non-obvious), picking country- and query-specific sources at runtime. Harvest customer reviews; extract **raw signals only** (do NOT synthesize segments): distinct Core Jobs, success criteria, causal real-criterion candidates, and 5–10 quotable quotes per competitor with source URLs. **Count every signal** — how many reviews or sources carry it, out of how many read, with the source references — and return anything carried by exactly one source in a separate *single signals* list. A single vivid quote is never reported as a widespread problem. Return the competitor list + counted review signals in your final message. ≤12 fetches / ~10 min.

**[P1] Asset Extraction.** Given the user input (idea + assets) + `nmt-key-theses.md`. From first principles, extract and name the idea's **essence**, **technology / capability**, **team expertise & unfair advantages**, **resources in hand** (money, partners, traction, distribution, data, brand), and **hard constraints**. Tag each asset **transferable** vs **idea-specific**. Return the asset inventory in your final message. No web.

**[P2] Market & Segment-Jobs Generation.** Given the [P1] asset inventory + the read set. Generate **5–8 candidate Big-Job markets** where the assets create value, across diverse angles (where the tech applies · where the team's expertise/access/partners apply · adjacent Big Jobs / climb-a-level moves). For **each** candidate, also generate the **Segment-and-Jobs hypothesis** — a named target segment (causal criteria) + its Core Jobs + success criteria — and which assets transfer. (Segment+Job is one analytical entity; a bare market name is not evaluable.) Depth = hypothesis, not deep research. Return the candidate markets in your final message. ≤2 fetches.

**[2] Segments Synthesis & Self-Critic.** Given the user input + the [1A] sizing + the [1B] competitor/review returns + the read set. Group customers from the mined signals into segments by **similar Core Jobs + similar success criteria + causal criteria**. Run the **three segmentation anti-pattern checks** before emitting anything (purchase channel is not a segment · industry is not a segment when the Core Jobs and criteria match · every segment is rooted in Core Jobs + success criteria + their priority order, or it merges). Carry the counts through: every segment-level claim states how many sources back it and which ones; single-source items go to the **Single signals** list, never into a segment block. Build each segment block per the Section-2 template (persona → Core Jobs → Big Jobs → size+budget+switchable share → **selection screen** → competitors inline). Order ✅ → ⚠️ → ❌; **depth follows the verdict** (✅ full block · ⚠️ half block · ❌ one paragraph). Include the cross-segment themes block. Run the **self-critic criteria** over the draft and fix in place. Keep internal-only items (Big-Job validation, antisegment causality, discarded segments) in your reasoning, not the output. Return the segment blocks + short method tables in your final message.

**[3] Strategy (Differentiation + action-RAT + strategic options).** Use the project context, sizing, segments and review signals. Read the relevant sections of the RAT, NMT strategy and value-mechanics canon. Pick the target segment (selection-screen composition + asset fit). Produce Section 3 (positioning headline → why this segment → criteria×competitors matrix → underserved wedge → one-line mechanic direction, NO feature list → Big-Job-level threat) and Section 5 (action-first RAT on the cause-and-effect chain: each risk positive + falsifiable + paired with its validation action; then the Step 1/2/3 action plan, ordered by RAT priority; drop any "≤1 week" constraint; **then the detailed per-assumption validation plan** — for the top 3–4 assumptions, a canon-grounded block each with Method / Steps / Kill criterion / Cost-time, so the reader can run the test, not just read the risk). Also draft the **Strategic options table (top 3–5, ranked)** for Section 4, drawing on the full move space (narrow / pivot / sequence markets / model change / Previous-Next Job / climb a level). Verify any load-bearing user claim from the ledger (≤2 of your fetches); a strategy resting on an unverified user claim must say so. **Nothing you invented may enter Section 3** — an idea no source mentions (a guarantee, an integration, a pricing twist) goes only into the **Hypotheses to validate** list at the end of Section 5. Return Section 3 + the strategic options + Section 5 (incl. the hypotheses list) in your final message. ≤6 fetches.

**[P3] Pivot Evaluation & Ranking.** Given the [P2] candidate markets + the [P1] assets + the [1A] sizing + the [2] segments + the read set. Score every candidate market on the **selection screen** (added value · demand · margin · size×switchability · existential-risk gate); drop gate-failures; rank; select top 3–5. Reuse main-pipeline sizing where a candidate overlaps a researched market. For each pick state **what changes vs. the original idea** (channel · UE · build · which assets carry) and a confidence level. Return the ranked pivot markets in your final message. ≤2 fetches.

### Assembly
1. Reconcile the sizing, alternatives and input claims. Synthesize segments only after reviewing source coverage, and develop the strategy from the resulting segments and asset fit.
2. Check each leg for distinct sources, traceable inputs and applicable method. Aim for at least three independent sizing inputs and real review sources across at least four competitors. If a necessary source is blocked, try an available authorized alternative, then record the source and coverage gap. Report any floor the evidence cannot meet. Where a concrete gap can be closed, use up to two focused passes. A missed floor leaves the affected conclusion provisional.
3. Preserve partial progress in the existing report when a long run has an authorized output owner. Mark unfinished sections and update that same file. For inline research, return the report or the remaining gaps in chat.
4. Assemble attribution and uncertainty, the three report layers and the field-validation plan. Write the reasoning and decision summary after the full analysis. Check source links, anchors, evidence status and the sections actually completed. Lead the chat response with the decision, the first validation step, and the report path if one was saved.
