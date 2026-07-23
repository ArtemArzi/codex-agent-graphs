# Единый документационный контракт

Project Start нормализует способ навигации, роли документов и правила authority. Он не заставляет разные проекты иметь одинаковое содержание и не переписывает хорошие документы ради одинаковых имён.

## Фиксированный вход

Каждый подготовленный репозиторий использует один маршрут:

`AGENTS.md → docs/README.md → канонический документ → ближайший вложенный AGENTS.md`.

- `AGENTS.md` остаётся коротким router и содержит `Scope`, `Map`, `Commands`, `Boundaries` и `Agent skills`.
- `docs/README.md` перечисляет смысловые роли, реальные пути, владельцев и порядок чтения. Он может ссылаться на уже существующие `architecture.md`, `business-logic.md` или другие подходящие файлы.
- `.project-start/state.json` хранит digest и machine-readable mapping, но не заменяет читаемую карту.

## Обязательные роли

Каждый успешный bootstrap и maintenance receipt хранит полный `coverage`:

| Роль | Содержание |
|---|---|
| `business` | цель, пользовательская ценность, продуктовые объекты и инварианты |
| `documentation_map` | всегда `docs/README.md` |
| `domain_context` | `CONTEXT.md` или `CONTEXT-MAP.md`; только доменный язык и отношения контекстов |
| `foundation` | архитектура, runtime, ownership и внешние границы |
| `engineering_standard` | stack-specific coding guide: модульные границы, framework patterns, anti-patterns, обработка ошибок и данных, тестовые обязанности, команды качества и исключения |
| `codebase` | модули, interfaces, seams, зависимости и реальные пути |
| `quality` | команды проверки, риски и acceptance evidence |
| `plan` | текущая стадия, порядок работы и критерии выхода |
| `agent_context` | всегда корневой `AGENTS.md` |
| `skill_contract` | всегда `docs/agents/domain.md`; вместе с `docs/agents/issue-tracker.md` |

Несколько ролей могут ссылаться на один качественный документ. Все пути должны входить в `canonical_docs`. `docs/README.md` должен ссылаться на каждую роль и оба файла skill contract.

`engineering_standard` не требует фиксированного имени. Переиспользуй существующий `DEVELOPMENT_GUIDE.md`, `ENGINEERING.md`, `CONTRIBUTING.md` или другой документ, только если он действительно закрывает роль; иначе создай один компактный guide. Формируй его из наблюдаемой структуры и конфигурации репозитория, официальной документации точного стека/версий и принятых проектных решений. Общий `coding-standards` — нижняя граница качества, а не источник framework-specific истины.

Guide должен отвечать на практические вопросы: куда помещать новую логику; какие зависимости и импорты разрешены; какие framework-native patterns обязательны; какие anti-patterns особенно вероятны у AI; как обрабатывать ошибки, данные, транзакции и конкурентность; когда добавлять или менять unit/integration/E2E; какие exact команды запускают formatter, linter, type-checker, structural checks и тесты; как оформить обоснованное исключение. Не дублируй правила, полностью исполняемые существующим инструментом: назови команду и храни semantic rule только там, где инструмент не выражает намерение.

Для крупного или плоского модуля роль `codebase` содержит компактный execution-flow index:

`change/flow → entry interface → implementation owners → adapters/persistence → callers/UI → focused tests → owning spec`.

Это навигация от изменения к публичному interface и владельцам, а не полное дерево файлов или generated symbol inventory.

## Instruction discovery и разделение ответственности

- Codex строит цепочку инструкций один раз при старте: global guidance, затем по одному instruction-файлу в каждой директории от project root до cwd. Файлы ниже cwd и в соседних территориях не загружаются автоматически.
- Ближайший к cwd файл имеет приоритет. Для работы в другой территории агент обязан явно прочитать её ближайший `AGENTS.md` до планирования и правок либо запустить новую сессию из этой территории.
- Проверь эффективный `project_doc_max_bytes` и representative chains для корня и устойчивых backend/frontend/service/API территорий. Default Codex — 32 KiB, но фактическая конфигурация проекта или пользователя может отличаться.
- `AGENTS.md` хранит стабильные `Scope`, `Map`, `Commands` и `Boundaries`; не хранит `READY`, `DONE`, current card, progress или receipts.
- Codebase-документ владеет runtime flow, interface, owners/adapters, callers, tests и owning spec. План/controller владеет текущим статусом и доказательствами выполнения.

## Matt Pocock skills

Bootstrap обязан применить:

- `domain-modeling` — проверить доменный язык против кода и отделить glossary от реализации;
- `codebase-design` — описать модули через interfaces, seams и зависимости, а не деревом файлов без смысла.
- доступный `coding-standards` — проверить базовые правила читаемости и over-engineering, затем сузить их фактическим стеком; если skill отсутствует, использовать `project-start:engineering-standard-fallback`.
- `setup-matt-pocock-skills`, если он доступен, — создать или нормализовать `Agent skills`, domain layout и issue tracker mapping.

Если `setup-matt-pocock-skills` отсутствует, используй внутренний fallback Project Start: этот контракт, `assets/templates/NESTED-AGENTS.md` и структурные проверки runner. Зафиксируй `project-start:skill-contract-fallback` в `capabilities`; отсутствие внешнего skill не является ошибкой bootstrap.

Это дисциплины внутри одного `work`, а не три новых узла. Если настройки очевидны из репозитория, прими безопасный default автоматически. Запрашивай решение только когда выбор меняет реальный workflow или доменные границы.

В maintenance при изменении `AGENTS.md` или `docs/agents/` используй доступный `setup-matt-pocock-skills` либо внутренний fallback, `domain-modeling` при изменении domain context, `codebase-design` при изменении foundation/codebase, а `coding-standards` либо engineering fallback — при изменении engineering standard. Остальные навыки используй только по сигналу задачи.

## Нормализация существующего проекта

1. Инвентаризируй существующие инструкции, документы, код, конфигурацию и команды.
2. Классифицируй документы как router/map, canonical truth, decision, plan, evidence или archive.
3. Отобрази хорошие документы на обязательные роли.
4. Создай только недостающие роли и короткие bridge-файлы. Для engineering standard сначала проверь существующий guide и команды качества; не создавай второй coding guide рядом с рабочим.
5. Явно отметь stale, contradictory и historical документы; не повышай их до authority.
6. Создай вложенный `AGENTS.md` только для стабильной самостоятельной границы.
7. Запиши точный coverage, canonical set и evidence в `project.json`.

Если код и конфигурация не доказывают продуктовую семантику, зафиксируй один `decision-required`; не заполняй пробел догадкой.
