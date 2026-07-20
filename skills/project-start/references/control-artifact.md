# Управляющие артефакты v3

Артефакты хранят квитанцию одного прохода. Каноническая истина остаётся в документах проекта.

## `project.json`

```json
{
  "schema_version": 3,
  "mode": "bootstrap",
  "summary": "Что установлено или синхронизировано",
  "classification": "bootstrap-ready",
  "capabilities": ["rg", "domain-modeling"],
  "agents": [],
  "canonical_docs": [
    "AGENTS.md",
    "docs/project/FOUNDATION.md",
    "docs/project/PLAN.md",
    "docs/project/PROJECT.md",
    "docs/project/QUALITY.md"
  ],
  "changed_docs": [],
  "created_docs": [
    "AGENTS.md",
    "docs/project/FOUNDATION.md",
    "docs/project/PLAN.md",
    "docs/project/PROJECT.md",
    "docs/project/QUALITY.md"
  ],
  "evidence": ["AGENTS.md", "docs/project/PROJECT.md"],
  "coverage": {
    "business": "docs/project/PROJECT.md",
    "foundation": "docs/project/FOUNDATION.md",
    "quality": "docs/project/QUALITY.md",
    "plan": "docs/project/PLAN.md",
    "agent_context": "AGENTS.md"
  },
  "verification": "self",
  "confidence": "high",
  "gaps": [],
  "decision": null
}
```

Maintenance использует `classification: no-change|factual|semantic` и `coverage: {}`. Для bootstrap дельта считается от `init`. Для maintenance `changed_docs` и `created_docs` включают дрейф канонических документов и `AGENTS.md` от последнего verified operational snapshot, а также документационные правки текущего run. Обычный внешний `CHANGELOG.md` или README не становится каноническим только из-за существования. Первый v3-проход над legacy state без точного operational snapshot всегда требует independent verify. Массивы должны точно совпасть с этой дельтой, а все затронутые документы входить в `canonical_docs`.

`agents` содержит только квитанции `explorer` или `explorer:<id>`, максимум две. `capabilities` перечисляет реально использованные навыки и инструменты, а не весь доступный каталог. `evidence` содержит существующие пути внутри репозитория.

Для запроса существенного решения в maintenance:

```json
"classification": "semantic",
"changed_docs": [],
"created_docs": [],
"decision": {
  "question": "Какой публичный договор становится каноническим?",
  "recommended": "Сохранить обратную совместимость",
  "scope": ["docs/architecture.md"]
}
```

После `decide` внеси правку и замени payload на `{ "id": "<decision-id>" }`. Runner сверяет id с зафиксированным ответом и разрешает последующую document delta только внутри `scope`. Один run объединяет существенные вопросы в одно решение.

Bootstrap decision использует `classification: bootstrap-ready`, а до ответа — пустые `canonical_docs`, `changed_docs`, `created_docs`, `evidence` и `coverage`. Decision-квитанция в обоих режимах всегда создаётся до правок текущего run. После ответа итоговый bootstrap обязан закрыть полный coverage и пройти independent verify. В maintenance уже существующий operational drift можно перечислить в decision-квитанции, но новых правок между `init` и `decision` быть не должно.

## `verification.json`

```json
{
  "schema_version": 3,
  "verdict": "pass",
  "work_sha256": "<sha256 project.json>",
  "docs_sha256": "<digest exact document snapshot>",
  "checked_docs": [
    "AGENTS.md",
    "docs/project/FOUNDATION.md",
    "docs/project/PLAN.md",
    "docs/project/PROJECT.md",
    "docs/project/QUALITY.md"
  ],
  "residual_risks": [],
  "repair_list": []
}
```

При `verdict: reject` используй outcome `failed` и непустой `repair_list`. Digest и список возьми из последней work-квитанции в `state.json`; не вычисляй «похожий» набор вручную.
