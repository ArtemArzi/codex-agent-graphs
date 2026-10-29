# Fresh context for engineering subagents

Owner: this record. Date: 2026-10-29.
Status: local delivery complete and independently accepted.

## Authorized outcome

The user requested applying the useful Codex subagent-context refinements to
the personal engineering skills, installing them in WSL and Codex Desktop,
and publishing the scoped source changes to GitHub.

## Basis and scope

- Source repository: ArtemArzi/codex-agent-graphs. Admission HEAD:
  `df7363d7593df3703048988f00e39a6a416d5971`, clean; remote main matched.
- Upstream: [Matt Pocock #1341](https://github.com/mattpocock/skills/pull/1341)
  (fresh child conversation) and [#1342](https://github.com/mattpocock/skills/pull/1342)
  (new implementer for a distinct independent job), both merged 2026-10-29.
- Existing global policy already requires `fork_turns="none"`. The gap is
  portability of individual dispatch instructions and an explicit requirement
  to carry relevant accepted constraints and readable sources in the brief.
- Nine maintained engineering skills receive instruction-only refinements:
  codebase-design, continuous-improvement, grilling,
  improve-codebase-architecture, project-start, research, software-factory,
  task-delivery and writing-for-agents. Contributor quality guidance and the
  changelog record the same convention for future changes.
- Root-only admission, role/model routing, invocation metadata, graph/runtime
  contracts and same-scope agent/reviewer reuse retain their existing owners.
  No mandatory additional agents, new controller or installed host policy edit.

## Delivery and preservation

Both installed homes have pre-existing differences outside the selected files.
An ordinary full skills-only installation would also replace those bytes.
Deliver only the nine exact changed instruction files using the existing
descriptor-bound file publisher in scripts/storage_install.py, its native
installer locks, preimage refusal, private backups, rollback and hash readback.
Its reviewed task-local input manifest pins before/after hashes; do not change
the released storage manifest or runtime. Every selected installed file must
match either its recorded source preimage or this candidate. Refuse unknown drift.

Private task evidence and the small pinned install payload live under the Work
task scratch `.local/subagent-context-20261029`, outside this public repository.
They are retained as delivery evidence, not credentials or a published package.
Native backups remain under each home's backups/agent-graphs directory for
recovery. No worktree, dependency copy or new cache is allocated.

## Verification and continuation

Required evidence: skill validation and repository check_all, whitespace check,
one read-only block result review, exact two-home readback, repeat-install no-op,
and comparison of every unrelated managed file plus protected host settings.
Use one required block reviewer because the change is bounded instruction text;
it does not change permissions, runtime or model routing. No whole acceptance
pair is admitted solely because the text is installed in two homes.

## Completed evidence

- `python3 scripts/check_all.py`: exit 0, final message "All workflow checks passed."
- `git diff --check`: PASS. New author text contains no U+2014.
- Nine selected instruction files installed in each home, 18/18 source hashes
  independently confirmed. Existing unknown drift in other files was retained.
- Unrelated managed content plus AGENTS.md, config.toml and configured role files:
  280 hashes unchanged in WSL; 274 unchanged in Desktop.
- Exact-delta verify: PASS. Repeating installation: 0 changes, 0 new backups.
- Native private backups were retained under each home's backups/agent-graphs;
  exact captured-file paths are in the task-local install.json.
- Fresh read-only block reviewer: PASS for source semantics, adapter, installed
  bytes, preservation and no-op. It did not review GitHub publication or certify
  automatic activation and quality on real projects.

GitHub publication is separately checked through the native push and remote
main readback. The introducing commit identifies the source delta; the private
task-local delivery.json retains its exact revision and delivery outcome at
closure. Neither tests nor local installation alone establish publication.

The exact changed source paths are:

```text
docs/CHANGELOG.md
docs/SKILL_QUALITY.md
docs/tasks/TD-SUBAGENT-CONTEXT/PLAN.md
skills/codebase-design/DESIGN-IT-TWICE.md
skills/continuous-improvement/SKILL.md
skills/grilling/SKILL.md
skills/improve-codebase-architecture/SKILL.md
skills/project-start/references/agent-operations.md
skills/research/SKILL.md
skills/software-factory/SKILL.md
skills/task-delivery/references/orchestration.md
skills/writing-for-agents/SKILL-MECHANICS.md
```

Next usage: start a fresh CLI/Desktop chat for a real engineering task and use
its ordinary workflow. The existing task's review is complete; file equality
does not establish activation by already running sessions or real-project gains.
