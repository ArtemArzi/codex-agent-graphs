---
name: verification-loop
description: Select and run proportionate checks for a software change, preserving real command outcomes and reporting evidence and gaps. Use to verify an implementation, refactor, bug fix, or release candidate. Follow project-owned quality requirements; do not invent a coverage quota or replace task orchestration.
metadata:
  origin: ECC
---

# Verification Loop

Turn the project's acceptance requirements into observed evidence. The project
owns requirements and commands; this skill selects and runs relevant checks.
Task Delivery and the user's routing policy own planning, delegation and review.

## Before checking

- Read the change scope, existing baseline and relevant project instructions.
  Resolve the project quality document through its documentation map when
  present; exact commands belong to the engineering guide or linked scripts/CI.
  Missing documentation does not require bootstrapping the whole project.
- Determine what could break: business rules, persistence, permissions,
  integrations, repeats/concurrency, recovery, load, interface or release path.
  Reuse existing checks and add a missing check only when it tests meaningful
  behavior. A trivial wording change needs proportionate verification.
- If missing business expectations materially change acceptance, ask a short
  plain-language question with the consequence and a recommendation. Discover
  commands and tools yourself. Reuse already answered questions.
- With an explicit no-questions instruction, continue using known requirements
  and reversible stated assumptions. Do not invent authorization, silently
  change requirements or claim an unknown mandatory criterion has passed.

For substantial work, briefly tell the owner what may fail and how you will
check it. Use their language and explain necessary technical terms; skip a
separate questionnaire for a small clear task.

## Select checks by change and risk

| Changed surface | Appropriate evidence |
| --- | --- |
| Code/configuration | Relevant types, lint, build and structural checks supported by the project |
| Business rule or state transition | Unit/component checks of allowed, rejected and boundary cases |
| Database or module/API boundary | Integration checks of real test persistence/adapters, transactions and error paths; contracts where appropriate |
| Critical user journey | Relevant E2E route and visible result, including affected error states |
| Bug fix | A reproduction that detects the defect plus the affected regression set |
| Queues, retries or concurrent changes | Duplicate, timeout, interruption/restart and concurrency scenarios |
| Storage, schema or release compatibility | Applicable migration/compatibility and restore checks in a suitable test environment |
| Load or capacity | Measurements against the project's workload and latency/throughput requirements |
| Access or sensitive boundaries | Relevant permission/security tests and configured scanners, with redacted evidence |
| Deployment | Smoke checks after the authorized deployment; pre-deploy tests remain separate |
| Nondeterministic AI behavior | Project eval cases and outcome checks; ordinary software tests still apply |

A regression set can include unit, integration and E2E tests; do not duplicate a
check merely to give it another label. Use project-owned coverage thresholds;
if none exists, report meaningful uncovered risks without inventing a percentage.
Not every row applies to every task. The task's test plan should identify which
checks already exist, which need adding, and when/where deferred checks run.

## Run checks faithfully

1. Discover existing commands, configuration and available tools before running.
   Do not invent slash commands, install missing tools or alter CI just to match
   this skill; use an authorized project fallback or report the missing check.
2. Run focused checks while changing the relevant behavior. Run expensive
   cross-component checks at the agreed integration/release boundary. Rerun
   when changes or new evidence invalidate a result; do not rerun by a timer.
3. Preserve the tested command's real exit code and inspect the relevant output.
   Read [command-evidence.md](references/command-evidence.md) when capturing or
   shortening output. A pipe to head/tail/tee can hide the producer's failure.
4. Confirm the intended tests actually ran. Exit zero with zero selected tests,
   a skipped target, only cached unrelated output, or an unavailable runner is
   insufficient. For an expected negative test, define its expected failure
   before the run and distinguish it from a failing acceptance check.
5. Record command, directory, scope/version, environment, expected and actual
   outcome, and a concise evidence path in the existing task report or CI.
   Do not print secrets or raw matching credential lines into the conversation.
6. Review the actual scoped diff against the captured baseline. Do not assume
   HEAD~1 represents this task, and preserve pre-existing user changes.

Failures require diagnosis: distinguish product defects, environment problems
and pre-existing failures. Continue independent authorized work; a failed or
unrun required check prevents claiming that criterion is satisfied. Do not
weaken tests or thresholds to make the candidate appear complete.

## Report what is established

For material checks use PASS, FAIL, BLOCKED/NOT RUN, or NOT APPLICABLE with a
reason. A passing negative test means the expected rejection was observed; it
does not mean an arbitrary failed command is a successful acceptance check.
Name deferred checks, their reason, next trigger and impact on readiness.

Explain briefly: what was checked, what happened, what remains uncertain, and
what that means for the requested delivery. Build, local tests, deployment,
external-provider delivery and human acceptance are separate claims. Do not
report security PASS from a keyword search or all-system readiness from a
partial test set. A hook firing is not proof that its check passed.
