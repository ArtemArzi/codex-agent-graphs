---
name: improve-codebase-architecture
description: Survey an existing codebase for demonstrated architectural friction and compare scoped improvement candidates. Use for an architecture review, repeated scattered edits or poor testability; a clear local fix does not require a repository-wide survey.
---

# Improve Codebase Architecture

Find useful architectural changes from real maintenance friction. This is a
survey and decision aid; Project Start owns foundation and Task Delivery owns
implementation. Reuse accepted architecture, domain language and current state.

## Select a meaningful scope

Read the nearest instructions, documentation map, architecture/decisions and
relevant tests. Follow the user's named area. Otherwise inspect a bounded
recent change history and real callers to identify recurring change clusters.
Frequently edited code is a lead, not proof of bad design. Do not scan every
subsystem or invent a refactor to fill a report.

Use available `codebase-design` for the shared discipline: meaningful behavior
behind a small interface, clean responsibility and testability through that
interface. If unavailable, compare actual callers, state ownership and tests
directly. A clear implementation can be correct without added abstractions.

## Establish candidates

For each worthwhile candidate, connect source evidence to a concrete cost:

- Which change or scenario requires scattered knowledge or coupled edits?
- Does an interface expose internal ordering/state that its callers must manage?
- Are tests coupled to internals while the important combined behavior is hard
  to exercise? What actual regression or useful scenario would become testable?
- Would removing a wrapper simplify the whole call path or merely move its
  complexity into every caller? Does combining modules create a new coupling?

Read decisive call paths and tests. Cite files/symbols and distinguish observed
friction from a hypothesis. Size, line count and a code-smell label alone do not
establish a defect. Preserve deliberate architecture and compatibility; explain
any proposed decision change rather than treating an old ADR as an error.

## Compare and hand off

Present a small set of supported candidates, or an honest no-op. Give each the
problem/evidence, affected scope, proposed responsibility/interface change,
expected benefit, cost/risks and a verification scenario. Compare to keeping
the present design. Use a diagram when it helps; HTML, a browser and a separate
report format are optional. Keep output in the existing task owner or the chat.

Recommend the strongest candidate with its tradeoff. Use grilling only for
unresolved consequential intent; resolve technical facts yourself. Design
detailed interfaces once a candidate is selected. If implementation is already
authorized, continue it through Task Delivery in scope; otherwise finish with
the recommendation. Persist agreed domain/architecture decisions through the
existing owners. Do not automatically rewrite code, open issues, create a
schedule or start a new graph/team merely because a survey found a candidate.

Adapted from [Matt Pocock's architecture survey](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/improve-codebase-architecture/SKILL.md).
See LICENSE. Delegation and review follow the host's existing policy.
