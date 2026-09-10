# Роли и стоимость

## Корневой агент

Корневой агент владеет пониманием проекта, выбором навыков, решениями,
интеграцией, reconciliation и итоговым `project.json`. При активной policy
bounded auxiliary agents получают свежий контекст и могут выполнять
независимые discovery, preparation, document implementation, synthesis или
focused review; они остаются leaf-only, а root принимает их доказательства.
Без такой policy обычный bootstrap или maintenance выполняется root-only.

## Auxiliary work and Explorer

При активной policy dispatch auxiliary agents только для самостоятельного
результата: preparation/implementation worker, synthesizer или focused checker
получает точный scope, exclusions, must-read evidence и acceptance. Это не
отменяет root integration и не позволяет child создать потомка.

Explorer остаётся read-only:

Подключай 1–2 read-only explorer-агента только когда большой репозиторий имеет независимые области исследования. Дай каждому точный вопрос, каталог, запрет на правки и требуемые доказательства. Корневой агент сам сверяет вывод с файлами и пишет документы.

Не подключай explorer для внешних источников — это область навыка `research`. Не запускай одновременно два одинаковых осмотра.

## Verifier

Без унаследованной acceptance policy verifier условный и read-only. При
активной policy для substantive работы до исполнения нужен свежий
`task_plan_reviewer`, а после кандидата — другой свежий `project_docs_verifier`
как whole-artifact acceptor. Оба получают bounded fresh context; focused checks
могут идти рядом с соответствующим acceptor, но root ждёт все выбранные checks
и reconciles material findings с источниками до PASS. Это операции внутри
`work`, не дополнительные graph nodes.

Verifier получает:

- точный SHA-256 `project.json`;
- точный список и digest канонических документов;
- применимые правила репозитория;
- задачу найти контрпример или расхождение, а не пересказать работу.

Self-проверка нормальна для малого factual/no-change прохода и ясного bootstrap
только без унаследованной policy. Иначе обязательная независимая приёмка не
отменяется малым размером. В legacy controller verifier оправдан широкой
дельтой, семантическим решением, security/compliance, конфликтом доказательств
или низкой уверенностью.

## Лимиты

- один корневой интегрирующий агент;
- не более двух explorer;
- один свежий plan acceptor до исполнения substantive плана и один другой
  whole-artifact verifier только после кандидата;
- глубина делегации 1;
- один verification repair;
- одна повторная попытка failed-узла.

Модель и степень рассуждения выбираются только унаследованной host policy по
роли. Этот reference не назначает модель или effort и не может ими
переопределить shared routing.
