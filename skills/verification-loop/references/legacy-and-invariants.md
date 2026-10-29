# Existing behavior and intended invariants

Read before a meaningful refactor when the affected existing behavior lacks
useful protection, or when stateful changes need properties beyond examples.
Keep good existing tests; a well-covered local edit needs no baseline campaign.

## Capture behavior without redefining the contract

Choose representative callers and the observable outputs, errors and state
changes that matter. Execute the unchanged baseline in isolation with controlled
data, time, randomness and dependencies. Preserve inputs and observed results,
version/environment and important limits in the owning test/evidence.
A value guessed by reading source is a hypothesis, not a captured observation.

Classify surprises against the accepted requirements. A characterization test
describes what happened; it does not make an accidental disclosure, lost update
or incorrect calculation acceptable. Keep intentional behavior changes explicit.
Do not edit expected values merely until a new implementation passes.

Use an existing seam to replace an uncontrollable external dependency while
retaining the relevant module contract. If no useful seam exists, make the
smallest behavior-preserving preparation and verify it before the wider refactor.
A fake provider or database adapter cannot prove actual provider delivery or
real-database transaction/concurrency behavior; retain applicable integration
checks from the project.

## Select properties from the actual rule

Use an independently established expectation, not the implementation under test
as its own oracle. For the affected behavior, examples may be enough; generative
or sequence tests help when a justified input space or state interaction matters.
Examples of properties, only when they match the accepted contract:

- Repeating the same accepted operation preserves its identity and does not add
  another record/effect; a conflicting payload is rejected by the agreed rule.
- A failed transaction preserves the relevant state and creates no partial intent.
- An export/import roundtrip preserves named relations, values and statuses.
- Old and new implementations agree outside an explicit intended behavior delta.

Generate valid and invalid boundaries and meaningful operation sequences.
Assert that the action and assertions actually ran. Avoid empty generators,
filters that discard all interesting inputs, self-comparisons, and a reference
implementation that calls the candidate. Preserve reproducible failing inputs;
seeds and repeated counts are evidence limits, not universal quality thresholds.
Use an installed suitable tool or a small deterministic table/sequence driver;
this guidance does not require a new property-testing dependency.

For important protection, confirm that the check detects the original defect or
a small representative mutation in an isolated copy. Do not weaken an accepted
requirement to accommodate the mutation. Report the scenarios protected and
remaining gaps; a passing baseline is not proof that any refactor is safe.

## Make a discriminating check reproducible

When forcing a failure by mutating code or a fixture, retain the pristine
candidate and inspect the actual diff before trusting the red. Confirm the
mutated path ran and failed for the intended behavior, not compilation, an
unavailable dependency or an unrelated error. Restore the intended candidate
and recheck; keep the mutation evidence separate from the delivered change.

For important rules choose a bounded sample of plausible faults. A survivor
can mean a missing case, weak oracle, unexecuted path or equivalent behavior;
classify it instead of adding meaningless assertions for a target score.
For generative/stateful failures preserve a minimal failing input/sequence,
version and all tool-specific replay information. Shrink without changing the
symptom, and add a readable regression example when useful. A roundtrip alone
does not prove an external format if encoder and decoder share the same error.
Use an independent literal/specification/implementation as appropriate.

The relevant [reference catalogue](reference-implementations.md#strong-tests-and-reproducible-failures)
contains examples and tool limits; it does not require a new dependency.

Independently written guidance informed by Michael Feathers's publisher excerpt
on [seams](https://www.informit.com/articles/article.aspx?p=359417&seqNum=2).
Observed behavior and intended correctness remain separate sources of evidence.
