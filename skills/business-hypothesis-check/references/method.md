# Method and evidence contract

Source: Ilya Krasinsky's user-provided talk transcript and educational Heroes
Camp / Product Heroes package, © Ilya Krasinsky, 2026, https://heroes.camp.
Local study source: a user-provided Heroes Camp educational ZIP; the private original is not included.
The original package is not distributed here; this is original local instruction
and code. Its upstream report collapsed unknown into falsified and mixed
PASS/INCONCLUSIVE into proof; this implementation preserves missing evidence.

Input JSON object: hypothesis (nonempty string), expectations (nonempty array).
Each row: id (unique string), expected (observable criterion), required (boolean,
default true), status (confirmed/partial/open/falsified, default open), evidence
(source, observed_at, scope, observation: nonempty strings when claiming evidence),
and optionally gap, next_action, owner, due. At least one row is required.

One required falsified row with evidence -> overall falsified. All rows confirmed
with evidence -> confirmed within those criteria. All rows open -> open.
Otherwise -> partial, including an optional contradiction. Unsupported statuses,
duplicate IDs and invalid structure are rejected. Any non-open row missing one
of the four evidence fields is downgraded to open, retaining its declared label.
Metadata is necessary, not proof of source truth; the reviewer must inspect the
actual referenced observations. Field evidence is needed for business claims.
