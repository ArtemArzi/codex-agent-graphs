# CAG: native Claude Code adaptation before installation

## Outcome and scope

Adapt the canonical Codex Agent Graphs source for native personal Claude Code skills, roles and runtime, then install that reviewed projection in the existing WSL profile. Keep AGENTS.md as the instruction source. Support the CLI and prepare the same profile for Desktop WSL; actual Desktop discovery and model execution remain deferred because the user has no active subscription. The user explicitly clarified that source adaptation comes before downloading/installing CAG, rather than copying an unadapted Codex pack.

This is substantial cross-subsystem engineering: packaging, role projection, runtime discovery, safe installation and capability inventory. Obtain a fresh whole-plan acceptance before code, and a different fresh whole-result acceptance. Native skill-only Task Delivery; no graph/controller is needed to record these reviews.

Canonical source: /home/artem/projects/codex-agent-graphs, clean HEAD ae4d048 at research entry. Work's existing task owns personal deployment state and references this source change; no changes to CWS, its release, pending work or sync policy. No model calls, account login, new subscription, permission expansion or publication.

## Research basis

- Existing CAG plugin manifests declare 0.1.2 and root skills discovery. The installed local plugin is 0.1.1. Its cache is preserved; it is not the source for adaptation.
- install.py has only Codex environment selectors. Its skills/runtime directory transaction already provides locks, source/target preimage checks, staging, readback, backup and conflict-preserving rollback.
- claude_agents_sync.py projects 13 top-level canonical roles plus a legacy explorer template. Seven policy-native roles are absent from the canonical projection. Claude models are independently specified in model-routing.toml; Codex models must remain unchanged.
- Project Start dependencies/maintenance and Task Delivery inventory append Claude roots after Codex roots. Tests currently encode that legacy order; the new requirement deliberately changes Claude's default selection while preserving Codex behavior and explicit overrides.
- Task Delivery inventory reads config.toml, not Claude JSON. It must report Claude MCP/agent/hook names without exporting credentials, values or command arguments.
- Core maintained engineering selection is the current install.SKILLS tuple (41 entries at entry), distinct from all 67 source skills/product packs. Default installation must not imply every pack. agent-graph-builder also requires a real skill-creator dependency; an installed plugin alone is insufficient for Desktop WSL.
- Official ordinary skills: https://code.claude.com/docs/en/skills. Native personal skills and subagents have supported discovery paths; plugin distribution is a separate namespace: https://code.claude.com/docs/en/plugins and https://code.claude.com/docs/en/sub-agents. AGENTS loading: https://code.claude.com/docs/en/memory#agentsmd. Desktop WSL limitations were verified in the preceding phase.
- Existing profile has four generic agents, six rules, four original personal skills, research/browser-modes added by this task, and seven MCP definitions. The previous offline setup is independently accepted. Native CLI diagnostics can write schema/onboarding state, so avoid treating CLI inspection as read-only.

## Intended design

1. Add one explicit Claude-only plan/install/verify entry point in canonical scripts. It generates native projection bytes from maintained source and never calls the Codex full installer on a Claude home. No settings, credentials, MCP JSON, plugin registries, AGENTS.md or CLAUDE.md writes from this generic installer.
2. Reuse the existing directory transaction for all owned units: individual selected skill directories, sibling agent-graph-runtime, and a dedicated agents/cag directory. Keep private agents and unrelated skills as sentinels. Use a managed provenance manifest inside the runtime; unmanaged name conflicts require explicit bounded adoption. For this user's two known overlaps research and verification-loop, backup and adopt after comparing current content. Do not silently overwrite future private drift.
3. Native projection supplies /skill invocation, exact installed skill location, native runtime location and canonical-to-Claude role aliases. Native agents use cag- prefixed names to avoid shadowing private generic agents. Plugin agents retain their plugin namespace. Keep canonical graph role IDs in deterministic protocols; actual provider/agent evidence remains explicit, never misrepresented as a Codex/Sol receipt.
4. Extend Claude role generation to all canonical policy roles and remove the duplicate explorer source. Preserve existing explicit Claude mappings. For previously unmapped roles use explicitly declared inherit projections, with appropriate medium/high effort; transfer explorer's existing Sonnet/high mapping unchanged. This preserves the user's selected Claude model instead of guessing equivalence to GPT. Codex policy model/effort and role templates remain unchanged. Leaf roles must not receive Agent/Task spawning tools; Bash does not constitute OS read-only isolation.
5. Native projection for agent-graph-builder uses the real skill-creator dependency, copied from an explicitly supplied installed source including supporting files and licence. Its Claude guidance excludes OpenAI-specific UI metadata requirements. Preserve the mandatory dependency contract; never invent a missing skill. No runtime dependency on a Codex home after copying.
6. Add one small shared host-path helper in the existing runtime. In Claude context, prefer the self-located/explicitly configured Claude skill root and do not silently select Codex copies. Codex default behavior and explicit caller selection remain compatible. Integrate the three existing discovery paths. Keep released graph identities, schemas and legacy project-state paths such as .codex/task-delivery unchanged.
7. Extend inventory for native Claude configuration metadata: personal/project skills, Claude roles and registered MCP/hook/plugin names. Parse only known metadata, never include raw JSON, headers, env values or full commands in output. File presence remains a candidate, not a live capability claim.
8. Document native and plugin modes, exact scope, role aliases, source-of-truth and update/rollback. Keep one generator/projection, not a second handwritten copy of CAG methods. Update applicable graph-builder guidance for native Claude metadata without creating new workflows.

## Installation and MCP phase

After source tests pass, install native core, required skill-creator and generated roles into /home/artem/.claude. Preserve the previous backup. Allocate at most 128 MiB of staging and 256 MiB of owned native backup history; stop rather than evict unknown data. Reuse existing source/runtime stores, no extra clone/worktree. Unknown/private drift is a stop, not an overwrite.

The old CAG plugin remains on disk but should be disabled only by its exact enabledPlugins key after native adoption, with a private preimage and CAS. This prevents the old plugin controller from competing with the adapted native installation. Preserve every other plugin, permissions, model, sandbox, auth and MCP definition. This local switch is distinct from the generic installer and does not run Claude/login.

Then validate that the new CAG inventory sees the already configured seven Claude MCP names. Reuse existing Context7/search/headless server installations rather than downloading duplicates. Where a local, credential-safe metadata handshake is possible without Claude/model/login, verify it and close owned clients. Do not exercise Google account login, Pencil GUI, sends or external writes. Any genuinely missing runtime/provider is recorded explicitly; new credentials or a new account remain outside scope.

## Acceptance and checks

- Source/package: every required canonical role projects deterministically; Codex model/effort stays equal; plugin/native aliases are distinct and resolvable; mandatory skill dependency and installed runtime are independent of Codex paths.
- Safe installation: fresh synthetic home, repeat, read-only target plan/verify, explicit adoption, private sentinels, active lock, symlink rejection, late failure with rollback, concurrent edits retained and no partial successful result. Test the complete directory transaction including agent directory.
- Host discovery: machine containing both profiles selects Claude under Claude markers/self-location, Codex otherwise, respects explicit roots and custom Claude home. Capability inventory redacts synthetic secret sentinels and reads the correct provider metadata.
- Runtime smoke: installed controllers/helpers execute from another CWD without CLAUDE_PLUGIN_ROOT; init/resume and representative bounded rejection paths retain released graph semantics. No model request or invented acceptance receipts.
- Regression: focused Claude packaging/host/install tests, source dependency checks and scripts/check_all.py once after integration. Keep optional native Claude advisory validation out of this no-model/no-config-side-effect gate and report any skip.
- Actual deployment: record exact source/target manifests, backup, adopted overlaps, changed paths, preserved profile fields/Codex files, MCP metadata and all cleanup. Obtain fresh whole-result acceptance for the complete source plus installation outcome, with targeted delta revalidation for corrections.

Stop on source/target drift, symlink ambiguity, unknown lock/backup, unsafe metadata leakage, need to weaken checks, unsupported role/model contract or unavailable required independent review. Continue independent safe preparation. No public push, release or client change is implied.

## Next step

Source implementation and native offline deployment are independently accepted. Actual Desktop WSL discovery and model behavior remain deferred until access returns. Exa availability remains pending after a public endpoint access denial. Persist personal deployment evidence only under the existing Work task or private profile backup.


## Implementation and acceptance evidence

- Fresh whole-plan PASS: CAG-CLAUDE-NATIVE-PLAN-20261025-7D31, before implementation. All source changes remain local on base ae4d048; no public push/release.
- Implemented explicit native installer/projection, all 20 policy roles, shared Claude-first host paths and secret-safe Claude capability inventory. Core selection is 41 skills plus real skill-creator, runtime and agents/cag; private profile and Codex configuration are outside the generic installer.
- Focused suite initially 37 tests; a result-review finding added the 38th regression across the three Claude suites. Full scripts/check_all.py passed after integration and again after repair. Optional native CLI advisory was skipped to avoid profile migration side effects. Source graph identities/schemas and Codex role models/efforts remain unchanged.
- Whole-result reviewer found the copied creator still directed new skills into Codex and a graph-builder step unconditionally required OpenAI UI metadata. Repaired native creator body/default paths/examples and conditioned shared graph-builder metadata on provider. The new test installs realistic source instructions, verifies Claude output paths, source preservation and source-less repeat verification. Reviewer independently demonstrated that disabling the fix makes this test fail.
- Actual native install and subsequent managed repair passed; source-less verify passed. Exact deployment/backup/protected-file evidence belongs to the Work task, not this public source. Existing personal agents/rules/skills and AGENTS.md are preserved. Codex configs matched the earlier checkpoint; one Windows-host Codex config changed later outside every declared task writer target. Its cause is unproven, its current bytes are preserved and the precise limit is recorded only in the personal deployment owner. No blanket final claim of unchanged host configuration is made. Only the old CAG plugin flag was disabled separately after native installation.
- MCP plan delta PASS: CAG-CLAUDE-NATIVE-PLAN-DELTA-20261025-94B2. Existing Context7/Exa bunx startup lacked runtimes. Anonymous official Context7 initialize/tools-list passed and only that local definition was switched to tested HTTP under private backup/CAS/readback. Exa public endpoint denied access with403/Cloudflare1010; its definition remains unchanged/pending. No credentials were transmitted, no search/model calls/login ran. Other provider definitions are preserved.
- Native agent discovery is unverified: installed claude agents --json lists sessions, so its empty output was rejected as loader evidence. Recursive agents are documented; actual Desktop/Claude consumption, model routing and skill effectiveness require a later real session.

Fresh whole-result PASS: CAG-CLAUDE-NATIVE-RESULT-20261025-A84F. The reviewer independently checked source/installed bytes, 37 original focused tests, 13 native tests after repair, a mutation control that catches the original creator defect, private semantic config deltas and current preservation limits. No material repair remains. Scope is canonical adaptation and actual offline deployment; real Desktop/native model discovery, external Exa availability and attribution of a later unrelated Windows config change are excluded.

The exact 15-file temporary edit staging was removed only after matching canonical source and independent acceptance. Canonical source, verification evidence and private backups remain. Source changes are uncommitted local work, with no public push/release. Personal Work report delivery is a separate standing native workflow, not CAG publication.

## Publication continuation, 2026-10-27

The historical acceptance above describes the original offline task. A later
explicit owner instruction authorizes consolidating all repository changes and
publishing one reviewed commit, including the local chat-coordination and
software-factory work and customer-research-prep. Reconciliation against remote
5cb2903 found the native implementation already published in 0ac1ac1; retain the
newer remote installer and UI/UX pack support rather than replacing them with
the older local copy. This document adds its historical acceptance context.
Private profile evidence and credentials remain outside the source tree. The
combined result receives fresh integration acceptance; actual Claude sessions
and Desktop discovery keep the limits stated above.
