## Specification and implementation divergence

Apply this invariant to all implementation work, regardless of which graph, skill or ad hoc workflow started it.

- Ошибка graph/controller protocol, digest, marker, receipt, runner budget, run partition, checkpoint schema или отсутствие optional reviewer не является specification/implementation divergence. Сделай максимум одну bounded controller repair, затем degrade или отключи control и продолжай код. Не запускай recovery и не считай controller ceremony попыткой без нового evidence. Если граф явно отключён пользователем, не активируй его снова.
- Treat an accepted specification as intended behavior, a plan as a proposed method, code as a candidate implementation, and tests or runtime observations as evidence. Do not change the specification or weaken evidence merely to make the candidate pass.
- Check for unresolved divergence after surprising evidence and before a meaningful commit. Trigger recovery immediately on a direct contract contradiction, material unplanned workaround or scope growth, suspected false checkpoint, security/data/external-state mismatch, or an attempted spec/test relaxation. Also trigger after two consecutive attempts create no new evidence.
- On a trigger, pause the current approach, reproduce the issue, locate the first false assumption in the specification, plan, implementation or verification, and use `$development-recovery` to choose `rebuild-from-checkpoint` or `repair-forward`.
- Keep routine local defects lightweight: repair them directly when specification and plan assumptions remain valid.
- Preserve user changes, failed-path evidence and the best-known verified state. Never destructively rewrite shared history as an automatic recovery action.
- Continue autonomously for bounded technical corrections. Ask the user when intended behavior must change, business contracts are ambiguous, or recovery would destructively alter history or external state.
