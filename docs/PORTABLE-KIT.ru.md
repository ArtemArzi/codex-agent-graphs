# Переносимый рабочий набор

`scripts/portable_kit.py` собирает самодостаточную папку: скиллы со всеми вложенными файлами, обязательные зависимости, роли, общий стандарт, graph runtime и выбранные знания. Её можно скопировать на другой Linux/WSL хост и установить одной командой. Нужен Python 3.12+. Установщик использует только стандартную библиотеку Python.

Canonical источник поддерживаемых нами скиллов и правил: этот репозиторий. Правки вносить сюда, проверять и сохранять в Git. Установленные файлы не являются вторым местом разработки. Внешние скиллы берутся из явно выбранного enabled native каталога; source paths и hashes записаны в манифесте. Новые canonical скиллы и вложенные файлы попадут в следующую сборку автоматически. Отключённые личные скиллы выбранного каталога остаются исключёнными.

## Подготовить полный набор

Из корня актуального исходного репозитория:

```bash
python3 -B scripts/portable_kit.py capture \
  --home "$HOME/.codex" --cwd /path/to/project \
  --output /private/kit-sources.json
python3 -B scripts/portable_kit.py build \
  --profile /private/kit-sources.json --output /private/kit-bundle
```

Родительские папки должны существовать. Существующий output не перезаписывается. Если codex отсутствует в PATH, у capture есть `--codex /absolute/path/to/codex`. Capture запрашивает только initialize и skills/list текущего Codex, отключает настроенные MCP для этого процесса, не запрашивает работу модели и не копирует auth. Из настроек импортируются только model и reasoning effort, личные AGENTS и выбранные источники. MCP, permissions, hooks и plugin registry не импортируются.

Для выбранных знаний добавить к capture:

```bash
--knowledge /path/to/knowledge --knowledge-policy /path/to/company/sync-policy.json
```

Политика содержит массив files с путями относительно корня проекта, то есть родителя папки company. Экспортируются только перечисленные существующие файлы внутри выбранного knowledge root. Без policy выбранная папка знаний экспортируется целиком. Другие рабочие документы, клиентские данные и локальная память автоматически не выбираются. Полный личный bundle и source profile считать приватными.

Для поддерживаемого набора этого репозитория:

```bash
python3 -B scripts/portable_kit.py build \
  --profile profiles/portable-core.json --output /private/core-bundle
```

Core требует reviewed skill-creator для Agent Graph Builder. Обычный Codex хранит его в `$CODEX_HOME/skills/.system`. На чистой машине добавить его root в dependency_roots source profile либо перенести уже собранный bundle. Build не скачивает неизвестные зависимости из сети.

## Установить и запустить

Скопировать bundle целиком. Исходный репозиторий и старые source paths для установки больше не нужны:

```bash
python3 -B kit-bundle/portable_kit.py verify-bundle --bundle kit-bundle
python3 -B kit-bundle/portable_kit.py plan --bundle kit-bundle --target /private/codex-kit
python3 -B kit-bundle/portable_kit.py install --bundle kit-bundle --target /private/codex-kit
python3 -B kit-bundle/portable_kit.py doctor --target /private/codex-kit
python3 -B kit-bundle/portable_kit.py run --target /private/codex-kit -- codex
```

Target должен быть новым, пустым или ранее созданным этим установщиком. Обычный глобальный ~/.codex, активный CODEX_HOME и непустые неизвестные профили запрещены. Вход в новый Codex выполняется пользователем обычным способом, секреты через bundle не переносятся.

Проверка bytes и hashes подтверждает целостность, а не подпись доверенного автора. Bundle исполняет Python и инструкции, поэтому получать его нужно из проверенного источника.

Doctor показывает внешние программы, dependency manifests/lockfiles, ссылки на прежние локальные пути и требуемые host capabilities. Наличие requirements или package-lock не означает установленные библиотеки. Инструкция установки остаётся у профильного скилла; нужные зависимости агент ставит для конкретной задачи в её изолированную среду. Installer не исполняет произвольные npm, pip и hooks всех скиллов сразу.

Plugin имена вроде `superpowers:brainstorming` получают уникальное переносимое имя `superpowers-brainstorming`. Sibling resources, доступные общие resources и лицензии сохраняются. Таблица имён: knowledge/kit-invocations.json. Native callbacks, подписки и browser tools требуют отдельного подключения. Перенос SKILL.md не создаёт эти инструменты. Новый сеанс должен подтвердить native обнаружение и нужный рабочий сценарий.

## Обновление и откат

Обновить canonical исходники штатным Git-порядком с сохранением незавершённых изменений. Повторить capture для изменившегося личного каталога либо использовать прежний профиль с актуальными путями. Build создаёт новый output. После проверки:

```bash
python3 -B new-bundle/portable_kit.py install --bundle new-bundle --target /private/codex-kit
python3 -B new-bundle/portable_kit.py verify --target /private/codex-kit
python3 -B new-bundle/portable_kit.py rollback --target /private/codex-kit
```

Одинаковая сборка устанавливается без нового поколения. Обновление переключает ссылку на неизменный payload. Auth, sessions, SQLite и native .system находятся в стабильном CODEX_HOME. Корневой skills является настоящим каталогом со ссылками на принадлежащие набору папки. Посторонние папки сохраняются; совпадение нового имени с чужой папкой блокирует установку. Удалённый из нового выпуска скилл не должен обнаруживаться через текущую ссылку.

Операции существующего профиля используют общий lock. Run удерживает его до завершения Codex, поэтому обновление выполняется после закрытия процесса. Прямой запуск CODEX_HOME без wrapper обходит эту договорённость, его нужно завершить самостоятельно. Неизвестный lock, изменённый payload или незавершённая transaction требуют сверки. Удалять marker/lock наугад нельзя.

Максимум три поколения общим объёмом 1 GiB. Когда есть current, previous и более старый выпуск, явно убрать проверенный старый ID из списка verify:

```bash
python3 -B new-bundle/portable_kit.py retire --target /private/codex-kit --release OLD_RELEASE_ID
```

Current и previous защищены. Чужие или изменённые bytes блокируют удаление. Retirement сохраняет intent и переносит принадлежащие данные в quarantine перед удалением; прерывание остаётся видимым и требует сверки. Другие профили, внешние backups, исходники и Git-ветки эта команда не очищает.

## Добавлять и улучшать скиллы

Поддерживаемый навык: skills/имя/SKILL.md и его scripts/references/assets. Для обязательного скилла добавить skill-dependencies.json с `required_skills: [{"name": "имя"}]`. Сборка замыкает обязательные зависимости через выбранные источники и dependency_roots; отсутствие и неоднозначность блокируют результат. Optional зависимости отражаются в манифесте и не включаются молча.

Не редактировать immutable release. Исправить canonical source, запустить `python3 scripts/check_all.py`, собрать новую версию. Перенос не делает старые личные абсолютные пути действительными: их список и prerequisites проверять через doctor на новом хосте. Source profile привязан к машине сборки, bundle самодостаточен для установки. При смене машины сборки обновить source paths или заново capture установленного каталога с актуальным canonical clone.

## Codex Cloud и следующий этап

Для пошаговой подготовки копии проекта доступен
[`$cloud-project-copy`](../skills/cloud-project-copy/SKILL.md). Скажи агенту:
«Хочу продолжить этот проект в Codex Cloud. Подготовь копию и проведи меня по шагам».
Он проверит текущий проект и доступы, подготовит нужные настройки и назовёт
оставшиеся действия человека. Готовый setup и проверенный запуск новой задачи
учитываются отдельно. Сам навык не подключает аккаунты без поручения.

Навык входит в обычный skills-only installer и следующие сборки полного пакета.
Уже сохранённый архив обновляется только новой сборкой; установка исходников
не обновляет его содержимое автоматически.

Cloud не синхронизирует локальные личные skills автоматически. Передать private bundle в выбранную Cloud environment, установить в её постоянную файловую область и проверить использование CODEX_HOME, ролей и host tools данным режимом запуска. Prepared cloud environments и старый setup-script flow отличаются. Локальный native smoke не подтверждает работу конкретного Cloud аккаунта.

Официальные источники: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments) и [Build skills](https://learn.chatgpt.com/docs/build-skills), проверены 01.11.2026. Штатный plugin подходит для распространения скиллов и коннекторов. Этот bundle дополнительно переносит принадлежащие нам роли, правила, runtime и выбранные знания с проверяемым обновлением отдельного home; зарегистрированные plugin capabilities остаются вне его договора. Большой каталог может сокращаться в начальном контексте Codex, поэтому наличие всех файлов не гарантирует выбор каждого скилла моделью.

MCP и Composio остаются вторым этапом: отдельные transport/config templates, версии и secrets целевого хоста. Этот installer их не устанавливает и не меняет разрешения.


Для второго этапа подготовлен отдельный [профиль Composio только для Cloud](COMPOSIO-CLOUD.ru.md). Он использует существующий аккаунт и secret целевой среды; локальные MCP и plugins сохраняются. Шаблон автоматически не применяется, live Cloud discovery требует отдельной проверки.
