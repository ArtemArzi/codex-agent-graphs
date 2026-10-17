# Matt companions: interviews and development quality

Status: source implemented and checked; awaiting result review/delivery, 2026-10-17.
Owner: this task document.

## Requested outcome

The user authorized adding the proposed non-overlapping Matt Pocock practices
to the personal global skills pack, making them discoverable and combining
them with Project Start and Task Delivery. Priority: questions that develop
an unclear product/task into explicit decisions. Exclude duplicate research,
implementation, TDD, handoff, review and debugging pipelines.

## Baseline and sources

- Canonical source: `/home/artem/projects/codex-agent-graphs`, clean HEAD
  `ca99989` at admission; candidate: `/tmp/codex-skills-matt-20261017`.
- Fresh upstream is `9816146cf9b19860acc191a89cf314bf9cd7231f`.
  Local source and upstream diverged: retain both local website/pipeline commits
  (`b570901`, `ca99989`) and five incoming business/agent/documentation commits.
  Candidate is a non-destructive merge with both histories preserved. Only the
  two README files conflicted: keep the new onboarding and link preserved
  website and development-pipeline capabilities. Prepared integration baseline
  tree: `699d6ef23fcd05216a1d5ff0d0ec6098494db0e8` (no runtime/skill changes).
- All 35 managed source trees matched WSL/Desktop at the preceding inventory.
  Recheck live preimages and canonical HEAD before delivery.
- Existing owners: grilling, domain-modeling, Project Start intake,
  Task Delivery capability routing/testing/review, Development Recovery's
  diagnostic reference, manifest-aware `scripts/install.py`.
- Primary upstream: https://github.com/mattpocock/skills at observed main
  `49dd158d1076134a641b33efb035946536778336`.
  Read grilling, grill-me, grill-with-docs, improve-codebase-architecture,
  diagnosing-bugs and code-review; preserve source attribution and MIT notices.
- Existing review confirms interviews, hypothesis comparison and both review
  concerns already exist. These are refinements, not missing entire disciplines.

## Implementation

1. Extend existing grilling with focused clarification and deliberate product
   discovery. Keep short rounds, dependency-aware follow-ups, no total-round
   cap, existing answers, meaningful stopping criteria and one decision owner.
   A clear small fix must not start a full interview. No universal final
   approval, compulsory subagents, new controller or fixed question quota.
2. Add discoverable native `grill-me` (explicit interview entry) and adapt the
   installed explicit-only `grill-with-docs` into canonical delivery for
   interview + domain decisions. Both reuse grilling; do not fork its logic.
   User explicitly requested agents see/use these in combination. Keep unrelated
   explicit-only skills and settings unchanged. Route product discovery and
   documentation mode through Project Start/Task Delivery descriptions/references.
3. Add `improve-codebase-architecture` as an on-demand survey of demonstrated
   architecture friction, prioritizing actual change history/affected scopes.
   Reuse codebase-design, respect existing architecture, permit no-op, compare
   evidence/cost/benefit, hand selected work to existing Task Delivery. No
   mandatory HTML/browser/parallel agents or automatic repository refactor.
4. Extend the existing diagnostic reference with practical ways to build and
   minimize a repeatable check of the exact symptom, rechecking the original
   scenario after correction. No second diagnosing-bugs skill or duplicate loop.
5. Clarify separate evidence for requirements and project standards within
   existing review; retain proportional reviewer count and include the actual
   uncommitted/staged/committed candidate. No standalone code-review skill.
6. Register exactly three new managed skill trees, update applicable validation,
   packaging and existing English/Russian maps; keep graph/runtime identities,
   roles, models, hooks, authorizations and other plugins unchanged.

## Verification and delivery

- Meaningful packaging/installer tests: new tree resources/metadata delivered,
  auto-discovery policy present, drift/concurrent-edit protections retained.
- Skill Creator validation for revised/new skills, `git diff --check`, and the
  complete required `python3 scripts/check_all.py` suite.
- Independent forward checks on bounded fixtures: ambiguous product interview
  (next round depends on first answers), clear local edit (no full interview),
  architecture survey (real change friction vs speculative refactor), diagnosis
  and review of a diff with a missed requirement. Use raw scenarios without
  revealing expected answers; preserve scope/artifacts and report limitations.
- Fresh whole-plan and different whole-result acceptance: concrete reason is
  coordinated global workflow routing, installer membership and live dual-home
  delivery, whose mistakes affect future projects rather than one local artifact.
- Before live write, freeze exact changed paths, source/tree manifests and live
  preimages. Use the existing skills-only installer with backups/CAS readback;
  do not copy whole configs or overwrite foreign drift. Verify protected
  settings hashes and repeat install as a no-op.
- Verify native skills/list discovery in fresh WSL CLI and Windows Desktop
  processes; installation hashes alone are not discovery or real project effect.
- Preserve canonical source alignment via narrow reviewed delivery. Repository
  publication only if covered by the requested pack update; do not publish
  unrelated content. Record actual local/remote/install/discovery outcomes here.

## Progress

- Read-only inventory/research and independent bounded recommendation review
  completed before implementation.
- Fresh plan acceptance: `PLAN-MATT-20261017-6e74b2a9`; reviewer highlighted
  checking every default-installer tree/runtime for unrelated live drift.
- Remote/local divergence reconciled in the isolated candidate. Targeted plan
  revalidation passed: `PLAN-MATT-20261017-6e74b2a9-BASELINE-699d6ef2`.
- Added exactly three native discoverable entries; extended grilling and the
  existing Project Start/Task Delivery routes and diagnostic/review references.
  Default engineering membership is 38. No duplicate operational pipeline added.
- Fresh upstream clone confirms Matt main is still
  `49dd158d1076134a641b33efb035946536778336` (2026-10-09). Compared 13 existing
  installed Matt entrypoints with current sources; retained local adaptations
  and unrelated explicit-only policies. New changes are selected methods above,
  not a wholesale replacement. Comparison: `/tmp/matt-installed-upstream-comparison-20261017.json`.
- Installer suite: 37 tests PASS (`/tmp/matt-install-tests.log`). New integration
  case proves legacy explicit-wrapper backup, complete three-tree/resource
  delivery, protected settings and repeat-install no-op with unchanged mtimes.
- Full `python3 scripts/check_all.py`: exit 0, `All workflow checks passed.`
  Log: `/tmp/matt-check-all-20261017.log`. Skill Creator validation passed for
  all selected packages; feature whitespace check against baseline tree passed.
  Incoming historical NMT/last30days whitespace is outside this feature delta;
  no broad whitespace PASS is claimed.
- Independent product forward-use: three actual dependent question rounds,
  existing answers reused, then grill-with-docs/domain-modeling saved agreed
  terms/rules in the existing fixture task owner. No implementation or external
  action. Fixture: `/tmp/codex-matt-forward-20261017/interview/task.md`.
- Independent quality forward-use: clear label edit verified without an
  interview; architecture survey used two historical changes and preserved an
  intentional adapter; exact duplicate-request symptom reproduced and traced;
  review found two SPEC violations in an unstaged candidate. 13 subprocess
  outcomes were checked against expectations. Raw source/evidence/report:
  `/tmp/codex-matt-forward-20261017/quality-evidence.json` and `quality-result.md`.
  These are synthetic bounded uses, not production effects or measured
  automatic invocation rates.
- Skills-only live plan reports exactly the seven authorized changed/missing
  trees per home; every other managed skill/runtime is in sync. Live preimages
  and 44 protected config/global-policy/role files captured in
  `/tmp/codex-skills-matt-preimages-20261017.json`. Recheck before write.
- Independent source checkpoint accepted:
  `RESULT-MATT-SOURCE-20261017-9d28c6f1`; reviewer checked the complete 31-path
  feature delta and reran both relevant installer integration tests. Live
  installation/discovery is pending and is not covered by this source receipt.
- Next: freeze/deliver candidate locally, skills-only install with backup/CAS,
  readback/idempotence and fresh native WSL/Windows discovery, then return this
  evidence to the same whole-result reviewer. GitHub publication and actual
  project effects remain unclaimed.
