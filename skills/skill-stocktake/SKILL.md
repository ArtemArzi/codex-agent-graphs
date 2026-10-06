---
name: skill-stocktake
description: Audit the current host's installed skills, duplicates, dependencies and workflow conflicts. Support a complete static inventory or a changed-skill scan with explicit coverage limits.
metadata:
  origin: ECC
---

# Skill Stocktake

Audit the host actually in use: Codex, Claude or explicitly requested homes.
List exact roots, active catalog versions and disabled entries before scanning.
Use host-provided discovery first. Typical local roots are `.codex/skills`,
`.agents/skills` and `.claude/skills`, plus project roots already identified.
Resolve symlink aliases once. Plugin paths must come from the current catalog
or configured active version; do not scan every cached release or whole home.
Finding a file does not prove it is enabled or currently selected.

## Inventory and coverage

Run the stdlib inventory helper with explicit known roots or individual files:

```bash
python3 scripts/inventory.py --root /known/current/skills --file /exact/active/plugin/SKILL.md --output /tmp/skills-inventory.json
```

It records names, descriptions, exact content hashes, resources and duplicate
groups. It does not decide enablement, usage or quality. Add those from host
configuration or observed evidence; use `unknown` where unavailable.
The older shell helpers are Claude-only legacy adapters, not Codex discovery.

A full stocktake inventories all selected files and checks every body for
metadata, dependencies, duplicated contracts and suspect execution instructions.
Read relevant sections in context before calling a hit a defect: fenced
illustrations and placeholders are not automatically missing resources.
State whether coverage was structural/pattern-based, line-by-line review or
actual execution. Static review is not certification of every integration.
For a quick scan, compare exact hashes with a prior matching-root inventory;
report removed and new entries as well as changed entries. Do not silently
carry forward a result from a different host/version scope.

## Evaluation

For each distinct body give a self-contained verdict and evidence:

| Verdict | Required basis |
|---|---|
| Keep | Useful contract with no demonstrated defect in checked coverage |
| Improve | Concrete conflict, missing dependency or unsafe instruction and bounded remedy |
| Update | Version-sensitive reference verified against primary current sources |
| Retire | Demonstrated defect and existing replacement; proposal unless removal authorized |
| Merge | Named target and useful content to preserve; proposal unless removal authorized |

Check trigger fit, host tool availability, instruction priority, authorization,
model routing, progress/retry behavior, recovery, state/receipt integrity,
source provenance and overlap. Read real failure history when the task concerns
stalls. Distinguish a controller fault from missing task authority or a genuine
project release gate. Do not remove exact signatures just to eliminate prompts.
Verify uncertain versions with primary sources and installed versions.

Default to root execution. Delegate a substantial independent branch or review
only under host policy; no fixed count of agents per batch. Save intermediate
coverage in the existing audit artifact and resume unevaluated entries.

## Corrections and delivery

Proceed with authorized bounded fixes; do not request permission again when
the user already requested fixes and synchronization. Preserve original
resources/provenance, dirty work, disabled rules, credentials and active runs.
Vendor caches are provider-owned: prefer maintained overrides or an upstream
report to in-place edits that the next plugin update would overwrite.
Deletion, enablement, migrations and external publication need their own
authority unless explicitly included in the request.

Validate meaningful regressions, skill metadata, live installed manifests and
the user's actual outcome. Apply the host's independent review threshold.
Report per-skill disposition, executed checks, deferred candidates and residual
limits. Never invent usage counts, runtime PASS or blanket 'latest version'.
Write results to an authorized artifact directory, not into an installed skill
or memory by default. Memory updates require an explicit user request.
