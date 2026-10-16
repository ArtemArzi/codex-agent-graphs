# Documentation / Документация

[English overview](../README.md) · [Обзор на русском](../README.ru.md)

Start with the task and installation scope. Product guides own their pack
contents; current `skills/`, `policies/` and project instructions own execution.

Начните с задачи и области установки. Руководство пака описывает состав и
применение; действующие правила находятся в скиллах, политиках и документах проекта.

## Start here / начать здесь

| Document | Read it when / когда читать |
| --- | --- |
| [Installation and updates](INSTALLATION.md) | Installing one pack, targeting CLI/Desktop, preserving settings, updating or using Claude Code |
| [Workflow guide](WORKFLOWS.md) | Choosing stage owners, understanding optional graphs, review, routing and artifact lifecycle |
| [Changelog](CHANGELOG.md) | Checking published changes and version sources |
| [Project Start handoff, RU](PROJECT_START_HANDOFF.ru.md) | Giving another person or their agent a project-setup starting point |
| [Software Factory, RU](SOFTWARE_FACTORY.ru.md) | Coordinating sequential/parallel engineering work with isolated context and integration checks |

Detailed installation and workflow guides are in English; the root Russian
README includes the overview, pack selection, examples and quick-start commands.

Подробные инструкции установки и архитектуры выше — на английском. Русский
README содержит обзор, выбор пака, примеры и команды быстрого старта.

## Product guides / руководства паков

| Guide | Owner and scope / область |
| --- | --- |
| [Business Automation](../products/business-automation/README.md) | Business context, process improvement, product methods, adoption and effect |
| [CRM Business Pack](../products/crm-business-pack/README.md) | Bitrix24/amoCRM configuration, integrations, launch and support |
| [Agent Lifecycle](../products/agent-lifecycle/README.md) | Agent design, memory, outcome E2E, pilot and handover |

Each product guide links its `pack.json`, sources and available validation.
Guidance validation and synthetic scenarios are bounded evidence, rather than
proof of live provider behavior or business effect.

## For contributors / для изменений

- [Repository instructions](../AGENTS.md): invariants and required checks.
- [Model routing](../policies/model-routing.toml): canonical role/model settings.
- [Installer](../scripts/install.py) and [shared-pack installer](../scripts/business_pack.py): current supported flags and behavior.
- [Repository gate](../scripts/check_all.py) and [tests](../tests/): validation owners.
- [Agent packaging checker](../scripts/check_agent_pack.py): product-owned manifests and packaging integrity.

## Historical evidence / история и доказательства

- [Research](research/): source investigations, audits and proposals.
- [Task records](tasks/): plans, observations, receipts and verification from particular tasks.

Historical files may refer to older versions or unimplemented proposals. They
remain available as evidence; use current source and project facts for new work.

Исторические материалы могут описывать старые версии и невнедрённые предложения.
Для новой задачи сверяйтесь с текущими исходниками и фактами проекта.
