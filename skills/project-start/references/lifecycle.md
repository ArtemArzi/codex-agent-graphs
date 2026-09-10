# Жизненный цикл Project Start v3

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
При активной policy substantive plan/result acceptance обязательна независимо от
этого перехода. Runner по-прежнему проверяет только допустимые переходы, пути,
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
