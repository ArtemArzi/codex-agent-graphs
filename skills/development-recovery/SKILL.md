---
name: development-recovery
description: Recover implementation work when code, tests, scope, or observed behavior diverges from an accepted specification or implementation plan. Use after a direct contract contradiction, repeated attempts without new evidence, an unplanned workaround or material scope increase, pressure to weaken a test or specification to fit the code, or suspicion that an earlier checkpoint rests on a false assumption. Classify the first false assumption, then choose a safe rebuild from a verified checkpoint or a repair forward while preserving Git evidence. Apply independently of Project Start, Research, and Task Delivery.
---

# Development Recovery

Treat recovery as a conditional development control, not as a graph or a mandatory stage. Keep the current root model as the judgment owner. Do not add agents or ceremony unless evidence localization or independent verification genuinely needs them.

## Не триггерить recovery из-за controller

Graph/controller protocol не является specification или implementation
evidence. Digest, marker whitespace, receipt/schema mismatch, agent/reviewer
budget, run partition, checkpoint format, unavailable optional reviewer и другая
служебная несовместимость сами по себе не запускают Development Recovery и не
считаются попыткой без нового evidence. Сделай одну bounded controller repair;
затем degrade/disable control и продолжай обычную работу с кодом. Если
пользователь отключил граф, не активируй его снова. If the user disabled the graph, keep it disabled for that task.

Порог двух попыток относится только к повторным гипотезам о specification,
implementation, tests или runtime behavior. Recovery начинается по semantic,
security, data, external-state либо acceptance divergence, а не ради приведения
служебного графа к зелёному состоянию.

## Establish the divergence

1. Read the accepted specification, active plan, relevant repository instructions, current diff and recent Git history.
2. Reproduce the unexpected behavior with the narrowest reliable check.
3. Identify the last known-green commit or checkpoint and the evidence that made it green. If none is proven, say so.
4. Preserve current user changes and the failed path. Do not rewrite the specification, weaken a test or erase history before classification.

A single ordinary coding defect does not require a recovery record. Enter the recovery decision when any of these signals is present:

- observed behavior directly contradicts an acceptance criterion;
- implementation requires an unplanned workaround or materially larger scope;
- two consecutive attempts produce no new evidence;
- continuing would require changing the specification or test to fit the implementation;
- an earlier design or checkpoint may rest on a false assumption;
- security, data integrity, migration or external-state behavior differs from the accepted contract.

## Classify the first false assumption

Choose one owner. If evidence is insufficient, continue diagnosis instead of guessing.

| Owner | Meaning | Required response |
| --- | --- | --- |
| `spec` | Intended behavior or constraint is wrong, incomplete or contradictory | Obtain the required product decision, update the canonical contract, and invalidate affected plan evidence |
| `plan` | The contract is sound but the proposed design or sequence is not | Keep the specification, revise the affected plan scope, and reconsider from the last green checkpoint |
| `implementation` | Specification and plan remain sound; code diverged | Add or preserve a reproducer and repair the implementation |
| `verification` | Test, fixture, tool, environment or observation is wrong | Correct the evidence source before changing product behavior |

Never amend a specification merely to justify a failed implementation. Put implementation lessons in the plan or recovery record unless they change durable intended behavior.

## Choose the route

Use `rebuild-from-checkpoint` only when all of the following are true:

- the last green checkpoint and its evidence are known;
- the affected scope is bounded and cheap to replay;
- discarding the candidate implementation is cheaper than understanding and repairing it;
- no irreversible migration, production mutation or external side effect would be rewound.

Otherwise use `repair-forward`. Prefer it for mature or widely depended-on code, persisted data, migrations, deployed behavior and expensive downstream work.

When the costs are close, prefer the route that preserves more verified state and introduces less external-state risk.

## Execute safely

For `rebuild-from-checkpoint`:

1. Preserve the failed candidate in Git or another explicit evidence artifact.
2. Create a separate branch or worktree from the verified checkpoint; do not destructively rewrite shared history.
3. Update only the owning specification or plan layer.
4. Reimplement the affected scope and rerun its acceptance evidence before integrating it.

For `repair-forward`:

1. Capture the failure with a regression test or equally strong reproducer.
2. Make the smallest coherent fix that restores the accepted contract.
3. Rerun affected checks and downstream acceptance evidence.
4. Update canonical documentation only when durable behavior or constraints changed.

If an accepted plan is changed, treat review evidence bound to its previous content or SHA as historical. Use no new review for a small implementation-only correction, a focused delta review for material plan changes, and a full independent review only when architecture, security, data or public contracts materially change.

## Record only material course changes

Add a compact recovery section to the active plan or task record only when the chosen route invalidates prior work or changes the course:

```md
## Recovery decision

- Trigger:
- First false assumption: spec | plan | implementation | verification
- Last verified checkpoint:
- Route: rebuild-from-checkpoint | repair-forward
- Invalidated scope or evidence:
- New verifying action:
```

Do not create this record for a routine local defect fixed without changing assumptions.

## Escalate and finish

Ask the user before changing intended product behavior, selecting between materially different business contracts, performing destructive history changes or rewinding external state. Continue autonomously for bounded technical corrections inside the accepted contract.

Finish only after the divergence is reproduced or explained, the selected route is complete, the relevant acceptance evidence is green, and the specification, plan and implementation no longer contradict one another. Report the trigger, classification, route, preserved checkpoint and verification result.
