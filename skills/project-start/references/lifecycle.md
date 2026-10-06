# Жизненный цикл Project Start v3

## Служебный сбой

`control-degrade --run <run> --reason <наблюдение>` меняет только здоровье
контроля в run, сохраняя общий Project Start state, active ownership, решения,
обязательства и квитанции. `complete` отказывает при degraded control, даже
когда отдельный verifier не требовался. Правки документов и проверки остаются
разрешены в существующем scope; результат и native review сохраняются в owning
handoff без объявления controller PASS. Если загрузка или запись run недоступны,
ничего в нём не исправляй вручную: используй тот же внешний handoff.

Это добавленная операция 3.5.1; известные 3.4.0/3.5.0 identities и схемы читаются
без миграции. Старые квитанции не переименовываются и не переподписываются.

## Состояния

- `running/work` — корневой агент координирует изучение и интегрирует документы;
  при активной policy bounded auxiliary agents могут выполнять самостоятельные
  части discovery, preparation, implementation, synthesis или focused review.
- `decision-required` — ожидается одно существенное решение; документы ещё не содержат неразрешённую семантическую правку.
- `running/verify` — controller-проверка включена legacy risk/uncertainty route;
  instruction-level policy acceptance может быть обязательной внутри `work` и
  не требует отдельного graph node.
- `running/complete` — модельная работа закончена, осталась детерминированная проверка целостности.
- `blocked` — узел завершился ошибкой или исчерпан repair; повтор ограничен.
- `completed` — квитанции и документы связаны SHA-256, общее состояние обновлено.
- `superseded` — вход изменился; run безопасно закрыт через `abandon`, обязательная Task Delivery квитанция при необходимости восстановлена.
- `restart-required` — run закрыт, Project Start остаётся fail-closed до успешного replacement run. Независимая Task Delivery допускается только когда нет document drift и verifier requirement; все семантические и evidence obligations продолжают блокировать её.

## Переходы

Диаграмма ниже описывает только legacy controller transitions. Унаследованная
policy-required plan/result acceptance выполняется внутри `work` и не меняет
эти graph identities.

```text
work --self--> complete
work --risk--> verify --pass--> complete
work --decision--> decision-required --answer--> work
verify --reject once--> work
work|verify --failure--> blocked --retry once--> same node
```

Без унаследованной policy решение модели определяет глубину исследования,
выбранные навыки, структуру документов и необходимость controller verifier.
При активной policy ordinary document review использует `block_reviewer`;
пара plan/result нужна только по глобальному complex-engineering/material-risk
порогу. Несовместимость старого controller устраняется по разделу Controller
compatibility в SKILL.md без ложной квитанции завершения. Runner по-прежнему проверяет только допустимые переходы, пути,
точную document delta, лимиты, квитанции и дрейф после записи.

## Остановка

Остановись, когда:

- нужен ответ, меняющий продуктовую семантику, публичный договор, полномочия или необратимое действие;
- повторная проверка снова отвергла документы;
- одна повторная попытка узла не устранила ошибку;
- состояние проекта, change receipt или зафиксированный документ изменился конкурентно.

При дрейфе исходников после `init` используй `abandon`, затем новый `init`; не создавай параллельный run поверх активного. `abandon` запрещён при `decision-required`, а verifier-риск переносится в replacement run. Scheduled-проходы различаются `cycle` (по умолчанию UTC-день).

Не создавай новый запуск для обхода существенного решения. Новый запуск уместен после осознанного изменения входа или области.

## Взаимодействие с Task Delivery

Bootstrap заканчивается фазой `execution`: Project Start не реализует задачи. Task Delivery после завершения пишет точный maintenance obligation. Новый Project Start maintenance run принимает `HANDOFF.md` только пока текущий implementation digest всё ещё совпадает с завершённой Task Delivery, синхронизирует канонические документы и возвращает статус `operational`. Любой неизвестный maintenance status блокирует следующую задачу fail-closed.

Если процесс оборвался между shared state и run receipt, выполни `project_graph.py recover --root <repo>`. Recover принимает только текущую версию/sha графа и не переоценивает уже committed completion по более позднему состоянию исходников.
