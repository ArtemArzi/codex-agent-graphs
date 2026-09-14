# Architecture smoke project

## Scope

Small single-process application. Keep changes inside the assigned module.

## Map

Before planning, implementing or reviewing read ARCHITECTURE.md and ENGINEERING.md.
Pass their applicable sections, constraints and checks explicitly to each subagent.

## Commands

Run `python3 check.py` from this directory.

## Boundaries

Payments owns payment state. Consumers use payments.public only.
No framework, service, broker or extra database is needed for this fixture.
