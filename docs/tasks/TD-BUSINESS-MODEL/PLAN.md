# Business Model pack delivery

Status: independently accepted for publication; installed skills verified.
Date: 2026-10-18. Base: ad402738886d1f1c6fa0a94256949bde36aeb08c.

## Accepted outcome

The user approved the inline proposal: one Business Model pack with three new
skills (business-model-design, business-economics, process-to-product), extending
business-work as the shared entrypoint. Two entrances: find a business opportunity
or investigate a recurring client process. Russia is the default target market;
foreign cases are references, not evidence of Russian demand/pricing/channels.
Reuse current research, NMT, marketing, hypothesis checking and engineering owners.
Create and verify the pack; commit and publish reviewed work to the user's GitHub
repository. The accepted plan includes packaging and skills-only installation;
preserve host settings and existing local edits. No market outreach, spending or
client/product deployment is authorized by this task.

## Baseline and isolation

Canonical checkout has four unrelated dirty chat-coordination paths. Candidate is
an independent clone in /tmp/codex-business-model-20261018 from the committed base;
origin main was observed at that same SHA. Preserve the original checkout and its
dirty bytes. Recheck remote before publishing; reconcile any incoming commits in
the candidate before delivery. Shared install paths require drift inspection and
the existing installer lock/preimage/backup/readback mechanisms. No settings,
policies, models, credentials or browser profiles are in installation scope.

## Complexity and review

New cross-skill contracts, shared router ownership and pack installer integration
cross existing subsystems. Use fresh task_plan_reviewer before implementation and
a different task_result_reviewer after the candidate and evidence exist. Root is
the only implementation writer. One independent bounded forward test is justified
because instruction quality cannot be established by static validators. Children
are leaves and read-only except writing their own disposable scenario outputs.
Use native review without introducing a graph/controller for the new business pack.

## Implementation

1. Author concise Russian SKILL.md and native openai.yaml for the three skills.
   Each skill is usable directly and has its own result contract. Keep substantial
   worked examples/forms in focused references. Write original guidance informed
   by the completed source research; do not vendor third-party packs or NMT canon.
2. Add business-work/references/business-model.md for both entrances, owner
   constraints, evidence-aware decision synthesis and return from delivery. Add
   references/market-context.md for Russian target evidence versus foreign
   references; all three new skills can link it. A user-selected different market
   remains respected. Extend existing router pointers conditionally, preserving
   its process/adoption/CRM behavior and existing task state owner.
3. Add products/business-model with version 0.1.0 pack.json, README, SOURCES,
   VALIDATION and synthetic scenarios/results. Managed members: business-work and
   the three new skills. Reused capabilities are optional, not vendored. In an
   environment without NMT/marketing, perform a bounded ordinary analysis with
   disclosed limits, without claiming special methodology or auto-installing it.
4. Register --skills-only --pack business-model in the existing shared installer.
   Reuse source snapshot, duplicate-name detection, locks, backups and readback.
   Verify clean installs, overlapping packs, repeat-install no-op, source/target
   drift and preservation of protected settings. Do not redesign the installer.
   Update Business Automation to 1.0.1 and matching installation metadata because
   the shared business-work source changes; preserve upstream pins and provenance.
5. Update bilingual root navigation, docs index, installation/workflow guidance,
   and changelog as needed. Keep product/source ownership and ordinary engineering
   defaults intact. Add focused packaging/integration tests to existing unittest
   infrastructure; no new financial execution engine or graph runtime.

## Behavioral contract

- Model: buyer/user/payer, value, channel, delivery, revenue/cost dependencies,
  alternatives and falsifiable critical assumptions; a canvas alone is not proof.
- Economics: units, source/date/period/currency, fixed and variable costs, owner
  labor, acquisition, setup, support, cash timing, capacity, scenario sensitivity;
  unknowns are not zero, one order is not mature LTV, no universal SaaS thresholds.
- Process-to-product: independent clients, common core, customization/exceptions,
  repeat delivery economics and founder dependence; retain an individual service
  when appropriate. A paid bespoke pilot does not prove standardized-product demand.
- Evidence: distinguish reference, hypothesis, observation, use, payment,
  repeatability and business effect. Keep results scoped; no simulated interviews
  as evidence or global validated=true. Predeclare experiment criteria; an
  inconclusive channel test does not automatically falsify demand.
- Early bounded technical experiments are permitted. A full validated business
  model is not a prerequisite for a useful technical spike. Business decisions and
  external execution still follow user authority. No blanket universal chain.

## Verification and delivery

Run quick_validate on new/changed skill entrypoints; validate UI metadata and local
links. Run focused installer/package tests, then python3 scripts/check_all.py as
required by repository AGENTS. Exercise synthetic requests independently, including
Russian/foreign evidence separation, loss-making delivery despite revenue, bespoke
versus product demand, service-first choice, missing data and early feasibility
prototype. Use invented inputs explicitly labelled as synthetic; no real commercial
pilot is claimed. Retain actual evaluator outputs and reconcile findings.

After different whole-result acceptance, commit exact owned paths. Publish only
the reviewed candidate after remote reconciliation. Inspect current installation
drift first; install only the reviewed four-skill pack using existing skills-only
commands, then verify hashes, protected settings, idempotence and fresh native
discovery where available. If native discovery is unavailable, report that layer
unverified. Never overwrite unknown installed drift; reconcile exact source/version
or leave that installation step pending while delivering the verified source.

## Ownership and exclusions

Owned: skills/{business-model-design,business-economics,process-to-product}/**,
skills/business-work/SKILL.md and its new references; existing installation metadata;
products/business-model/**, Business Automation version/documentation; narrow
scripts/{business_pack,install,check_all}.py integration; focused tests and named
documentation navigation/changelog/task record. Existing graph identities, model
policy, source NMT, marketing package, credentials, production and unrelated dirty
chat-coordination files are excluded.

## Evidence and next action

Source research and ordinary proposal review completed in the prior phase. This
plan carries the approved outcome into implementation; it does not reuse the old
research verdict as implementation acceptance. Implementation and independent
acceptance are recorded below. Publish the accepted source; the next use-stage
is a real business-process pilot. Synthetic checks do not replace that pilot.

## Implementation evidence

- Whole-plan PASS: business_model_plan, receipt PLAN-BUSINESS-MODEL-20261018-7F93.
  Requirements carried forward: pack-specific validation, both installation
  orders, explicit live drift reconciliation, historical baseline preservation
  and targeted post-install closure with the same whole-result reviewer.
- Three original skills, shared market/model references, optional owner routing
  and Business Model 0.1.0 implemented. Business Automation 1.0.1 updates the shared
  router without changing NMT/last30days pins. Router UI metadata was updated as
  a bounded integration edit within the accepted shared-router scope.
- Skill validators passed. Nine focused package/installer tests passed; full
  python3 scripts/check_all.py passed with exit 0. A first race-test fixture used
  nonexistent stage_directory; corrected to the existing shutil.copytree staging
  seam already used by the baseline tests. No implementation contract was relaxed.
- Independent forward pass completed A-E. Initial economics case repeated the
  reference example; strengthened current B input and reran only B as B2 with
  different values. Actual responses are in product validation/FORWARD-RESULTS.md.
  D tests choosing a technical experiment; no document extraction is claimed
  because the raw fixture does not include documents.
- Live baseline Business Automation 1.0.0 plan: all eleven installed skills match
  the committed base. New pack plan: only shared business-work differs as expected,
  other three skills are missing. Before installation compare every installed
  source again to that known base; use supported Business Automation update from
  this candidate, which should change only business-work, then install the new
  pack with drift refusal. Preserve unknown changes if any appear.
- Canonical dirty chat-coordination checkout is untouched. No controller was
  admitted; native independent acceptance owns this delivery.
- Whole-result source PASS: business_model_result,
  RESULT-BUSINESS-MODEL-SOURCE-20261018-C41E, fingerprint
  c653452fc7108abccc7a26a672fe83a939f6a06400fa6f261d994fffc6c127b4.
- Live supported install updated only business-work in Business Automation1.0.1
  after known-base comparison and backup, then installed three new Business Model
  members. Both selected homes resolve to the pre-existing shared physical root.
  verify ok; repeat install all in-sync with no backup. 5,595 protected files and
  four foreign dirty sources retained their pre-install hashes.
- Fresh native WSL app-server skills/list forceReload finds each managed member
  exactly once, enabled, without owned loader errors and with matching prompts.
  Restricted startup could not respond; an authorized local startup succeeded.
  Separate fresh Windows Desktop UI loading and automatic selection remain untested.
- Original installation and preservation conclusions are recorded in the task
  history; their temporary raw files were lost during the host restart.
  Product VALIDATION records this limit and the fresh checks below.
  No model requests, market contacts, client execution or expenses occurred.

## Restart recovery and fresh verification

- The host restart removed the uncommitted temporary candidate. Recovered only
  completed file-change events from this task into a new isolated clone.
- All 34 files reproduce the source review fingerprint c653452fc7108abccc7a26a672fe83a939f6a06400fa6f261d994fffc6c127b4
  when the two subsequent evidence documents are substituted with their reviewed
  versions. Skill, installer and test bytes are unchanged from accepted source.
- Repeated the complete check_all gate (exit 0), nine focused tests (all PASS),
  installed-byte verify (ok), supported repeat install (all four in-sync,
  backup=null), and fresh WSL native discovery (one enabled entry per skill).
- The original pre-install hash map cannot be rechecked after its loss. A new
  current-state snapshot checks preservation through repeat install/publication;
  it does not replace historical pre-install evidence.
- Fresh snapshot readback: 5,598 of 5,599 protected/foreign files are unchanged,
  including all four foreign repository files. The shared config.toml changed
  during the observation window; attribution is unknown. No-op reported no
  writes and this task does not edit or restore that file. Full current settings
  preservation is not claimed.
- Independent final closure PASS: RESULT-BUSINESS-MODEL-CLOSURE-20261018-C284EBDC-R1.
  Scope: source/package publication readiness, installed skill bytes and bounded
  discovery. Full host-settings preservation remains unverified for the stated
  config change. Commit/push may proceed; remote delivery is confirmed separately.
