---
name: continuous-improvement
description: >-
  Найти в репозитории одну доказуемую проблему и безопасно довести её до no-op, issue-ready или проверенного commit через существующий Task Delivery. Использовать, когда пользователь просит автономно пробежаться по проекту, найти и исправить точечный баг, улучшать код по расписанию, разобрать падающий CI или явно вызывает $continuous-improvement. Граф ограничивает поиск одним кандидатом, запрещает высокорисковую автономную работу и не заменяет Task Delivery.
---

# Continuous Improvement

Автономно найди одну полезную задачу и либо докажи, что менять нечего, либо передай точное исправление в `$task-delivery`. Граф — короткий контроллер отбора, а не второй цикл разработки.

## Маршрут

Оба режима используют `work → complete` либо при сомнительном доказательстве `work → verify → complete`.

Continuous Improvement по умолчанию остаётся `tracked`: отбор автономного
кандидата, clean baseline и передача в Task Delivery должны быть
возобновляемыми и проверяемыми. Отдельного skill-only пути нет; для обычного
известного исправления используй quick Task Delivery напрямую.

- `full` — режим по умолчанию: найти одного кандидата, исправить только доказанный низкорисковый дефект через Task Delivery и подготовить отдельный commit; иначе завершить `no-op` или `issue-ready`.
- `audit` — только исследование: не менять код и не создавать commit; вернуть `no-op` или `issue-ready`.

Внутри `work` корневой агент сам выбирает источники сигнала, исследует, воспроизводит и оценивает риск. Не превращай эти действия в узлы графа.

## Начни запуск

Прочитай root и ближайший `AGENTS.md`, карту проекта и команды проверки. Выполни `git status --short`; существующие изменения считай пользовательскими. `full` требует чистой производственной рабочей копии либо отдельного чистого worktree. `audit` может работать поверх dirty baseline, но не менять его.

```bash
python3 scripts/continuous_improvement_graph.py init \
  --root <repo> --mode <full|audit> \
  --focus "<вопрос пользователя или область поиска>"
```

После `init` используй абсолютные команды, возвращённые runner.

## Один рабочий проход

1. Ищи по сильным сигналам в порядке полезности: failing CI/test, воспроизводимый issue, недавняя регрессия, type/lint/static-analysis error, доказуемый broken contract или documentation defect. Не ищи эстетическое «что-нибудь улучшить».
2. Выбери максимум одного кандидата. Для большой неясной области допустим один bounded read-only `explorer`; дождись его и сам сверь доказательства.
3. Используй MCP только когда кандидат зависит от внешнего или живого
   состояния: GitHub MCP для issue/CI/PR, Context7 для текущей документации
   библиотеки и owning provider MCP для его данных. Для строго локального
   сигнала запиши `mcp:not-applicable:<reason>` без ритуального discovery; при
   сбое релевантного сервера запиши `mcp:fallback:<reason>`. Не добавляй MCP
   node.
4. Подключай только применимые skills. `$research` нужен для внешнего меняющегося факта; локальный поиск и тесты — для кода. `$development-recovery` срабатывает при расхождении спецификации и наблюдений. Project Start обновится через handoff Task Delivery, а не отдельный вложенный цикл.
5. Воспроизведи проблему командой или наблюдением, сформулируй acceptance и минимальный scope. Если доказательства недостаточны — `no-op` либо `issue-ready`, но не код.
6. Классифицируй риск. Автономная доставка разрешена только для `low` без protected domains. Данные и миграции, auth/permissions/security, billing/payments, secrets, deployment/infrastructure, публичные контракты и широкая бизнес-семантика всегда становятся `issue-ready`.
7. В `audit` остановись. В `full` создай отдельную ветку `codex/continuous-improvement-<run-id>` и вызови `$task-delivery` в `full` с точным кандидатом, reproduction, acceptance и bounded scope. Его план должен лежать в `.agent-graphs/continuous-improvement-runs/<run-id>/task-delivery/PLAN.md`, чтобы служебный контроллер не попадал в продуктовый diff. Профиль Task Delivery должен быть не ниже `standard`; дождись его полного результата и проверь реальный diff, тесты и handoff.
8. Создай один commit только из точных `changed_paths` Task Delivery. Не коммить control artifacts, не push, не merge и не deploy: публикация остаётся отдельным явно разрешённым действием вне этого запуска.
9. Создай `improvement.json` по [control-artifact.md](references/control-artifact.md) и зафиксируй `work`.

```bash
python3 scripts/continuous_improvement_graph.py record \
  --run <run-dir> --node work --outcome <succeeded|verify>
```

## Условная проверка

Вызови `improvement_verifier`, если уверенность не `high`, доказательство неоднозначно, кандидат пришёл из слабого сигнала или root сам эскалировал риск. Передай точные SHA-256 `improvement.json`, candidate evidence и Task Delivery receipt при наличии. Проверяющий не перепроводит разработку и не расширяет scope; root сохраняет возвращённый `verification.json`.

```bash
python3 scripts/continuous_improvement_graph.py record \
  --run <run-dir> --node verify --outcome <succeeded|failed>
```

Один reject возвращает в `work`; второй блокирует запуск. High/protected risk нельзя «проверить» до автономной доставки — только `issue-ready`.

## Заверши

```bash
python3 scripts/continuous_improvement_graph.py complete --run <run-dir>
python3 scripts/continuous_improvement_graph.py status --run <run-dir>
python3 scripts/continuous_improvement_graph.py retry --run <run-dir> --node <work|verify>
```

`complete` повторно проверяет graph identity, immutable receipts, отсутствие недекларированной дельты, Task Delivery completion и точный non-default-branch commit. Затем создаёт `IMPROVEMENT.md` со статусом `no-op`, `issue-ready` или `delivered`.

После успешного `complete` упакуй terminal run через `<CODEX_HOME>/agent-graph-runtime/artifact_lifecycle.py compact --root <repo> --run <run-dir>`. Runtime сохранит копию `IMPROVEMENT.md`, если она находится внутри run. Никогда не упаковывай `running` или `blocked`; pruning остаётся отдельной dry-run-first операцией.

Нормальный результат может быть `no-op`. Не создавай задачу ради самого запуска и не запускай бесконечный loop: один trigger — один bounded проход — один кандидат максимум.
