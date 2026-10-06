---
name: token-budget-advisor
description: Help choose response depth or estimate a token budget when the user requests it. Honor an already specified length without interrupting the task.
metadata:
  origin: community
---

# Token Budget Advisor

Honor the user's requested length immediately. A request for a brief answer,
detailed explanation or a numeric budget is already a choice; do not ask again.
Continue the authorized work even when its final explanation should be short.

If the user explicitly wants help choosing depth and the choice materially
changes the output, offer at most three choices: direct answer, explanation
with an example, or detailed analysis. Use the host's question tool when present.
Otherwise choose a proportionate default and proceed. Preserve the choice in
this chat until the user changes it. Do not write memory unless asked.

Use actual tokenizer or host usage data when available. Otherwise label token
counts as rough estimates; language, code and formatting change the ratio.
`words × 1.3` for English prose or `characters / 4` can orient an estimate, but
do not claim a measured accuracy percentage or infer output size from input
size alone. Respect the configured output limit and any explicit budget.

Authentication, payment and session tokens do not trigger this skill. Routine
answers need no budget preamble, depth menu or repeated disclaimer.

Adapted from [Token Budget Advisor](https://github.com/Xabilimon1/Token-Budget-Advisor-Claude-Code-).
