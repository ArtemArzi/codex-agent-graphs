# Examples: tests tied to observable behavior

These are illustrative scenarios, not claims about observed incident frequencies
or a mandatory framework. Use only the examples relevant to the change.

## API field and database mapping

Suppose a response must include `notification_settings` from a stored profile.
A hand-built sandbox object containing that field says nothing about whether
the real query selects it. Seed a representative record in the test database,
read it through the relevant real adapter/API and assert the agreed field/value
and permissions. If the API legitimately allows null, test that case separately.
Inspect error handling as well as response shape. Do not blindly switch to
SELECT * to satisfy a field check: select the required columns and preserve the
intended response/access boundary.

## Sandbox/real-path agreement

Run the same declared contract against both relevant paths in their test
environments. An isolated sandbox pass must be labelled as sandbox-only evidence
when the real path could not be exercised. Do not label a single mocked test
"sandbox and production match".

Fixtures must force the intended branch. A loop such as "if rows are nonempty,
check their fields" can pass without checking anything. Arrange a known matching
record, assert the expected nonempty result, and then check fields and values.
Use a separate test for a legitimate empty result. Merely asserting nonempty
without preparing the correct data is not a stable fixture.

## Duplicate action and restart

For a queued notification, define the expected behavior before testing:
accepted request persisted, interruption point, what happens after restart,
and how a repeated attempt is identified. Interrupt a test worker at the chosen
point, restart it, then observe stored state and relevant side effects. Distinguish
"one stored job", "one provider request" and "one delivered message". Provider
uncertainty may prevent a blanket exactly-once delivery promise.

Do not run destructive failure or load experiments against production merely
because the scenario is listed. Use a suitable authorized test environment.

## Error state and optimistic UI

Agree what the user should see after a failed request: previous confirmed data,
an explicit stale state, removal of invalid data, or a retry action. Automatically
clearing every list on error is not a universal rule.

For optimistic deletion/update, verify success, failure and a second concurrent
change while the first request is pending. Restoring an old whole-list snapshot
can discard the later valid change. Assert the final visible and persisted
state against the agreed behavior; the test should detect that lost update.

## Environment and negative outcomes

An expected permission rejection should assert the relevant response and absence
of forbidden side effects. An unrelated timeout or missing runner does not
prove access was rejected correctly. Keep environment failures distinct from
product failures and record unverified portions for the next appropriate check.
