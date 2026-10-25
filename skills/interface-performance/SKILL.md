---
name: interface-performance
description: Diagnose and improve frontend loading, interaction latency, scrolling and rendering using comparable measurements. Use for a slow UI or explicit performance work; a visual redesign alone does not require an optimization pass.
metadata:
  version: "0.1.1"
---

# Interface Performance

Make the user's actual path fast without changing its meaning or behavior.
Use the installed interface-design [host adapter](../interface-design/references/hosts.md)
when present. Standalone use follows the current host catalog and permissions;
no Codex-only tools or TOML configuration are assumed in Claude Code.
Read the current task, target version, framework, device/load constraints and
existing measurements. Preserve the accepted UI, accessibility and data contract.

## Measure before choosing a fix

Identify what feels slow: first useful view, first input, a search/filter, a long
list, scrolling, a transition or a remote request. Reproduce one representative
workload. Record version, device/browser, network/cache state, dataset and actions.
Capture an appropriate baseline: navigation timings, a performance trace,
interaction delay, transferred/parsed JS, render work or a repeatable elapsed task.
Separate backend wait from frontend work; an empty dependency list does not prove
fast interaction. If measurement is blocked, return a scoped diagnosis and the
missing measurement without invented before/after numbers.

## Select the smallest supported change

- For React/Next.js, use available build-web-apps:react-best-practices for the
  relevant category: request waterfalls, bundle/loading or rerender work.
- For UI layout/effects/assets, use available impeccable optimize or project
  tooling. Do not invoke both paths for an equivalent completed investigation.
- Prefer existing image sizing, lazy boundaries, component/state and list
  mechanisms. Virtualization must preserve keyboard focus and navigation.
- Missing or explicitly disabled capabilities stay unavailable. Do supported
  native profiling and bounded implementation, naming only the missing check.
- Confirm version-sensitive claims with current official docs. Motion shorthand
  acceleration is not governed by the blanket prohibition in the older source
  snapshot. Avoid adding dependencies for a trivial transition.

## Verify the same path

Repeat the same workload and conditions after the change. Report the observed
values, repeatability/limits and tradeoffs; do not compare a cold baseline to a
warm optimized run without stating it. A smaller bundle alone does not prove
faster task completion. Local lab data does not establish production Web Vitals.

Recheck relevant flow and visual states, mobile/keyboard behavior and data
correctness. Preserve loading feedback, recovery and reduced motion. Save evidence
with the current task, stop after sufficient evidence and close owned profiling
holders/scratch while retaining the requested output. No mandatory controller,
universal score, arbitrary percent target or full optimization pass for a label edit.
