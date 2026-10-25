# Interface Design Pack

Один вход для понятного интерфейса: человек и задача → flow и состояния →
текст и иерархия → визуальное решение → реализация → проверка результата.
Подключаются только нужные методы. Замена подписи не запускает полный редизайн.

| Состав | Задача |
|---|---|
| [interface-design](../../skills/interface-design/SKILL.md) | Связать flow, содержание, визуальное решение и существующие инструменты |
| [interface-performance](../../skills/interface-performance/SKILL.md) | Найти узкое место, измерить и проверить ускорение на той же нагрузке |
| [Локальные методы](../../skills/interface-design/references/methods.md) | Flow, навигация, состояния, референсы и качество взаимодействия |
| [Профиль оформления](../../skills/interface-design/references/design-policy.md) | Предпочтения владельца, применяемые до выбора структуры и оформления |
| [Библиотека источников](THIRD_PARTY.md) | 31 выбранный текстовый файл из 8 закреплённых upstream с лицензиями |
| [Демо «Поток»](demo/PRODUCT.md) | Статический рабочий интерфейс с назначением заявки и восстановлением после ошибки |

Профиль оформления содержит авторские предпочтения. Это не универсальный список
признаков плохого UX или способ определить авторство ИИ. Существующий продукт и
явный бриф определяют допустимые исключения. Фальшивые отзывы и доказательства
не допускаются; обратная связь, доступность и восстановление проверяются по задаче.

## Установка в Codex

Python 3.11+, стандартная библиотека, проверенная копия этого репозитория.
WSL и Desktop используют существующий выбор сред и общего skill root:

```sh
python3 scripts/install.py plan --skills-only --pack interface-design --wsl
python3 scripts/install.py install --skills-only --pack interface-design --wsl
python3 scripts/install.py verify --skills-only --pack interface-design --wsl
```

Для Desktop заменить `--wsl` на `--desktop`; для обеих сред использовать `--all`.
При неоднозначном корне указать существующий общий `--skill-root PATH`.
Подробности: [установка CAG](../../docs/INSTALLATION.md).
Вход: `$interface-design`; ускорение по необходимости: `$interface-performance`.

## Установка в Claude Code

Выбрать один канал: обычные personal skills или существующий плагин `cag`.
Установка ordinary skills использует принятую нативную адаптацию CAG:

```sh
python3 scripts/install_claude.py plan --pack interface-design
python3 scripts/install_claude.py install --pack interface-design
python3 scripts/install_claude.py verify --pack interface-design
```

По умолчанию: `~/.claude/skills`. Для отдельного профиля указать
`--claude-home PATH`; при необходимости `--skill-root PATH`.
Вход: `/interface-design`, `/interface-performance`. Этот путь ставит только два
UX-навыка. Существующий инженерный комплект, его роли, runtime и ownership receipt
сохраняются. Codex и Claude могут иметь свои копии на одном компьютере.

Для установленного и включённого `cag` обновить плагин штатным способом из
проверенной версии репозитория. Его root `skills/` включает оба навыка:
`/cag:interface-design`, `/cag:interface-performance`.
Нативный установщик не проверяет все plugin caches и не удаляет дубли плагина
автоматически. Одновременно оба канала для этих навыков не использовать.
Реальная загрузка в Claude требует отдельной проверки в активной сессии.

Оба установщика сначала показывают plan, отказываются перезаписывать drift,
проверяют исходные и конечные hashes и используют существующие транзакции CAG.
Неизменённая повторная установка не меняет навыки. Настройки моделей, MCP,
аккаунтов и инструкций профиля не входят в установку этого пака.

## Дополнения и демо

Impeccable, Interface Clarity, Product Design, Frontend App Builder, shadcn и
React Best Practices используются по потребности, если доступны и разрешены на
текущем хосте. Пак не устанавливает их и не включает плагины автоматически.
Имена из [карты зависимостей](../../skills/interface-design/references/dependencies.json)
обозначают возможности. [Host adapter](../../skills/interface-design/references/hosts.md)
объясняет поиск эквивалента и fallback. UI UX Pro исключён из маршрута.

Из корня репозитория:

```sh
python3 -m http.server 8767 --bind 127.0.0.1 --directory products/interface-design/demo
```

Открыть `http://localhost:8767/`. Данные вымышленные и живут в памяти страницы.
Backend, отправки, API и аналитика отсутствуют. Демо не доказывает человеческое
удобство или производственный эффект. [Проверки и ограничения](VALIDATION.md).
