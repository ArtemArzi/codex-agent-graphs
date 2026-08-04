# Профили и агенты

## Матрица

| Профиль | План | Реализация | Итог | Независимых запусков |
|---|---|---|---|---:|
| `light` | self | root | self | 0 |
| `standard` | self | root; worker только для независимого slice | self либо risk-triggered verifier | 0–2 |
| `complex` | self либо uncertainty-triggered plan reviewer | root; worker только для независимого slice | self либо risk-triggered verifier | 0–3 |
| `critical` | self либо uncertainty-triggered plan reviewer | root + `task_risk_reviewer`; worker только для независимого slice | `task_result_reviewer` | 2–4 |

Режим `plan` не получает reviewer только из-за профиля. Plan reviewer нужен
при реальной неоднозначности архитектуры, evidence или acceptance либо по явному
запросу. `standard/complex` result reviewer также risk-triggered; `critical`
сохраняет risk review и итоговый verifier.

## Дополнительные роли

- `task_explorer` — read-only локализация одной независимой области большой кодовой базы. Обычно 0, максимум 2.
- `task_worker` — реализация одного независимого slice по immutable packet. Обычно 0–1. Default budget — 2 normal packet/worker receipts; явный `--slice-budget` допускает до 6 последовательных slices с учётом фактически обязательных profile reviews. Critical допускает до 6 normal slices в одном run: repair заранее место не отнимает и получает отдельный условный budget только после verifier reject. Root принимает реальный diff, повторяет один быстрый check и владеет checkpoint по [implementation-slices.md](implementation-slices.md).
- Агенты Research — только когда реально запущен внешний или глубокий исследовательский проход.

Все роли — leaf-only. Они не создают потомков, не коммитят и не пушат. Корневой агент интегрирует изменения, запускает итоговые тесты и владеет `task.json`.

## Общие пределы

- Root-only — fast path для любого профиля. Не запускай worker только из-за размера задачи или свободного слота.
- Считай только фактические agent starts. Не резервируй агента под возможный
  repair и не приравнивай read-only/evidence/controller этап плана к worker
  slice.
- Не более 8 агентов на Task Delivery run, включая Research и явный bounded slice budget.
- Не более 2 одновременно активных агентов.
- Ровно один агент каждой review-роли. Несколько block reviewers допустимы только по явному deep/multi-review запросу вне обычного Task Delivery receipt.
- Не создавай агента на каждый файл, дублирующий scout или обзор обзора.
- Один verifier repair; повторный reject блокирует граф.
- Same-scope retry обязан назвать новое evidence; две подряд безуспешные попытки блокируют граф независимо от общего slice budget.

Независимый агент нужен для поиска контрпримеров. Если он только пересказывает diff, проверка не состоялась.
