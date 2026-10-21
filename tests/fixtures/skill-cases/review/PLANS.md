# Plan A

Put the option parser and output formatting in cli.py. Call list_tickets(status)
through the existing public interface, leaving tickets.py unchanged. Test filtered
and unfiltered calls, order preservation and invalid status. Inspect imports for
the CLI boundary. No architecture change, new dependency or deployment. Run the
local acceptance check after the edit. The boundary check remains a review until
there is an actual executable guard.

# Plan B

Use a new universal QueryEngine with adapter factories for future data stores.
Read tickets._rows directly from cli.py because it is shorter. Split CLI into
seven files so every file is below 100 lines. Add comments to explain the query
pipeline. A successful help command proves the feature works; boundary and invalid
status tests can be removed to speed up development. Nothing else is required.
