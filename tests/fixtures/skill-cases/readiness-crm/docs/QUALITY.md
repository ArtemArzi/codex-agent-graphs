# Harbor release criteria

For candidate r2, required now:
- ACCESS: alice belongs to alpha, bob to beta. Own records return exit0;
  another tenant's record must return exit3 and no private record content.
  The real local boundary is exercised by checks.py.
- LOAD: demonstrate delivery of 1000 read operations over60seconds before
  claiming this project target is supported. Inspect actual delivered work
  and latency/errors; do not infer the cause of undelivered load without data.
- RECOVERY: demonstrate usable restored state before production handoff.
  A completed backup job alone does not meet this requirement. Numerical
  RPO/RTO goals have not been selected and must not be invented.

Payments, AI, browser accessibility and public indexing are outside this slice.
