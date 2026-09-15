# Как передать Project Start человеку или его ИИ

Этот документ — короткий маршрут для безопасной передачи всего рабочего
комплекта. Репозиторий публичный и скачивается без доступа к аккаунту автора.
Публичность позволяет скачать и изучить код, но сама по себе не предоставляет
open-source лицензию; текущий юридический статус указан в корневом README.

## Зачем нужен Project Start

`Project Start` подготавливает новый или унаследованный репозиторий к надёжной
работе с ИИ и затем поддерживает его документацию в актуальном состоянии. Он:

- создаёт единый вход `AGENTS.md → docs/README.md → канонические документы`;
- отделяет доменный контекст, архитектуру, карту кода, инженерные правила,
  качество и план работы;
- привязывает утверждения к реальным файлам, командам и проверкам;
- сохраняет существующие хорошие документы и пользовательские изменения;
- передаёт программную реализацию в `$task-delivery`, а не смешивает её с
  подготовкой документации.

Передавать нужно весь репозиторий, а не один `SKILL.md`. Каталог
`skills/project-start/` содержит справочники, шаблоны, граф, Python-контроллеры
и тесты, а общая установка добавляет совместимые роли и политики приёмки.

## Что прочитать про архитектуру

- [`skills/project-start/SKILL.md`](../skills/project-start/SKILL.md) — рабочий
  процесс и границы навыка.
- [`skills/project-start/references/documentation-contract.md`](../skills/project-start/references/documentation-contract.md)
  — какие смысловые роли должны покрывать документы проекта.
- [`skills/project-start/references/architecture-playbook.md`](../skills/project-start/references/architecture-playbook.md)
  — встроенный переносимый маршрут архитектурного выбора, используемый, когда
  проект или workspace не предоставляет собственный справочник.
- [`skills/project-start/references/lifecycle.md`](../skills/project-start/references/lifecycle.md)
  — жизненный цикл, остановки и восстановление.
- [`research/AGENTIC_ARCHITECTURE_LANDSCAPE_2026-07-28.md`](research/AGENTIC_ARCHITECTURE_LANDSCAPE_2026-07-28.md)
  — историческая карта агентских циклов, графов и мультиагентных подходов.
- [`research/delegation-economy-proposal-2026-09-14.md`](research/delegation-economy-proposal-2026-09-14.md)
  — невнедрённое предложение по снижению лишнего делегирования.

Историческое исследование объясняет происхождение решений, но действующими
правилами остаются текущие файлы `skills/`, `policies/` и корневой `AGENTS.md`.
Пользовательский архитектурный справочник проекта/workspace может уточнять
встроенную базу и имеет приоритет среди справочников. В обоих случаях требования,
принятые решения и фактическое состояние целевого проекта остаются главнее, а
выбранная архитектура закрепляется в его собственных документах.

## Требования и внешние зависимости

Для установки нужны Git, Python 3.11+ и Codex CLI или Codex Desktop. Полный
bootstrap также ожидает навыки `$domain-modeling` и `$codebase-design`: этот
репозиторий их не поставляет. `$coding-standards` полезен для инженерного
стандарта; при его отсутствии Project Start использует документированный
fallback. `$setup-matt-pocock-skills` необязателен.

Если внешних навыков нет, ИИ должен прямо зафиксировать fallback или пробел, а
не притворяться, что зависимость установлена.

## Рекомендуемая установка Codex

Сначала скачать репозиторий и посмотреть план изменений:

```bash
git clone https://github.com/ArtemArzi/codex-agent-graphs.git
cd codex-agent-graphs
python3 scripts/install.py plan --wsl
```

Для WSL/CLI:

```bash
python3 scripts/install.py install --wsl
python3 scripts/install.py verify --wsl
```

Для WSL и Codex Desktop одновременно:

```bash
python3 scripts/install.py plan --all
python3 scripts/install.py install --all
python3 scripts/install.py verify --all
```

Установщик не должен молча перезаписывать локальный drift: он показывает
конфликт, делает резервные копии управляемых файлов и проверяет их хеши. После
установки нужно открыть новую задачу или CLI-сессию.

## Установка в Claude Code

Тот же исходный комплект упакован как Claude Code plugin:

```bash
claude plugin marketplace add ArtemArzi/codex-agent-graphs
```

Затем внутри Claude Code:

```text
/plugin install cag@codex-agent-graphs
/reload-plugins
```

Вызов навыка в Claude Code: `/cag:project-start`. Установка через plugin и
установка Codex через `scripts/install.py` — разные каналы; не нужно смешивать
их в одном окружении.

## Готовый текст для ИИ человека

```text
Скачай публичный репозиторий
https://github.com/ArtemArzi/codex-agent-graphs.git в отдельную папку.

Сначала прочитай README.ru.md, AGENTS.md и
docs/PROJECT_START_HANDOFF.ru.md, а также встроенный справочник
skills/project-start/references/architecture-playbook.md. Определи, где запущен
Codex: WSL/CLI, Codex Desktop, оба варианта или Claude Code. Проверь Git и
Python 3.11+.

Не копируй только SKILL.md и не перезаписывай существующие настройки вручную.
Сначала выполни scripts/install.py plan для нужного окружения и покажи мне
точные изменения, конфликты и резервные копии. После моего подтверждения
выполни install и verify. Для Claude Code используй только описанный plugin
channel. Затем открой новую сессию и проверь `$project-start` в Codex либо
`/cag:project-start` в Claude Code.

Отдельно проверь наличие $domain-modeling и $codebase-design. Если их нет,
сообщи об этом и используй только предусмотренный Project Start fallback;
ничего дополнительно не устанавливай без моего разрешения.

При запуске Project Start сначала используй архитектурный справочник целевого
проекта/workspace, если он явно указан в его инструкциях. Если такого файла нет,
используй встроенный architecture-playbook.md. Не копируй его механически в
проект: выбери только применимые решения и зафиксируй их в канонических
документах проекта вместе с основаниями и проверками.
```

## Первый запуск

Открыть целевой репозиторий новой задачей Codex и написать:

```text
$project-start подготовь этот репозиторий к надёжной разработке с ИИ.
Сохрани существующие документы и незакоммиченные изменения, сначала покажи
фактическую карту проекта и выполни предусмотренные проверки.
```

Для уже подготовленного проекта тот же навык автоматически выбирает
maintenance и синхронизирует только затронутые смысловые слои.
