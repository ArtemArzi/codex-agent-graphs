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
  "capabilities": ["rg", "project test command", "mcp:fallback:local-only-task"],
  "agents": [],
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
    "review": {"mode": "self", "verdict": "pass"}
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
  "documentation_impact": "Обновить описание фактически доставленного поведения.",
  "rollback": "Вернуть два изменённых файла к baseline и повторить узкий тест.",
  "residual_risks": [],
  "decision": null
}
```

Правила:

- `mode`, `profile`, `task_id`, путь и digest плана должны точно совпадать с run.
- Для `plan`: `implementation.status` равен `not-run`, `strategy` равен `root-only`, `slices`, `changed_paths` и `tests` пусты; implementation workers запрещены.
- Для `implement/full`: `implementation.status` равен `complete`; `changed_paths` точно совпадает с дельтой относительно baseline; минимум одна фактически прошедшая проверка.
- `implementation.strategy` равен `root-only` или зарегистрированной `delegated-sequential`. При adaptive `standard/complex/critical` root-only требует конкретный `delegation_reason`; явный запрос `delegated-sequential` запрещает root-only. Каждый принятый delegated slice содержит точные packet/receipt SHA-256 и `root_acceptance` с проверенными путями и независимо прошедшими тестами по [implementation-slices.md](implementation-slices.md).
- `research.internal` непустой. Для внешнего исследования используй `status: used` и receipt Research run; иначе дай содержательную причину `not-needed`.
- `capabilities` всегда содержит MCP-квитанцию: `mcp:<server>` после реального вызова или `mcp:fallback:<reason>` после обязательной проверки доступности. Успешный MCP receipt и fallback вместе недопустимы.
- Обычный agent receipt имеет поля `role`, `phase`, `receipt`, `outcome`. `task_worker` дополнительно содержит `slice_id`, `packet_sha256`, `receipt_sha256`, а `outcome` точно равен worker status. Роли и количество обязаны соответствовать профилю.
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
