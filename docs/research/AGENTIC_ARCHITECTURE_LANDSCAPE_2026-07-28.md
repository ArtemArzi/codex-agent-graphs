# Агентские циклы, графы и мультиагентные системы: практическая карта

Дата исследования: 2026-07-28
Режим: deep, multi-branch, primary-sources-first

> Исторический снимок исследования на указанную дату. Он объясняет исходные
> архитектурные решения, но не заменяет текущие политики репозитория. В
> частности, упоминания `optional verify` ниже не отменяют действующую
> обязательную независимую приёмку плана и результата.

## Короткий вывод

В рассмотренной официальной документации и исследованиях нет одного победившего
подхода «агентский цикл» или «агентский граф». Общий для этой выборки паттерн
2025–2026 годов — гибрид:

1. известные переходы, ограничения, права, сохранение состояния и остановки
   принадлежат обычному коду или небольшому графу;
2. модель получает свободу внутри неоднозначной рабочей области;
3. дополнительные агенты появляются только там, где работа действительно
   распараллеливается, требует изоляции контекста или независимой экспертизы;
4. результат проверяется внешним сигналом — тестом, инструментом, источником,
   runtime-наблюдением или человеком, а не просто ещё одной копией той же модели.

Главное следствие для `codex-agent-graphs`: выбранная нами модель небольшого
контрольного графа правильна. Не нужно превращать Project Start или Task
Delivery в подробную диаграмму каждого мыслительного шага. Стоит добавить
выбор *внутренней топологии выполнения* внутри узла `work`, сохранив простой
внешний lifecycle:

```text
work → optional verify → complete
```

То есть граф должен контролировать границы работы, а не заменять саму работу.

## Шесть разных архитектур, которые часто смешивают

| Архитектура | Кто выбирает следующий шаг | Когда полезна | Главный риск |
|---|---|---|---|
| Один вызов модели/инструмента | Приложение | Простая локальная задача | Недостаточно для итеративной работы |
| Agent loop / ReAct | Модель внутри ограниченного цикла | Открытый поиск, работа инструментами, локальная разработка | Бесконечный поиск, рост контекста и стоимости |
| Детерминированный workflow/chain | Код | Известная последовательность и бизнес-процесс | Хрупкость при неожиданных ситуациях |
| Graph/DAG/state machine | Код + отдельные agent nodes | Ветвление, параллельность, resume, HITL, типизированное состояние | Церемония графа становится важнее результата |
| Supervisor–worker / manager-as-tools | Центральная модель | Специализация и изоляция контекста при одном владельце результата | Потери и искажения через пересказ менеджера |
| Team/blackboard/event-driven | Несколько агентов и общий протокол | Независимые участники, долгоживущие события, распределённая координация | Чаттер, конфликты состояния, дорогая интеграция |

Отдельно существует не новая топология, а режим эксплуатации:
**continuous/autonomous loop**. Он повторно запускает один из перечисленных
механизмов по событию или расписанию. Без ограниченного кандидата, бюджета и
условия остановки такой loop превращается в бесконечную активность.

## Что говорят официальные платформы

### OpenAI

OpenAI прямо разделяет model-led и code-led orchestration. В manager-паттерне
главный агент сохраняет владение контекстом и финальным ответом, а специалисты
вызываются как инструменты. Handoff передаёт активный диалог специалисту.
Code-led orchestration рекомендуется там, где важны предсказуемые стоимость,
скорость и поведение: chains, evaluator loops и явный parallel fan-out.

Agents SDK даёт loop, sessions, guardrails, human approvals, tracing и
ограничение числа turns, но не требует строить многоагентную систему.
Официальная рекомендация — начинать с одного агента и добавлять специалистов,
когда это реально улучшает изоляцию capabilities/policies, ясность промпта или
трассировку.

Источники:
[Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/),
[Agents SDK](https://openai.github.io/openai-agents-python/),
[Practical guide](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/).

### Anthropic

Anthropic использует полезное различие:

- **workflow** — заранее определённый кодовый путь;
- **agent** — модель динамически выбирает процесс и инструменты.

Их базовый совет: начинать с самого простого решения, потому что дополнительная
архитектура обменивает latency и cost на возможный прирост качества.
Orchestrator-workers оправдан, когда подзадачи невозможно предсказать заранее;
parallelization — когда ветки независимы; evaluator-optimizer — когда критерий
качества формализуем.

В production research system Anthropic multi-agent показал сильный внутренний
результат на breadth-first исследованиях, но расходовал примерно в 15 раз больше
токенов, чем обычный chat, и плохо подходит для задач с тесно связанным общим
контекстом. Ранние версии создавали до 50 агентов на простые вопросы, бесконечно
искали и отвлекали друг друга обновлениями. Исправления: чёткие пакеты
делегирования, effort budget и условия завершения.

Источники:
[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents),
[Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system),
[Claude Code subagents](https://code.claude.com/docs/en/sub-agents),
[Claude Code agent teams](https://code.claude.com/docs/en/agent-teams).

### Google ADK

Среди рассмотренных источников ADK 2.0 наиболее явно проводит границу: известную
последовательность предлагается исполнять детерминированно, оставляя LLM
неоднозначные узлы. Graph workflows задают nodes/edges, типы, параллельность,
checkpointing и HITL. Dynamic workflows переносят циклы, conditions, recursion
и `asyncio.gather` в обычный код, когда статический граф становится громоздким.

Это важная поправка: «настоящий граф» не обязан быть огромным JSON со всеми
переходами. Нормальный Python/TypeScript control flow с устойчивыми checkpoint
boundaries может быть более подходящим графовым runtime.

Источники:
[Graph workflows](https://adk.dev/graphs/),
[Dynamic workflows](https://adk.dev/graphs/dynamic/),
[Sessions, state and memory](https://adk.dev/sessions/),
[Why we built ADK 2.0](https://developers.googleblog.com/en/why-we-built-adk-20/).

### Microsoft Agent Framework / AutoGen / Semantic Kernel

Текущий Microsoft Agent Framework рекомендует agent для открытой автономной
работы, workflow — для известного порядка выполнения и координации. Workflow
поддерживает typed routing, parallel supersteps, checkpoints и HITL. Встроены
sequential, concurrent, handoff, group-chat и Magentic-паттерны.

Superstep даёт детерминированный fan-in и удобный checkpoint, но создаёт barrier:
следующий шаг ждёт самую медленную ветку. Это полезно только там, где дальнейшая
работа действительно требует всех результатов.

AutoGen и Semantic Kernel показывают широкий набор командных паттернов, но
официальная документация также советует сначала оптимизировать одного агента.
Документация Semantic Kernel помечает agent orchestration как experimental, а
Microsoft Agent Framework позиционируется как текущий объединённый successor.

Источники:
[Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/),
[Workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/),
[Execution model](https://learn.microsoft.com/en-us/agent-framework/workflows/workflows),
[Semantic Kernel orchestration](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/),
[AutoGen teams](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html).

## Рабочие паттерны

### 1. Local agent loop

```text
goal → model → tool → observation → model → ... → exit
```

Это лучший default для одной связной задачи. Нужны явные выходы:
финальный результат, доказанный blocker, лимит turns/времени/стоимости или два
шага без нового evidence.

### 2. Router

Один классификатор выбирает специалиста или инструмент. Полезен при большом
числе разных доменов; не нужен, если основной агент и так уверенно выбирает из
небольшого набора инструментов.

### 3. Supervisor–worker

Главный агент сохраняет задачу и принимает результат, worker получает компактный
bounded packet. Это соответствует нашей модели slices. Worker не должен получать
всю историю сессии и не должен менять общий controller.

### 4. Fan-out / fan-in

```text
                  ┌→ independent branch A ─┐
question/router ──┼→ independent branch B ─┼→ reducer → answer
                  └→ independent branch C ─┘
```

Лучший паттерн для внешнего research, поиска по независимым подсистемам,
сравнения гипотез и независимых read-only reviews. Каждая ветка должна иметь
отдельный вопрос, а reducer — явное правило объединения и разрешения
противоречий.

### 5. Evaluator–optimizer

```text
candidate → external evaluator → bounded repair → re-evaluate
```

Работает, когда evaluator имеет независимый сигнал: тест, schema validator,
линтер, runtime, источник или человеческую оценку. «Та же модель ещё раз
подумает» — слабая проверка и не должна создавать бесконечный review loop.

### 6. Durable graph

Нужен, если работа должна переживать процесс/сессию, ждать человека, иметь
долгие внешние операции или восстанавливаться на уровне узлов. Checkpoint должен
фиксировать минимальное состояние задачи, а не полный шум каждой реплики.

### 7. Event-driven / blackboard

Оправдан для реально распределённых, долгоживущих агентов и внешних событий.
Для обычной разработки это почти всегда излишне: центральный владелец с
immutable result packets проще и надёжнее общего изменяемого пространства.

## Что подтверждают исследования, а не только документация

### Multi-agent полезен условно

Положительные результаты есть, но они зависят от задачи:

- Anthropic получил большой внутренний прирост на сложном breadth-first research;
- свежая работа Wunderlich et al. показывает преимущество debate и
  mixture-of-agents на 1,3 и 2,7 процентного пункта над self-consistency в
  изученных MMLU-Pro/BBH конфигурациях; результат недавний и не доказывает тот
  же эффект в tool-using workflows;
- в benchmark LangChain с одним модельным и искусственно расширенным
  tool/context setup изоляция доменов помогала при добавлении нерелевантных
  инструментов; это не общий benchmark произвольной декомпозиции.

Но равный inference budget меняет картину:

- Huang et al. показали, что self-consistency превосходил debate на GSM8K при
  том же числе ответов;
- Wang et al. показали сопоставимость хорошо промптированного single agent и
  обсуждения, когда доступны demonstrations;
- Silo-Bench показывает, что с ростом числа участников integration overhead
  уничтожает parallel gains.

Вывод: агентов нужно добавлять не для «умности», а для независимого
декомпозируемого труда, изоляции контекста или другого инструментария.

### Несколько моделей не равны независимой проверке

Kim et al. измерили значительную корреляцию ошибок среди 350+ моделей, включая
разные архитектуры и провайдеров. Поэтому nominal model diversity не гарантирует
независимость. Тест или внешний источник обычно ценнее второго мнения той же
семьи моделей.

### Топология влияет на качество

Sparse debate может соответствовать или превосходить all-to-all при меньшей
стоимости. В одном ограниченном benchmark LangChain с добавленными
нерелевантными tool/wiki domains supervisor немного уступил swarm; авторы
связали это с промежуточным пересказом результатов специалистов. Практический
вывод — возвращать typed evidence packet и позволять root читать первичные
артефакты, а не доверять свободному пересказу.

### Селективное размышление лучше фиксированных кругов

SELENE запускает debate только при определённых сигналах неопределённости и
несогласия и сообщает почти двукратную экономию токенов. Это пока не универсально
реплицированный закон, но хорошо согласуется с production-практикой:
review/debate должен включаться по риску или evidence gap, а не на каждом шаге.

Основные исследования:
[Du et al., ICML 2024](https://arxiv.org/abs/2305.14325),
[Huang et al., ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/8b4add8b0aa8749d80a34ca5d941c355-Paper-Conference.pdf),
[Wang et al., ACL 2024](https://aclanthology.org/2024.acl-long.331/),
[Kim et al., ICML 2025](https://proceedings.mlr.press/v267/kim25e.html),
[Li et al., EMNLP 2024](https://aclanthology.org/2024.findings-emnlp.427/),
[Cemri et al., 2025](https://arxiv.org/abs/2503.13657),
[Silo-Bench, ACL 2026](https://arxiv.org/abs/2603.01045),
[Wunderlich et al., ACL 2026 SRW](https://arxiv.org/abs/2605.01566),
[LangChain multi-agent benchmark](https://www.langchain.com/blog/benchmarking-multi-agent-architectures),
[SELENE, EACL 2026](https://aclanthology.org/2026.eacl-industry.7/).

## Когда выбирать какой подход

| Ситуация | Default | Усложнение только при сигнале |
|---|---|---|
| Маленькая локальная правка | Один agent loop | Focused test |
| Связная задача в одной области | Root-only loop | Один bounded worker при узком slice |
| Внешнее исследование с независимыми вопросами | Fan-out/fan-in | Claim verifier для важных выводов |
| Большая незнакомая кодовая база | 1–2 read-only explorers | Внешний researcher, если документация меняется |
| Много независимых файлов/миграций | Dynamic map-reduce | Изолированные worktrees и reducer |
| Последовательный бизнес-процесс | Workflow/graph | Agent node только для неоднозначного решения |
| Долгий процесс с паузами/approval | Durable graph + checkpoints | Event-driven runtime |
| Поиск улучшений | Один bounded candidate/run | Внешнее расписание повторяет запуск |
| Высокий риск | Root + external evidence | Независимый reviewer по конкретному risk surface |

## Что стоит внедрить в наши процессы

### Общий контракт Agent Graph Builder

Сохранить внешний граф `work → optional verify → complete` и добавить
опциональное поле/решение `execution_topology` внутри `work`:

- `local-loop` — default;
- `fan-out-read-only` — независимый discovery/research;
- `delegated-sequential` — связанные implementation slices;
- `isolated-parallel` — только независимые области/worktrees;
- `evaluate-repair` — только при независимом проверяемом критерии.

Выбор топологии должен объясняться одним предложением. Если явной выгоды нет,
остаётся `local-loop`.

### Project Start

Оставить root-only. До двух read-only explorers нужны только для большой
неизвестной кодовой базы с двумя независимыми execution paths. Обновление
документации делает root, потому что нужен один канонический редактор и
согласование общей карты.

### Research

Это наиболее естественный настоящий diamond graph:

```text
orient → 1–3 independent scouts → root synthesis → conditional verifier
```

Число scouts зависит от независимых исследовательских вопросов, а не от желаемой
«глубины». Источники расширяются до saturation/evidence coverage, а не до
фиксированной цифры. Verifier нужен для consequential claims, не для каждого
обычного ответа.

### Task Delivery

Сохранить `root-only` default. Discovery можно распараллеливать read-only.
Реализацию вести:

- root-only для тесно связной работы;
- delegated-sequential для slices с общим baseline;
- parallel только для независимых worktrees и без shared writes.

Slice packet/receipt полезен как context compression и handoff, но protocol
failure не должен блокировать код: одна bounded repair, затем control-degrade.
Focused tests выполняются в slice; дорогой integration/E2E gate — после
интеграции всех затронутых slices, кроме случаев, где без него нельзя проверить
сам slice.

### Continuous Improvement

Не делать бесконечный внутренний loop. Один запуск выбирает максимум один
доказанный low-risk candidate, реализует и проверяет его. Повторяемость должна
принадлежать внешнему trigger/расписанию. Это сохраняет наблюдаемость и не даёт
агенту постоянно «улучшать» собственную инфраструктуру.

## Чего не внедрять сейчас

- Не создавать отдельный агент на каждую роль или файл.
- Не превращать девять implementation slices в девять обязательных graph nodes.
- Не запускать fixed-round debate для каждого плана.
- Не делать all-to-all agent chat.
- Не хранить полную историю каждого worker в root context.
- Не давать нескольким workers одновременно менять один artifact.
- Не принимать reviewer wording или receipt за доказательство без проверки diff,
  тестов и runtime.
- Не вводить durable graph там, где задача завершается за одну сессию.

## Минимальный план adoption

1. Зафиксировать `execution_topology` как внутреннее решение узла `work`.
2. Добавить triggers и anti-triggers для пяти топологий в Agent Graph Builder.
3. Провести A/B на 6–10 реальных задачах:
   `local-loop` против выбранной усложнённой топологии.
4. Измерять:
   wall-clock time, total tokens/tool calls, число агентов, accepted defects,
   repair attempts, steps without new evidence и долю времени на control plane.
5. Сохранять сложную топологию только там, где она улучшает качество или время,
   а не просто создаёт более красивую трассу.

## Итоговая ментальная модель

```text
Внешний trigger
      ↓
Маленький lifecycle-контроллер
      ↓
Один свободный work-loop модели
      ↓
При доказанной необходимости:
  route / fan-out / bounded delegate / external evaluate
      ↓
Root проверяет первичные evidence
      ↓
Complete или честный blocker
```

Модель выполняет задачу. Граф задаёт ограничения, восстановление и точки
проверки. Субагенты дают независимый труд или изоляцию контекста. Тесты и
источники дают истину. Если любой слой начинает обслуживать сам себя, его нужно
degrade или убрать из текущего run.
