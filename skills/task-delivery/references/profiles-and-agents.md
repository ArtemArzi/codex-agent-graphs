# Профили и агенты

## Матрица

| Профиль | План | Реализация | Итог | Независимых запусков |
|---|---|---|---|---:|
| `light` | self | root | self | 0 |
| `standard` | self | root; worker только для независимого slice | self либо risk-triggered `task_result_reviewer` | 0–2 |
| `complex` | `task_plan_reviewer` | root; worker только для независимого slice | self либо risk-triggered `task_result_reviewer` | 1–3 |
| `critical` | `task_plan_reviewer` | root + `task_risk_reviewer`; worker только для независимого slice | `task_result_reviewer` | 3–4 |

В режиме `plan` нет проверки результата реализации. Для `complex/critical`
проверяющий плана становится внешним узлом `verify`; для `light/standard`
корневой агент останавливается после собственной проверки. В реализации
`standard/complex` result reviewer не является следствием имени профиля:
нужен фактический risk/uncertainty signal. `critical` всегда verified.

## Дополнительные роли

- `task_explorer` — read-only локализация одной независимой области большой кодовой базы. Обычно 0, максимум 2.
- `task_worker` — реализация одного независимого slice по immutable packet. Обычно 0–1. Default budget — 2 normal packet/worker receipts; явный `--slice-budget` допускает до 6 последовательных slices; только после verifier reject допустим один дополнительный bounded repair worker. Root принимает реальный diff, повторяет один быстрый check и владеет checkpoint по [implementation-slices.md](implementation-slices.md).
- Агенты Research — только когда реально запущен внешний или глубокий исследовательский проход.

Все роли — leaf-only. Они не создают потомков, не коммитят и не пушат. Корневой агент интегрирует изменения, запускает итоговые тесты и владеет `task.json`.

## Общие пределы

- Root-only — fast path для любого профиля. Не запускай worker только из-за размера задачи или свободного слота.
- Не более 8 агентов на Task Delivery run, включая Research и явный bounded slice budget.
- Не более 2 одновременно активных агентов.
- Ровно один агент каждой review-роли. Несколько block reviewers допустимы только по явному deep/multi-review запросу вне обычного Task Delivery receipt.
- Не создавай агента на каждый файл, дублирующий scout или обзор обзора.
- Один verifier repair; повторный reject блокирует граф.
- Same-scope retry обязан назвать новое evidence; две подряд безуспешные попытки блокируют граф независимо от общего slice budget.

Независимый агент нужен для поиска контрпримеров. Если он только пересказывает diff, проверка не состоялась.
