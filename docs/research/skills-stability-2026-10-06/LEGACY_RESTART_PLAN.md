# Continuing or replacing old workflow instances

Status: accepted for implementation. Independent receipt:
`PLAN-20261006-LEGACY-RESTART-PASS-c3496a81`. Implementation accepted by a
different whole-result reviewer:
`RESULT-20261006-LEGACY-RESTART-CANDIDATE-PASS-61b454e0-60f9-4b21-93e3-d2b46efb4461`.
Both installations match; final publication reconciliation is tracked in
[LEGACY_RESTART.md](LEGACY_RESTART.md).

## User outcome and authority

Follow-up to the skills stability audit: old Task Delivery or Project Start
instances sometimes fail to launch. User explicitly permits retiring old
instances and creating current ones. Interpret instances as saved workflow
runs, not Docker/site images. Implement and synchronize maintained skills to
WSL/Desktop and GitHub under the existing authorization. Do not sweep unrelated
live tasks or alter product code, provider settings, signatures or secrets.

This is a material extension of the earlier plan, which excluded old-state
replacement: it changes persistent ownership and admission contracts. Obtain
a fresh whole-plan acceptance and a different whole-result acceptor.

## Research basis

Canonical source clean at 4567983a55276bb308a8746ec6c547f3e2b2e99c; isolated clone
and source/protected-setting manifests created. Bounded known-project read-only
inventory: 89 runs, 19 nonterminal. All observed graph identities are currently
supported; eighteen active TD runs load, one PS run rejects a changed shared
project-state hash. This does not prove all stalls are version mismatches and
does not authorize interfering with other active chats.

Independent historical discovery: released PS3.1.0 at 2e25f661a217 has exact
graph SHA f27635bb0d2dd02a5c2167231a8077647ac5dc84baab751a5af388c566578a0a;
same run/shared schema versions but earlier document/evidence contracts.
Current ordinary PS loader only accepts exact3.4/3.5/current; raw recover also
rejects3.1. TD allows exact3.0 through3.9, but unknown graph identity blocks
retire/degrade. Existing TD retire saves bytes but has no successor contract;
existing PS abandon preserves obligations/verification/drift but requires the
strict loader and drift restoration before init. Full old-path compatibility
is not proved by substituting old identities into current-shaped test states.
Evidence packets: /tmp/codex-legacy-runs-20261006.json and
/tmp/codex-legacy-active-loads-20261006.json; historical source via git show.
No original states changed.

## Bounded contract

1. Ordinary execution loaders, digest algorithms, receipts and allowlists
   remain strict. Known old v2 work uses existing legacy runner, documented
   directly; unknown schema/corrupt ownership stays preserved/native, never
   converted by guessing. No blanket acceptance of unknown graph identities.
2. Add explicit `restart` lifecycle operation to each current controller for
   structurally valid unfinished v3 runs, including an unrecognized graph
   identity. It requires reason and --acknowledge-incomplete, which agents may
   supply from this user's existing permission. Restart does not certify or
   execute old evidence. Separate validated structural loading from ordinary
   identity/evidence loading; validate root/run containment, plain files,
   indexes/shared owner, exact current preimages, supported modes/profiles and
   statuses. Reject completed runs, ambiguous ownership, symlinks, live locks,
   malformed state and unresolved material decisions. Existing permission to
   restart is not an answer to a business decision. Native continuation remains
   possible within real authorization when a restart cannot safely be admitted.
3. Before mutations, snapshot old run/index or shared state exactly and capture
   current document/source basis as needed. Preserve all old evidence and useful
   code/docs. Record explicit unfinished retirement/supersession and successor
   linkage. Never change old graph identity, edit old receipt bytes, copy a PASS
   as current acceptance, or treat old file hashes as authorization for new code.
4. TD: preserve the old task/run with retirement snapshots; create a new task
   ID deterministically unless supplied. New current full/plan run carries the
   original intended outcome, nondecreasing risk and a COPY of its plan as a
   fresh candidate (original retained). Reformat contained scope in that copy
   if necessary, preserving text/selection and requiring fresh review. No old
   acceptance is copied. Both successor states retain resolved decision answers
   verbatim with their original scope/source as mandatory constraints and carry
   rejected-review repair requirements. Unresolved decisions block restart.
   TD verification_required is inherited (including rejected verifier evidence),
   never reset by initialize; fresh review must address carried constraints.
   Pending Project Start obligation blocks TD retirement
   as today. New task lineage is explicit; collision/tampering fails closed.
5. PS: validate the actual shared state and matching active owner. A changed
   shared hash alone is not silently trusted for completion: restart captures
   the fresh shared preimage and requires complete fresh revalidation. Restore
   consumed Task Delivery obligation exactly; preserve other shared fields,
   pending requirements and prior rejected/required verification. Preserve
   document drift in a mandatory inherited-revalidation record rather than
   requiring deletion/restoration of useful edits. Carry that record into the
   successor; fresh work/verification must cover inherited changed/removed
   paths. The record binds baseline/current hashes, using an explicit missing
   value for removed files, and its digest must be named by fresh work and
   verifier receipts. Existing mandatory documents must be restored when missing;
   restart grants no new deletion authority and validate_work retains its deletion
   prohibition. Reviewer verifies inherited changes against the captured basis,
   not just the successor baseline. Completion may discharge the record only
   on genuine new evidence satisfying these constraints.
   Fresh PS admission uses current graph and current source/docs. Unknown old
   receipts cannot become authority; missing/mismatched actual obligation
   evidence blocks its release and remains visible.
6. Replacement is restartable/idempotent under owned locks and verified
   preimages. Preflight successor plan/geometry/admission before retiring old
   ownership. A durable per-workflow restart marker under the repository admission
   guard reserves ownership throughout transfer. Ordinary init/recover must
   refuse pending markers rather than steal ownership or clear obligations.
   Only restart of the exact marker may reconcile its verified preimages; it
   targets that run, never loosens the ordinary recovery sweep.
   Staged crash snapshots/transition marker reconcile interrupted
   retirement or successor activation. Never create duplicate successors,
   overwrite concurrent external edits or claim all-or-nothing rollback if
   recovery is pending. Preserve resumable partial state with precise next step.
7. Add only necessary graph version/policy changes, retaining exact previous
   identities and legacy behavior. Document resume versus restart and finite
   fallback in entrypoints. Avoid a new orchestration framework or global hook.

## Architecture conformity

Governing source AGENTS.md, README design principles and existing lifecycle
contracts remain authoritative. Existing TD/PS controllers own state transitions;
shared repository admission guard and shared-state compare-and-swap own
concurrency. Use Python standard library and existing atomic writes/locks only.
No model makes lifecycle decisions, no new orchestration runtime or global hook,
and ordinary graph-identity/evidence loaders remain strict.

## Verification and release

Use meaningful fixtures: actual historical PS3.1-shaped state from historical
tests/source; TD old state shape; unsupported identity ordinary commands still
reject but lifecycle restart creates current successor; live-ish shared hash
drift does not silently pass completion; code/docs/old artifacts unchanged;
old pending decisions/obligations/rejected review retained or block restart;
nondecreasing risk; old plan outside digest region normalized only in new copy;
successor has no old PASS; genuine current work/review/completion required;
idempotence, repeated request, interrupted writes and concurrent/source/target
drift; symlink/escape/collision rejection and legacy v2 resume guidance.

Fresh behavioral fixture agent chooses from real installed skills without the
diagnosis/expected route; no changes to active real tasks. Run focused suites,
shared lifecycle/contracts, metadata and scripts/check_all.py; strict staged
diff check. Fresh whole-result candidate acceptance before canonical/install
mutations, then same reviewer revalidates actual manifests/idempotence,
protected settings and normal GitHub push/readback. Source copy uses baseline
guards and backups. Existing --skills-only install preserves configuration.
Record bounded evidence/results in this owning audit directory. A supported
restart utility is the outcome; unrelated real runs are not mass replaced.
