# Design It Twice

When alternative interfaces would help resolve a concrete design decision, compare a few different shapes. Apply the inherited native delegation and review policy. A small, well-mapped choice can be explored by the root alone; independent variants are useful only when they repay the handoff. Based on "Design It Twice" (Ousterhout).

Uses the vocabulary in [SKILL.md](SKILL.md) — **module**, **interface**, **seam**, **adapter**, **leverage**.

## Process

### 1. Frame the problem space

Before exploring alternatives, explain the problem space for the chosen candidate:

- The constraints any new interface would need to satisfy
- The dependencies it would rely on, and which category they fall into (see [DEEPENING.md](DEEPENING.md))
- A rough illustrative code sketch to ground the constraints — not a proposal, just a way to make the constraints concrete

Explain the meaningful choice plainly and continue within the existing authorization. A missing material owner decision blocks only the work depending on it.

### 2. Explore distinct variants

Generate distinct interfaces yourself for a bounded choice. When independent design blocks justify delegation, use the host's native agents, configured roles and limits, normally one or two non-overlapping read-only assignments. Children remain leaves. More variants do not require more agents.

Give each variant a technical brief (file paths, coupling details, dependency category from [DEEPENING.md](DEEPENING.md), what sits behind the seam). Choose the constraints that illuminate the actual trade-off:

- Minimal surface: "Minimize the interface — aim for 1–3 entry points max. Maximise leverage per entry point."
- Required flexibility: "Support the actual known use cases and extension points."
- Common caller: "Make the default case trivial."
- Dependencies, if applicable: "Design around ports & adapters for cross-seam dependencies."

Use the [SKILL.md](SKILL.md) vocabulary and the project's selected glossary owner from its documentation map, whether GLOSSARY.md, legacy CONTEXT.md or another term section. Include relevant accepted architecture, constraints and source pointers without duplicating the whole context.

For each useful variant, capture:

1. Interface (types, methods, params — plus invariants, ordering, error modes)
2. Usage example showing how callers use it
3. What the implementation hides behind the seam
4. Dependency strategy and adapters (see [DEEPENING.md](DEEPENING.md))
5. Trade-offs — where leverage is high, where it's thin

### 3. Present and compare

Present designs sequentially so the user can absorb each one, then compare them in prose. Contrast by **depth** (leverage at the interface), **locality** (where change concentrates), and **seam placement**.

After comparing, give your own recommendation: which design you think is strongest and why. If elements from different designs would combine well, propose a hybrid. Be opinionated — the user wants a strong read, not a menu.
