# Профили и агенты

## Матрица

Apply the global complex-engineering/material-risk threshold to EVERY review instruction below. Simple engineering gets one auxiliary `block_reviewer` result review; ordinary non-engineering reviews also use `block_reviewer` for the complete bounded artifact. Trivial chat/wording stays root-only. Only complex engineering or concrete material consequences require the whole-plan/whole-result acceptance pair. Length, a skill invocation, a profile label or a review request alone does not select an acceptance role. Stage/skill switches and routine same-outcome repairs reuse valid acceptance and the existing reviewer. Keep additional focused reviews bounded and justified; do not split risky work to evade acceptance.

Матрица ниже описывает legacy controller defaults. Если унаследованная
user-level policy требует independent acceptance, она имеет приоритет над
self/risk-triggered ячейками: только complex engineering / material risk требует
свежий `task_plan_reviewer` и другого whole-result reviewer. Простое инженерное
изменение получает одно `block_reviewer`; обычные неинженерные ревью используют
эту же auxiliary роль. Эти review operations выполняются внутри `work`, поэтому
обязательная приёмка не требует нового graph node или controller run.

| Профиль | План | Реализация | Итог | Независимых запусков |
|---|---|---|---|---:|
| `light` | self* | root | self* | 0 |
| `standard` | self* | root; worker только для независимого slice | self* либо risk-triggered verifier | 0–2 |
| `complex` | self* либо uncertainty-triggered plan reviewer | root; worker только для независимого slice | self* либо risk-triggered verifier | 0–3 |
| `critical` | self* либо uncertainty-triggered plan reviewer | root + `task_risk_reviewer`; worker только для независимого slice | `task_result_reviewer` | 2–4 |

`*` обозначает legacy root verification. При активной policy простое инженерное
изменение получает одно итоговое `block_reviewer`, а complex engineering /
material risk — whole-plan/whole-result с разными identities. Обычные
неинженерные ревью используют `block_reviewer`; тривиальные ответы остаются root-only.

Без унаследованной policy режим `plan` не получает reviewer только из-за
профиля. Plan reviewer нужен при реальной неоднозначности архитектуры,
evidence или acceptance либо по явному запросу. `standard/complex` result
reviewer также risk-triggered; `critical` сохраняет risk review и итоговый
verifier. При активной policy её порог сложности/риска определяет, нужны ли
`task_plan_reviewer` и другой whole-result acceptor. Простые задачи остаются
без пары общих приёмщиков, но простые инженерные изменения получают одно
`block_reviewer`; название профиля само по себе не включает whole acceptance.

## Дополнительные роли

- `task_explorer` — read-only локализация одной независимой области большой кодовой базы. Обычно 0, максимум 2.
- `task_worker` — независимая область реализации по immutable packet, обычно 0–1 одновременно. В 3.9 `--slice-budget` — оценка, не потолок числа последовательных принятых частей; root может выполнять этапы без worker. Repair получает один отдельный packet только после verifier reject. Root проверяет реальный diff, повторяет один быстрый check и владеет checkpoint по [implementation-slices.md](implementation-slices.md).
- Агенты Research — только когда реально запущен внешний или глубокий исследовательский проход.

Все роли — leaf-only. Они не создают потомков, не коммитят и не пушат. Корневой агент интегрирует изменения, запускает итоговые тесты и владеет `task.json`.

## Общие пределы

- Root-only — fast path для domain work любого профиля. Не запускай worker
  только из-за размера задачи или свободного слота; обязательные policy
  acceptors остаются отдельным исключением и не заменяются self-review.
- Считай только фактические agent starts. Не резервируй агента под возможный
  repair и не приравнивай read-only/evidence/controller этап плана к worker
  slice.
- В graph 3.9 суммарные запуски учитываются как расход; фиксированного потолка на всю задачу нет. Каждый запуск должен оправдывать стоимость передачи и приёмки. Активные 3.8 runs сохраняют прежние границы.
- По умолчанию не более 2 одновременно активных субагентов. Ограничения хоста сохраняются; при недоступности делегирования продолжай локальную работу и явно сохраняй пробел независимой проверки.
- Ровно один свежий агент каждой обязательной whole-review роли. Focused/block
  reviewers могут идти рядом с acceptor над тем же кандидатом, если закрывают
  конкретный риск; несколько одинаковых focused reviewers допустимы только по
  явному deep/multi-review запросу.
- Не создавай агента на каждый файл, дублирующий scout или обзор обзора.
- Один verifier repair; повторный reject блокирует граф.
- Same-scope retry обязан назвать новое evidence; две подряд безуспешные попытки блокируют граф независимо от общего slice budget.

Независимый агент нужен для поиска контрпримеров. Если он только пересказывает diff, проверка не состоялась.
