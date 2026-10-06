---
name: to-questionnaire
description: Draft a focused questionnaire for an identified person who holds facts or decisions needed to resolve material project unknowns.
---

Turn a material knowledge gap into a Markdown questionnaire the user can hand to a knowledge owner or use during a meeting. The recipient holds information the user and agent cannot establish from available evidence. This is a drafting capability; sending the document requires separate explicit authorization.

## Establish the gap

Read the existing conversation and owning project documents first. Infer the recipient's role, expertise, relationship to the user, and needed decision from confirmed context. Reuse answers already given. Ask only for missing facts that materially change the questionnaire: who holds the answer, what the user must be able to decide afterward, or a meaningful audience constraint. Group related clarifications in one concise exchange when needed. Do not interview the user about subject matter specifically owned by the recipient.

Map each material unknown to the decision it affects. Remove questions already answered by project evidence and avoid expanding the scope into a generic discovery survey. If the owner is unknown, use a clearly labeled role assumption when sufficient; ask when choosing the wrong recipient would invalidate the document.

## Write one owning deliverable

Update the existing questionnaire or agreed document when present. Otherwise create `to-questionnaire-<topic>.md` in the authorized workspace and report its path. Produce one owning deliverable, not competing copies. Adapt the user's language, tone, and project vocabulary to the recipient.

Order the most consequential questions first, since an asynchronous response may be incomplete. Group by theme when useful. Give each question one answerable idea and an answer stub. Add a short explanation only where it prevents misunderstanding. Cover every confirmed needed decision without demanding unrelated sensitive information. Distinguish known context, assumptions, and unresolved items.

## Adaptable document structure

```markdown
# <Questionnaire title>

**Purpose:** <the decision or action these answers will enable>

**From:** <known sender or role>
**To:** <recipient or knowledge-owner role>
**How answers will be used:** <owning decision or document>

## Context

<One short paragraph with the facts the recipient needs.>

## How to answer

<Include a known deadline or effort expectation only when supplied.
Partial answers and uncertainty are useful; mark unknowns explicitly.>

## <Theme>

### What load is expected at launch?

_Why this matters: it affects whether burst capacity is needed now._

Answer:

## Anything else?

What relevant constraint or risk have we missed?

Answer:
```

The structure is a starting point, not a mandatory long form. Do not invent sender identities, deadlines, response commitments, or factual answers. Before finishing, check that each material unknown has a clear question, known answers are not requested again, and the document can be understood by someone outside the conversation. Report the artifact and any remaining limitation. Do not automatically email, message, publish, or distribute it.
