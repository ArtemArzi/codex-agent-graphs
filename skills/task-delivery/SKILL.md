---
name: task-delivery
description: >-
  Провести одну программную задачу от исследования и Markdown-плана до реализации, тестов и проверки результата. Использовать для режима только плана, реализации по уже проверенному плану, полного цикла plan-to-code, исправления или явного вызова $task-delivery. Граф удерживает scope, квитанции и лимиты, но оставляет исследование, проектирование и реализацию сильной модели.
---

# Task Delivery

Доведи одну задачу до доказанного результата. Граф — это короткий контроль границ, а не пошаговый заменитель инженерного мышления.

## Главный маршрут

Все режимы используют один граф:

`work → complete` или, только когда профиль либо фактический риск требует независимости, `work → verify → complete`.

Внутри `work` корневой агент сам исследует кодовую базу, выбирает навыки, создаёт и проверяет план, реализует, запускает тесты и формирует один `task.json`. Не превращай эти действия в обязательные узлы графа.

## Определи режим

- `plan` — исследовать, сохранить и проверить план, затем остановиться без изменения производственного кода.
- `implement` — открыть точный ранее проверенный план, проверить дрейф, реализовать и проверить результат.
- `full` — план, реализация, тесты и итоговая проверка в одном вызове без промежуточного согласования.

Если пользователь явно просит сначала обсудить план, выбери `plan`. Если он даёт готовый план или просит продолжить после `plan`, выбери `implement`. Иначе выбери `full`.

## Найди владельца плана

Перед `init` прочитай корневой и ближайший `AGENTS.md`, карту документации и существующие соглашения проекта. План всегда должен быть Markdown-файлом внутри целевого проекта.

- Сначала используй уже установленный каталог планов: например, `docs/development/plans/active/`, `docs/plans/.../active/` или `.planning/`.
- Передай точный путь через `--plan`.
- Не создавай второй каталог только ради этого навыка.
- Если проект не задаёт владельца и `--plan` не передан, runner использует `docs/tasks/<task-id>/PLAN.md`.

```bash
python3 scripts/task_graph.py init \
  --root <repo> --mode <plan|implement|full> \
  --task-id <id> --title "<название>" \
  --outcome "<наблюдаемый результат>" \
  --plan <relative/path/PLAN.md> --profile <light|standard|complex|critical> \
  --implementation-strategy <auto|root-only|delegated-sequential>
```

Относительные команды запускай из каталога установленного навыка. После `init` используй абсолютные команды, возвращённые runner.

## Выбери профиль, а не число этапов

Оцени риск по области, обратимости, новизне, внешним контрактам и последствиям ошибки.

- `light` — малая локальная обратимая правка, ясные критерии: самопроверка плана и результата, 0 независимых агентов.
- `standard` — обычная продуктовая задача: самопроверка плана и 1 независимая проверка результата.
- `complex` — несколько модулей, новая граница или неоднозначный план: 1 проверка плана и 1 проверка результата.
- `critical` — безопасность, данные, миграция, деньги, необратимость или широкий blast radius: проверка плана, проверка риска и итоговая проверка, всего 3 независимых запуска.

`plan` в профилях `complex/critical` использует проверяющего плана как внешний узел `verify`; проверяющий риска нужен только для реализации. Низкая уверенность всегда поднимает результат в `verify`. Подробная матрица — в [profiles-and-agents.md](references/profiles-and-agents.md).

## Один рабочий проход

1. Выполни `git status --short`; все существующие изменения считай пользовательским baseline.
2. Прочитай только относящиеся к задаче инструкции, текущий план и исходный код. Для неясной большой кодовой базы допустимы до двух независимых `task_explorer`; для обычной локализации работай сам.
3. Выбери навыки и инструменты по задаче:
   - локальный поиск, LSP/AST и навыки кодовой базы — сначала для внутреннего исследования;
   - `$research` — только для внешних, текущих или смешанных фактов; его агенты входят в общий лимит Task Delivery;
   - MCP discovery обязателен: осмотри доступные `mcp__*` tools/resources и вызови релевантный сервер до нативного внешнего пути;
   - provider-specific MCP используй для данных его продукта, Context7 — для официальной документации библиотек, research MCP — для внешнего поиска, Playwright или другой live MCP — для относящейся к acceptance живой системы;
   - если задача строго локальная и подходящего сервера нет либо релевантный MCP не сработал, зафиксируй fallback и продолжай локально; не выполняй внешнюю запись без полномочий.
4. Создай или обнови один план. В замороженной части должны быть outcome, основания, acceptance, шаги, тесты, stop conditions и точный `task-delivery:scope`. Не веди гигантский журнал снимков внутри плана.
5. Проверь план сам. В `complex/critical` вызови `task_plan_reviewer` до реализации. В режиме `implement` повторно используй прошлый review только если runner принял неизменный план и scope.

Пункты 6–7, `slice-accept`, checkpoint, scope amendment и verifier repair ниже относятся к новым graph `3.4` runs. Активный `3.3.0` run завершай по его v1 packet и inline root-acceptance contract; не вызывай для него команды `3.4`.

6. Выбери implementation strategy один раз. `light` по умолчанию `root-only`; в `standard/complex/critical` предпочитай `delegated-sequential` и отдай fresh `task_worker` хотя бы один независимо проверяемый bounded slice. Пропускай slice только для действительно маленькой или тесно связанной работы и зафиксируй конкретную причину. Если пользователь сказал «реализуй слайсами», `slice`, `делегируй реализацию` или эквивалент, запусти `init --implementation-strategy delegated-sequential`: завершение без packet/receipt/acceptance запрещено. До spawn создай immutable packet по [implementation-slices.md](references/implementation-slices.md), передай точный path и digest, зафиксируй worker receipt, затем сам проверь diff и выполни `slice-accept`. `plan` не запускает workers; `implement` связывает packet с точным прошлым review; `full` создаёт его после валидного плана. `delegated-parallel` остаётся fail-closed без изолированных worktrees.
7. На каждом slice запускай только быстрые проверки его области. Worker обновляет или добавляет затронутые unit/integration/E2E tests согласно `test_impact`; root повторяет минимум один exact slice check. Дорогие интеграционные и E2E рубежи из `deferred_final_checks` запускай один раз после интеграции всех slices и внеси exact command/purpose в `task.json.tests`. Не утверждай успех по diff или словам агента.
8. В `critical` отдельно вызови `task_risk_reviewer`. Создай один `task.json` по [control-artifact.md](references/control-artifact.md).

В `capabilities` обязательно запиши `mcp:<server>` для реально использованного MCP либо `mcp:fallback:<reason>` после проверки доступности. Нативный web/browser и затем `curl` являются fallback, а не первым выбором при наличии подходящего MCP.

В graph `3.4` каждый делегированный slice получает только применимые skills, ближайшие инструкции, must-read файлы и уже проверенный MCP/research-контекст. Worker обязан применить required skills и вернуть `capabilities_used`; недоступный skill или недостаточный контекст означает `needs_context`. Root самостоятельно проверяет реальный diff, ownership и тесты, фиксирует отдельный immutable acceptance до следующего packet. Итоговая delegated delta обязана состоять ровно из union root-accepted paths; скрытых root integration edits нет. В `task.json` переносится только digest acceptance, а worker report не является доказательством.

В graph `3.4` после `slice-accept` runner создаёт компактный `context-checkpoint.json`: принятые digests и exact paths, проверенные discoveries, исходный `plan_scope`, deferred checks и следующий objective. `plan_scope` не выдаётся за вычисленный остаток directory scope. Если нужен ещё один slice, сначала выполни `context-rehydrate`; следующий packet будет связан с точным checkpoint SHA-256. Физический host compact можно использовать по ситуации, но он не является частью correctness contract и не нужен после последнего slice.

Если runtime evidence обнаружил пропущенный технический путь, не выдумывай токен подтверждения. `scope-amend` разрешён root без человека только для bounded paths, связанных с exact reviewed base, когда outcome, acceptance, публичный контракт, данные, безопасность, внешнее состояние и профиль риска не меняются. Миграции, secrets, env и CI workflows требуют нового решения и review. Подробный JSON-контракт находится в [implementation-slices.md](references/implementation-slices.md).

Для обычного самостоятельного завершения:

```bash
python3 scripts/task_graph.py record --run <run-dir> --node work --outcome succeeded
```

Когда профиль требует проверку или корневой агент сам эскалировал риск:

```bash
python3 scripts/task_graph.py record --run <run-dir> --node work --outcome verify
```

Проверяющий получает точные SHA-256 `task.json`, плана и реализации, пытается опровергнуть результат и возвращает `verification.json`. Корневой агент записывает этот JSON в run-каталог:

```bash
python3 scripts/task_graph.py record --run <run-dir> --node verify --outcome <succeeded|failed>
```

Один `reject` возвращает работу в `work`. Второй `reject` блокирует run: не создавай бесконечный цикл исправлений.
Для delegated graph `3.4` run после первого reject возьми `verification_repair_work_sha256` из ответа runner, rehydrate latest checkpoint и создай ровно один дополнительный repair slice. Он проходит обычные worker receipt, root acceptance и повторный verify; неуспех этого repair slice блокирует run.

## Паузы и человеческий контроль

Не спрашивай человека о безопасной локальной реализации, формулировке, выборе теста или восстановимом инженерном решении. Остановись только когда отсутствуют полномочия либо ответ меняет продуктовую семантику, публичный контракт, данные, необратимое внешнее действие или существенный риск.

Запиши вопрос в `task.json` и выполни:

```bash
python3 scripts/task_graph.py record --run <run-dir> --node work --outcome decision
python3 scripts/task_graph.py decide --run <run-dir> --answer "<точный ответ>"
```

Режим `plan` сам является согласованной остановкой: после `complete` состояние станет `awaiting_implementation`. Режим `full` не добавляет искусственную паузу между планом и кодом.

## Завершение и совместимость

```bash
python3 scripts/task_graph.py complete --run <run-dir>
python3 scripts/task_graph.py status --run <run-dir>
python3 scripts/task_graph.py retry --run <run-dir> --node <work|verify>
```

`complete` повторно проверяет immutable receipts, digest плана, фактическую дельту и тестовую квитанцию. Для `plan` он сохраняет reviewed plan и останавливается. Для `implement/full` он автоматически создаёт совместимый `HANDOFF.md`, закрывает задачу и, если Project Start активен, атомарно открывает обязательную документационную maintenance.

Глобальный hook не является источником истины этого протокола. Не меняй hooks для запуска Task Delivery: checkpoint создаёт и проверяет сам skill. После отдельного внедрения hook может только повторно вызвать `context-rehydrate` на `SessionStart(source=compact)`; изменение hook во время активных задач требует отдельной безопасной активации.

Не редактируй канонические документы Project Start внутри Task Delivery: передай фактическую документационную дельту через handoff.

Состояния schema v2 не мигрируй на месте. Заверши их прежним `task_delivery.py` по [legacy-v2-resume.md](references/legacy-v2-resume.md). Активные graph `3.3.0` runs завершаются по своему v1 slice contract; новые runs используют `3.4.0`. Все новые задачи запускай через `task_graph.py`.

## Служебные ресурсы

- `graph.json` — исполняемый трёхузловой контракт v3.
- `scripts/task_graph.py` — состояние, baseline, scope, digest, retry и handoff.
- `references/implementation-slices.md` — опциональный packet/receipt/acceptance contract внутри `work`.
- `scripts/task_delivery.py` и старые templates/references — только совместимое возобновление v2.
- `scripts/test_task_graph.py` — целевые проверки нового короткого маршрута.
