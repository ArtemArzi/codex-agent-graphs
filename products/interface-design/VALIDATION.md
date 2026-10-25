# Validation scope

The original local adapter passed independent plan/result acceptance, selected
source hash/license checks, three blind instruction scenarios (flow, missing
capability, performance) and real-browser demo inspection. The demo's pending
selection race and last-unassigned-item cases were corrected and rechecked in
Chromium. These are bounded local results, not human usability measurements.

The package adds dual-host installation tests in
[test_interface_pack.py](../../tests/test_interface_pack.py): native Codex and
Claude installation, same-user coexistence, no-op repeat, drift/duplicate refusal,
profile and native-engineering preservation, CLI argument boundaries, pinned
source integrity and portable resources. The full repository gate is:

```sh
python3 scripts/check_all.py
```

Release candidate verification: all seven package tests passed, the full
repository gate passed, and Claude Code 2.1.289 accepted both plugin.json and
marketplace.json through `plugin validate --strict`. Profile preservation and
native-engineering compatibility were exercised in disposable synthetic homes.
The packaged demo matches the previously inspected source bytes. This adds no
claim of a live Claude session or production deployment.

The native Claude CLI path and the existing cag plugin have different delivery
contracts. Structural discovery under root `skills/` and a successful file install
do not establish automatic skill selection or real model/tool execution. Actual
Claude CLI/Desktop activation remains unverified without an active session.
The pack does not silently install optional visual plugins, paid services or
browser runtimes. Native installer duplication checks cover known native roots;
enabled plugin copies require deliberate channel selection.

The local performance exercise used a synthetic 2,400-row list and compared the
same click-to-two-animation-frames workload. It is not production Web Vitals or
evidence of a universal speedup. Performance changes on a real product require
their own representative baseline and equivalent after-measurement.
