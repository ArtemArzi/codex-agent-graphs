# Acceptance

- Q1: Valid CSV is persisted; identical reimport keeps one record per SKU.
- Q2: Invalid or duplicate rows are rejected before any stored row changes.
- Q3: The sample has 2 items and 5 total units; summary reports those values.
- Q4: Export without operator config preserves the output and database.
- Q5: With an operator-provided destination, actual sample export has the exact
  sorted items and repeat export has identical bytes.

Run python3 -B checks.py for isolated CLI/database contracts. Its temporary
configuration is synthetic and is not evidence of the operator completing Q5
on the actual .local/manifest.sqlite3 and .local/export.json.
After the operator supplies .local/operator.json, exercise the real import,
summary and export commands on those paths and retain bounded evidence.
The local exercise has no real provider, UI or cloud behavior to verify.
