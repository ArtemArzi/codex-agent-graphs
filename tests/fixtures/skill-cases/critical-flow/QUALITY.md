# Quality and environment

Run python3 checks.py from this repository. Python standard library is available.
The script is a small existing smoke set, not complete acceptance coverage.

Observe the public process_event result and caller-owned state after each
operation. Assertions must independently express the accepted rule and run on
nonempty fixtures. Preserve a known-bad or baseline outcome when adding a guard.

This fixture is an in-memory normalized-event simulator. In the real project,
the configured persistence target is Postgres and the provider adapter remains
unavailable in this exercise. Neither a gateway success nor real row locking,
webhook authenticity, browser checkout or UAT is established here. Identify
relevant follow-up checks and their environment/trigger rather than inventing
business policy, accounts, a database service or new permission.
