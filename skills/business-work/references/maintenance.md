# Repository-first maintenance

Canonical source: https://github.com/ArtemArzi/codex-agent-graphs. Product owner:
`products/business-automation/pack.json`; each managed skill lives once in
`skills/<name>`. Installed metadata is [installation.json](installation.json).
Installed files are deployment targets, not an alternative source of truth.

On an explicit update request, inspect canonical and installed state first.
Stage changes in a repository candidate, preserve accepted local patches,
update the pack version, upstream pins and adaptation record together, then
validate and obtain the host's required review. Publish only when authorized;
install the exact reviewed repository version using the pack's installer.
Never apply an upstream update directly to global installed trees or run its
project installer/telemetry. If the canonical source or review is unavailable,
prepare the candidate and report the remaining step instead of bypassing it.

Install command from the canonical checkout:
`python3 scripts/install.py install --skills-only --pack business-automation --all`.
Use its plan/verify modes first/afterwards; pass `--business-root` when needed
to retain the host's known native discovery root. Preserve existing root aliases
and one physical managed entry per name. Do not copy this pack into both modern
and legacy skill roots. Backups stay outside discoverable skills on the target
filesystem. Preserve unrelated skills, config, profiles, models and credentials.

Keep NMT canon/contracts and path/precedence/output/telemetry adaptations, original
CC BY-NC-SA notices and source attribution. Each dependency retains its own
terms; this collection does not change them. last30days remains pinned MIT
source with local SKILL/launcher changes. Optional provider/browser setup stays
outside ordinary installation; Beads remains deferred.

Do not treat source equality, native metadata or synthetic checks as real client
use/effect. Test the changed behavior in an authorized project and update only
the owning project evidence. Private originals, backups and verification logs
do not belong in the public source tree.
