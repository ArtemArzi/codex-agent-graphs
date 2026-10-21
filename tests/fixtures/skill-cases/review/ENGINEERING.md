# Existing engineering standard

tickets.py owns ticket storage and exposes list_tickets(status=None). CLI imports
that interface; it must not read tickets._rows. CLI owns argument/output handling.
No universal file length limit exists. A cohesive implementation may stay in one
file. New behavior should not create unrelated shared frameworks or dependencies.
AI adds no comments, docstrings/JSDoc, TODO notes or commented-out code. Existing
data and public behavior are preserved. These rules are enforced by review in
this fixture; no automated import guard is currently installed.
