---
name: nmt-update
description: Maintain the pinned NMT business library through its canonical repository
  when the user explicitly requests an update; preserve local adaptations and publish
  a reviewed source version before global installation.
---

# Controlled NMT maintenance

Read [installed source metadata](../business-work/references/installation.json)
and [repository-first maintenance](../business-work/references/maintenance.md).
Canonical owner is `products/business-automation/pack.json` in
https://github.com/ArtemArzi/codex-agent-graphs. The upstream original remains in
references/upstream-SKILL.md.txt as source data; do not execute its installer or telemetry.

On an update request, locate or prepare the canonical repository candidate.
Fetch the selected upstream version into separate staging, compare canon,
shared contracts and the seven operational skills, and preserve local patches
and CC BY-NC-SA attribution. Update canonical `skills/nmt-*` sources, pack
version/pins, business-work installation metadata and adaptation notes together.
Do not apply upstream bytes directly to the installed global tree.

Validate reference closure and changed behavior, reconcile installed drift,
and obtain the current host's required review. Publish the reviewed candidate
when authorized, then install that exact repository version through
`scripts/install.py --skills-only --pack business-automation` (action/targets
as documented by its CLI). Verify installed hashes, native discovery boundaries
and idempotence. Source publication, installation and practical use are distinct.

If source ownership, publication authority or required review is unavailable,
preserve the candidate and report the unmet step. Keep state in the existing
owning task, never rewrite project AGENTS from upstream defaults, and report
old/new pins and the observations actually established.
