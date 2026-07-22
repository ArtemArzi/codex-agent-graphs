# Профили и агенты

## Матрица

| Профиль | План | Реализация | Итог | Независимых запусков |
|---|---|---|---|---:|
| `light` | self | root | self | 0 |
| `standard` | self | root или обычно 1 bounded worker | `task_result_reviewer` | 1–2 |
| `complex` | `task_plan_reviewer` | root + обычно 1 bounded worker | `task_result_reviewer` | 2–3 |
| `critical` | `task_plan_reviewer` | root + bounded worker + `task_risk_reviewer` | `task_result_reviewer` | 3–4 |

В режиме `plan` нет проверки результата реализации. Для `complex/critical` проверяющий плана становится внешним узлом `verify`; для `light/standard` корневой агент останавливается после собственной проверки.

## Дополнительные роли

- `task_explorer` — read-only локализация одной независимой области большой кодовой базы. Обычно 0, максимум 2.
- `task_worker` — реализация одного независимого slice по immutable packet. Обычно 0–1, максимум 2 normal packet/worker receipts; только после verifier reject допустим один дополнительный bound repair worker. Root принимает реальный diff, повторяет один быстрый check и владеет checkpoint по [implementation-slices.md](implementation-slices.md).
- Агенты Research — только когда реально запущен внешний или глубокий исследовательский проход.

Все роли — leaf-only. Они не создают потомков, не коммитят и не пушат. Корневой агент интегрирует изменения, запускает итоговые тесты и владеет `task.json`.

## Общие пределы

- Не более 5 агентов на обычный Task Delivery run, включая Research.
- Не более 2 одновременно активных агентов.
- Исключение — уже обоснованный `critical` review из трёх разных ролей; это не разрешение на дополнительные роли.
- Не создавай агента на каждый файл, дублирующий scout или обзор обзора.
- Один verifier repair; повторный reject блокирует граф.

Независимый агент нужен для поиска контрпримеров. Если он только пересказывает diff, проверка не состоялась.
