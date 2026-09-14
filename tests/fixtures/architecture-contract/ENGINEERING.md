# Engineering standard

Rule E1: notifications may import payments.public, never payments._store.
Rule E2: only payments owns payment state; no direct storage access by consumers.

`python3 check.py` is executable locally. It checks notification behavior and
AST-visible imports of payment internals. It is not configured as required CI
and does not claim to prove dynamic access or all data-ownership properties.
Data ownership beyond these imports requires review.

Report missing architecture context before dependent edits. Do not infer an
exception or amend A1 silently. Changes to A1 require an explicit decision and
re-review of the affected plan before implementation.
