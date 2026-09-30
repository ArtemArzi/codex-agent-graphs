# Sol 6.1 routing verification, 2026-09-30

Independent plan acceptance: `SOL61-PLAN-20260930-b9146f-pass`.
Independent result acceptance: `SOL61-RESULT-20260930-8b61-pass`.

- Full `python3 scripts/check_all.py`: PASS after the final sync correction.
- Sync tests: 9 PASS, including asymmetric manual efforts and source/target edits
  between planning and deployment. Two new regressions failed before the repair.
- ECC `node tests/scripts/codex-hooks.test.js`: 13 PASS in WSL; the sandbox denied
  child Node execution with EPERM, so the same checks ran in the real environment.
- Both CRM documentation gates and scoped whitespace checks: PASS.
- Native installer verification: WSL and Windows/Desktop both `status: ok`.
- Portable sync and the old compatibility entry point: `status=verified`.
- Each home: 20 identical native role files, 10 Sol 6.1/Medium,
  9 Sol 6.1/High, 1 Astra/Medium (`deep_reviewer`); root Sol 6.1/Max,
  depth 1 and multi-agent V2 enabled. Protected platform values match their
  original hashes. Old global reviewer and the three ECC definitions are backed
  up outside active agent discovery.
- Fresh native app-server read the installed root/defaults and all 20
  registrations. An ephemeral read-only thread selected Sol 6.1/Max.
  No inference or external account action was performed by this smoke check.

The live homes retain local backups under `backups/agent-graphs`,
`backups/desktop-sync` and `backups/project-routing`. Home configs, backup contents,
authentication, caches and private resume material are excluded from Git.

Project changes are committed only in their scoped local checkouts. Their portable
patches and base/result commits are in [project-changes](project-changes/README.md),
published with the canonical routing source. CRM's unrelated unpublished history,
ECC's local marketplace origin and AI marketing's missing remote are preserved.

Active Desktop/session hot reload and per-role inference are not claimed. Start
new sessions to load the new catalog; restart Desktop after the active task when
its backend still holds the previous configuration. The portable full-snapshot
helper requires a quiet Desktop profile: snapshot checks detect observed concurrent
edits but do not provide an OS-level lock against another running app.
