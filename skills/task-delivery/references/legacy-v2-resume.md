# Возобновление Task Delivery v2

Используй этот путь только если `.codex/task-delivery/<task-id>/state.json` имеет `schema_version: 2`. Не переносить активное состояние в v3 и не создавать поверх него новый run с тем же task-id.

1. Прочитай `state.json`, `PROGRESS.md` и текущий `status` старого раннера.
2. Продолжай через `scripts/task_delivery.py`; его команды и доказательные рубежи остаются авторитетными для этой задачи.
3. Используй старые подробные контракты в `references/workflow.md`, `references/planning-contract.md`, `references/testing-and-review.md` и шаблоны в `assets/templates/`.
4. Заверши `verification`, `code-review`, `handoff` и `complete --apply` в старом порядке. Не подделывай квитанции ради перехода на короткий граф.
5. Следующую новую задачу запускай через `scripts/task_graph.py` с новым task-id.

Быстрая проверка:

```bash
python3 scripts/task_delivery.py status --root <repo> --task-id <id>
```

Если v2-состояние повреждено, остановись с фактической диагностикой. Не редактируй `state.json` вручную и не удаляй lock вслепую.
