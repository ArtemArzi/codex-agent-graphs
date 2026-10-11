# Readiness before parallel work and costly verification

Use this for the affected path before dispatching writing jobs or starting a
costly combined check. Reuse the existing task record and Task Delivery checks;
no separate checklist file, controller, fixed test count or extra agent is needed.
For ordinary small work, perform only the checks its changed behavior requires.

## Resolve shared prerequisites

Trace the changed artifact or behavior through its real consumers, not only the
files assigned to workers. Inspect the existing mechanisms and relevant callers:

- Shared interfaces, generated files and mutable resources: settle the contract,
  owner and isolation before dependent writers start.
- Packaging or installed-file changes: check the exact permitted paths and the
  inventories used by validation, update, rollback or restore where applicable.
  Adding a file to a release allowlist does not prove that older installations
  can upgrade or reverse it correctly. Preserve private-path and history guards.
- New or changed command examples: exercise a representative command in a
  disposable fixture with the intended runtime. If commit/delivery takes exact
  paths, include generated artifacts and their references; do not substitute a
  broad staging command or silently rely on a sibling's unfinished implementation.

Use a small baseline probe or inspect the existing inventory before dispatch.
When the final scenario needs code that has not been written, settle the shared
interface now and name that scenario as pending combined verification. Tell the
leaf which local checks can pass on its base and which need the integrated code.
Do not require the future full implementation to pass before allowing its work.

A missing prerequisite blocks only dependent work. Root can complete it first,
or keep unaffected work running. If the bound base must change, freeze and inspect
the affected jobs before changing it; preserve their commits, prepare a new
workspace/context and repeat affected combined checks on the new candidate.

## Probe the real runner and environment

Prefer the project's canonical test command and existing reporting mechanism.
Do not write a replacement runner merely for Factory metadata. If a wrapper is
necessary, smoke-test its discovery, intended import/build origin, log output and
exit propagation on a small existing case before using it for a long suite.
Zero discovered tests or an instrumentation exception is a setup failure.
Diagnostic instrumentation must preserve the real validator, assertions and
failure exit; it must not turn an expected failure into a pass.

Probe only capabilities required by the chosen checks: interpreter/dependencies,
local sockets, native Windows interop, browser/display, ports, or writable fixture
roots as relevant. Use isolated synthetic resources; a probe does not authorize
network writes, installation, credentials or production actions. Record the
actual command, CWD, candidate and environment in the existing evidence.

If a capability fails, discriminate environment failure from a product defect
with a small unchanged case. Use an already authorized suitable environment,
or request the actual missing authority. Preserve the failed result; do not
disable a check, weaken its oracle or change permissions just to obtain green.

## Run and report proportionate checks

Run affected local checks, then the combined acceptance scenario and the required
full set at the project's chosen boundary. After a failure, identify its cause
and check the smallest reproducer before repeating a costly suite. A changed
candidate or environment can justify a new required full run; do not repeat an
unchanged long run without new evidence or invent duplicate checks by category.

Bind results to the actual candidate and environment. Keep passed, failed,
interrupted and not-yet-run checks distinct. An isolated successful repeat does
not replace a required full-suite result. A lost tool session or retained lock
does not prove completion; follow the existing interruption rules and keep the
old evidence. Review/acceptance still follows the inherited policy.

Where useful, derive preparation, worker overlap, integration, check and repair
time from existing logs in the task record. Explain the observed bottleneck;
do not equate more agents or overlapping turns with measured speed or savings.
