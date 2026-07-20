# Поддержка канонической документации

## Назначение и граница

Maintenance-route является второй веткой одного графа `project-start`, а не четвёртым пользовательским навыком. Он принимает фактическое состояние репозитория и необязательный `HANDOFF.md` от `task-delivery`, проверяет весь набор канонических документов и возвращает проект в `operational` state.

Route не реализует продуктовую задачу, не меняет смысл одобренных решений и не публикует задачи. `task-delivery` владеет реализацией; `project-start` владеет документацией и рубежами.

## Инварианты

1. `graph.json` — исполняемый договор узлов, ролей, навыков, веток и лимитов.
2. Состояние run хранится в игнорируемом Git каталоге `.agent-graphs/project-start-maintenance/<run-id>/`; долговечный итог записывается в `.project-start/state.json`.
3. Run доступен только из `execution` или `complete` и привязан к точным SHA-256 канонических документов и change receipt.
   Идентификатор также учитывает снимок исходников/конфигурации; повторный запуск на том же входе возобновляется, а изменение репозитория создаёт новый run. Для принудительной периодической проверки передай `--cycle <ключ>`; scheduled-trigger без него использует текущий UTC-день.
4. До узла `documentation-update` канонические документы обязаны оставаться неизменными.
5. `factual` может менять уже известные канонические документы. Единственное разрешённое создание — `<stable-module>/AGENTS.md`, если оно только проецирует уже принятые команды, карту и границы существующего модуля, наследует родителя и не вводит новую политику. Любой другой новый документ, новое полномочие, решение, изменение поведения, архитектурного направления, плана или критериев приёмки является `semantic`.
   `VERIFICATION.md` входит в полный аудит, но является защищённым доказательством: factual-ветка не переписывает его и не пересчитывает связанные record receipts.
6. `documentation-verify` выполняет отдельная read-only роль. PASS запрещён при оставшихся устаревших утверждениях или противоречиях.
   PASS привязывается к точным SHA-256 полного набора документов; factual PASS также обязан совпасть с последним update receipt.
7. Семантическая ветка не пишет документы и не сбрасывает рубеж тихо; она возвращает точную preview-команду `reopen`.
8. Каждый узел создаёт неизменяемый receipt snapshot. Изменение receipt, graph contract или task handoff блокирует продолжение.
9. Допустимы два исправления после reject и два retry одного failed-узла. После исчерпания лимита run остаётся blocked.
10. Объявленные документы не исчезают из набора при удалении: baseline хранит маркер `missing`, а PASS запрещён, пока документ не восстановлен или semantic-ветка не открыла нужный рубеж. Последний полный canonical set сохраняется в Project Start ledger.
11. Все файловые `AGENTS.md`, включая git-ignored локальные инструкции, входят в аудит, кроме служебных/generated/vendor/build/dependency-деревьев.

## Классификация влияния

| Класс | Примеры | Маршрут |
|---|---|---|
| `no-change` | Код и конфигурация соответствуют всем текущим утверждениям | Проверить и завершить без записи документов |
| `factual` | Путь, команда, версия, имя файла, наблюдаемый результат или ссылка изменились без смены принятого смысла; появился устойчивый модуль, которому нужна наследуемая локальная карта | Узкая автоматическая правка/создание вложенного `AGENTS.md` → независимая проверка → обновление затронутого approval digest |
| `semantic` | Изменились бизнес-правило, словарь, граница версии, архитектурный шов, риск, критерий приёмки, план или порядок задач | `reopen discovery`, `foundation` или `planning` |

Если есть сомнение между `factual` и `semantic`, выбирай `semantic`. Цена лишнего reopen ниже цены скрытого изменения договора.
Reject после `no-change` возвращает граф в `drift-audit`, потому что первоначальная классификация опровергнута. Reject после `factual` возвращает в `documentation-update`.

## Артефакты узлов

Все артефакты имеют `schema_version: 1`.

### `intake.json`

```json
{
  "schema_version": 1,
  "reason": "Task TD-042 completed",
  "trigger": "task-delivery",
  "canonical_docs": ["CONTEXT.md", "docs/project/PROJECT.md"]
}
```

`canonical_docs` копируй из `init.data.canonical_docs`; не сокращай список.
Для `--trigger task-delivery` change receipt обязателен. `HANDOFF.md` должен принадлежать завершённому Task Delivery state, содержать `Canonical docs changed: NO` и содержательное `Proposed documentation maintenance`. Task Delivery оставляет канонические документы Project Start нетронутыми; иначе его handoff gate блокируется.

### `capabilities.json`

Команда `init` создаёт этот артефакт детерминированно. Он обязан содержать каждый навык из `capability_registry.skills`, статус наличия и непустой список узлов маршрутизации. Запиши готовый файл как узел; не подменяй живой осмотр догадкой.

### `drift.json`

```json
{
  "schema_version": 1,
  "checked_docs": ["CONTEXT.md", "docs/project/PROJECT.md"],
  "findings": [
    {
      "document": "docs/project/PROJECT.md",
      "claim": "Runtime command is npm start",
      "evidence": "package.json:scripts.dev",
      "impact": "The documented local command is stale"
    }
  ]
}
```

Проверяй точный полный набор документов. Для изменчивого внешнего факта используй `research` и первичный источник; для локального факта достаточно репозитория и выполненной команды.

### `classification.json`

```json
{
  "schema_version": 1,
  "classification": "factual",
  "rationale": "Only a local command name changed; behavior and architecture are unchanged",
  "affected_docs": ["docs/project/PROJECT.md"]
}
```

Для `semantic` добавь `"reopen_stage": "discovery|foundation|planning"`. Outcome команды `record` обязан совпадать с полем: `no-change`, `factual` или `semantic`.

### `update.json`

```json
{
  "schema_version": 1,
  "changed_docs": ["docs/project/PROJECT.md"],
  "created_docs": [],
  "source_receipts": ["package.json:scripts.dev", "command:npm run dev -- --help:exit-0"],
  "summary": "Updated the factual local-development command"
}
```

`changed_docs` должен в точности совпадать с реально изменёнными старыми каноническими документами. `created_docs` обычно пуст; он может содержать только новый вложенный `<stable-module>/AGENTS.md` с заполненными `Scope`, `Map`, `Commands`, `Boundaries`. Незаявленные файлы, placeholder-содержимое и служебные/generated/vendor/build-каталоги блокируются.

## Иерархия AGENTS.md и хуки

- Корневой `AGENTS.md` маршрутизирует по репозиторию и задаёт общие запреты.
- Ближайший вложенный `AGENTS.md` владеет только устойчивым поддеревом и наследует всё сверху; повторять родительский текст запрещено.
- Аудитор предлагает новый файл только при реальной модульной границе: отдельный владелец, публичный контракт, локальные команды или особые ограничения.
- Куратор создаёт файл по `assets/templates/NESTED-AGENTS.md` только из подтверждённых договоров. Любое новое решение переводит finding в `semantic`.
- Проверяющий сверяет полный набор старых и новых `AGENTS.md`, отсутствие противоречий и точные SHA-256.
- Git hook или файловый watcher может только подать trigger `repository-change`/поставить audit в очередь. Автоматическая запись из hook запрещена: смысл определяет граф, результат подтверждает независимый verifier.

### `verification.json`

```json
{
  "schema_version": 1,
  "verdict": "pass",
  "checked_docs": ["CONTEXT.md", "docs/project/PROJECT.md"],
  "stale_claims": [],
  "contradictions": [],
  "residual_risks": []
}
```

Для `reject` добавь непустой `repair_list` и запиши outcome `rejected`. Проверяющий должен сверять текущие документы, а не только `update.json`.

### Ошибка узла

Любой нетерминальный узел может вернуть outcome `failed` с минимальным артефактом:

```json
{"schema_version": 1, "error": "Concrete failure and missing evidence"}
```

Runtime долговечно переводит общий Project Start maintenance status в `blocked`; продолжение возможно только через ограниченный `retry` с новой стратегией.

## Маршрутизация установленных навыков

Каждый навык учитывается в capability discovery, но запускается только когда форма узла ему соответствует.

| Навык | Узлы и назначение |
|---|---|
| `grilling` | Discovery или reopen, когда требуется решение пользователя |
| `domain-modeling` | Discovery, классификация изменения словаря и смысловая правка после reopen |
| `grill-with-docs` | Только явно запущенное интервью discovery; не автоматическая maintenance-правка |
| `codebase-design` | Foundation и классификация изменений модулей, интерфейсов и направлений зависимостей |
| `setup-matt-pocock-skills` | Однократная настройка трекера и доменных документов на planning |
| `to-spec` | Публикация уже одобренного договора после foundation |
| `to-tickets` | Публикация сквозных задач после approval плана |
| `wayfinder` | Большая многосессионная неопределённость до плана |
| `research` | Foundation stack research и изменчивые внешние факты в drift audit/update |
| `prototype` | Один спорный вопрос до окончательного решения; результат одноразовый |
| `task-delivery` | Реализация одной готовой задачи и выпуск `HANDOFF.md` |

Этот набор относится к Matt-style engineering skills и нашим трём графам. Репозиторий Sandcastle является отдельной библиотекой исполнения. Если проект явно выбирает её, она может дать sandbox/branch/provider backend, но не должна запускать второй независимый граф внутри активного Project Start run.

## Внутренние роли

- `project_docs_auditor`: Terra High, read-only; полный drift ledger.
- `project_docs_curator`: Terra XHigh, workspace-write; только ограниченная factual-правка.
- `project_docs_verifier`: Sol Max, read-only; независимая попытка опровергнуть актуальность.
- root: intake, capability receipt, классификация, переходы и финализация.

Роли являются leaf workers: потомки, коммит, push и внешние записи запрещены. Если custom roles ещё не появились в текущем сеансе после установки, открой новую CLI/Desktop-задачу; не заменяй независимую проверку самопроверкой куратора.

## Восстановление

- `status --run <run-dir>` показывает единственный текущий узел.
- `ready --run <run-dir>` возвращает роль, допустимые навыки, артефакт и номер попытки.
- Установленный навык находит общий каталог навыков автоматически. При проверке прямо из Git checkout передай `init --skills-root <checkout>/skills`, чтобы capability receipt ссылался на checkout, а не на ранее установленную копию.
- После `failed` используй `retry --run <run-dir> --reason "<новая стратегия>"`; слепой повтор без новой стратегии запрещён.
- После изменения `graph.json`, task handoff или канонических документов вне разрешённого узла создай новый run. Старый run нельзя форсировать.
- После `reopen-required` сначала проверь preview-команду, затем примени `reopen --apply` и пройди открытые смысловые рубежи bootstrap-route.
