---
name: business-hypothesis-check
description: Define observable expectations and compare them with sourced facts when
  checking a business claim, operational pilot or implementation outcome; distinguish
  missing evidence from contradiction and define the next test.
---

# Expectation versus observed fact

Original local implementation informed by the talk of Ilya Krasinsky and the
user-provided Heroes Camp educational package. No original ZIP code is copied.
Read references/method.md for attribution and the input contract.

Use one bounded hypothesis and normally 3-7 observable expectations, scaled to
the task. Before testing, state criterion, source, scope/time and which criteria
are decisive. Afterwards compare actual observations, keeping missing facts open.
For each unresolved row identify a next action, actual owner or unknown owner,
and deadline if known. Use the existing task/plan/acceptance document.

Statuses: confirmed = declared criterion observed within its stated scope;
partial = evidence covers only part; open = no adequate observation;
falsified = observation contradicts the criterion. No observation means open.
The helper conservatively downgrades unsupported labels to open and calculates
an overall result. It summarizes supplied observations; it does not verify
sources, inspect live systems or establish causality/economic value.

Run `python3 <this-skill>/scripts/hypothesis_report.py <existing-task>/evidence.json`
for Markdown stdout or add --json for a machine-readable result. No automatic
files or third-party packages. Use normal task validation to gather evidence.

Separate local test, deployed behavior, real user completion and economic effect.
For financial joins preserve the project's ID/cardinality/provenance rules and
manual exceptions; no universal phone=person or blanket percentage thresholds.
A technical PASS never independently approves money, identities or live changes.
Host/user/project rules and review policy govern. Do not create a new controller.
