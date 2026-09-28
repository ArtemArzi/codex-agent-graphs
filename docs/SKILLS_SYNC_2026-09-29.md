# Skills reconciliation, 29 September 2026

The publication combines the previously published architecture update with
subsequent local collaboration, testing and proportional-review improvements.
Neither GitHub nor either installed profile was a complete superset before
reconciliation.

## Preserved architecture behavior

- Project Start consults the project's own architecture guidance first, then its
  bundled `references/architecture-playbook.md`. The playbook retains its examples,
  alternatives and proposal format; project requirements remain authoritative.
- The documentation contract records module boundaries, public contracts, data
  ownership and allowed dependencies in the project's owning documents.
- Task Delivery reads these decisions before planning, includes constraints in
  its plan and in delegated context, and checks implementation against them.
- The plan template's architecture section and architecture regression tests are
  retained. Architecture-document snapshots and missing-document rejection are
  still checked by the released controller tests.
- A read-only Project Start reviewer returns the verification payload; the root
  writes the file. This ownership correction is preserved during the merge.

## Added and reconciled rules

- Shared collaboration guidance: read context first, ask only material questions,
  honor explicit no-question instructions within existing authority, explain
  consequential choices plainly and preserve accepted decisions.
- Project Start owns project quality documentation; Task Delivery selects checks
  and timing for the affected requirements and risks.
- Review thresholds follow the user's routing policy. Simple engineering receives
  an auxiliary result review; whole-plan and whole-result acceptors are reserved
  for qualifying complex engineering or concrete material risk.
- `verification-loop` and `ai-regression-testing` are included as non-graph
  companions in the installer and structural validation. They preserve command
  failures, reject false completeness claims, distinguish mocked and real paths,
  and allow tests for new critical behavior before its first incident.

The companions are local adaptations of installed skills marked `origin: ECC`,
not an unmodified upstream release. Upstream attribution:
[Everything Claude Code / ECC](https://github.com/affaan-m/ECC).
The upstream MIT notice is preserved beside both adaptations; this notice does
not change the licensing of unrelated repository content.

## Verification and scope

Run `python3 scripts/check_all.py` before committing. It covers graph contracts,
architecture tests, temporary-home installer checks, model-routing consistency,
skill format and the generated Claude agent projection. It is not a benchmark
of real user tasks. Earlier two next-response probes establish only the observed
clarification/no-question distinction, not universal workflow reliability.

Synchronize source and installed skill trees by content hashes with backups.
Do not replace a whole host configuration merely to update skills: root-model
preferences, credentials and host-specific integrations are separate settings.
Keep active-run identities and state untouched. Existing chats may retain old
instruction context; new chats load the updated installed skills.
