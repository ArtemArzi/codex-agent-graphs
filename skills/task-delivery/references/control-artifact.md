# Управляющий артефакт v3

Создай в каталоге run один `task.json`. Это квитанция прохода, а не второй план и не журнал рассуждений.

Минимальная форма:

```json
{
  "schema_version": 3,
  "task_id": "TD-123",
  "mode": "full",
  "profile": "standard",
  "summary": "Что фактически сделано и доказано.",
  "confidence": "high",
  "capabilities": ["rg", "project test command", "mcp:not-applicable:local-only-task"],
  "agents": [
    {"role": "task_plan_reviewer", "phase": "plan-review", "receipt": "/root/task_plan_review", "outcome": "pass"}
  ],
  "research": {
    "internal": ["Какие текущие пути и контракты проверены"],
    "external": {
      "status": "not-needed",
      "reason": "Задача зависит только от стабильной локальной реализации."
    }
  },
  "plan": {
    "path": "docs/development/plans/active/TD-123.md",
    "digest": "64 hex",
    "review": {"mode": "independent", "verdict": "pass"}
  },
  "engineering_standard": {
    "path": "docs/architecture/ENGINEERING.md",
    "sha256": "64 hex",
    "status": "applied",
    "exceptions": []
  },
  "implementation": {
    "status": "complete",
    "changed_paths": ["src/module.py", "tests/test_module.py"],
    "strategy": "root-only",
    "delegation_reason": "The change is one tightly coupled local seam with no independently testable worker result.",
    "slices": []
  },
  "tests": [
    {
      "command": "python3 -m unittest tests.test_module",
      "purpose": "Проверить изменённое поведение",
      "exit_code": 0,
      "status": "passed"
    }
  ],
  "documentation_impact": {
    "class": "factual",
    "summary": "Обновить описание фактически доставленного поведения."
  },
  "rollback": "Вернуть два изменённых файла к baseline и повторить узкий тест.",
  "residual_risks": [],
  "decision": null
}
```

Правила:

- `mode`, `profile`, `task_id`, путь и digest плана должны точно совпадать с run.
- Если Project Start объявил `coverage.engineering_standard`, `task.json.engineering_standard` обязан содержать его exact path/SHA-256, `status: applied` и явный список обоснованных исключений. План должен ссылаться на тот же путь; drift guide после `init` требует свежий run. Для проекта без этой роли поле можно опустить.
- Для `plan`: `implementation.status` равен `not-run`, `strategy` равен `root-only`, `slices`, `changed_paths` и `tests` пусты; implementation workers запрещены.
- Для `implement/full`: `implementation.status` равен `complete`; `changed_paths` точно совпадает с дельтой относительно baseline; минимум одна фактически прошедшая проверка.
- `implementation.strategy` равен `root-only` или зарегистрированной `delegated-sequential`. Root-only является adaptive fast path для любого профиля; явный запрос `delegated-sequential` запрещает root-only. В graph `3.4+` каждый успешный worker receipt обязан получить immutable root acceptance до следующего packet или final work; каждый принятый slice содержит точные `packet_sha256`, `receipt_sha256` и `acceptance_sha256`, а в graph 3.7+ `implementation.changed_paths` равен объединению verified slice paths и явно объявленных `implementation.integration_paths`. Root integration допускается только для небольшой связующей правки внутри reviewed scope и требует task-level passing tests; необъявленная delta запрещена. Canonical root acceptance хранится отдельно и проверяется runner по [implementation-slices.md](implementation-slices.md).
- Для delegated run `tests` содержит все deduplicated `deferred_final_checks` каждого accepted slice с exact command/purpose, `status: passed` и `exit_code: 0`. Быстрый worker check не заменяет итоговый интеграционный или E2E gate.
- `research.internal` непустой. Для внешнего исследования используй `status: used` и receipt Research run; иначе дай содержательную причину `not-needed`.
- `capabilities` содержит один тип MCP-квитанции: `mcp:<server>` после реального вызова, `mcp:fallback:<reason>` после неудачи релевантного MCP или `mcp:not-applicable:<reason>` для локальной задачи. Эти типы нельзя смешивать.
- `documentation_impact.class` равен `none`, `factual` или `semantic`. Только два последних открывают Project Start maintenance.
- Graph `3.10.0` допускает `block_reviewer` в `verify` для `light` и `standard`.
  При низкой уверенности или после `reject` запиши outcome `verify`.
- В `complex` и `critical` режим `plan` завершает положительная проверка
  от `task_plan_reviewer`. Для реализации нужен `pass` этой роли в фазе
  `plan-review` на точный план или подтверждение из сохранённого планового
  запуска. В `verification.json` реализации используй другой
  `reviewer_receipt` от `task_result_reviewer`. Для явно выбранной по
  политике глубокой приёмки результата допустима роль `deep_reviewer`.
  Проверяющий должен отличаться и от авторов реализации, записанных как
  `task_worker`.
- Для новой `critical` реализации укажи `risk_review.coverage` с конкретными
  рисками и проверками в общей приёмке. Если нужен отдельный обзор, укажи
  `risk_review.separate_risk` и приложи положительный receipt
  `task_risk_reviewer` в фазе `result-review`. Иначе укажи
  `"separate_risk": null`. В прежних версиях сохраняются их роли и
  обязательный дополнительный обзор для critical реализации.
- Обычный agent receipt имеет поля `role`, `phase`, `receipt`, `outcome`. `task_worker` дополнительно содержит `slice_id`, `packet_sha256`, `receipt_sha256`, а `outcome` точно равен worker status. Acceptance и checkpoint принадлежат root controller, не worker. Роли и количество обязаны соответствовать профилю.
- При существенном вопросе `decision` содержит как минимум `question`; обычный результат использует `null`.

Внешний `verification.json` связывает проверку с точным кандидатом:

```json
{
  "schema_version": 3,
  "task_id": "TD-123",
  "mode": "full",
  "reviewer_role": "task_result_reviewer",
  "reviewer_receipt": "/root/task_result_review",
  "verdict": "pass",
  "work_sha256": "64 hex",
  "plan_digest": "64 hex",
  "implementation_digest": "64 hex",
  "checked_claims": ["scope, tests, behavior and rollback"],
  "residual_risks": [],
  "repair_list": []
}
```

При `reject` `repair_list` обязан быть непустым. Не переписывай прошлую квитанцию: исправь работу и запиши новый work receipt.
