# Changelog / Изменения и версии

[Repository](../README.md) · [Русский README](../README.ru.md) · [Documentation](README.md)

The repository contains independently versioned packs and graph contracts.
There is no single suite version. Dates below identify published source commits;
they do not establish installation, deployment or adoption.

В репозитории отдельные версии паков и контрактов графов. Единой версии всего
набора пока нет. Публикация исходников не подтверждает установку или внедрение.

## 2026-10-16 — repository documentation / документация репозитория

Bilingual overview, task/pack selection, a conditional lifecycle map, dynamic
pack-version badges and separate installation/workflow guides. Product versions
and runtime behavior are unchanged by this documentation update.

Русский и английский обзор, выбор пака по задаче, карта процесса, бейджи версий
и отдельные руководства установки и работы. Документация не меняет версии паков
и поведение runtime.

## 2026-10-16 — product packs / продуктовые паки

| Component | Published version | Change and source |
| --- | --- | --- |
| [Agent Lifecycle](../products/agent-lifecycle/README.md) | 0.1.2 | Four lifecycle skills and shared installation; native WSL/Desktop discovery clarified. [Commit b29e998](https://github.com/ArtemArzi/codex-agent-graphs/commit/b29e9984df70d57ba6ae02c9b08df589a8a07212) |
| [Business Automation](../products/business-automation/README.md) | 1.0.0 | Business workflow, hypothesis checks, pinned NMT/last30days sources; 11 managed skills. [Commit 907bb8d](https://github.com/ArtemArzi/codex-agent-graphs/commit/907bb8d) |
| [CRM Business Pack](../products/crm-business-pack/README.md) | 1.0.0 | Bitrix24/amoCRM design, integrations, launch and support guidance. Source use available; no general-installer registration. [Commit f3e30d9](https://github.com/ArtemArzi/codex-agent-graphs/commit/f3e30d9) |

Agent Lifecycle 0.1.1 was introduced in [ce063ed](https://github.com/ArtemArzi/codex-agent-graphs/commit/ce063ed974c9954bc584c142cbe97e6f5703c927);
0.1.2 adds host-discovery documentation and validation evidence.

Добавлены отдельные продукты для работы с бизнесом, CRM и агентами. Бизнес-пак
и агентский пак поддержаны общим установщиком как отдельные scopes. CRM-пак
опубликован как исходники. Их состав, проверенные границы и происхождение
описаны в собственных руководствах и манифестах.

## 2026-10-14 — release and product care / выпуск и сопровождение

- [Deployment](../skills/deployment/SKILL.md): project-native preparation,
  authorized release and interrupted-rollout resume, with adaptive checks and
  target verification. [Commit 1c16ed3](https://github.com/ArtemArzi/codex-agent-graphs/commit/1c16ed3).
- [Product Care](../skills/product-care/SKILL.md): review, diagnose and follow-up
  for operating products; return implementation/release work to existing owners.
  [Commit e97aa12](https://github.com/ArtemArzi/codex-agent-graphs/commit/e97aa12).

Deployment отвечает за подготовку и выпуск; Product Care — за наблюдение работы,
разбор проблем и проверку применения изменения.

## Earlier history / предыдущая история

- [Software Factory guide](SOFTWARE_FACTORY.ru.md): dependency-based ordinary,
  sequential and isolated parallel Task Delivery.
- [6 October stability report](research/skills-stability-2026-10-06/REPORT.ru.md):
  historical audit and corrections; current contracts remain in `skills/`.
- [Git history](https://github.com/ArtemArzi/codex-agent-graphs/commits/main/):
  complete source history.

## Version sources / источники версий

| Kind | Canonical source | Meaning |
| --- | --- | --- |
| Product pack | `products/<pack>/pack.json` → `version` | Reviewed pack composition and published product version |
| Operational graph | `skills/<workflow>/graph.json` → `graph_version` | Execution contract; existing runs also pin its hash |
| Claude plugin | `.claude-plugin/plugin.json` and `marketplace.json` | Separate distribution metadata |
| Installed copy | Installer `verify` against an identified checkout | Actual installed bytes; a README badge cannot establish them |

README version badges query raw published pack manifests through Shields.io.
They can be cached or unavailable independently of the source. Follow the pack
link for its manifest and exact version. They do not select a model or update
any installed copy.

Бейджи показывают опубликованную версию пака, а не версию локальной установки.
Чтобы обновить установленную копию, выполните соответствующие `plan`, `install`
и `verify` по [инструкции](INSTALLATION.md).

## Maintaining this changelog / как обновлять

For a source release, describe the user-visible change and its scope here.
Update the owning pack/version metadata when the product changes, keeping pins,
installation metadata and packaging manifests consistent. A graph-contract
change follows that graph's compatibility/versioning rules. Documentation-only
navigation edits do not invent a new product or suite release.

Run `python3 scripts/check_all.py` and `git diff --check` before committing.
Publication, installation and project validation are reported separately.
