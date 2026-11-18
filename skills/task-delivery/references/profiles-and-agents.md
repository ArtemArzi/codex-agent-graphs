# Профили и агенты

## Матрица

Apply the global complex-engineering/material-risk threshold to EVERY review instruction below. Simple engineering gets one auxiliary `block_reviewer` result review; ordinary non-engineering reviews also use `block_reviewer` for the complete bounded artifact. Trivial chat/wording stays root-only. Only complex engineering or concrete material consequences require the whole-plan/whole-result acceptance pair. Length, a skill invocation, a profile label or a review request alone does not select an acceptance role. Stage/skill switches and routine same-outcome repairs reuse valid acceptance and the existing reviewer. Keep additional focused reviews bounded and justified; do not split risky work to evade acceptance.

При действующей общей политике выбирай уровень проверки по сложности задачи и последствиям ошибки. Для запуска графа учитывай также версию, профиль и режим, записанные в его состоянии.

| Задача | Кто проверяет |
|---|---|
| Тривиальная правка текста или настройки с известным ожидаемым значением | Основной агент проверяет результат напрямую в пределах исключений общей политики. |
| Простая инженерная правка или обычное ревью документа | Один `block_reviewer` проверяет готовый результат. |
| Сложная инженерная задача или существенный риск | `task_plan_reviewer` проверяет план до реализации. Готовый результат проверяет другой `task_result_reviewer` либо выбранный по общей политике `deep_reviewer`. |

В графе `3.10.0` для `light` и `standard` поддерживается `block_reviewer` в узле `verify`. Для `complex` и `critical` режим `plan` заканчивается независимой проверкой плана. В `implement` и `full` нужны подтверждение точного плана и отдельная итоговая проверка. При `critical` реализации опиши, какие риски покрывает общая приёмка. Если остаётся отдельный конкретный риск, запиши его в `risk_review.separate_risk` и привлеки `task_risk_reviewer`. Иначе укажи `null`. См. [формат подтверждения](control-artifact.md).

Без унаследованной политики учитывай сигналы для независимой проверки, указанные в навыке, и обязательные проверки версии запущенного графа. Ранее начатые запуски сохраняют свои роли и подтверждения. В частности, `3.9.2` требует отдельного `task_risk_reviewer` для `critical` в режимах `implement` и `full`.

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
