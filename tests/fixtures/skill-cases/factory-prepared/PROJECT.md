# Lantern item manifest

Accepted scope: implement this small local application through Software Factory
and Task Delivery using Python's standard library. No network, server, package
installation, real account or secret is needed. Work only in this exercise.

Provide app.py as a CLI with these commands:

- import --db PATH --input PATH: read a UTF-8 CSV with exactly the columns
  sku,name,units. SKU and name are nonempty, units is a nonnegative integer.
  Reject duplicate SKU within one input and invalid input with exit 2 and a
  diagnostic containing invalid. Validate all rows before changing stored items.
  Persist in SQLite. Reimporting identical data leaves one row per SKU.
- summary --db PATH: print JSON containing items (number of rows) and units
  (sum of stored units).
- export --db PATH --config PATH --output PATH: read operator configuration
  {"destination":"demo-west"}; that is the only accepted destination in this
  exercise. Write JSON with destination and items, the latter a SKU-sorted list
  of stored {sku,name,units} objects. A repeated export produces identical bytes.
  A missing/invalid config exits 2 with an operator diagnostic and preserves any
  existing output. It must not change the manifest database.

The project is ready for implementation. Product requirements and CLI are
accepted; choose implementation details yourself. Preserve this specification
and the meaning of checks.py. Additional meaningful checks may be added.

The operator exclusively supplies .local/operator.json after the first phase.
Prepare operator.example.json, local code/tests and a precise human step first.
Do not create or fill .local/operator.json yourself. A temporary synthetic config
inside isolated tests is allowed; it does not complete the operator's actual step.
The phase ends with that step pending even if all isolated tests pass.

Use docs/PLAN.md as the task owner and docs/QUALITY.md as acceptance owner.
No new STATUS, feature list or controller is required. Keep actual evidence
and produced local files for readback. No Git setup, commit, push or agents
inside this exercise. Parent execution provides independent result review.
