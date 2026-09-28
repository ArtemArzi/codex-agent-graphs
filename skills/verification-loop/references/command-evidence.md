# Preserve command outcomes

Prefer the tool's direct exit code for a command without an output pipeline.
If output must be shortened, capture it first and preserve the producer's status.
The example below runs in its own Bash process; replace `npm run test` with the
actual project-owned command. It is illustrative, not a universal test command.

```bash
check_log=$(mktemp) || exit 1
if npm run test >"$check_log" 2>&1; then
  check_rc=0
else
  check_rc=$?
fi
tail -n 40 "$check_log"
printf 'Command exit: %s; full log: %s
' "$check_rc" "$check_log"
exit "$check_rc"
```

The conditional captures a failure even when Bash uses `set -e`. `mktemp` avoids
clobbering another task's log. Store a relevant sanitized excerpt in the task's
evidence location when durable evidence is needed; a temporary path is not a
long-term receipt. Avoid persistent logs containing secrets; configure redaction
at the check or keep sensitive output out of shared artifacts and chat.

With an existing pipeline, inspect the producer's status (for example Bash
PIPESTATUS immediately after execution) or use an appropriate pipefail wrapper.
Piping through head can also terminate the producer early; file capture is
preferable when the full test must finish. A formatter/tail exit code alone
cannot establish the test result. Preserve timeouts and interruptions as
incomplete/failed runs instead of silently converting them to success.

A command's zero exit code is necessary for ordinary successful checks but may
not be sufficient: confirm the intended target ran, test discovery was nonempty
where tests were expected, and result assertions match the requirement. Missing
commands (often exit 127), permission failures, broken fixtures and missing
dependencies are environment evidence, not proof of a product defect.

For deliberate defect reproduction or expected rejection, record the expected
failure first; inspect that it failed for the intended reason. A random error
with the same exit code does not validate the negative scenario.
