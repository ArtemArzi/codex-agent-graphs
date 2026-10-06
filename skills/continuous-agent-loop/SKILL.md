---
name: continuous-agent-loop
description: Select a bounded autonomous loop with explicit completion criteria, progress evidence and recovery limits. Reuse the host's available loop workflow.
metadata:
  origin: ECC
---

# Continuous Agent Loop

This is a small router, not a replacement for the detailed `autonomous-loops`
reference. If that skill is enabled and the task needs its patterns, discover
and read it through the current host catalog. Do not install or enable skills
just because this router names them.

1. Define the authorized outcome, affected scope, checks and stopping boundary.
2. Reuse the existing plan, controller and latest verified checkpoint. Ordinary
   local work can run natively; do not create another orchestration stack.
3. Choose a sequential loop by default. Use PR, RFC or parallel patterns only
   when the task needs them and their capabilities actually exist. Host model
   routing, delegation thresholds and user authorization govern execution.
4. At each iteration, record the new observation and next bounded action in
   the existing task owner. Resume it after waiting or compaction.
5. After two attempts without new evidence, pause the failing approach, locate
   its first false assumption and use `development-recovery` if available.
   A controller-only failure permits one bounded repair, then native work with
   preserved pending checks; it is not evidence of an implementation failure.
6. Run checks for the affected contract and finish the usable result. Preserve
   required independent acceptance. A degraded controller cannot claim PASS.

Quality gates, eval tools and session persistence are optional capabilities.
Do not assume `/quality-gate`, `/harness-audit` or a particular REPL exists.
No model escalation, package install, timer activation, paid operation or
external publication follows merely from selecting a loop.
