# Verification of the development pipeline package

Date: 2026-10-15. Baseline: b5709016e1eeb3595d25615ebda5a63964a46b20.
User scope: implement/package/commit source; no push, live install or deployment.

## Package and compatibility

- Existing Project Start, Task Delivery, Software Factory, Deployment and Product
  Care entrypoints/references updated. Two new conditional references and one
  human cycle map; no standalone skill, controller, runtime/schema/model change.
- All four released graph.json files byte-identical to baseline. Existing
  scripts and global configuration were not edited.
- Five affected skills passed native quick_validate.py; relative local pointers
  in the new references/cycle map resolve. git diff --check passed.
- Full python3 -u scripts/check_all.py passed with exit 0 on the frozen
  /tmp/pipeline-verified-dhkj1vch snapshot. 343 source files were byte-verified
  against the candidate, with no source drift when the run completed. Subsequent
  task evidence records are documentation only, reviewed separately. Original
  output is [check-all.log](evidence/check-all.log).
- The full check includes installer preservation/idempotence, native graph
  compatibility, artifact lifecycle and Factory's real two-job integration,
  stale/dirty/overlapping ownership and combined-behavior failure cases.
- Disposable skills-only install/verify passed. Both new references matched
  source bytes; user-owned config/global instructions/isolated profile were
  unchanged; repeated installation was entirely in-sync. [packaging.json](evidence/packaging.json).

## Preserved failed verification attempt

An early check_all run started against the mutable candidate while the author
was still editing it. The installer correctly detected "Concurrent install
source edit"; its adversarial test expected a different injected race. The run
failed and is not counted as a clean baseline or final result. The author froze
a byte-verified snapshot before the successful full run. No test was weakened
and no guard was bypassed. Original failed output remains in the originating
chat work/pipeline-baseline-check.log.

## Independent forward observations

The evaluators received raw fixture requests and candidate skill paths, without
the implementation plan, expected answers or research synthesis. Their writes
were restricted to separate synthetic fixtures. They did not spawn descendants,
install, commit, call providers or claim controller/production acceptance.

| Case | Observed result | Evidence and boundary |
|---|---|---|
| Existing project adoption | Preserved Python/SQLite, code, tests, existing decisions/operations and an untracked user note. Created mapped document candidates and actual consumer/error/state scenarios. Missing channel/recovery/load decisions remain questions | [Foundation forward report](FOUNDATION-FORWARD.md), [architecture output](ADOPTION-FOUNDATION.md), [first slice/questions](ADOPTION-PLAN.md). 1 existing unittest before/after passed; no bootstrap controller completion or external research claimed |
| Factory route choice | Independent readers selected parallel; unsettled frontend/backend contract and shared DB/port require sequential prerequisites/isolation; spelling fix stays ordinary root-only | Same forward report. These route cases are decision-only, distinct from actual helper integration tests in check_all |
| TDD and simplicity | Real pre-fix RED detected whitespace defects; same public tests became GREEN after a one-line split/join fix. Independent literal expectations, six tests, no new dependency. Existing helper retained because extra cleanup had no benefit | [Delivery forward report](DELIVERY-FORWARD.md), [RED](evidence/red-output.json), [GREEN](evidence/green.log), [final](evidence/final.log), [run records](evidence/runs.json), before/after/test files in fixtures/behavior |
| Deployment and Product Care | Concrete local source-check lane, exact subject/evidence and explicit missing target checks. Follow-up question, version/source/owner/window unknowns and meaningful next trigger recorded; no collection/schedule/effect fabricated | [Prepared continuation](DELIVERY-FOLLOW-UP.md). Preparation only, target-version/public-route NOT RUN |

Architecture output separates current create/list from proposed notifications,
accepted decisions from options, saved ticket ID from external delivery, data
ownership from adapters, and local tests from provider E2E. The first slice links
governing sections and conditions. This is content evidence, not a read flag.

The inherited Project Start controller/default-tier wording was not changed.
The restricted foundation exercise therefore reports a document candidate,
not successful tracked bootstrap. Existing native graph tests supply separate
bounded compatibility evidence. Global activation and future arbitrary agent
behavior remain outside these observations.

## Reproduce the retained behavior oracle

RED output contains original trailing spaces from unittest's failure display.
It is retained losslessly as JSON content plus its original SHA-256 so Git's
source whitespace check stays useful without rewriting evidence or suppressing
the check. Original raw logs remain in the originating fixture.

In a disposable directory, copy fixtures/behavior/test_slug.py to tests/test_slug.py
and either before.py or after.py to slug.py. Run
python3 -m unittest discover -s tests -v. Before should execute six tests and
fail on intended assertions; after should execute six and pass. Keep that
expected negative separate from a failing acceptance test.

## Independent acceptance and release boundary

Fresh whole-plan acceptance: PLAN-PIPELINE-20261015-9c73e1ab, accepted plan
SHA-256 254c186b5a485e9f1a106d23e92d556a0280a16d42a0fca72435c1b09fbe545a.
A different fresh whole-result reviewer checks the exact candidate and original
evidence before canonical integration. Its actual verdict is recorded after
completion; this document does not issue its own independent approval.

Canonical integration must recheck baseline HEAD and clean status, apply only
the reviewed owned paths and use a normal commit with hooks. No global skills
install, push, production operation or business-effect claim is part of delivery.
