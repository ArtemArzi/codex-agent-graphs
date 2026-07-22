# Public launch README

Status: AWAITING PUBLICATION APPROVAL
Task ID: TD-README-PUBLIC

<!-- task-delivery:plan:start -->
## Outcome

GitHub repository is public and its README clearly explains value, workflows, installation, native Codex integration, and validation

## Research basis

- Internal: inspect every shipped skill and graph contract, installer behavior, custom-agent configuration, global policy installation, repository history, current GitHub metadata, and the existing README before writing claims.
- External: use the current official Codex manual only to verify how Codex describes skills, custom agents, `AGENTS.md`, MCP, and plugins. The repository code remains authoritative for this installer and its exact file layout.

## Acceptance

- `README.md` opens with a clear problem/value proposition and lets a new reader understand the package in under a minute.
- The README accurately distinguishes the three runtime graph skills, the graph-building meta-skill, the recovery skill, and the installed large-codebase discovery policy.
- It includes a copy-paste quick start from clone through plan/install/verify and explains both WSL CLI and Desktop targets, backups, session restart, and validation.
- It states the real native Codex integration: skills, custom agents, managed `config.toml`, managed global `AGENTS.md` blocks, and MCP-first runtime policy.
- It explicitly says that no plugin package or mandatory MCP server is bundled, and names only dependencies proven by repository files.
- It avoids unsupported claims about autonomy, validation, compatibility, licensing, plugins, users, adoption, or performance.
- The full repository gate and installer verification pass; a public-safety scan finds no real credential material.
- The GitHub repository is public, its description/topics match the README, and the committed README is visible on `main`.

## Implementation plan

1. Build an evidence-backed inventory of capabilities, dependencies, install behavior, and public-release risks.
2. Rewrite `README.md` around buyer intent: promise, use cases, workflow map, capability detail, quick start, native integration, safety model, extension path, and honest limitations.
3. Validate Markdown claims against source, run the repository gate and installer plan/verify commands, and repeat the secret-safe release scan.
4. Commit and push the coherent documentation package, switch the verified GitHub repository to public, update discovery metadata, and verify the live state.

## Tests

- `python3 scripts/check_all.py`
- `python3 scripts/install.py plan --all`
- `python3 scripts/install.py verify --all`
- `git diff --check`
- targeted README link/path/command checks and secret-pattern scans over the worktree and Git history
- `gh repo view ArtemArzi/codex-agent-graphs --json visibility,isPrivate,url,description,repositoryTopics,defaultBranchRef`

## Stop conditions

- Stop before public release if a plausible credential, private personal data, or unexpected user-authored change is found.
- Do not add an open-source license or claim “open source” without an explicit license choice from the owner.
- Stop if the live GitHub target differs from `ArtemArzi/codex-agent-graphs`, admin permission is absent, or the local branch cannot be proven aligned with `origin/main`.
- Do not weaken graph contracts or tests to make documentation claims pass.

## Scope

<!-- task-delivery:scope
README.md
docs/tasks/TD-README-PUBLIC/PLAN.md
-->
<!-- task-delivery:plan:end -->

## Plan review

Self-review: PASS. The plan is limited to public-facing documentation and GitHub metadata/visibility; source contracts are read-only. Public visibility is explicitly authorized by the user. Licensing is intentionally excluded because no license choice was provided.

## Delivery result

- Rewrote `README.md` around the three user-facing workflows, supporting capabilities, native Codex architecture, copy-paste installation, dependencies, plugin/MCP boundaries, validation, and current limitations.
- Verified the current official Codex descriptions of skills, custom agents, `AGENTS.md`, MCP, and plugins before using that terminology.
- `python3 scripts/check_all.py` passed, including every graph contract and workflow test suite.
- `python3 scripts/install.py plan --all` and `python3 scripts/install.py verify --all` both reported WSL and Desktop fully `in-sync`.
- `git diff --check` and the targeted public-safety scans passed; the only secret-like historical string is an intentional synthetic test fixture.
- GitHub confirmed the exact target and admin permission, but the visibility mutation is paused because the execution policy requires a fresh user confirmation after disclosure risk is stated. The repository remains private until that confirmation.
