---
name: task-delivery
description: >-
  Провести одну программную задачу от исследования и плана до реализации, тестов и проверки результата через быстрый skill-only, отслеживаемый или независимо проверяемый маршрут. Использовать для небольшой локальной правки, режима только плана, реализации по уже проверенному плану, полного plan-to-code цикла, исправления или явного вызова $task-delivery. Root выполняет работу; controller подключается только для resumability, durable scope/baseline, handoff, сохранения packet/receipt делегированных частей или повышенного риска. Обычные локальные этапы сами по себе не требуют controller.
---

# Task Delivery

Вызов по хосту: `$task-delivery` в Codex, `/cag:task-delivery` в Claude Code.

Доведи одну задачу до доказанного результата. Граф — это короткий контроль границ, а не пошаговый заменитель инженерного мышления.

## Plain-language user updates

Все промежуточные и итоговые сообщения пиши на языке пользователя простыми
словами. Сначала скажи, что сделано или что мешает работе, затем — влияет ли это
на план, код, срок или решение пользователя, и в конце — что будет дальше. Не
показывай журнал контроллера вместо объяснения.

Обязательный порядок: результат → влияние → следующий шаг.

Слова `controller`, `root`, `worker`, `packet`, `receipt`, `digest`,
`checkpoint`, `gate`, `authority`, `control-degrade` и `recovery route`
используй только когда точное служебное имя нужно пользователю для действия или
проверки; при первом упоминании сразу объясни его обычными словами. Хеши, точные
имена артефактов и состояние протокола выноси после понятного сообщения в
необязательный блок `Технически:`. Обычный статус — один короткий абзац.

Например, вместо «Recovery route выбран: canonical authority будет выполнена
как root-owned maintenance gate» напиши: «Перед кодом нужно отдельно обновить
главные документы проекта. Утверждённый план не меняется; после обновления начну
первый блок реализации.»

## Project first, controller second

Task Delivery controls boundaries; it does not replace engineering work. In every
pass, read the nearest AGENTS.md, architecture map, engineering standard, plan,
production path, and relevant tests before controller artifacts. Read controller
detail only at a current boundary: resume, slice handoff, independent
verification, or completion.

A digest, marker, receipt, reviewer budget, run partition, or other protocol
failure is not a task blocker and does not trigger Development Recovery. Make at
most one bounded controller repair. If it produces no new evidence, run
`control-degrade` and continue local implementation and tests. Degraded control
may reject `verified completion`; it may not prevent reading files, changing
code, running checks, or returning a skill-only handoff.

Stop the task only for missing authority, actual data/security/external-state
risk, ambiguous business behavior, or proven specification/code/runtime
divergence. If the user explicitly disables Task Delivery, disable its controller
for that task and do not reactivate it automatically.

## Сначала выбери уровень исполнения

- `quick` (`skill-only`) — default для небольшой или средней локальной,
  обратимой и понятной задачи, которая завершится в одной сессии. Root
  исследует, планирует внутри рабочего контекста, реализует, запускает тесты и
  отвечает без `init`, run-каталога, `task.json`, обязательного Markdown-плана,
  worker или reviewer.
- `tracked` — используй controller, если задача может прерваться, имеет
  существенный diff, требует durable Markdown-плана/handoff, точного
  scope/baseline, сохранения packet/receipt делегированных частей или
  продолжения в другой сессии.
- `verified` — `tracked` плюс независимый verifier при низкой уверенности,
  неполных тестах, необъяснённых warnings, публичном API, auth/security,
  миграции, деньгах/данных, широком blast radius, нескольких архитектурных
  слоях или прямом запросе независимой проверки.

Явный запрос `quick`, `tracked`, `verified`, долговечного плана или resumability
имеет приоритет. Просьба работать поэтапно или слайсами допускает локальный
`skill-only`: она сама по себе не требует ни делегирования, ни служебных
артефактов. Для `tracked` нужна отдельная причина из списка выше. Если сигналов
controller нет, не создавай run «на всякий случай».

Tracked и verified используют один граф:

`work → complete` или, только когда профиль либо фактический риск требует независимости, `work → verify → complete`.

Внутри `work` корневой агент сам исследует кодовую базу, выбирает навыки, создаёт и проверяет план, реализует, запускает тесты и формирует один `task.json`. Не превращай эти действия в обязательные узлы графа.

## Делегирование по пользе

- Один адресный поиск, небольшую правку или тесно связанный этап выполняй сам. Explorer нужен для самостоятельного неясного пути, worker — для отдельной области реализации, reviewer — для поиска контрпримеров при существенном риске или явном запросе.
- По умолчанию 0–2 одновременно активных субагента. Число запусков за всю задачу — наблюдение о расходе, а не причина остановки. Соблюдай более строгие ограничения хоста; новый run их не обнуляет.
- Не создавай агента на каждый файл/этап и не поручай двум агентам один вопрос. Пока агент исследует назначенную область, работай над другой; после результата проверь решающие факты, не повторяй весь поиск.
- Передавай только относящиеся файлы, факты и критерии. Проси компактный результат со ссылками и неопределённостями. Не копируй весь чат и не добавляй навыки «на всякий случай».
- Если хост больше не позволяет делегировать, продолжай разрешённую работу сам. Для незакрытого delegated run сохраняй принятые квитанции; если его контракт не допускает честное завершение основным агентом, используй control-degrade и обычный handoff, не фиктивный worker. Обязательную независимую проверку нельзя заменить self-review и объявить прошедшей.
- Возвращай тому же проверяющему только исправленные замечания его области. Две попытки без нового evidence останавливают неудачный цикл; служебный лимит не отменяет разрешённую локальную работу.

## Переключение между незавершёнными задачами

Незавершённые задачи независимы. Перед явным переключением создай один компактный
checkpoint, не review:

```bash
python3 scripts/task_graph.py suspend --run <run-dir> \
  --reason "<почему переключаемся>" --next-objective "<с чего продолжить>"
python3 scripts/task_graph.py resume --run <run-dir>
```

Checkpoint хранит plan digest, текущий узел, изменённые пути, accepted slices и
следующую цель. При resume перечитай checkpoint, ближайшие проектные документы,
реальный diff и decisive source files. Не пытайся восстановить рассуждения из
истории чата и не требуй закрыть или отревьюить первую задачу перед началом
другой.

При служебной несовместимости после одной попытки:

```bash
python3 scripts/task_graph.py control-degrade --run <run-dir> \
  --reason "<точная несовместимость controller>"
```

Устаревший незавершённый run закрывай только по явному указанию пользователя:

```bash
python3 scripts/task_graph.py retire --run <run-dir> \
  --reason "<почему работа больше не продолжается>" --acknowledge-incomplete
```

`retire` — отдельный неуспешный terminal status. Он сохраняет точные снимки
run/task state, не завершает узлы, не создаёт handoff и не разрешает compaction.

## Адаптивность и настоящие блокеры

Skill обязан помогать продолжать работу, а не превращать собственный протокол в
причину остановки. Разделяй:

- `technical-recovery` — marker whitespace, производный digest, несовместимая
  нумерация этапов, разбиение работы между bounded runs, mapping plan phase к
  root evidence-gate или worker packet, локальная перестановка проверки при
  неизменных outcome/acceptance/risk. Root выбирает минимальную
  детерминированную поправку, сохраняет evidence, повторяет относящийся review и
  продолжает без вопроса человеку;
- `authority-decision` — новый доступ к приватным данным, назначение человека
  на ответственную роль, изменение бизнес-смысла, acceptance, публичного
  контракта, данных, безопасности, существенного риска или внешнего состояния.
  Только это переводит run в `decision-required`.

Digest всегда вычисляет runner из канонического plan contract. Не проси
пользователя выбрать между двумя хешами семантически одинакового текста и не
считай служебный перевод строки изменением плана. Если review отклонил только
техническую совместимость, repair-forward план/packet и автоматически выполни
fresh review; REJECT сам по себе не означает человеческий blocker.

## Определи режим tracked/verified

- `plan` — исследовать, сохранить и проверить план, затем остановиться без изменения производственного кода.
- `implement` — открыть точный ранее проверенный план, проверить дрейф, реализовать и проверить результат.
- `full` — план, реализация, тесты и итоговая проверка в одном вызове без промежуточного согласования.

Если пользователь явно просит сначала обсудить план, выбери `plan`. Если он даёт готовый план или просит продолжить после `plan`, выбери `implement`. Иначе выбери `full`.

## Quick path

Прочитай ближайшие инструкции и engineering standard, проверь dirty baseline,
локализуй изменение, выполни минимальную правку и относящиеся тесты. Не создавай
служебные JSON/Markdown-артефакты. Если обнаружилась потребность в durable
handoff, delegated slice, широкой документационной дельте или независимой
проверке, остановись до разрастания scope и начни свежий `tracked` run.

## Найди владельца durable плана

Перед `init` прочитай корневой и ближайший `AGENTS.md`, карту документации и существующие соглашения проекта. Если Project Start объявил `coverage.engineering_standard`, runner связывает задачу с точным path/SHA-256: прочитай этот stack-specific guide до плана и реализации. План всегда должен быть Markdown-файлом внутри целевого проекта.

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
  --implementation-strategy <auto|root-only|delegated-sequential> \
  [--slice-budget <positive-estimate>]
```

Относительные команды запускай из каталога установленного навыка. После `init` используй абсолютные команды, возвращённые runner.

## Выбери профиль, а не число этапов

Оцени риск по области, обратимости, новизне, внешним контрактам и последствиям ошибки.

- `light` — малая локальная обратимая правка, ясные критерии: самопроверка плана и результата, 0 независимых агентов.
- `standard` — обычная продуктовая задача: self plan/result; reviewer только по фактическому risk signal.
- `complex` — несколько модулей, новая граница или неоднозначный plan: self-review по умолчанию; независимый reviewer только при реальном risk/uncertainty signal.
- `critical` — безопасность, данные, миграция, деньги, необратимость или широкий blast radius: обязательны risk reviewer и итоговый verifier; plan reviewer подключается только когда сам план остаётся существенным источником неопределённости.

`plan` не получает reviewer только из-за имени профиля. Независимый plan review
нужен при неоднозначной архитектуре, слабом evidence, публичном контракте или
явном запросе. Critical-реализация сохраняет risk reviewer и итоговый verifier.
Подробная матрица — в [profiles-and-agents.md](references/profiles-and-agents.md).

## Один рабочий проход

1. Выполни `git status --short`; все существующие изменения считай пользовательским baseline.
2. Прочитай только относящиеся к задаче инструкции, canonical engineering standard, текущий план и исходный код. Из guide вынеси в план применимые модульные границы, framework patterns, тестовые обязанности и exact quality commands; не копируй весь документ. Для неясной большой кодовой базы допустимы до двух независимых `task_explorer`; для обычной локализации работай сам.
3. Выбери навыки и инструменты по задаче:
   - локальный поиск, LSP/AST и навыки кодовой базы — сначала для внутреннего исследования;
   - `$research` — только для внешних, текущих или смешанных фактов; его агенты входят в общий лимит Task Delivery;
   - MCP discovery выполняй, когда задаче нужны внешние факты, официальная документация библиотек, provider data или живая система; локальная стабильная работа не делает ритуальный обход серверов;
   - provider-specific MCP используй для данных его продукта, Context7 — для официальной документации библиотек, research MCP — для внешнего поиска, Playwright или другой live MCP — для относящейся к acceptance живой системы;
   - для строго локальной задачи запиши `mcp:not-applicable:<reason>`; если релевантный MCP проверен, но не сработал, запиши `mcp:fallback:<reason>` и продолжай подходящим fallback; не выполняй внешнюю запись без полномочий.
4. Создай или обнови один план. В замороженной части должны быть outcome, основания, ссылка на exact engineering standard или честное `N/A`, применимые правила/команды, acceptance, шаги, тесты, stop conditions и точный `task-delivery:scope`. Не веди гигантский журнал снимков внутри плана. Названный в плане этап не обязан становиться worker slice: read-only baseline, authorization, evidence freeze, integration и final acceptance root выполняет внутри `work`, если независимый worker не даёт отдельной полезной дельты.
5. Проверь план сам. Подключи `task_plan_reviewer` только при реальной неопределённости плана или явном запросе; профиль сам по себе не создаёт pre-code gate. В режиме `implement` используй принятый plan как рабочую основу и переходи к коду, если semantic scope не изменился.

Пункты 6–7, `slice-accept`, checkpoint, scope amendment и verifier repair относятся к staged graph `3.4+` runs. Активный `3.3.0` run завершай по его v1 packet и inline root-acceptance contract.

6. Выбери implementation strategy по пользе. `root-only` — default для любого профиля: root может сам выполнить несколько этапов. Просьба «слайсами» означает небольшие проверяемые части, а не обязательный spawn. Только явная просьба делегировать реализацию либо доказанная польза независимого worker выбирает `delegated-sequential`. Перед spawn кратко укажи в dispatch, какой самостоятельный результат оправдывает запуск и передачу контекста; отдельной квитанции этого решения не нужно. Один active write slice; до следующего прими реальный diff и тесты через `slice-accept`. `--slice-budget N` в 3.9 — положительная оценка объёма, а не запрет продолжать после N. Не разбивай одну задачу на новые runs ради счётчика агентов. `plan` не запускает workers; `implement` связывает packet с точным прошлым review; `full` создаёт его после валидного плана. Полный протокол: [implementation-slices.md](references/implementation-slices.md). `delegated-parallel` остаётся fail-closed без доказанной изоляции worktrees.
7. На каждом slice запускай только быстрые проверки его области. Worker обновляет или добавляет затронутые unit/integration/E2E tests согласно `test_impact`; root повторяет минимум один exact slice check. Дорогие интеграционные и E2E рубежи из `deferred_final_checks` запускай один раз после интеграции всех slices и внеси exact command/purpose в `task.json.tests`. Не утверждай успех по diff или словам агента.
8. В `critical` отдельно вызови `task_risk_reviewer`. Создай один `task.json` по [control-artifact.md](references/control-artifact.md).

В `capabilities` запиши ровно один тип MCP-квитанции: `mcp:<server>` для реально использованного MCP, `mcp:fallback:<reason>` после неудачи релевантного сервера либо `mcp:not-applicable:<reason>` для локальной задачи. Нативный web/browser и затем `curl` являются fallback, а не первым выбором при наличии подходящего MCP.

В graph `3.4+` каждый делегированный slice получает только применимые skills, ближайшие инструкции, must-read файлы и уже проверенный MCP/research-контекст. Для новых runs runner автоматически добавляет Project Start engineering standard в `must_read` и связывает packet с его digest; root не должен полагаться на то, что worker догадается о guide по имени. Worker обязан прочитать весь `must_read`, применить required skills и вернуть `capabilities_used`; недоступный skill или недостаточный контекст означает `needs_context`. Root самостоятельно проверяет реальный diff, ownership, соответствие guide и тесты, фиксирует отдельный immutable acceptance до следующего packet. Итоговая delegated delta состоит из union root-accepted paths и явно объявленных `implementation.integration_paths`. Root может выполнить небольшую связующую правку внутри reviewed scope, но обязан назвать её, прогнать относящиеся тесты и не маскировать новый самостоятельный slice. В `task.json` переносится только digest acceptance, а worker report не является доказательством.

В graph `3.4+` после `slice-accept` runner создаёт компактный `context-checkpoint.json`: принятые digests и exact paths, проверенные discoveries, исходный `plan_scope`, deferred checks и следующий objective. `plan_scope` не выдаётся за вычисленный остаток directory scope. Если нужен ещё один slice, сначала выполни `context-rehydrate`; следующий packet будет связан с точным checkpoint SHA-256. Физический host compact можно использовать по ситуации, но он не является частью correctness contract и не нужен после последнего slice.

Публикуй progress только при смене состояния, blocker или появлении значимого нового evidence. Не создавай новый агент, review или artifact во время ожидания. Same-scope successor требует `retry_evidence`; две подряд безуспешные попытки терминальны, даже если общий slice budget больше.

Если runtime evidence обнаружил пропущенный технический путь, не выдумывай токен подтверждения. `scope-amend` разрешён root без человека только для bounded paths, связанных с exact reviewed base, когда outcome, acceptance, публичный контракт, данные, безопасность, внешнее состояние и профиль риска не меняются. Для миграций, secrets, env и CI workflows проверь уже выданные полномочия и относящийся риск. Новое решение нужно только при выходе за них; не запрашивай повторно то же разрешение. Технический scope-amend не расширяет исходные полномочия. Подробный JSON-контракт находится в [implementation-slices.md](references/implementation-slices.md).

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
Для delegated graph `3.4+` run после первого reject возьми `verification_repair_work_sha256` из ответа runner, rehydrate latest checkpoint и создай ровно один дополнительный repair slice. Он проходит обычные worker receipt, root acceptance и повторный verify; неуспех этого repair slice блокирует run.

## Паузы и человеческий контроль

Не спрашивай человека о безопасной локальной реализации, формулировке, выборе
теста, derived digest, run partition, mapping этапов к packets или
восстановимом инженерном решении. Если пользователь не зафиксировал точный
byte-level запрет, формулировку «не переписывай план» трактуй как запрет менять
его смысл, acceptance и authority, а не как запрет исправить marker whitespace
или доказанную техническую противоречивость; каждую такую поправку покажи в
handoff. Остановись только когда отсутствуют полномочия либо ответ меняет
продуктовую семантику, публичный контракт, данные, необратимое внешнее действие
или существенный риск.

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

`complete` повторно проверяет immutable receipts, digest плана, фактическую дельту и тестовую квитанцию. Для `plan` он сохраняет reviewed plan и останавливается. Для `implement/full` он автоматически создаёт совместимый `HANDOFF.md` и закрывает задачу. В `task.json.documentation_impact` укажи `{class: none|factual|semantic, summary: ...}`. Только `factual|semantic` атомарно открывают Project Start maintenance; `none` не создаёт лишнее обязательство.

После успешного `implement/full complete` сохрани plan и handoff на их канонических путях и упакуй только successful terminal run через `<HARNESS_HOME>/agent-graph-runtime/artifact_lifecycle.py compact --root <repo> --run <run-dir>` (дом харнеса: `~/.codex` под Codex, `${CLAUDE_PLUGIN_ROOT}` под плагином Claude Code). `plan` со статусом `awaiting_implementation`, active, blocked, `retired` и unresolved legacy state не упаковывай: runtime сам отклонит их. Pruning остаётся отдельной dry-run-first командой и никогда не запускается hook.

Глобальный hook не является источником истины этого протокола. Не меняй hooks для запуска Task Delivery: checkpoint создаёт и проверяет сам skill. После отдельного внедрения hook может только повторно вызвать `context-rehydrate` на `SessionStart(source=compact)`; изменение hook во время активных задач требует отдельной безопасной активации.

Не редактируй канонические документы Project Start внутри Task Delivery: передай фактическую документационную дельту через handoff. Если реализация доказала устойчивое новое coding rule, команду качества или framework boundary, укажи `documentation_impact=factual|semantic`; одноразовый workaround не превращай в правило.

Состояния schema v2 не мигрируй на месте. Заверши их прежним `task_delivery.py` по [legacy-v2-resume.md](references/legacy-v2-resume.md). Поддерживаемые graph `3.0.0`-`3.8.0` runs можно дочитать или явно закрыть через `retire`; их не переписывай под новый контракт. Новые runs используют `3.9.0`: суммарное число агентов и оценка слайсов не блокируют продолжение. Активные 3.8 runs сохраняют прежние лимиты, проверки и exact graph identity; не переписывай их под 3.9. Если старый лимит мешает, продолжай разрешённую работу через control-degrade, не выдавая её за verified completion. Все новые задачи запускай через `task_graph.py`.

## Служебные ресурсы

- `graph.json` — исполняемый трёхузловой контракт v3.
- `scripts/task_graph.py` — состояние, baseline, scope, digest, retry и handoff.
- `references/implementation-slices.md` — опциональный packet/receipt/acceptance contract внутри `work`.
- `scripts/task_delivery.py` и старые templates/references — только совместимое возобновление v2.
- `scripts/test_task_graph.py` — целевые проверки нового короткого маршрута.
