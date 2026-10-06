---
name: domain-modeling
description: Resolve domain terminology and durable decisions when designing a project, changing business concepts, or updating its owning glossary or ADR. Reuse the project documentation map and accepted decisions.
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline — challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `GLOSSARY.md` for vocabulary is not this skill — that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

## Resolve the owning documents first

Read the project's documentation map and nearest instructions. Reuse the existing owner of term definitions and the chosen decision/ADR location. A mapped glossary or term section has priority over filenames in the examples below.

Support both `GLOSSARY.md` / `GLOSSARY-MAP.md` and legacy `CONTEXT.md` / `CONTEXT-MAP.md`. When no map selects an owner, use the existing glossary convention. If both files exist and ownership is unclear, inspect their content and callers before changing either; resolve a material conflict rather than merging or renaming them automatically. Create a new `GLOSSARY.md` only when there is a resolved term and no existing owner.

The glossary-only rule applies to term definitions, not to a larger owning domain document that also contains other canonical sections. Keep architecture decisions with their existing owner. The layouts below are examples; preserve the project's actual paths and references. Explain ambiguous business terms to the user plainly and ask only material unknown decisions under the host policy.

## File structure

Most repos have a single context:

```
/
├── GLOSSARY.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `GLOSSARY-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── GLOSSARY-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── GLOSSARY.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── GLOSSARY.md
│       └── docs/adr/
```

Create documents lazily, only when there is something resolved to record and no existing owner. Use a new `GLOSSARY.md` only after the ownership lookup above; create a decision location only when the project has none and the first qualifying ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `GLOSSARY.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update GLOSSARY.md inline

When a term is resolved, update the selected owning glossary or term section right there. Do not batch these up. Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md) where compatible with that owner's existing format.

Keep the glossary or term section focused on domain definitions. Specifications, task state and implementation decisions stay with their respective owners; a larger canonical document may contain them in its other sections.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).
