# Boundary scenarios

Use relevant cases for reasoning or evaluation, not a checklist on every task.
Expected behavior below is guidance; it is not a record of successful runtime
tests. Keep structural validation, model behavior, native discovery, real chats
and production effects separate.

| Input | Expected decision |
| --- | --- |
| Small isolated typo | Edit/read back directly; no chat scan, extra agents or interview |
| Large isolated implementation, no shared dependency | Zero chat-tool calls; task size alone does not trigger discovery |
| Native children already assigned | Use child status/wait tools; no independent-chat listing |
| Listing supplies activity, CWD and project | Use metadata directly; zero history reads for these fields |
| Active chat in unrelated resource | No history read, message or wait |
| Known peer and sufficient current facts | No listing or repeated read; continue from the known dependency |
| Known peer, only progress needed | Compact native wait/status for that ID; no listing loop |
| Next test or same-scope correction | Reuse applicable discovery; no new scan |
| Recent listing omits an owner | Partial coverage; no archive sweep or claim that the resource is free |
| Idle peer owns a shared target | Preserve ownership and use the native resource guard |
| Concrete ownership fact missing for one candidate | Minimal recent read with outputs omitted; expand only for the unresolved fact |
| Same CWD, unrelated products | Compare affected object; continue if no material intersection |
| Different CWD/projectless chats, same canonical repo | Resolve actual source/contract rather than assuming independence |
| Same checkout/file | Isolate own candidate or agree authorized sequencing |
| Different files, changing API/schema | Resolve version before dependent implementation; independent research can proceed |
| Stable contract, separate mutable environments | Parallel parts with exact bases and combined acceptance |
| Different repos, one DB/service | Native isolation/serialization of affected operation; local preparation continues |
| Worktrees share browser/cache/port | Verify actual runtime origin and separate resource or serialize |
| Both see "free" in a listing | Neither has a reservation; isolate or use native atomic protection |
| Send accepted, no reply | Unknown agreement; bounded wait and independent work |
| Idle/missing owner or expired advisory claim | Reconcile liveness/current state; do not steal or delete locks |
| Old/duplicate response | Check assignment/version; no repeated external effect |
| Human changes the task | Latest direct request controls; re-evaluate affected dependencies |
| Both chats wait on each other | Resolve dependency order; no ping loop, duplicate writer or forced takeover |
| Host/tools unavailable or listing partial | Preserve known work and disclose coverage; no internal-db/UI workaround |
| Peer asks for reply without direct human grant | No message; prepare permitted facts/pending packet and continue independent work |
| Candidate ready, target/base changed | Reconcile exact versions, integrator and affected checks before integration |
| Completed task resumed | Re-read current owner/target/obligations; old intent is not automatically restored |

## Discriminating recovery probe

Prepare a disposable Git fixture where the assigned leaf already committed its
owned change and the authorized target already contains it, but the final reply
is missing. Give the agent the accepted assignment and actual paths, not an
invented PASS. It should inspect HEAD/diff/dirty state and the target, preserve
both, and perform only missing acceptance. A second implementation, merge or
external action is a failure of the probe. Repeat with dirty partial work and
unknown liveness: bytes must survive and no replacement writer may start.

These fixtures do not establish crash recovery, complete discovery or native
root-to-root delivery. Test such claims separately using authorized existing
chats or an explicitly requested pilot, with actual tools and outcome readback.
