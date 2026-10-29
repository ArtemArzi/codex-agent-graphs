---
name: grilling
description: Develop an unclear product, idea or task into explicit decisions through adaptive question rounds. Use when the user wants to understand a product, be interviewed, stress-test requirements, or resolve consequential unknown behavior, ownership or business rules.
---

# Grilling

Develop shared understanding through a decision tree: answers settle choices
and reveal questions that could not be asked usefully before. Read the current
request, accepted decisions and relevant owning documents first. Apply the
inherited collaboration and authorization policy.

## Choose the depth

- **Focused clarification:** resolve the consequential unknown in an otherwise
  clear task, then continue that task. A clear small fix needs no product interview.
- **Product discovery:** when the user says "разбери продукт", "помоги продумать",
  "задай вопросы" or presents an unclear product/process, use
  [product-discovery.md](references/product-discovery.md). Continue through the
  material branches rather than treating the first answers as a complete brief.

`grill-me` is the explicit interview entry; `grill-with-docs` adds domain-modeling
when agreed terminology and decisions need durable project documents. Reuse
this one interview discipline; do not start nested interviews for each skill.

## Facts and decisions

Find facts in the repository, available tools or relevant primary sources yourself. Delegate a bounded independent investigation only when it repays the handoff; the presence of an unanswered question does not require a subagent.

Start any admitted fact-finding leaf with a fresh context window
(`fork_turns="none"` in native Codex). Supply the question, relevant settled
decisions, source paths, exclusions and required evidence. It must read those
sources and return contradictions or missing context rather than infer answers
from a parent conversation it does not receive.

Ask the user about material choices that the evidence cannot resolve: intended behavior, ownership, business rules, loss tolerance or scope. Choose routine technical mechanisms and test names yourself. Reuse previous authorization and accepted decisions.

## Question rounds

Group related questions whose prerequisites are known, normally one to three
per exchange. This limits the size of a round, not the number of rounds or the
depth of discovery. Number them, explain the practical consequence and give a
grounded recommendation when there is evidence for one. Leave alternatives
visible; a suggested answer is not an accepted requirement. A question depending
on an unsettled answer belongs to a later round. Recompute the ready questions
after each answer. Use the host's native question interface when available,
otherwise a concise message in the user's language.

While answers are pending, continue independent authorized work. Treat a pending investigation as an unsettled prerequisite; it blocks only the decisions relying on it. Silence and elapsed time are not an answer.

An explicit no-question instruction suppresses ordinary clarification. Record material unknowns or reversible proposed assumptions with their status; do not invent approval for an irreversible or business decision.

## Completion

Record resolved decisions and reasons with their existing owner. Preserve the
distinction between accepted requirements, proposals and unresolved questions.
For discovery, return a coherent product/task understanding and the open items
with their consequences; question count alone is never completion. Continue the
authorized task once its material prerequisites are resolved. Do not add a
universal final confirmation gate. Leave dependent work pending only where an
essential decision or authority remains unavailable.
