# Installation and updates

[Repository](../README.md) · [Русский README](../README.ru.md) · [Documentation map](README.md)

Use the installer from a reviewed checkout. **Choose the scope before running
`install`**: the default engineering set, a selected product pack, host routing,
and full host setup are different operations.

## 1. Get the source

Requirements: Git, Python 3.11+ and the target Codex CLI/Desktop installation.
Commands below run from a shell with access to the target paths, typically WSL.

```bash
git clone https://github.com/ArtemArzi/codex-agent-graphs.git
cd codex-agent-graphs
python3 scripts/install.py --help
```

To inspect instructions before installation, ask your agent to read the relevant
`skills/<name>/SKILL.md` from this checkout. That is explicit source use, rather
than proof that the skill is installed or automatically discovered.

## 2. Choose the scope

| Scope | Managed content | Host settings |
| --- | --- | --- |
| `--skills-only` | Engineering skill set and shared artifact runtime | Models, profiles, roles, policies and credentials preserved |
| `--skills-only --pack business-automation` | Only the 11 skills in the business manifest | Preserved; shared modern skill root |
| `--skills-only --pack agent-lifecycle` | Only the 4 skills in the agent manifest | Preserved; shared modern skill root |
| `--routing-only` | Managed role files, routing block, subagent defaults and usage hint | Selected root model/effort and unrelated settings preserved |
| No scope flag | Engineering skills/runtime, supplied roles, managed host policies and configuration | Applies the configured root defaults and managed registrations |

The current source of the default skill set is `SKILLS` in
[scripts/install.py](../scripts/install.py). Product membership is owned by
[business pack.json](../products/business-automation/pack.json) and
[agent pack.json](../products/agent-lifecycle/pack.json).
**`--all` selects WSL and Desktop environments; it does not select every pack.**

The legacy `playwright-interactive` companion is updated by the default
skills-only installer only where it already exists.

## 3. Select the environment

| Selector | Target |
| --- | --- |
| `--wsl` | CLI/WSL Codex home; defaults to the running user's `~/.codex` |
| `--desktop` | Desktop Codex home, detected when possible |
| `--all` | Both environments; also the default when no selector is provided |
| `--wsl-home PATH` / `--desktop-home PATH` | Explicit Codex home override |

On a machine where the default homes are unsuitable, supply known paths with
**every** `plan`, `install` and `verify` invocation. For example, adapt the
Desktop username to your machine:

```bash
python3 scripts/install.py plan --skills-only --all \
  --wsl-home "$HOME/.codex" \
  --desktop-home /mnt/c/Users/YOUR_NAME/.codex
```

Repeat the same arguments with `install` and `verify` after reviewing the plan.
The default engineering set lives in `<CODEX_HOME>/skills`, with the runtime
beside it. Shared product packs use the modern discovery roots described below.

## 4. Install the engineering workflows

For an existing host whose settings should remain intact:

```bash
python3 scripts/install.py plan --skills-only --wsl
python3 scripts/install.py install --skills-only --wsl
python3 scripts/install.py verify --skills-only --wsl
```

Replace `--wsl` with `--all` to target both configured homes. This mode does not
register missing custom roles or change global policies. If a task requires an
unavailable role, report that gap or use a supported native route.

For **full host setup**, preview the additional configuration changes explicitly:

```bash
python3 scripts/install.py plan --wsl
python3 scripts/install.py install --wsl
python3 scripts/install.py verify --wsl
```

The full mode installs the roles and managed policy/configuration surfaces owned
by this repository. Inspect [model-routing.toml](../policies/model-routing.toml)
before choosing it. Valid existing manual root effort is preserved by the
routing policy; full setup can still change the root model and managed defaults.

## 5. Install a product pack

Each pack is selected and verified separately:

```bash
# Business Automation
python3 scripts/install.py plan --skills-only --pack business-automation --all
python3 scripts/install.py install --skills-only --pack business-automation --all
python3 scripts/install.py verify --skills-only --pack business-automation --all

# Agent Lifecycle
python3 scripts/install.py plan --skills-only --pack agent-lifecycle --all
python3 scripts/install.py install --skills-only --pack agent-lifecycle --all
python3 scripts/install.py verify --skills-only --pack agent-lifecycle --all
```

These examples assume an existing, unambiguous shared modern skill root visible
to both selected environments. The installer considers
`<CODEX_HOME>/.agents/skills` and `<CODEX_HOME parent>/.agents/skills`, preserving
intentional aliases to the same physical directory. It checks known legacy
roots for duplicate names as well.

For a new single environment without an existing modern root, select `--wsl`
or `--desktop`; the default new root is its `<CODEX_HOME parent>/.agents/skills`.
For a fresh or ambiguous dual-home setup, explicitly select a known shared
physical root with `--skill-root /absolute/path/to/skills`, or configure one
environment at a time. `--business-root` remains a compatible alias. Use the
same root and home selectors throughout plan/install/verify.

The installer does not create discovery aliases or configure a new host's
loader for you. Confirm that your chosen root is visible to the selected hosts.
For the shared layout, confirm native discovery through each environment's
user-level `$HOME/.agents/skills` (Windows USERPROFILE and WSL HOME differ).
A physical copy under `CODEX_HOME/.agents/skills` alone does not establish
Desktop discovery. The [agent pack native-root guide](../products/agent-lifecycle/README.md#native-каталог-каждой-среды)
explains host-specific aliases, conflicts and checks. Avoid installing a second
physical copy of the same declared skill name.

See [Business Automation](../products/business-automation/README.md) and
[Agent Lifecycle](../products/agent-lifecycle/README.md) for their exact
membership, sources, validation and use cases. Referenced companion skills
are not installed automatically.

### CRM status

[CRM Business Pack](../products/crm-business-pack/README.md) is published as
sources. It is **not registered** in the general installer: there is no
supported `--pack crm-business-pack` command. To use it from the clone, ask the
agent to read `skills/crm-implementation/SKILL.md`. A separately installed copy
must follow your host's discovery and duplicate checks. CRM connections,
accounts and permission to change a portal remain separate prerequisites.

## 6. Verify and load the result

`verify` compares the selected installed content against this checkout.
Open a new CLI session or Desktop task to load the updated instructions and
confirm the required names in that session's active catalog.

A successful copy/hash check establishes installed bytes. It does not establish
implicit invocation, a working CRM connection, a live agent, deployment or
business effect. Run the relevant project scenario to establish those results.

## Update an existing installation

1. Preserve local source changes and inspect the target revision before updating
   your checkout. Avoid pulling over unreviewed local work.
2. Read the [changelog](CHANGELOG.md) and the affected pack manifest.
3. Run `plan` for the exact scopes, roots and environments you intend to update.
4. Reconcile unexpected local drift before replacement; inspect duplicate-name
   or source/version conflicts instead of removing another installation blindly.
5. Run `install`, then `verify` with the same arguments. Repeat the installation
   to confirm that the same version produces no further changes.
6. Start a new session and check the relevant task with the installed version.

Default installer backups live under `<CODEX_HOME>/backups/agent-graphs/`.
Shared-pack backups live outside discoverable skills, on the target filesystem;
the command output records their location. Staged writes check source and target
preimages and finish with manifests/hashes. Error rollback restores only owned
writes when the current state still matches; it does not erase concurrent edits.
Agent-pack drift is refused pending explicit reconciliation. Other modes may
replace planned differences with backups; inspect the plan rather than assuming
every mode rejects every kind of drift.

Publishing source on GitHub does not update installed files. There is no
background updater. Keep backups containing private configuration local.

## Optional routing and full Desktop synchronization

For model-routing changes only:

```bash
python3 scripts/install.py plan --routing-only --all
python3 scripts/install.py install --routing-only --wsl
python3 scripts/install.py verify --routing-only --wsl
python3 scripts/install.py install --routing-only --desktop
python3 scripts/install.py verify --routing-only --desktop
```

For the separately intended portable WSL/Desktop configuration snapshot:

```bash
python3 scripts/sync_desktop.py --check
python3 scripts/sync_desktop.py --apply
python3 scripts/sync_desktop.py --verify
```

This is a configuration operation, not a pack update. It preserves valid
per-home root effort and platform-specific settings under its own contract.
Close Desktop before applying a full portable snapshot to avoid app writes.
See [workflow and routing ownership](WORKFLOWS.md).

## Claude Code distribution

The repository contains `.claude-plugin/` metadata and uses the shared `skills/`
tree. Codex's Python installer and Claude's marketplace are separate channels.

```bash
claude plugin marketplace add ArtemArzi/codex-agent-graphs
```

Inside a Claude Code session:

```text
/plugin install cag@codex-agent-graphs
/reload-plugins
/cag:research investigate a small question in this scratch repository
```

The skill namespace is `cag`; roles are generated by
`scripts/claude_agents_sync.py` from the canonical Codex role definitions.
The plugin selects the shared skills directory, rather than the Codex installer's
individual `--pack` options. That packaging does not establish that every pack
has been executed successfully in Claude; the Software Factory guide records
its Codex-native validation boundary.

- Reviewer tool restrictions in Claude are not equivalent to a Codex OS
  read-only sandbox; a role with Bash may still write through it.
- Omitting web tools is a tool restriction, rather than a network sandbox.
- Refresh both installation channels before sharing a controller run after a
  graph change. A run pins its graph version and hash.
- Use one active harness per run directory; the state lock rejects concurrent
  operators. Do not restart an active run blindly after an uncertain operation.

To uninstall this plugin, use `/plugin uninstall cag` and
`claude plugin marketplace remove codex-agent-graphs`. Those commands do not
uninstall Codex's independent copies.
