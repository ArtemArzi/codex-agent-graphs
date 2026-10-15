# Independent forward foundation exercise

2026-10-15. Это наблюдение использования кандидатных skills на raw fixture,
не final acceptance. Родительские research reports, implementation plan и desired
criteria не читались. Изменения только в work/forward/adoption и этом результате.
Canonical/candidate skills неизменны. Нет network/external actions, установок,
дополнительных агентов, controller runs, commits или integration.

## A. Подключение существующего проекта

Использованы candidate project-start/SKILL.md и references: documentation-contract,
quality-and-intake, architecture-playbook, architecture-from-usage. Дисциплины:
candidate domain-modeling, codebase-design, writing-for-agents; host coding-standards
прочитан как floor, его React/TypeScript примеры в Python проект не переносились.

Fixture HEAD: 3302b6af2c8b553ea9ea779c92121155227420ef. Первоначально только
`?? operator-notes.txt`. Chat root не Git repo: первый status это показал,
последующие проверки выполнялись в настоящем fixture root. Прочитаны AGENTS,
docs/README, OPERATIONS, DECISIONS, tickets.py, tests/test_tickets.py и заметка.
Установлены Python/SQLite, один текущий оператор, create/list и отсутствие
уведомлений. Документация называет CLI, но executable/parser в fixture нет;
команда CLI не выдумана. Единственный тест использует :memory:, не файловый restart.
Исходное сравнение стека не сохранилось; новая оценка не названа его историей.

Выбран bootstrap по фактам: прежнего основания нет. Создан native документальный
кандидат в пределах делегирования. Контроллер запрещён условиями оценки, поэтому
не выполнены init/ready/record/complete, не созданы .project-start state или
поддельные project.json/receipts. Это неполная протокольная часть, не tracked PASS.
В skill есть напряжение: рекомендация skill-only/native для ordinary работы и
последующее утверждение, что отдельного skill-only маршрута нет. Runner-решение
этого противоречия здесь не проверялось. Независимый review остаётся у родителя.

Изменены AGENTS.md и docs/README.md. Созданы docs/CONTEXT.md, FOUNDATION.md,
ENGINEERING.md, QUALITY.md, PLAN.md, docs/agents/domain.md, docs/agents/issue-tracker.md.
Карта покрывает 10 ролей, business/foundation/codebase совмещены в FOUNDATION.
OPERATIONS/DECISIONS, код, тест и пользовательская untracked заметка сохранены.
Вложенных AGENTS не добавлено: самостоятельных территорий нет.

Решения и предложения:
- Сохранены принятые stdlib/SQLite и числовой return ID. Web переделка не принята.
- CONTEXT различает заявку, создание, доставку и разные повторы. Код проверяет
  strip(), но сохраняет исходный текст, create не имеет ключа дедупликации.
- FOUNDATION содержит сценарии успеха, пустого ввода, отказа канала, рестарта;
  сравнивает отправку после commit и сохранённое намерение в той же SQLite.
  Второй вариант условно рекомендован, если нужно восстановление. Это предложение,
  не принятие новых business правил и не реализованная таблица.
- При неизвестном provider outcome exactly-once не обещается. Канал, recipient,
  payload, retries, latency, нагрузка, downtime/loss, чувствительность данных и
  support owner неизвестны. В PLAN оставлены точные вопросы с последствиями.
- Первый будущий срез: после принятия договора create → сохранённая заявка →
  fake отправитель, без изменения return ID. Проверки empty/failure/retry;
  для варианта B ещё atomic intent и reopening DB. Реальная доставка отдельна.
- Срез ordinary/sequential: общая транзакция и ещё неустойчивый договор не
  оправдывают параллельных writers. Task Delivery получает sections и критерии;
  deployment/наблюдение автоматически не запускаются.

Capabilities: `mcp:not-applicable:local-read-only-fixture-and-documentation`;
`project-start:skill-contract-fallback`: setup-matt-pocock-skills отсутствует в
доступном каталоге, установки запрещены; использован внутренний document contract.
Runner structural check не выполнен, своя probe не названа его эквивалентом.
Coding skill доступен, engineering fallback как отсутствие skill не заявлялся.

Внешние URL не открывались: network исключён. Для сохранения стека опора локальная.
Новая интеграция предварительна: primary-source исследование выбранного канала и
точных API/версий нужно до реализации. Это явно incomplete research, не готовая
приёмка foundation. Исследование провайдера и бизнес-ответы не заменены догадками.

## B. Software Factory

Прочитаны candidate software-factory/SKILL.md, references/routing-and-context.md
и readiness-and-checks.md. Только ответы на factory-requests.md: реальных
репозиториев трёх запросов нет; runner/worktree probes и checks для них не выполнены.
Helper-usage не понадобился: никаких worktree operations. Перед реальным запуском
проверить dependency Task Delivery и native tools, не считать чтение запуском.

### 1. Два существенных report readers

Route: parallel двумя writing leaves → последовательная root integration →
единый combined check. Приняты input schema/status meanings, файлы разные,
fixture DB/output directory изолированы, работа существенная. До dispatch нужны
реальные paths, base revision, canonical runner и applicable output/error/
comparability contract: они не заданы; root проверяет их, не выдумывает.

Prerequisites/resources: clean authorized base, actual AGENTS/map/spec sections,
accepted contract revision, один root owner общей регистрации/CLI/lockfile.
Проверить отсутствие общих generated paths/cache и реальный import/build origin
worktrees. Перед дорогим run выполнить baseline probe actual runner. Helper при
использовании требует Git/Python 3.10+, но prepare не запускает агента.

Handoff каждому writer: exact absolute CWD и brief, accepted revision, schema/
status/error contract, owned reader/test paths, исключения shared files, своя DB/
output path, local commands и pending combined checks. Context передать через
prepare --context после проверки источников. Leaf возвращает SHA, owned diff,
actual commands/results, assumptions/limits. Не брать sibling uncommitted edits.
Root читает actual diff и выполняет требуемый review exact integrated candidate.

Полезный combined check: на логически эквивалентной принятой выборке через
реального consumer запустить оба readers с отдельными DB/output directories;
сверить expected records/status и malformed/unknown input согласно договору,
отсутствие перезаписи чужого output. Сравнивать отчёты по принятому comparability
правилу, не автоматически требовать одинаковых чисел у разных reader. Затем
canonical full check совместного кандидата. Это план, не PASS/speed saving/deploy.

### 2. Frontend/backend, общие mutable SQLite и fixed HTTP port

Next: последовательно определить request/response/error contract и UI реакции
на backend errors, назначить одного владельца. Разные файлы не доказывают
независимость. Затем исследовать runner и изолировать per-job SQLite, output/cache
и порты с корректным consumer URL. Если isolation невозможна, serialize конфликтующие
операции. Worktree не изолирует DB/port.

Route: sequential preparation → условно parallel implementation лишь после
принятого договора и проверенной isolation → sequential integration. При остаточной
связности/неокупаемом handoff root выполняет всю цепочку последовательно. Сейчас
не запускать двух writers. Schema/migrations/config имеют одного владельца.
Согласование предусловий сейчас не требует прохождения будущей ещё не написанной
полной функции.

Handoff: frontend получает accepted schemas/status/errors и URL своего стенда;
backend получает accepted validation/persistence/error semantics и свою DB.
Обоим exact base, owned paths, правила, local tests и исключения shared state.
Contract change останавливает dependent части, root обновляет packet и получает
acknowledgment, не создаёт duplicate owner.

Combined check на isolated integrated стенде: UI отправляет valid request → backend
сохраняет → UI показывает принятый результат; invalid request/backend failure
дают согласованные ошибки без ложного успеха; повтор согласно accepted contract.
Проверить actual DB/port ownership и canonical targeted/full checks, требуемую
независимую приёмку. Oracle повторов пока неизвестен. Ничего из этого не запускалось.

### 3. Одна опечатка README

Route: ordinary root-only. Jobs/worktrees/worker packet/Project Start bootstrap
не окупаются. Проверить exact spelling diff, отсутствие случайной смысловой правки
и git diff --check; текущая task record получает actual delta/check. Combined
check ограничен итоговым README/diff, полный продуктовый suite spelling не проверяет.
Implementation запрещена этой оценкой, исправленного diff сейчас нет.

## Actual verification

Project checks CWD:
`/mnt/c/Users/artem/Documents/Codex/2026-10-15/https-github-com-michael-denyer-pstack/work/forward/adoption`.
Discovery commands из chat root.

| Exact actual command | Outcome |
| --- | --- |
| git status --short -- work/forward/adoption | FAIL: chat root not Git repo |
| git -C work/forward/adoption status --short | Initial only ?? operator-notes.txt |
| python3 --version | 3.12.3 |
| git -C work/forward/adoption rev-parse HEAD | 3302b6af2c8b553ea9ea779c92121155227420ef |
| git -C work/forward/adoption ls-files | AGENTS, three old docs, tickets.py, test_tickets.py |
| rg -n 'project_doc_max_bytes' /mnt/c/Users/artem/.codex/config.toml | 65536 |
| wc -c AGENTS.md | 1400 bytes; fixture root has no nested chain; full parent/global chain not measured |
| PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v | Before/after: 1 test, OK |
| git diff --check | No whitespace errors |
| git diff --exit-code -- tickets.py tests/test_tickets.py docs/OPERATIONS.md docs/DECISIONS.md | No delta |
| git status --short | M AGENTS/map, 5 new docs + docs/agents, preserved untracked note |

Actual limited structural probe (chat root):

```bash
python3 - <<'PY'
from pathlib import Path
p=Path('work/forward/adoption')
required=['business','documentation_map','domain_context','foundation','engineering_standard','codebase','quality','plan','agent_context','skill_contract']
m=(p/'docs/README.md').read_text()
assert all('| '+role+' |' in m for role in required)
for name in ['AGENTS.md','docs/OPERATIONS.md','docs/DECISIONS.md','docs/CONTEXT.md','docs/FOUNDATION.md','docs/ENGINEERING.md','docs/QUALITY.md','docs/PLAN.md','docs/agents/domain.md','docs/agents/issue-tracker.md']:
 assert (p/name).is_file(),name
assert (p/'operator-notes.txt').read_text()=='Existing user-owned note. Preserve this untracked file.\n'
assert not (p/'.project-start').exists()
print('PASS: 10 roles mapped; 10 referenced owners exist; user note preserved; no controller state')
PY
```

Exit 0, printed stated PASS. Это карта/existence/preservation, не semantic review.
Initial oversized concatenated reads были truncated; relevant missing ranges
перечитаны меньшими вызовами, coding-standards затем полностью. Initial truncated
output не считается полным чтением. Первая попытка записи этого отчёта через
Python heredoc завершилась SyntaxError: nested PY delimiter закрыл внешний блок;
файл тогда не создан, повторная запись использовала уникальный delimiter.

## Observations for parent

Guidance дала применимый путь сохранения решений, сценариев интерфейса, сравнения
малых вариантов, ownership и точных вопросов. Software Factory разделила маршруты
по dependencies/resources. architecture-from-usage помогла отделить saved ID от
delivery и не выдумать дедупликацию create. Runtime/controller/installed invocation,
полная instruction-chain size и внешняя актуальность этим прогоном не доказаны.
