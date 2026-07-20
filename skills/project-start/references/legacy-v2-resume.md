# Возобновление активного maintenance v2

Используй этот договор только если каталог существующего run содержит `state.json` с `graph_version: 2.0.0`. Новый v2 run не создавай.

```bash
python3 scripts/project_maintenance.py ready --run <existing-run-dir>
python3 scripts/project_maintenance.py record \
  --run <existing-run-dir> --node <ready-node> \
  --artifact <artifact.json> --outcome <outcome>
python3 scripts/project_maintenance.py complete --run <existing-run-dir>
```

Каждый JSON использует `schema_version: 1`:

- `maintenance-intake`: `reason`, `trigger`, `canonical_docs` из state.
- `capability-discovery`: `skills` со всеми registry-именами; у каждого `available` и непустой `route_nodes`.
- `drift-audit`: `checked_docs`, `findings`; finding содержит `document`, `claim`, `evidence`, `impact`.
- `impact-classification`: `classification: no-change|factual|semantic`, `rationale`, `affected_docs`; semantic также требует `reopen_stage: discovery|foundation|planning`.
- `documentation-update`: `changed_docs`, `created_docs`, непустой `source_receipts`, `summary`.
- `documentation-verify`: `verdict: pass|reject`, точный `checked_docs`, `stale_claims`, `contradictions`, `residual_risks`; reject требует непустой `repair_list`.
- `maintenance-complete`: достаточно `schema_version: 1`; фактический отчёт завершения создаёт runner.

Для `failed` любой узел принимает `schema_version: 1` и непустой `error`. Не подставляй v3 `project.json` или verification schema в старый run. Auditor, curator и verifier выбирают legacy-форму по graph version.
