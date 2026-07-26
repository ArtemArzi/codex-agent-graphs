---
name: project-start
description: >-
  Быстро подготовить новый или существующий репозиторий к разработке и затем поддерживать его каноническую документацию. Использовать для основания проекта, восстановления карты документации, синхронизации документов после изменений, создания и обновления корневых или вложенных AGENTS.md и явного вызова $project-start. Не использовать вместо реализации одной программной задачи: после готового основания передать её task-delivery.
---

# Project Start

Вызов по хосту: `$project-start` в Codex, `/cag:project-start` в Claude Code.

Создай ровно столько проектного основания, сколько помогает сильной модели уверенно работать дальше. Граф — это контроль границ, целостности и возобновления, а не сценарий мышления.

## Главный маршрут

Оба режима используют один короткий граф:

`work → complete` или, только при реальном риске, `work → verify → complete`.

`decision-required` — условная пауза внутри `work`, а не обязательный этап. Один корневой агент исследует и редактирует документы. До двух read-only explorer-агентов допустимы только когда большой репозиторий действительно можно изучать независимыми частями.

Project Start по умолчанию использует `tracked`: его смысл — создать или
поддержать долговечное каноническое основание. `verified` включай только при
широкой семантической дельте, слабых доказательствах, конфликте документов,
высоком риске или прямом запросе независимой проверки. Отдельного skill-only
маршрута здесь нет: для разовой правки текста без синхронизации основания
Project Start не нужен.

## Выбери режим

- `bootstrap` — проект ещё не имеет рабочего основания Project Start. Нормализуй его под единый документационный контракт: карта, доменный контекст, техническое основание, engineering standard, кодовая база, качество, план и агентский контекст.
- `maintenance` — основание уже готово; синхронизируй документы с проверенным изменением или текущим состоянием репозитория.
- `auto` — режим по умолчанию; runner выбирает его из `.project-start/state.json`.

```bash
python3 scripts/project_graph.py init \
  --root <repo> --mode auto --reason "<зачем нужен проход>"
```

Относительные команды запускай из каталога установленного навыка. После `init` используй возвращённые runner-команды: они содержат абсолютный путь и работают из целевого репозитория.

После Task Delivery передай точную квитанцию:

```bash
python3 scripts/project_graph.py init \
  --root <repo> --mode maintenance --reason "Task <id> completed" \
  --trigger task-delivery --change-receipt <HANDOFF.md>
```

Команда возвращает каталог run. Затем:

```bash
python3 scripts/project_graph.py ready --run <run-dir>
```

## Один рабочий проход

1. Прочитай ближайшие инструкции и существующую карту документации. Проверь `git status`; не присваивай чужие изменения. В bootstrap прочитай [documentation-contract.md](references/documentation-contract.md) и отобрази существующие хорошие документы на его смысловые роли вместо массового переименования.
2. Определи, нужен ли внешний или живой контекст. Для чисто локальной
   синхронизации сначала используй локальный поиск и LSP/AST и запиши
   `mcp:not-applicable:<reason>` без ритуального обхода серверов. Если нужны
   provider data, текущая документация библиотеки, GitHub/Linear/Notion или
   live-система, осмотри доступные `mcp__*` tools/resources и примени owning
   MCP. Нативный web/browser и затем `curl` допустимы только после отсутствия
   или сбоя подходящего релевантного MCP; тогда запиши
   `mcp:fallback:<reason>`.
3. В bootstrap обязательно примени `domain-modeling` для доменного слоя и `codebase-design` для карты модулей внутри того же `work`, не превращая их в отдельные стадии. Для per-repo skill contract сначала используй `setup-matt-pocock-skills`, если он реально доступен. Если его нет, выполни внутренний fallback Project Start по [documentation-contract.md](references/documentation-contract.md), шаблону вложенного `AGENTS.md` и структурным проверкам runner; запиши `project-start:skill-contract-fallback` в `capabilities`. Для роли `engineering_standard` примени доступный `coding-standards` как базовую дисциплину и профильные навыки стека только по фактическому стеку. Если skill отсутствует, используй официальную документацию точных версий, существующий код/конфигурацию и [ENGINEERING.md](assets/templates/ENGINEERING.md), затем запиши `project-start:engineering-standard-fallback`. Не копируй общий skill в документ и не придумывай правила, не подтверждённые стеком или проектом. В maintenance подключай дисциплины только при изменении соответствующей роли. Остальные навыки подключай по потребности:
   - `grilling` и `domain-modeling` — когда неясны продукт, поток или инварианты;
   - `grill-with-docs` или `wayfinder` — только для действительно длинного неоднозначного основания, не для обычного старта;
   - `codebase-design` — когда нужно установить модульные границы;
   - `to-spec` и `to-tickets` — когда проекту реально нужны отдельная спецификация или публикация задач; не создавай их автоматически;
   - `setup-matt-pocock-skills` — если доступен, настрой или проверь один общий контракт `AGENTS.md` + `docs/agents/`; иначе используй внутренний fallback выше. Безопасные выводимые настройки принимай автоматически, а `decision-required` используй только для действительно неоднозначного issue tracker или domain layout;
   - `research` — для внешних, текущих или смешанных фактов; не запускай его ради чисто внутренней карты;
   - навыки стека, тестирования и безопасности — только к относящемуся риску;
   - навыки Matt Pocock — как составные дисциплины; не запускай весь каталог и не делай из них вложенный оркестратор.
4. Обнови документы сам. Для локализованного maintenance одного смыслового
   слоя используй fast maintenance: без explorer, без verifier и без
   повторного чтения всего основания. Не отдавай параллельным агентам
   пересекающиеся документы и не запускай отдельного «куратора» по умолчанию.
5. Создай один `project.json` по [договору управляющего артефакта](references/control-artifact.md). Это квитанция прохода, не второй источник истины.

В `capabilities` запиши ровно один MCP-статус:
`mcp:<server>` для реально использованного сервера,
`mcp:fallback:<reason>` после сбоя релевантного сервера либо
`mcp:not-applicable:<reason>` для локального прохода. Fallback не разрешает
пропустить доступный релевантный MCP. Не выполняй внешнюю запись через MCP без
полномочий пользователя.

Для обычного результата:

```bash
python3 scripts/project_graph.py record --run <run-dir> --node work --outcome succeeded
```

Если изменение широкое, высокорисковое, неоднозначное или основано на слабых доказательствах:

```bash
python3 scripts/project_graph.py record --run <run-dir> --node work --outcome verify
```

Проверяющий читает точный `project.json` и точный набор документов, пытается найти расхождение с репозиторием и пишет `verification.json`. Один `reject` возвращает работу корневому агенту; второй блокирует цикл.

## Существенное решение

Не спрашивай человека о фактической синхронизации, формулировке или безопасном восстановимом выборе. Остановись только если ответ меняет продуктовую семантику, публичный договор, необратимую внешнюю операцию, существенный риск или полномочия.

В bootstrap и maintenance сначала запроси решение без семантической правки документа:

```bash
python3 scripts/project_graph.py record --run <run-dir> --node work --outcome decision
python3 scripts/project_graph.py decide --run <run-dir> --answer "<точный ответ пользователя>"
```

После ответа внеси правку и запиши новый `project.json` со ссылкой на `decision.id`.

## Документация и AGENTS.md

- Во всех проектах сохраняй одинаковый вход: `AGENTS.md → docs/README.md → канонические документы → ближайший вложенный AGENTS.md`.
- `docs/README.md` обязан отображать смысловые роли на реальные пути. Существующие качественные документы сохраняй; создавай bridge-файлы и недостающие роли, а не дубликаты.
- `engineering_standard` — обязательная смысловая роль для stack-specific coding guide. Переиспользуй существующий `DEVELOPMENT_GUIDE.md`, `ENGINEERING.md` или равноценный документ; фиксированного имени нет. Он хранит модульные границы, разрешённые framework patterns, anti-patterns, обработку ошибок/данных, требования к тестам, точные команды качества и правила исключений. Стилизацию, которую уже гарантирует formatter/linter/type-checker, не дублируй прозой.
- Строй engineering standard по порядку `репозиторий и конфигурация → официальная документация точных версий → проектные решения → общий coding skill`. В `AGENTS.md` оставляй только короткий router и несколько hot-path запретов; подробные правила принадлежат engineering standard, runtime-навигация — codebase map, критерии доказательства — quality.
- Используй `CONTEXT.md` для одного доменного контекста или `CONTEXT-MAP.md` для нескольких; не превращай их в PRD, план или техническое описание.
- Канонические документы описывают текущее состояние, владельцев, границы и реальные команды; журнал run хранит только квитанции.
- Не переписывай историю проекта и не создавай документацию ради количества.
- Корневой `AGENTS.md` остаётся коротким маршрутизатором.
- Вложенный `AGENTS.md` создавай лишь у стабильного самостоятельного модуля с собственными командами или границами. Заполни `Scope`, `Map`, `Commands`, `Boundaries`; не клади его в generated/vendor/build-каталоги.
- Codex строит instruction chain один раз при старте: от project root до текущей рабочей директории. Вложенный `AGENTS.md` ниже cwd или в соседней территории не становится активным только потому, что агент открыл там файл. Запускай задачу из ближайшей стабильной территории либо явно прочитай относящийся к изменению `AGENTS.md` до планирования и правок.
- Проверь эффективный `project_doc_max_bytes` и размеры representative root-to-leaf chains. При риске truncation сокращай родительские инструкции и размещай только subtree-specific правила на стабильных границах.
- `AGENTS.md` хранит стабильные `Scope`, `Map`, `Commands` и `Boundaries`; task status, progress и receipts принадлежат плану/controller, а подробные runtime flows и owner navigation — codebase-документу.
- Хук может обнаружить дрейф и предложить Project Start, но не должен сам редактировать смысловые документы.

Единый контракт — в [references/documentation-contract.md](references/documentation-contract.md), правила maintenance — в [references/maintenance.md](references/maintenance.md), роли и стоимость — в [references/agent-operations.md](references/agent-operations.md).

## Завершение и восстановление

```bash
python3 scripts/project_graph.py complete --run <run-dir>
python3 scripts/project_graph.py status --run <run-dir>
python3 scripts/project_graph.py retry --run <run-dir> --node <work|verify>
python3 scripts/project_graph.py abandon --run <run-dir> --reason "<почему нужен свежий init>"
python3 scripts/project_graph.py recover --root <repo>
```

`complete` повторно сверяет SHA-256 артефактов и документов, переводит bootstrap в `execution`, закрывает maintenance obligation и сохраняет канонический набор вместе с точным `coverage.engineering_standard` в `.project-start/state.json`. После bootstrap следующая программная работа принадлежит `task-delivery`; после неё Project Start снова запускается только для документационной дельты.

Если исходники или конфигурация изменились после `init`, не подменяй baseline: закрой run через `abandon` и выполни свежий `init`. До успешного replacement run состояние остаётся `restart-required`, поэтому новая Task Delivery не стартует. Незакрытая Task Delivery obligation и требование повторного verifier сохраняются. Неразрешённое существенное решение нельзя обойти через `abandon`. Если в abandoned run уже менялись документы, свежий `init` останется заблокирован до их восстановления к исходному digest; сохрани нужную дельту отдельно и примени её уже в новом проходе.

`recover` нужен только после прерванной записи состояния. Он сверяет identity графа и immutable receipts, снимает незаконченную активацию либо согласует shared/run state. Не используй его для обхода verifier или решения. Для периодического запуска можно передать `--trigger scheduled --cycle <ключ>`; без ключа используется текущий UTC-день.

Старые активные v2 maintenance runs можно завершить прежним `project_maintenance.py` по [legacy-инструкции](references/legacy-v2-resume.md); новые запуски всегда используй через `project_graph.py`.

После успешного завершения сохрани канонические документы и `.project-start/state.json` на месте, затем упакуй только terminal run через `<HARNESS_HOME>/agent-graph-runtime/artifact_lifecycle.py compact --root <repo> --run <run-dir>` (дом харнеса: `~/.codex` под Codex, `${CLAUDE_PLUGIN_ROOT}` под плагином Claude Code). Не упаковывай active, blocked, restart-required или непроверенный superseded run. Очистка остаётся отдельной dry-run-first командой, а не узлом или hook.

Полный жизненный цикл и условия остановки: [references/lifecycle.md](references/lifecycle.md).

## Служебные ресурсы

- `graph.json` — короткий исполняемый контракт v3.
- `scripts/project_graph.py` — состояние, пути, digest, решения, retry и завершение.
- `scripts/project_start.py` — совместимый state/scaffold слой для Task Delivery и старых проектов.
- `scripts/project_maintenance.py` + `assets/legacy-graph-v2.json` — только возобновление v2.
- `scripts/test_project_graph.py` — самопроверка нового маршрута.
