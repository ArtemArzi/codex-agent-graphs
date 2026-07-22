# Implementation slices

Этот протокол живёт внутри одного узла `work`. Он добавляет проверяемые handoff-границы, но не превращает Task Delivery в длинный граф.

Ниже описан v2 slice contract только для новых graph `3.4` runs. Активный `3.3.0` run сохраняет v1 packet/receipt и inline root acceptance без `slice-accept`, checkpoint, scope amendment и verifier-repair команд.

## Стратегии и режимы

- `root-only` — `light`, маленькая или тесно связанная реализация; slice artifacts отсутствуют.
- `delegated-sequential` — один активный write slice, максимум два normal packet за run; после verifier reject допускается ровно один дополнительный repair packet.
- `delegated-parallel` — fail-closed, пока нет доказанной изоляции отдельных worktrees.

`plan` не запускает workers. `implement` переиспользует exact review сохранённого плана. `full` создаёт packet после текущего plan review. Явная просьба реализовать слайсами требует `--implementation-strategy delegated-sequential`; root-only completion тогда запрещён.

## Короткий цикл

Для каждого успешного slice:

`slice-create → task_worker → slice-record → root diff/test review → slice-accept`

Если нужен следующий slice:

`context-rehydrate → slice-create`

После последнего slice root запускает union дорогих final checks и формирует один `task.json`. Физический compact сессии опционален: controller checkpoint, а не память чата, является переходным контрактом.

## Slice packet v2

Root создаёт draft в run-каталоге или `/tmp` и выполняет:

```bash
python3 scripts/task_graph.py slice-create --run <run-dir> --packet <draft.json>
```

```json
{
  "schema_version": 2,
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
  "test_impact": [
    {"level": "unit", "action": "update", "paths": ["tests/api/index.test.ts"], "reason": "Изменено unit-поведение."},
    {"level": "integration", "action": "reuse", "paths": ["tests/api/contract.test.ts"], "reason": "Контракт уже покрыт."},
    {"level": "e2e", "action": "not-applicable", "paths": [], "reason": "User journey не меняется."}
  ],
  "slice_checks": [{"command": "npm test -- api-unit", "purpose": "Быстрый контракт API"}],
  "deferred_final_checks": [{"command": "npm run e2e -- api-flow", "purpose": "Интегрированный API flow"}],
  "capability_context": {
    "skills": [{"name": "coding-standards", "reason": "Применить правила стека.", "required": true}],
    "mcp": [{"receipt": "mcp:context7", "mode": "provided", "purpose": "Использовать уже проверенную документацию."}]
  },
  "supersedes": null,
  "repair_for_work_sha256": null
}
```

`test_impact` обязан классифицировать unit, integration и E2E как `reuse`, `update`, `add` или `not-applicable`. Для `update/add` test path входит в ownership и должен реально измениться. Runner добавляет canonical `check_id = SHA-256(command + purpose)`, plan/baseline digests, hashes `must_read`, предыдущий checkpoint digest и timestamp.

Передай fresh worker только canonical packet path, packet SHA-256 и ближайшие инструкции. Worker полностью читает максимум три required skills и использует переданный MCP/research context; вся история root-сессии ему не нужна.

## Worker receipt v2

```bash
python3 scripts/task_graph.py slice-record \
  --run <run-dir> --slice-id <slice-id> --receipt <worker-receipt.json>
```

```json
{
  "schema_version": 2,
  "slice_id": "implementation-api",
  "packet_sha256": "64 hex",
  "worker_receipt": "/root/task_worker_api",
  "status": "done",
  "summary": "Что сделано.",
  "changed_paths": ["src/api/index.ts", "tests/api/index.test.ts"],
  "tests": [{"command": "npm test -- api-unit", "purpose": "Быстрый контракт API", "exit_code": 0, "status": "passed"}],
  "test_changes": [
    {"level": "unit", "action": "update", "paths": ["tests/api/index.test.ts"]},
    {"level": "integration", "action": "reuse", "paths": ["tests/api/contract.test.ts"]},
    {"level": "e2e", "action": "not-applicable", "paths": []}
  ],
  "deferred_final_checks": [{"command": "npm run e2e -- api-flow", "purpose": "Интегрированный API flow"}],
  "artifacts": [],
  "capabilities_used": [{"kind": "skill", "name": "coding-standards", "status": "applied", "evidence": "Как skill повлиял на реализацию."}],
  "concerns": [],
  "residual_risks": [],
  "discoveries": [{"fact": "Новый проверенный факт.", "source": "src/api/index.ts"}],
  "context_request": null,
  "blocker": null
}
```

`done|done_with_concerns` требуют все `slice_checks` зелёными, exact test-impact report и неизменный список deferred checks. Worker не обязан поднимать весь стенд на каждом slice и не имеет права помечать deferred E2E как выполненный. До первой правки worker сохраняет обратимый patch или private pre-edit copy только своей owned delta. Перед `needs_context|blocked` он откатывает только собственные edits к exact slice baseline, не использует broad git restore и не оставляет непринятую дельту. Controller проверяет это по manifest и fail-closed останавливает receipt при остаточных или параллельных изменениях; provenance он не угадывает и файлы автоматически не перезаписывает.

## Root acceptance и checkpoint

Root читает фактический diff, проверяет ownership и соседние контракты, повторяет минимум один exact `slice_check` и создаёт draft:

```json
{
  "schema_version": 1,
  "slice_id": "implementation-api",
  "packet_sha256": "64 hex",
  "receipt_sha256": "64 hex",
  "verdict": "accepted",
  "verified_changed_paths": ["src/api/index.ts", "tests/api/index.test.ts"],
  "tests": [{"command": "npm test -- api-unit", "purpose": "Быстрый контракт API", "exit_code": 0, "status": "passed"}],
  "verified_discoveries": [],
  "concerns_resolution": [],
  "next_objective": "Интегрировать следующий bounded slice или перейти к final checks."
}
```

```bash
python3 scripts/task_graph.py slice-accept \
  --run <run-dir> --slice-id <slice-id> --acceptance <acceptance.json>
```

Runner сохраняет immutable `root-acceptance.json` и обновляет `context-checkpoint.json`. Следующий packet запрещён, пока успешный worker receipt не принят root. В `task.json.implementation.slices` root переносит только `slice_id`, `packet_sha256`, `receipt_sha256` и `acceptance_sha256`; controller сам перечитывает canonical acceptance и требует, чтобы final changed paths ровно совпали с union accepted path provenance. Root-only integration edits внутри delegated strategy не допускаются.

Если нужен следующий slice:

```bash
python3 scripts/task_graph.py context-rehydrate --run <run-dir>
```

Команда проверяет checkpoint identity и возвращает accepted slices, проверенные discoveries, исходный `plan_scope`, exact accepted paths, deferred checks и next objective. `plan_scope` не изображает вычисленный остаток для directory scope: следующий objective определяет root. Следующий packet получает exact checkpoint SHA-256. После последнего slice rehydrate не требуется.

## Final tests

Worker запускает быстрые проверки только своей области. Root после интеграции всех slices запускает deduplicated union `deferred_final_checks`, включая существующие, обновлённые или новые E2E tests, которые покрывают изменённый flow. Каждый exact command/purpose должен появиться зелёным в `task.json.tests`; иначе work не завершится.

## Repair после verifier reject

Reject не открывает новый этап графа: controller возвращает тот же узел `work` и публикует `verification_repair_work_sha256` в `ready/status`. Для delegated run последовательность одна:

`verify reject → context-rehydrate → slice-create(repair_for_work_sha256) → task_worker → slice-record → slice-accept → новый task.json → verify`

Repair packet связан с exact отклонённым `task.json`, использует тот же reviewed plan/scope и является единственным дополнительным worker packet сверх двух normal packets. Несовпадающий SHA-256, второй repair packet или `needs_context|blocked` от repair worker блокируют run; скрытый root bypass запрещён. Если второй normal packet завершился `needs_context|blocked`, run также становится явно blocked вместо бесконечного продолжения.

## Safe scope amendment

Если реальный trace доказал пропущенный технический owner, а активный packet завершился `needs_context|blocked`, root может подготовить:

```json
{
  "schema_version": 1,
  "authority": "root-technical",
  "plan_review_receipt": "root:self-review",
  "added_paths": ["src/api/adapter.ts"],
  "evidence_paths": ["src/api/contract.ts"],
  "reason": "Trace доказал обязательный implementation owner.",
  "impacts": {
    "outcome_changed": false,
    "acceptance_changed": false,
    "public_contract_changed": false,
    "data_or_security_changed": false,
    "external_state_changed": false,
    "risk_profile_changed": false
  }
}
```

```bash
python3 scripts/task_graph.py scope-amend --run <run-dir> --amendment <amendment.json>
```

Runner связывает amendment с exact reviewed base, добавляет максимум два безопасных пути набора, создаёт ordered digest receipt и сохраняет review через эту цепочку. Изменение семантики, acceptance, публичного контракта, данных, безопасности, внешнего состояния, риска, migrations, secrets, env или CI workflow не является technical amendment: требуется решение пользователя и новый review. Никакого «разреши случайный hash» в контракте нет.

## Повтор и durable facts

Для same-scope correction после первого `needs_context|blocked` создай второй normal packet с новым `slice_id` и `supersedes`; общий лимит — два normal packet. Второй неуспешный normal packet является явной терминальной остановкой. Root переносит в checkpoint только проверенные discoveries. Durable факт попадает в каноническую документацию только через обычный `HANDOFF → Project Start maintenance`.
