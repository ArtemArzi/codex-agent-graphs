# Shared website check and evidence contract

Contract revision 1. This is the package's single shared evidence reference;
project quality documents own actual requirements and commands. Deployment owns
release execution/state. This reference is not a second test registry or receipt
schema and does not change released task/graph formats.

For each material check retain, using the existing record format:

| Field | Meaning |
| --- | --- |
| Requirement/check | What must hold, owning document and stable check ID if useful |
| Subject | Source SHA/digest, artifact/config and relevant interface version |
| Environment | Local fixture/staging/production, target/provider identity and scope |
| Method | Actual native argv/cwd or bounded observation, runner/trust and prerequisites |
| Outcome | Expected behavior, observed result, original evidence, time and coverage |
| Gaps | Missing/failed/skipped checks, consequence, owner and next allowed trigger |
| Dependencies | Code, test, recipe, toolchain, config, policy, data and external state |

Use safe aliases/private version references for secrets, never their values or
public hashes. A supplied JSON `passed`, exit 0, source marker, cache hit or old
receipt does not by itself establish the expected result. Keep source review,
executed local checks, activated target, provider delivery and human acceptance
separate. `not_applicable` needs a reason; unknown/not_run is not PASS. Do not
average a blocker away with a numeric score.

Native owners decide reuse by complete unchanged inputs and trust. A skill/mode
switch alone adds no new review pair or full-suite rerun. Changed build-time
origin/config creates a different static artifact even at the same source SHA.
Changed route/robots/redirect affects URL checks; event/consent/counter changes
affect measurement; schema/worker/provider changes affect intake/delivery.
Unknown dependency closure widens checking. Fresh live ACL/health/account/target
observations remain necessary independently of code hashes.

Use the available Deployment check/evidence reference for release placement and
transfer; do not duplicate its rules. Handoff carries original request/decisions,
exact subjects, owners, check results/original receipts, affected inputs, gaps,
next action and applicable authority. Link the native rollout journal instead of
copying mutable release state. Apply current host review policy without fixing
models, agent counts or controllers in this package.

Run effects only within the named authorised environment. In a local form test,
allowlisted intake/fake-delivery POSTs legitimately carry synthetic fields and
protocol keys. Prevent unrelated egress and leaks into analytics, URLs, normal
logs and exported raw evidence; sanitise saved captures. Blocking every payload
would make the intake test invalid. A restore, fault injection, account event or
test lead is an action with its own consequences, not an automatic audit step.

Evidence/version refresh: record check-contract/profile version and source date
when relevant. Breaking receipt/key semantics need a compatibility/migration
decision in the project owner. Refresh dynamic provider rules before changing a
real integration; a dated source snapshot is not a current account observation.
