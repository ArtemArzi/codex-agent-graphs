# Implementation slices

Этот протокол действует только внутри существующего узла `work`, когда root действительно вызывает `task_worker`. Он не создаёт новый graph node и не добавляет overhead для `root-only`.

## Содержание

- [Стратегии и режимы](#стратегии-и-режимы)
- [Slice packet](#slice-packet)
- [Worker receipt](#worker-receipt)
- [Root acceptance](#root-acceptance)
- [Повтор и discoveries](#повтор-и-discoveries)

## Стратегии и режимы

- `root-only` — default только для `light`, маленькой или тесно связанной реализации; никаких slice artifacts.
- `delegated-sequential` — один активный write slice, максимум два packet за run.
- `delegated-parallel` — зарезервирован, но fail-closed до проверяемой изоляции отдельных worktrees.

`plan` никогда не запускает implementation workers. `implement` выдаёт packet только после проверки неизменного reviewed plan. `full` сначала доводит текущий план до валидного состояния и затем может зарегистрировать packet внутри того же `work`.

Профиль `light` остаётся root-only. Для `standard/complex/critical` adaptive-маршрут предпочитает хотя бы один `delegated-sequential` slice. Root-only допустим, когда реализация слишком мала или настолько связана, что handoff не даёт отдельного проверяемого результата; запиши эту конкретную причину в `implementation.delegation_reason`.

Явная просьба пользователя «реализуй слайсами», `slice`, «делегируй реализацию» или эквивалент сильнее adaptive-решения. Инициализируй run с `--implementation-strategy delegated-sequential`; runner не примет root-only результат. Явный `--implementation-strategy root-only` сохраняет прямое выполнение. В режиме `plan` implementation strategy всегда root-only, потому что код не меняется.

## Slice packet

Root создаёт draft вне производственного manifest, например внутри run-каталога или `/tmp`, затем выполняет:

```bash
python3 scripts/task_graph.py slice-create --run <run-dir> --packet <draft.json>
```

Минимальный draft:

```json
{
  "schema_version": 1,
  "slice_id": "implementation-api",
  "strategy": "delegated-sequential",
  "plan_review": {"mode": "self", "receipt": "root:self-review"},
  "objective": "Наблюдаемый результат слайса.",
  "owned_paths": ["src/api/", "tests/api/"],
  "excluded_paths": ["src/schema/"],
  "must_read": ["AGENTS.md", "docs/architecture.md", "src/api/contract.ts"],
  "known_facts": [{"fact": "Проверенный факт.", "source": "src/api/contract.ts"}],
  "stop_questions": ["Остановиться, если требуется изменить общий schema contract."],
  "acceptance": ["Наблюдаемая проверка проходит."],
  "verification_commands": [{"command": "npm test -- api", "purpose": "Узкий контракт API"}],
  "capability_context": {
    "skills": [{"name": "coding-standards", "reason": "Применить правила стека.", "required": true}],
    "mcp": [{"receipt": "mcp:context7", "mode": "provided", "purpose": "Использовать уже проверенную документацию."}]
  },
  "supersedes": null
}
```

Runner сам добавляет exact plan digest, repository baseline digest, SHA-256 каждого `must_read` файла и timestamp. `owned_paths` обязаны быть подмножеством plan scope и не пересекаться с `excluded_paths`.

В `full` packet фиксирует уже состоявшийся `self` или `independent` plan review; `complex/critical` требуют independent receipt до worker. В `implement` runner сам связывает packet с сохранённым точным review прошлого plan run и записывает `reused`.

Передай свежему worker только canonical packet path, packet SHA-256 и запрет выходить за packet. Не передавай всю историю root-сессии.

Выбирай максимум три применимых skills. Worker обязан полностью прочитать каждый required skill из каталога текущего запуска и ближайшие instruction-файлы из `must_read`. Не загружай весь каталог навыков.

## Worker receipt

Worker пишет draft receipt и root фиксирует его:

```bash
python3 scripts/task_graph.py slice-record \
  --run <run-dir> --slice-id <slice-id> --receipt <worker-receipt.json>
```

Receipt содержит:

```json
{
  "schema_version": 1,
  "slice_id": "implementation-api",
  "packet_sha256": "64 hex",
  "worker_receipt": "/root/task_worker_api",
  "status": "done",
  "summary": "Что сделано.",
  "changed_paths": ["src/api/index.ts", "tests/api/index.test.ts"],
  "tests": [{"command": "npm test -- api", "purpose": "Узкий контракт API", "exit_code": 0, "status": "passed"}],
  "artifacts": [],
  "capabilities_used": [{"kind": "skill", "name": "coding-standards", "status": "applied", "evidence": "Как skill повлиял на реализацию."}],
  "concerns": [],
  "residual_risks": [],
  "discoveries": [{"fact": "Новый проверенный факт.", "source": "src/api/index.ts"}],
  "context_request": null,
  "blocker": null
}
```

Допустимые статусы: `done`, `done_with_concerns`, `needs_context`, `blocked`. `done` требует выполненные назначенные проверки и отсутствие скрытых concerns. Недоступный required skill или недостающий authority context требует `needs_context`, а не догадку.

Runner проверяет packet digest, plan drift, точную дельту с slice baseline, ownership, commands и required capabilities. Receipt остаётся указателем на evidence, а не доказательством истины.

## Root acceptance

Root читает реальный diff, проверяет ownership и соседние контракты, повторяет узкие проверки и добавляет принятый slice в `task.json.implementation.slices`:

```json
{
  "slice_id": "implementation-api",
  "packet_sha256": "64 hex",
  "receipt_sha256": "64 hex",
  "root_acceptance": {
    "verdict": "accepted",
    "verified_changed_paths": ["src/api/index.ts", "tests/api/index.test.ts"],
    "tests": [{"command": "npm test -- api", "purpose": "Root replay", "exit_code": 0, "status": "passed"}],
    "concerns_resolution": []
  }
}
```

`done_with_concerns` требует `accepted_with_concerns` и непустое объяснение resolution. Не создавай reviewer на каждый маленький slice; общий `task_result_reviewer` проверяет уже интегрированный кандидат согласно profile.

## Повтор и discoveries

`needs_context` и `blocked` завершают конкретный immutable packet. Для same-scope correction создай второй packet с новым `slice_id` и `supersedes`; общий лимит остаётся два packet на run.

Discoveries остаются внутри worker receipt. Root переносит только проверенные относящиеся факты в следующий packet. Они не попадают автоматически в memory или канонические документы; durable факт проходит обычный `HANDOFF → Project Start maintenance`.

Выбор остаётся лёгким routing-решением внутри `work`, а не новым этапом графа. Eval стратегии не является стадией пользовательского run.
