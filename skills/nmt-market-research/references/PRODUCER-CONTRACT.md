# Producer evidence guidance for NMT Market Research

This market research adaptation retains the evidence, validation and report
principles of the shared producer contract. Its active
[entrypoint](../SKILL.md) owns scope and intake. Use the evidence sections
below for the full study. Quick discussion uses the relevant method and
honest evidence status without a separate report framework.

## 1. Orientation when needed

If a full study still has an unresolved premise, describe the decision and
evidence needed in a few lines before asking. Start analysis from the known
context whenever it is sufficient.

## 2. Report format

Use Markdown by default for an authorized file. If the user requests HTML,
use a self-contained document with the same attribution, report layers,
sources and working internal navigation. For an inline request, answer in
chat. Use the [readability guidance](READABILITY-CONTRACT.md) for a full report.

## 3. Assess the evidence supplied

From user testing: on a project that came in with a deck + landing + codebase, the skill *took the descriptions as truth, baked them into the wedge, and never proposed checking them* — substituting the team's imagined Job for the customer's real one. The canon forbids skipping field validation (Phase II).

Identify what each source actually establishes. A product brief or code can establish a design decision or implemented behavior. Claims about customer demand still need customer or market evidence.

Two concrete obligations:

**(a) Actively hunt for risks inside the provided material.** Don't just record claims — interrogate them. For each load-bearing input, ask:
- Is this a customer-validated fact, or the team's belief about the customer? (A landing page is the team's hypothesis about value, not proof customers want it.)
- Does the stated Job / segment look like the customer's real Job, or the team's projection? (The most expensive error — seen in real runs.)
- Are there internal contradictions, or numbers presented as data that are actually guesses?
- What would have to be true for this to hold — and is that checked?

**(b) Emit a dedicated, visible block in the output** — *"What you gave me — and the risks I see in it."* This is Ivan's explicit ask: *"when you gave me this information, I see these risks in it,"* marked separately. Place it in **Layer 2** (where trust is built), as its own subsection, and surface the single worst one in **Layer 1** as (or alongside) the make-or-break risk. Format:

```markdown
## What you told me — and the risks I see in it
*These inputs support different parts of the analysis. Each row shows what it supports and what I would check.*

| What you provided / claimed | How I treated it | The risk I see in it | How to check it fast |
|---|---|---|---|
| {claim / material, tagged data / observation / hunch} | {used as hypothesis in {where}} | {the specific risk — e.g., "this is your team's stated value, not customer-validated; the real Job may differ"} | {the cheapest falsifying test} |
```

**Hard gate:** no verdict, target-segment pick, wedge, value proposition, or PRD scope may rest *primarily* on an unvalidated user input without the output saying so explicitly and pointing a RAT row at it. If the wedge is built on a Job taken from the user's materials and not confirmed by customer evidence, that is named as the single most expensive risk.

## 4. Visible validation debt + "GO (to validation)"

From user testing — *"A PRD built in 20 minutes on guesses looks as convincing as one after 8 interviews. Print the debt."* And: *"`GO` reads to a founder as 'build it — 3 months'; by your own algorithm GO means 'go validate' — 8 interviews and a fake door."*

Two changes:

**(a) Validation-debt line in Layer 1** — one line, near the top of the answer:

> **Validation debt:** this stands on **{N}** unvalidated assumptions — **{M}** of them fatal (would sink it if wrong). The fatal ones are the first things to check. [see them ▸](#l2-risks)

N = count of risky assumptions in the RAT / risk table. M = those tagged "kills it if wrong." Count honestly; a Quick run on thin input has high debt — say so. This makes a fast artifact legibly fast, not falsely authoritative.

**(b) Verdict wording** — wherever a skill emits a `GO` verdict, write **`GO (to validation)`**, never bare `GO`. Keep `NARROW` and `PIVOT` as-is (they already read as "not yet building"). In Layer 1 add a half-line gloss the first time: *"GO (to validation) — the idea is worth the next step, which is checking it in the field, not building it yet."*

**(c) Hand-off carries the debt.** When a skill hands off to the next in the chain (`$nmt-market-research` → `$nmt-craft-value-proposition` → `$nmt-product-requirements` → `$nmt-craft-go-to-market`), the next skill **opens by asking what from the prior artifact's validation debt has since been checked**, and re-tags anything still unvalidated. Debt travels down the chain; it is not silently dropped.

## 5. Report owner

Use the existing task or project owner for saved material. Respect its path
and the user’s explicit destination. Keep a single current report.

## 6. Deep-mode evidence checks

Use the [full research procedure](full-research.md) for the source floor, gap
handling and focused self-check. Try a permitted alternate source for a blocked
leg when it can answer the question. Record the coverage actually reached.

## 7. Market and language

Use the market, audience and language from the user and project sources. Keep
unknown geography open and ask only if the answer depends on a market-specific
claim you cannot support yet.

## 8. Project context

Use relevant local files already authorized for the task. Preserve their
provenance and applicable sharing boundaries.

## 9. Every claim carries its status

Every claim in the output is one of three things, and says which:

- **Backed** — a quote or a number that is actually in the source. Cite it: the quote, or the file and row it came from.
- **Derived** — inferred from the data. Say *from what*: *"derived from the 4 calls where the buyer named price before delivery."*
- **Model hypothesis** — the skill's own idea, present in none of the sources. Label it as such.

**A number a respondent said out loud is that person's opinion, not a market fact.** *"60–70% of deals go through tenders"* ships as *"per the sales director — an estimate, not a measured figure."* A spoken number never becomes a market-sizing input, a chart value, or a headline without an outside source behind it (Rule 2).

**Ideas the model invented stay out of the findings.** A warranty nobody mentioned, a persona nobody described, a channel nobody named — these may appear **only** in a clearly-marked *"Hypotheses to validate"* section, never inside the value proposition, the segments, the sizing, or the verdict as if the data supported them.

## 10. Frequency counts on every aggregated claim

Wherever the skill aggregates claims from source material — interviews, sales calls, reviews, support logs, survey open-ends, documents the user supplied — **every segment-level or market-level claim carries a frequency count and its source references**: *"said in 7 of 22 interviews: #3, #7, #9, #11, #14, #18, #21."* Without the count and the list, the claim does not ship.

**A claim supported by exactly one source may not appear in a segment-level or market-level conclusion.** It goes into a separate list — *"Single signals — verify before acting"* — with its source and what would confirm it.

**One vivid quote is never "the segment's main pain."** Vividness is not frequency; a memorable sentence from one respondent is the most common way a report invents a segment that isn't there.

## 11. Confidence scaled to the input the user actually gave

Claimed confidence is computed per run from the evidence on hand. This complements the fixed disclaimers (Rule 3) — those are static, this one is measured.

Count the real evidence: interviews, analytics exports, reviews, documents, verifiable external sources.

**Thin input** — no interviews, no analytics, just a description of the idea:

- Put a warning in the header, where it can't be missed: **"Thin input: estimates are ±X ranges, segments are hypotheses."**
- Give every number as a **range**, not a point value; write *hypothesis* beside every segment.
- List the **top 3 inputs that would most raise accuracy**, concrete and ordered by how much each would move the answer — *"10 interviews with {segment}," "your last 6 months of activation data," "your win/loss notes."*

With richer input, tighten the ranges and say what they now rest on. A Quick run on one paragraph must never read with the same confidence as a Deep run on twenty interviews.

---

Adapted from Ivan Zamesin’s public NMT producer contract at
`f8e87d10255b48d381ebc7fa65172960eb6d483f`, v0.6.18, [CC BY-NC-SA 4.0](../LICENSE).
