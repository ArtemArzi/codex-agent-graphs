# Task Delivery: context continuity, staged tests, and bounded scope amendments

## Conclusion

Keep the graph at `work -> optional verify -> complete`. Add three small control
contracts inside `work`, not new graph nodes:

1. an accepted-slice checkpoint that is rehydrated before the next slice;
2. a two-level test contract (`slice_checks` and `deferred_final_checks`) with
   explicit test impact (`reuse`, `update`, `add`, or `not-applicable`);
3. a bounded scope-amendment receipt that the root may approve autonomously when
   the task outcome and risk boundary do not change.

Do not change the user's global hook for this release. Codex already supports
`PreCompact`, `PostCompact`, and `SessionStart(source=compact)`, but changed
non-managed hook definitions require renewed trust and matching hooks from
multiple sources run concurrently. The Task Delivery controller is the safer
source of truth; a hook can be evaluated later as an optional no-op bridge.
[OpenAI Hooks](https://learn.chatgpt.com/docs/hooks)

## Evidence and implications

### Context continuity

Anthropic recommends the smallest high-signal context and identifies compaction,
structured notes, and focused subagents as complementary techniques for
long-horizon work. Structured notes live outside the context window and are
loaded later; focused workers return condensed evidence instead of their whole
trace. This supports a compact controller-owned checkpoint rather than saving
the root transcript. [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

LangChain's documented checkpointer pattern persists thread state, updates it at
steps, and reads it again at the start of each step. The transferable invariant
is therefore `persist after acceptance -> read before next slice`, independent
of whether the host physically compacted the chat.
[LangChain short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)

Codex exposes manual `/compact`, while hooks expose automatic and manual compact
events. The skill must remain correct without forcing either mechanism.
[Codex slash commands](https://learn.chatgpt.com/docs/reference/slash-commands)

The checkpoint should contain only verified state:

- run, graph, plan, baseline, and accepted-slice digests;
- accepted changed paths and root-replayed checks;
- verified discoveries and unresolved risks;
- the next objective, original plan scope, and exact accepted paths;
- final checks still deferred.

`slice-create` should rehydrate this checkpoint and bind its digest into the next
packet. A normal `ready`/`status` should expose the exact rehydrate command when
one is required. No transcript or free-form chain of thought belongs in the
checkpoint.

### Staged tests

Playwright explicitly recommends an affected-test pass for fast feedback, but
calls it heuristic and says the full suite must still run afterward. This maps
directly to slice-local checks followed by an integrated final gate.
[Playwright CI](https://playwright.dev/docs/ci)

Playwright projects, filters, tags, and dependencies allow focused smoke or
feature packs without repeatedly booting every environment for each slice.
[Playwright projects](https://playwright.dev/docs/test-projects)

Each slice packet should declare:

- `test_impact`: existing coverage to reuse, stale coverage to update, missing
  coverage to add, or a justified `not-applicable`;
- `slice_checks`: fast checks that the worker must pass;
- `deferred_final_checks`: expensive integration/E2E/project gates that the root
  runs once after all slices integrate.

The worker may create or update E2E source in its owned paths, but normally does
not repeatedly start the full stack. Root acceptance replays at least one
independent slice check. Final completion requires every deferred final check to
appear passed in `task.json.tests`. A failing final gate gets one bounded repair
wave. In delegated mode this may be one additional packet bound to the rejected
candidate; it reuses normal root acceptance and final verification rather than
adding a graph node. A second failure invokes the existing Development Recovery
stop rule.

### Scope amendments and the observed blocker

The current controller has no `amend` command. It only rejects paths outside the
frozen Markdown scope. Therefore the quoted `Разрешаю amendment <sha>` blocker
was model-created ceremony, not a deterministic Task Delivery requirement. It
occurred because two implementation-required paths were omitted from the plan
and the instructions only described user decisions, not safe technical scope
expansion.

External guidance favors enforced boundaries that permit autonomy inside them
instead of per-action approval prompts; Anthropic reports fewer prompts when
filesystem/network boundaries are explicit.
[Anthropic sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
GitHub likewise recommends researching, planning, iterating, testing, and
reviewing changes on a branch before merge rather than treating every iteration
as a new user decision.
[GitHub coding-agent practices](https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results)

Add a controller command that records a scope amendment without a new graph
node. Root may approve it autonomously only when all are true:

- outcome, acceptance, public behavior, data model, security boundary, and
  external side effects remain unchanged;
- added paths are repository-local, reversible, evidence-backed, and needed for
  implementation, tests, or owned documentation;
- the risk profile does not increase and protected paths are not introduced.

The receipt binds the old/new plan digests, old/new scope, added paths, reason,
evidence paths, and authority (`root-technical`). Product-semantic, public
contract, security/data, irreversible, or broad amendments still require an
ordinary semantic user decision and invalidate the relevant plan review. The
controller may bind that answer to internal digests, but it must never ask the
user to echo an amendment hash.

## Recommended implementation

- Bump Task Delivery to graph `3.4.0`; preserve `3.3.0` active-run compatibility.
- Add `context-checkpoint`, `context-rehydrate`, and `scope-amend` controller
  commands as operations inside `work`.
- Require a checkpoint after each root-accepted slice and rehydrate it before a
  subsequent `slice-create`.
- Extend slice packet/receipt validation with test impact and two-level checks.
- Keep `plan` mode free of slices/checkpoints; apply the changes to `implement`
  and `full` only.
- Do not install or modify global hooks until focused tests, repository-wide
  gates, fresh-agent evaluation, and independent review are green.

## Residual risks

- Host compaction timing remains outside the skill's control; correctness must
  be proven by explicit rehydrate tests, not by assuming a compact event.
- Project test commands vary, so the controller can validate declared evidence
  but cannot infer every relevant E2E pack semantically.
- Scope-amendment classification remains partly model-owned; deterministic
  protected-path and risk-increase guards must fail closed.
