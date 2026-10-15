# Independent forward delivery result

This is an executable candidate result for parent evaluation, not acceptance,
controller completion, deployment readiness or product-effect proof.

## Candidate behavior

Fixture: `work/forward/behavior`, initial clean HEAD
`f862e1ad3a8c677891ca10a6f4821f0f1b71e36a`, Python 3.12.3.
Changed only `slug.py`, `tests/test_slug.py`, and notes under `docs`.
No commits, installation, network, external operations, controllers or child
agents. Candidate/canonical skill sources were read-only.

`normalize_title` now returns `'-'.join(_to_lower(value).split())`.
The signature, lowercase behavior, edge trimming, empty/all-whitespace result
and non-whitespace punctuation are preserved; whitespace groups become one
separator. No runtime dependency. The pre-existing private helper was retained:
removing baseline structure did not simplify this one-line change.

Source hashes in `behavior/docs/evidence/candidate-source.json`:
- slug.py: ae0a1c089ed2073eb71d29ac985fd62e2d81c845b6a5989063e7bdcfd79e4262
- tests/test_slug.py: 5771e77219818f9fe7779018475f2a1c30d583fc71aa8b223b575da9c44b141f

## Evidence and commands

All commands below ran from the fixture directory. `docs/evidence/runs.json`
records UTC timestamps, command, purpose, actual/expected exit and matching.

| Step | Command | Actual outcome | Original evidence |
| --- | --- | --- | --- |
| Baseline | `python3 -m unittest discover -s tests -v` | exit 0, 1 test PASS | baseline.log |
| RED, before source edit | same | exit 1, 6 tests executed; 6 intended assertion failures, including hello---world and retained tabs | red.log |
| Minimal GREEN | same | exit 0, all 6 tests PASS | green.log |
| Final after simplicity review | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` | exit 0, all 6 tests PASS | final.log |
| Source whitespace check | `git diff --check` | exit 0 | diff-check.log |

Tests use literal independent expected values through the public function.
They cover repeated spaces, tabs, mixed/newline/Unicode whitespace, empty and
all-whitespace, single word with boundaries, lowercase, punctuation preservation,
and the retained original simple case. Actual RED/GREEN establishes the new
oracles can detect the original error. No coverage percentage was measured;
the project declares no percentage gate. No unsupported input contract was added.

`docs/evidence/baseline-slug.py.txt` and `baseline-test_slug.py.txt` preserve
original bytes. `candidate.patch` is the exact owned source/test delta.
Local challenge research used Python's builtin str.split documentation, retained
in `str-split.txt`: whitespace splitting groups delimiters and omits edge tokens.
Compared regex/manual iteration with the standard builtin; selected simplest
contract-compatible split/join. No forbidden external research was attempted.

## Applied guidance and continuation

Read and applied candidate Task Delivery SKILL with testing-and-review,
code-simplicity and project-state references; candidate Deployment SKILL,
workflow.yaml, check-placement, checks-and-evidence and handoff; candidate Product
Care SKILL, follow-up and handoff. Candidate `skills/tdd-workflow/SKILL.md` is
absent (observed failed read); used the available installed
`/mnt/c/Users/artem/.codex/skills/tdd-workflow/SKILL.md` companion and active
Superpowers `test-driven-development/writing-good-tests.md`. No skill was installed.

`behavior/docs/TASK.md` owns compact request, governing rules, pre-code plan,
first false assumption, local research, TDD, simplicity and current next step.
`behavior/docs/DEPLOYMENT.md` extends the existing native facts with a concrete
local command lane, exact subject/evidence, check IDs/kinds/runner/environment/
prerequisites, source recovery boundary and explicit target gaps. No duplicate
controller or release registry was introduced; no new build or deploy command
was invented for this targetless fixture.

The same runbook contains the bounded Product Care handoff: expected consistency
of imported titles, actual user episode to establish, missing deployed identity,
unknown permitted real source/owner/window, meaningful next trigger and comparison
conditions. Collection and scheduling have not occurred. Target-version readback
and real public-route checks are explicitly NOT RUN because no target/operator
exists and no release is authorized. Application and effect remain unknown.

Parent owns independent artifact evaluation; no leaf review or acceptance claim.
Next allowed action is inspect these files/logs and evaluate candidate behavior.
A later real release/observation needs its actual native target/operation,
authority, fresh target checks and separately permitted meaningful data/window.
