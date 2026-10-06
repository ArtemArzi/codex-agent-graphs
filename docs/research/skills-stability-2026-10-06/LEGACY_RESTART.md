# Старые экземпляры Task Delivery и Project Start

Дополнение к общему аудиту 6 октября. Task Delivery **3.9.2** и
Project Start **3.5.2** прошли независимую приёмку кандидата и установлены
в WSL и Windows. Завершающая проверка публикации указана ниже; результаты
общего аудита до дополнения остаются отдельным проверенным выпуском.

## Наблюдаемый сбой и первое неверное допущение

«Любой schema-compatible v3 можно продолжить или закрыть» оказалось неверно.
Реально выпущенный Project Start 3.1 отклоняется новым loader ещё до abandon
и recover. У Task Delivery известные старые identities поддерживаются, но
повторный full/init того же незавершённого task-id не создаёт новый запуск,
а неизвестная identity не допускается даже к retire. Дополнительно Project
Start может отклонять изменённый shared-state hash при сохранённом owner.

В read-only инвентаризации четырёх известных проектов найдено 89 запусков,
из них 19 незавершённых. Все их identities известны текущим loaders;
18 Task Delivery состояний читаются, один Project Start state отклонён из-за
shared-state hash. Это граница исследования: не каждый зависший запуск
является проблемой версии. Чужие активные состояния не изменялись.

## Выбранное решение

Существующие legacy runners и строгие execution loaders сохранены. Вместо
добавления неизвестных identities в trusted execution добавлена отдельная
операция `restart`: structural preflight старого unfinished v3, точные
snapshots старого состояния и новая текущая candidate instance. Старый run
остаётся незавершённым retired/superseded; его graph identity и evidence не
переписываются. PASS не переносится.

Task Delivery создаёт новый task-id и копию плана с сохранением результата,
scope и profile. Project Start сохраняет полезные документы, фиксирует
исходные/нынешние hashes и missing paths для новой проверки. Принятые scoped
решения, прежние обязательства и замечания отвергнутого ревью ограничивают
successor, включая повторную замену successor до проверки. Отсутствующие
обязательные документы нужно восстановить. Незакрытое решение, повреждённые
receipt/owner, неизвестная schema и невоспроизводимая obligation остаются
blocked/native, без догадок о полномочиях.

Перед retirement готовится полный successor. Durable marker резервирует
admission; init/recover и обычные записи не могут его обойти. Повторная та же
restart-команда сравнивает preimage/postimage каждого файла и продолжает
прерванную замену. Чужие правки сохраняются и останавливают автоматическую
запись. Обычное продолжение старого supported run и v2 legacy route сохранены.

У пользователя уже есть разрешение исправлять/заменять старые экземпляры.
Агент сам исполняет служебную команду в этих пределах; повторная особая фраза
с хешем не требуется. Настоящее разрешение на продукт/production определяется
его проектным протоколом и не возникает из разрешения менять скиллы.

## Проверка и границы

Использованы реальные historical constructors, а не только подстановка версии:
PS3.1 из `2e25f661a217`; TD3.0 из
`f2dd1447fd3ca50a8901b3a4988903dc5afa0e97`. Portable fixture assets сохраняют
их структуру и provenance. Воспроизведение PS3.1 отказа выполнено до ремонта.

Регрессии проверяют точные старые bytes, отсутствие переноса PASS, новые
work/verifier requirements, scoped решения и repair requirements, повторные
замены, прерывания записи, admission, concurrent edits, containment и legacy
v2 fallback. Полный `python3 scripts/check_all.py` прошёл, включая 82 PS graph test и
12 новых TD restart tests; прежние 117 TD graph tests и legacy suites также
прошли. Strict diff check прошёл. Свежий агент использовал установленные candidate skills на двух одноразовых
проектах с настоящими старыми states. Обе restart операции прошли; local VALUE
исправлен 1→2, прежний unittest прошёл, original test не изменён. Компактная
документация прошла checker, прежний README prefix и original snapshots
сохранены. PS successor остаётся честно degraded с обязательным verify, TD
successor running/work: native delivery не выдаётся за controller completion.
Независимый reviewer обнаружил CLI source-symlink gap; lexical path исправлен,
новый regression и 82 PS tests прошли. Свежая сверка после восстановления
доступа к WSL подтвердила установленные версии в обеих средах.

Это исправление поддерживаемого lifecycle, а не массовая миграция всех
сохранённых состояний. Ни сайт, ни инфраструктура, ни provider bindings,
ни настройки моделей/ролей/профилей не входят в изменение.

## Независимые проверки и синхронизация

Plan acceptance: `PLAN-20261006-LEGACY-RESTART-PASS-c3496a81`.
Candidate/result acceptance PASS:
`RESULT-20261006-LEGACY-RESTART-CANDIDATE-PASS-61b454e0-60f9-4b21-93e3-d2b46efb4461`.

Две изменённые skill trees установлены в каждой среде с backups:
WSL `backups/agent-graphs/20261006-210509-981075-1477412`,
Windows `backups/agent-graphs/20261006-210510-103473-1477412`.
После установки verify и повторная установка подтвердили все 59 items in-sync
без замен. После сбоя WSL выполнена новая независимая от старых логов сверка:
281 source file совпал с принятым кандидатом; обе текущие verify/plan проверки
успешны, повторная установка по plan не нужна. Все 319 unmanaged skill bodies
и шесть из семи защищённых файлов совпадают с исходными snapshots.
Windows `config.toml` изменился после прежней проверки установки; происхождение
изменения не установлено. Текущая версия сохранена, конфиг не перезаписывался.

Из-за заполненного C: предыдущая синхронизация была прервана до commit.
Сохранённые 281 файл сверены и скопированы с D: обратно на C:, резервная копия
на D: сохранена. Сейчас проверка вне песочницы показывает WSL root `rw`,
пробная запись успешна. Агент не выполнял shutdown, remount или filesystem
repair; это не доказательство полной исправности файловой системы.
Восстановленная рабочая копия:
`C:\Users\artem\.codex\backups\skills-stability-20261006-resumed`.
Финальная независимая приёмка установленного и опубликованного кода PASS:
`RESULT-20261006-LEGACY-RESTART-LIVE-5C43F30D-3cb49617`.
Опубликованный код: [5c43f30d8d411ec64315b80ea344bb52e79d6728](https://github.com/ArtemArzi/codex-agent-graphs/commit/5c43f30d8d411ec64315b80ea344bb52e79d6728).
Reviewer самостоятельно сверил remote main, чистый source worktree, все 281
Git blobs, обе установки, повторную установку без замен/backups и семь
текущих защищённых настроек. Новый канонический `check_all.py` прошёл.
После этого документируется только этот результат; runtime и skills не меняются.
