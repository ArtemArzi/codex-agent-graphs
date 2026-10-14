# Project mapping and check planner v1

The mapping is a small JSON document, commonly `deploy/deployment.json`, linked
from the existing deployment runbook. Reuse existing owners; do not add a second
quality policy or release journal. JSON avoids adding a YAML parser to runtime.
`workflow.yaml` is the agent-readable route, not an executable shell language.
The helper uses Python 3.10+ standard library and never runs project commands.

## Mapping

Required top-level keys:

- `schema_version`: integer 1 (booleans are invalid).
- `project_id`: stable identifier.
- `owners`: `deployment`, `quality`, `engineering` repo-relative document paths.
- `native`: `status`, `release`, `rollback` nonempty owning references; references
  are navigation, not permissions or scripts to evaluate.
- `commands`: object keyed by IDs. Each value has `argv` (nonempty string array),
  `cwd` (repo-relative directory, `.` allowed), optional positive integer
  `timeout_seconds`. Never interpolate free text into shell commands.
- `checks`: object keyed by IDs, described below.
- `profiles`: object keyed by IDs, each a nonempty array of check IDs. Profiles
  represent project-approved lanes, not a way to bypass required checks.
- `default_profile`: existing profile ID, normally the ordinary release lane.

IDs use lowercase letters/digits plus `.`, `_`, `-`, maximum 64 characters.
Unknown fields, duplicate JSON keys/IDs, invalid references and malformed values
are errors. Each JSON input is bounded to 1 MiB and 64 nesting levels. Expanded
plan JSON is bounded to 4 MiB (excluding stdout's final newline); repeated shared
commands cannot amplify a small input into unbounded output. Exceeding a limit
returns invalid-input/exit 2, never truncation or a partial plan. Relative paths cannot be
absolute, traverse `..`, contain backslashes/control characters or target a
symlink. With `--project-root`, owners must be existing regular files and command
working directories existing directories inside that root; no file contents or
credentials are loaded. Without a root, validation establishes shape only.

Each check has:

| Field | Meaning |
| --- | --- |
| `kind` | Any nonempty project label: unit, E2E, accessibility, migration, AI eval, manual acceptance, etc. No fixed test-kind enum |
| `phase` | `source`, `artifact`, `environment`, `postdeploy`, `scheduled`; release milestones independent of named environment |
| `environment` | Named environment ID, e.g. local-db or staging; never a password/connection string |
| `method` | `command` or `manual` |
| `subject` | `source` or `artifact`; what result is bound to |
| `command` | Required command ID for method=command; absent for manual |
| `criterion`, `acceptance_owner` | Required nonempty references for method=manual; manual acceptance is not generated from an exit code |
| `depends_on` | Optional array of prerequisite check IDs; includes stack readiness, artifact production or other required work |
| `binding_keys` | Optional distinct input-reference IDs from context.inputs, e.g. toolchain/config/dataset/operator |
| `reuse_verifier` | Optional native command ID that must verify any potential reused evidence; absent means run/check manually |
| `max_age_seconds` | Optional positive integer age limit for reuse |
| `fresh` | Optional boolean; true forbids reuse. Postdeploy checks are always fresh |

All checks included by the selected profile and their transitive prerequisites
are required. A missing ID, duplicate dependency, cycle or dependency on a later
phase is an error. A source-phase E2E may depend on source-phase local-stack setup;
artifact E2E may depend on a build and staged environment readiness. Do not force
all environment preparation into the `environment` milestone. Scheduled checks
belong to separate profiles unless the project explicitly requires them for a
release; a required scheduled check is not silently discarded.

## Context and evidence

Optional context JSON has only `source` (nonempty identity), `environments`
(environment ID -> nonempty identity), `artifact` (nonempty digest/identity),
`inputs` (input ID -> nonempty version/content reference). Missing bindings remain
visible as `await_bindings`; a plan does not invent them. Native owners must
verify that supplied identities represent reality. Secrets are never input refs.

For each check, expected `subject` is an object with `source`, `environment`,
`contract_digest`, `check_digest`, `inputs`, and `artifact` for subject=artifact.
Digests use canonical sorted compact JSON/SHA256, binding the entire mapping and
the check plus its command (or manual criterion). This is conservative: changes
may invalidate more evidence rather than claiming unproven dependency closure.

Optional evidence JSON has `schema_version: 1`, `checks: {check_id: record}`.
Records have `status` (passed/failed/skipped/blocked/unknown), optional `subject`,
`completed_at` (timezone-aware ISO timestamp), `receipt_ref` (native evidence ref).
Unknown fields/check IDs are rejected. A potential reuse requires exact expected
subject, passed status, nonempty native receipt reference, valid nonfuture time,
applicable age bound, nonfresh check and a declared native reuse verifier.

Even a matching record yields only `verify_reuse`, NEVER skipped/accepted/PASS.
The agent must run the native verifier against the original receipt and obey
project trust/attestation. If it rejects evidence, run the original required check;
do not reinterpret a supplied JSON field as authority. Manual evidence additionally
requires its declared owner. Live target/current/authority/ACL/backup checks remain
native and fresh even when source evidence can be reused.

## Commands and output

Resolve `deployment.py` against the installed skill directory, not project CWD:

```text
python3 <skill-dir>/scripts/deployment.py validate --contract CONTRACT --project-root REPO
python3 <skill-dir>/scripts/deployment.py plan --contract CONTRACT --project-root REPO --profile release --context CONTEXT --evidence EVIDENCE
```

Context/evidence/root/profile are optional. stdout is structured JSON; no output
files or subprocesses are created. Exit 0 means valid contract/planning operation;
exit 2 means invalid inputs. It never means deployment authorized or completed.

`validate` returns `status: contract_valid`, schema/project IDs and filesystem
validation scope. `plan` returns `status: planned`, selected profile,
`contract_digest`, ordered `checks`, `release_authorized: false` and
`release_verified: false`. Each planned check includes ID/kind/phase/environment/
method/dependencies, expected subject, original command or manual owner/criterion,
and an action: `run_required`, `manual_required`, `await_bindings` or
`verify_reuse` with the verifier command and receipt ref. Missing/mismatched/
failed/stale evidence never removes a required check. Recompute after bindings
become available or inputs change; do not treat the plan as runtime state.

The output bound uses the standard-library streaming
[JSONEncoder.iterencode](https://docs.python.org/3.12/library/json.html#json.JSONEncoder.iterencode)
with the same encoder formatting as final stdout. Input bounds alone do not bound
expanded shared-command output; this is checked separately before serialization.
