# Accepted change

The local support app lists open tickets. Add an optional status filter to its
CLI. The existing public tickets.list_tickets(status=None) interface already
supports that filter and owns ticket data. No new storage or network delivery.
Preserve output order and the unfiltered call. Unknown status produces the
existing ValueError. Required evidence: filtered and unfiltered output, invalid
status and a check that the CLI uses the public interface. Existing acceptance
checks are run locally. Nothing is deployed in this exercise.
