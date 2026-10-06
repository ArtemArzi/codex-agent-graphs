---
name: writing-for-agents
description: Write or revise agent-facing skills, instructions, and navigation references with precise conditions, usable completion criteria, and preserved constraints.
---

Follow the current host instructions and the owning project documents. Preserve essential constraints, useful examples, and supported native Codex mechanics; this skill advises on writing, not workflow routing or delegation. Use the user's language for communication.

Reference for writing any document an agent consumes: a skill, an `AGENTS.md` / `CLAUDE.md`, a doc reached by a pointer. The packaging differs, but precise selection conditions, clear ownership, and usable completion evidence help make each document easier to apply. Instructions can improve consistency; they do not guarantee identical process or output.

When the document you're writing is a skill, read [`SKILL-MECHANICS.md`](SKILL-MECHANICS.md) for frontmatter, invocation policy, and capability boundaries.

## Context pointers

A **context pointer** is a reference held in the agent's context that names some out-of-context material and encodes the condition for reaching it. A skill's description is one; a line in `AGENTS.md` naming a doc is the same object. The pointer's wording helps the agent decide when to reach the material; availability, host discovery, and task context also affect selection. For required guidance, make the pointer explicit and check that its target exists. Keep essential constraints inline when deferring them could lead to incorrect actions.

A pointer does two jobs: state what the material is, and list the **branches** that should trigger reaching it (a branch is a distinct case the document handles, so different runs take different paths through it). Keep frequently loaded pointers specific without deleting necessary conditions:

- **Name the task and condition**: for example, "Before changing database schemas, read docs/migrations.md for rollback constraints."
- **One trigger per branch.** Synonyms that rename a single branch are one branch written twice; collapse them and keep only genuinely distinct branches.
- Include enough identity to distinguish the target from adjacent guidance.

## The two loads

Every document and pointer you add spends one of two budgets:

- **Context load** is the cost of always-loaded material on the agent's window: an `AGENTS.md` line, a skill description, other frequently loaded material, consuming attention even when it is not relevant to the immediate task.
- **Cognitive load** is the cost on the human: which documents exist and when to reach for each. The human is the index. Keep document ownership and discovery understandable; retain human decision points where they matter.

Material reached only through a pointer escapes context load at the price of the pointer's own line; material with no pointer at all rides entirely on cognitive load.

## Information hierarchy

A document is built from two content types: **steps** (the ordered actions the agent performs) and **reference** (definitions, rules, facts consulted on demand). The two mix freely: all steps (a recipe), all reference (a review's rules, this skill), or both. The core decision is where each piece sits on the **information hierarchy**, a ladder ranked by how immediately the agent needs the material:

1. **In-file step** is the primary tier: what the agent does, in order.
2. **In-file reference** is consulted on demand. Often a legitimately flat peer-set (every rule of a review on one rung), which is a fine arrangement, not a smell.
3. **Disclosed reference** is pushed out into a separate file, reached by a context pointer, loaded only when the pointer fires. Spans a sibling file in the same folder through fully external reference that lives anywhere and any document can point at.

Push too little down and the top bloats; push too much and you hide material the agent actually needs. That tension is the whole decision.

**Progressive disclosure** is the move down the ladder (out of the main file and behind a pointer) so the top stays legible. Not primarily a token optimisation: it is how the hierarchy is protected. Branching is the cleanest disclosure test: inline what every branch needs, and push behind a pointer what only some branches reach. When a document has steps, unrelated reference can obscure them. Keep prerequisites, critical constraints, and examples needed for correct execution with the steps they support.

**Co-location** is the within-file companion: where the ladder decides _how far down_ a piece sits, co-location decides _what sits beside it_ once there. Keep a concept's definition, rules, and caveats under one heading rather than scattered, so reading one part brings its neighbours with it. The test: the document should read like documentation written for the agent. Grouped material reads that way; scattered material does not. (Distinct from duplication: that repeats one meaning in two places; scattering fragments one meaning across many.)

**Sprawl** occurs when a reader must load substantial unrelated material to find the guidance for the current branch. Disclose branch-specific reference behind explicit pointers where helpful. Length alone is not a reason to remove useful requirements or examples.

## Steps and completion criteria

Every step ends on a **completion criterion**, the condition that tells the agent the work is done. Two properties make it a lever:

- **Clarity**: can the agent tell done from not-done? A vague bound ("understanding reached") invites **premature completion**: ending the step before it is genuinely done, attention slipping to _being done_. The visible steps still ahead (the **post-completion steps**) supply the pull; the criterion's clarity is the resistance. Defend in order: **sharpen the bound first** (local and cheap); only if it is irreducibly fuzzy _and_ you observe the rush, hide the later steps by splitting the sequence. A separate file alone is not evidence of an isolated context boundary. Do not introduce agents or handoffs solely to hide later steps; delegation remains governed by the host policy.
- **Demand**: how much it requires. "Every modified model accounted for" defines stronger evidence than "produce a change list" when complete model coverage is a real requirement. Demand drives **legwork** (the digging the agent does within the work, latent in the wording rather than written as its own step), and it is not step-bound: "every rule applied" binds a body of flat reference just as "every step done" binds a sequence, which is how an all-reference document still carries an exhaustiveness bar.

Use checkable criteria proportionate to the task. Define what evidence establishes completion and what remains unverified.

## When to split

Splitting one document into two spends one of the two loads, so split only when the cut earns it:

- **By sequence**: split a long procedure when different phases need substantially different reference material. Keep the shared contract and completion evidence visible; prefer a clear local bound before adding new documents.
- **By invocation**, skill-specific: see [`SKILL-MECHANICS.md`](SKILL-MECHANICS.md).

## Useful terms and wording

A compact, familiar term can help connect a pointer to its reference. Prefer the project's established vocabulary and define unfamiliar terms where they first affect a decision. A short term is useful only if it preserves the meaning the reader needs.

For example, "red test" is a useful shorthand when the document has already established which test fails and why. "Tight loop" does not replace an actual latency or cost bound. Do not collapse "fast, deterministic, low-overhead" into one vague adjective when those are separate requirements.

State the desired action clearly. Explicit prohibitions remain appropriate for authorization, security, data preservation, and other real boundaries; do not remove them on a general theory that negation cannot work.

## Pruning

- Keep each meaning in a **single source of truth**: one authoritative place, so changing the behaviour is a one-place edit. **Duplication** (the same meaning in more than one place) costs maintenance and tokens, and inflates a meaning's prominence on the ladder past its real rank. (The accidental inverse of a leading word, which repeats a token on purpose, never the meaning.)
- The **environment** is a source of truth too (`package.json` scripts, config files, the directory layout, `--help` output), and a document that restates it is a **cache**: a copy of a lookup, earning its load only when the lookup is expensive. Cache what the agent cannot find by looking: the unwritten convention, the reason behind a choice, the gotcha no config confesses. Prefer a reliable lookup for changing facts. Retain essential commands, prerequisites, constraints, or examples when they materially reduce ambiguity, and identify their owner so they can be maintained.
- Check every line for **relevance**: does it still bear on what the document does? A line loses relevance by never bearing on the task (mere exposition, or a branch that should be disclosed) or by going stale as the behaviour or world it describes changes. Shorter documents are easier to keep relevant. Without a pruning discipline the default fate is **sediment**: stale layers that settle because adding feels safe and removing feels risky, until you must core down through them to find what is still live.
- Review suspected **no-ops** using observed behavior and the document's audience. Remove redundant advice only when it does not carry a requirement, rationale, example, or useful reminder. A claim that the model "already knows" something is not evidence that an operational constraint is safe to delete.

## Check the result

Confirm that conditional pointers resolve, each substantial branch has the context it needs, and essential constraints and examples survived editing. Use proportionate real scenarios when behavior is uncertain. Native skill validation checks metadata and scaffolding; it does not prove future automatic invocation or successful task execution.
