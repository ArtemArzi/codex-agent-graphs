# Engineering standard

This document remains the owner of engineering rules for this Python 3.11
stdlib CLI in one process. Existing accepted architecture is unchanged.

## Module responsibilities and extension path

service.py owns ticket operations and ticket data. cli.py parses arguments and
renders results. Call service.list_tickets, not service._rows. Keep business
rules and data access in service.py; keep flags, argument translation and output
formatting in cli.py. The service must not depend on CLI rendering. Preserve
existing public contracts, data and error behavior when adding options.

For a new filter, extend the existing public service operation only when needed,
then translate the CLI option into that operation's arguments. Check the service
behavior separately from argument parsing and rendering. A CLI-only output option
belongs in cli.py and does not justify a new data-access path.

Keep each module cohesive and its public interface small. Prefer descriptive
names and straightforward control flow. Use the existing stdlib mechanisms before
introducing abstractions or dependencies. Do not split this small app into services
or add a universal query framework for hypothetical future stores.

## Growth and maintainability

The known baseline has one small function per module. There is no evidence of an
oversized file or a performance issue. File/function growth, increased branching,
cyclic dependencies or unrelated reasons to change a module are signals to review
responsibilities, not automatic failures. No file growth threshold has been
accepted. Line count alone neither proves quality nor justifies splitting code
into thin wrappers.

If an actual extension mixes unrelated responsibilities, identify the concrete
caller and a seam that can be changed and checked independently. Extract only the
cohesive responsibility justified by that change. A local feature is not authority
for a broad refactor or architecture change.

## Code without new comments

AI adds no inline/block comments, docstrings/JSDoc, TODO/FIXME notes or
commented-out code. Express intent through names, contracts, types where useful,
and structure. Put explanations and decision rationale in documentation outside
code. Preserve existing licenses and machine directives. Do not mass-delete
existing comments outside the task.

## Checks and evidence

The declared behavior acceptance command is `python3 check.py`. When changing
behavior, add or adjust relevant checks with the implementation and run that
command on the current candidate. Cover the unfiltered path, changed input/output
and affected error cases where relevant; preserve order and public behavior.

Import boundaries, cohesion, justified abstractions, growth and the prohibition
on new comments are currently checked by review. Review actual imports and calls,
not just passing behavior checks. There is no CI line-count, complexity or import
check. No formatter, linter or type-checker command is established by the supplied
context; do not claim those checks ran. This documentation-only fixture does not
contain check.py, service.py or cli.py, so their implementation and command result
cannot be verified here.

An automated boundary guard is a possible future improvement, not installed
coverage. If separately authorized, prove such a guard rejects a known violating
example before reporting enforcement. Do not install tools or change check
configuration as part of this maintenance task.

## Decisions and handoff

Future contributors using Project Start or Task Delivery read this guide before
planning, implementing or reviewing an affected change. Include its applicable
boundaries and exact checks in the existing task, not another policy file.
Record observed behavior separately from intended behavior and unrun checks.
A justified exception or a change to a public contract, dependency policy or
architecture requires an explicit scoped decision from the owner in the existing
task before dependent implementation. This maintenance update grants none of
those changes.
