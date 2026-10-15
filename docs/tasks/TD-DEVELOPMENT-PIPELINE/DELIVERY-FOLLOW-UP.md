# Native release facts

This synthetic package has no configured production target or release operator.
Source unit tests can run locally. Required target checks are version readback
and the public user route after activation; neither can run without a target.
A planned source build is not an activated version. The intended improvement
is that imported ticket titles normalize consistently. Its real application and
effect need a permitted source and meaningful observation window; neither exists
in this fixture. No external action or schedule is authorized.


## Prepared local path and release handoff (2026-10-15)

Preparation only. Lane: local source verification for this pure Python utility.
No configured build, artifact, target, native activation command, release journal,
operator or CI trust bridge exists. Inventing a deployment command or adding a
platform would exceed the known facts. This local path is usable now:

```bash
cd /mnt/c/Users/artem/Documents/Codex/2026-10-15/https-github-com-michael-denyer-pstack/work/forward/behavior
sha256sum slug.py tests/test_slug.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

Exact source: baseline HEAD f862e1ad3a8c677891ca10a6f4821f0f1b71e36a plus
uncommitted slug.py/tests delta, bound by evidence/candidate-source.json and
candidate.patch. No artifact or activated version has been produced.
Original evidence: evidence/runs.json, baseline.log, red.log, green.log,
final.log and diff-check.log. The author inspected actual logs; no native release
evidence verifier is configured. Future operator must inspect originals and
candidate/toolchain freshness under its eventual native trust policy; this note
cannot authorize reuse as an external release PASS.

| Check ID / kind | Subject / runner / environment | Milestone and prerequisites | Result / next condition |
| --- | --- | --- | --- |
| source-unit / unit regression | exact slug.py + tests; Python 3.12.3 unittest; local fixture | source; AGENTS/QUALITY, no dependencies or services | 6 tests PASS in green.log/final.log; revalidate changed source/recipe/runtime inputs |
| source-diff / whitespace check | candidate tracked delta; local Git | source; final owned source/tests | diff-check.log; current result in runs.json |
| target-version / identity readback | eventual activated version; native operator unknown | postactivation; configured target, bound artifact/version, explicit release authority | NOT RUN; release readiness unresolved |
| target-public-route / public user route | imported ticket title through actual application; runner unknown | postactivation; actual route, authorized data/scenario, fresh version readback | NOT RUN; local function checks cannot replace this |

No toolchain, configuration, data model or permanent quality policy changed.
No browser/Docker/integration/load suite applies to this pure function fixture;
no universal coverage requirement was added. Check placement is local now;
no unchanged suite is repeated solely for switching skills. A future artifact
requires artifact-specific verification and actual target checks remain fresh.

Release remains pending: identify actual release operator/target, native recipe,
artifact/version identity, trust policy and compatible recovery path; obtain
release authority, then perform native activation and required fresh target
checks. Until then local source readiness is the bounded claim.
Recovery: original source/tests are retained in evidence/baseline-*.txt and Git
HEAD. Restore only owned paths in a separately authorized future rollback; do not
reset the repository or assume that source restoration changes an active target.
Any later live rollback must follow the target's compatibility/native procedure.

## Product Care follow-up (pending, no collection or schedule)

Question: after an actual release, do imported ticket titles containing repeated
spaces/tabs consistently appear with one hyphen between words, without changing
case normalization, empty-title handling or punctuation? Expected benefit is
consistent imported titles; no measured adoption, time saving or business effect
is claimed.

Episode: a person imports ticket titles through the real product and uses the
normalized result. Person/role, application route, actual target and deployed
version are unknown. First establish activation through the target checks above,
then establish that this episode used that version. Release is not application.

Permitted evidence currently consists only of local synthetic source/tests;
no external source is permitted. Real import records, logs or observed episodes
would need a specifically permitted bounded source, fields, sensitivity/load
limits and an identified owner. No such source or owner exists here.

Next observable trigger: owner provides release/target identity and authorizes a
bounded source of actual import episodes. Select a meaningful observation window
from actual import frequency and adoption delay, rather than inventing a fixed
number of days or sample threshold. Compare compatible exposed versions/episodes
containing whitespace with a relevant baseline; confirm denominator and event
semantics, and inspect errors, empty results and manual correction effort.
Account for later releases and changes to import/instrumentation before attributing
effect. With no exposure or source, outcome remains unknown, never zero defects.

Product Care can read this same task/release record when that trigger is met.
Return any verified new software defect through Task Delivery with reproduction;
reuse unchanged technical acceptance under its owner. No new task, message,
automation, reminder, data read or release was created by this handoff.
