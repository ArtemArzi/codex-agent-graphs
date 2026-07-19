#!/usr/bin/env python3
"""Adversarial, forward-safe contract tests for project_start.py."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("project_start.py")


def run(root: Path, *arguments: str, expected: int = 0) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"Unexpected exit {result.returncode}, expected {expected}\n"
            f"command: {' '.join(arguments)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Output is not JSON:\n{result.stdout}") from exc
    for key in ("status", "summary", "next_actions", "artifacts", "data"):
        if key not in payload:
            raise AssertionError(f"Missing output field: {key}")
    return payload


def remove_markers(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--\s*PROJECT-START:REQUIRED.*?-->", "", text, flags=re.DOTALL)
    path.write_text(text, encoding="utf-8")


def fill_marked_template(path: Path, prefix: str) -> None:
    text = path.read_text(encoding="utf-8")
    counter = 0

    def replacement(_: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f"{prefix}: подтверждённое решение раздела {counter} с владельцем, границей и проверяемым результатом."

    text = re.sub(r"<!--\s*PROJECT-START:REQUIRED.*?-->", replacement, text, flags=re.DOTALL)
    path.write_text(text, encoding="utf-8")


def fill_decisions(path: Path) -> None:
    path.write_text(
        """# Факты, предположения, решения и риски

| ID | Вид | Формулировка | Состояние | Источник/доказательство | Владелец | Проверка | Пересмотр | Последствия ошибки |
|---|---|---|---|---|---|---|---|---|
| D-001 | decision | Первый выпуск проводит один заказ через полный безопасный поток | accepted | Одобренный PROJECT.md | Founder | Дымовой сквозной сценарий | При изменении первой версии | Потребуется пересмотр архитектуры |
""",
        encoding="utf-8",
    )


def fill_manifest(path: Path, research_path: str) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    value["profile"] = "web-single-service"
    value["product_shape"] = ["single web application"]
    value["stack_research"] = {
        "completed": True,
        "date": "2026-07-19",
        "artifact": research_path,
        "alternatives_compared": ["Python with FastAPI and PostgreSQL", "TypeScript with Fastify and PostgreSQL"],
        "external_constraint": False,
        "constraint_reason": "not-applicable",
    }
    value["runtime"] = {"language": "Python", "version": "3.12", "package_manager": "uv"}
    value["architecture"] = {
        "style": "modular-monolith",
        "modules": ["domain-core", "external-adapter"],
        "dependency_rules": ["external-adapter may depend on domain-core only"],
        "structural_check_command": "python -m architecture_check",
    }
    for key in value["commands"]:
        value["commands"][key] = "not-applicable: toy repository has no command for this contract"
    value["commands"]["verify"] = "python -m tests"
    for key in value["risk_flags"]:
        value["risk_flags"][key] = False
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return value


def write_verification(path: Path, *, failed: bool = False) -> None:
    if failed:
        rows = "| 2026-07-19 | foundation | python -m tests | success | failed with error | nonzero | logs/failure.txt | verifier |\n"
    else:
        rows = (
            "| 2026-07-19 | foundation | python -m tests | success | all checks passed | 0 | docs/project/VERIFICATION.md | verifier |\n"
            "| 2026-07-19 | architecture | python -m architecture_check | success | dependency rules passed | success | docs/project/VERIFICATION.md | verifier |\n"
        )
    path.write_text(
        """# Доказательства проверки

| Дата | Область | Команда/действие | Ожидание | Фактический результат | Код/статус | Артефакт | Проверил |
|---|---|---|---|---|---|---|---|
"""
        + rows
        + "\n## Непроверенное\n\nНепроверенных обязательных команд и сценариев не осталось.\n",
        encoding="utf-8",
    )


def write_plan(path: Path, count: int) -> None:
    blocks = []
    for number in range(1, count + 1):
        blocks.append(
            f"""### {number}. Сквозной результат номер {number}

- **Поведение:** Пользователь завершает полезный сквозной сценарий номер {number} и видит подтверждённый результат.
- **Доказательство готовности:** Автоматическая проверка и демонстрация подтверждают результат части номер {number}.
- **Зависит от:** Только от явно перечисленных предыдущих сквозных результатов и одобренного основания.
- **Основные риски:** Ошибка данных или неполное восстановление выявляются отрицательным сценарием.
- **Не входит:** Дополнительные оптимизации и удобства, не нужные для этого проверяемого поведения.
"""
        )
    path.write_text(
        """# Верхнеуровневый план

## Цель

Доставить одобренный первый выпуск через последовательные проверяемые пользовательские результаты.

## Крупные части

"""
        + "\n".join(blocks)
        + """
## Порядок и открытый фронт

Первая часть открыта сейчас; каждая следующая открывается после доказательства своего блокера.

## Правило дробления

Каждая крупная часть дробится на сквозные задачи, помещающиеся в один свежий контекст.
""",
        encoding="utf-8",
    )


def record(root: Path, event: str, evidence: str, note: str = "Подэтап проверен и принят") -> dict:
    return run(
        root,
        "record",
        "--root",
        str(root),
        "--event",
        event,
        "--evidence",
        evidence,
        "--note",
        note,
        "--apply",
    )


def test_path_safety(base: Path) -> None:
    collision = base / "collision"
    collision.mkdir()
    run(
        collision,
        "bootstrap",
        "--root",
        str(collision),
        "--stage",
        "discovery",
        "--business-doc",
        ".project-start/state.json",
        "--apply",
        expected=2,
    )
    assert not (collision / ".project-start/state.json").exists()

    duplicate = base / "duplicate"
    duplicate.mkdir()
    run(
        duplicate,
        "bootstrap",
        "--root",
        str(duplicate),
        "--stage",
        "discovery",
        "--business-doc",
        "same.md",
        "--decisions-doc",
        "same.md",
        "--apply",
        expected=2,
    )
    assert not (duplicate / "same.md").exists()

    if hasattr(os, "symlink"):
        outside = base / "outside"
        outside.mkdir()
        linked = base / "linked"
        linked.mkdir()
        try:
            os.symlink(outside, linked / ".project-start", target_is_directory=True)
        except OSError:
            return  # Native Windows may deny symlink creation without Developer Mode.
        run(linked, "bootstrap", "--root", str(linked), "--stage", "discovery", "--apply", expected=2)
        assert not (outside / "state.json").exists()

        temp_attack = base / "temp-attack"
        temp_attack.mkdir()
        (temp_attack / ".project-start").mkdir()
        external_file = base / "external.txt"
        external_file.write_text("unchanged", encoding="utf-8")
        os.symlink(external_file, temp_attack / ".project-start/state.json.tmp")
        run(temp_attack, "bootstrap", "--root", str(temp_attack), "--stage", "discovery", "--apply")
        assert external_file.read_text(encoding="utf-8") == "unchanged"


def test_v1_migration(base: Path) -> None:
    root = base / "migration"
    (root / ".project-start").mkdir(parents=True)
    old = {
        "schema_version": 1,
        "phase": "planning",
        "created_at": "2026-07-01T00:00:00+00:00",
        "updated_at": "2026-07-01T00:00:00+00:00",
        "approvals": {"business": {"at": "old"}, "foundation": {"at": "old"}, "plan": None},
        "artifacts": {"business": "docs/project/PROJECT.md", "decisions": "docs/project/DECISIONS.md"},
        "history": [],
    }
    state_path = root / ".project-start/state.json"
    state_path.write_text(json.dumps(old), encoding="utf-8")
    status = run(root, "status", "--root", str(root))
    assert status["status"] == "warning" and "migrate" in " ".join(status["next_actions"])
    run(root, "migrate", "--root", str(root), "--note", "Adopt verified v2 gates")
    assert json.loads(state_path.read_text())["schema_version"] == 1
    run(root, "migrate", "--root", str(root), "--note", "Adopt verified v2 gates", "--apply")
    migrated = json.loads(state_path.read_text())
    assert migrated["schema_version"] == 2 and migrated["phase"] == "discovery"
    assert migrated["approvals"] == {"business": None, "foundation": None, "plan": None}
    assert json.loads((root / ".project-start/state.v1.backup.json").read_text())["schema_version"] == 1

    resumed = base / "migration-resume"
    (resumed / ".project-start").mkdir(parents=True)
    resumed_state = resumed / ".project-start/state.json"
    resumed_backup = resumed / ".project-start/state.v1.backup.json"
    resumed_state.write_text(json.dumps(old), encoding="utf-8")
    resumed_backup.write_text(json.dumps(old), encoding="utf-8")
    preview = run(resumed, "migrate", "--root", str(resumed), "--note", "Resume interrupted migration")
    assert preview["data"]["backup_action"] == "keep-matching"
    run(resumed, "migrate", "--root", str(resumed), "--note", "Resume interrupted migration", "--apply")
    assert json.loads(resumed_state.read_text())["schema_version"] == 2

    mismatch = base / "migration-mismatch"
    (mismatch / ".project-start").mkdir(parents=True)
    (mismatch / ".project-start/state.json").write_text(json.dumps(old), encoding="utf-8")
    (mismatch / ".project-start/state.v1.backup.json").write_text(json.dumps({**old, "phase": "foundation"}), encoding="utf-8")
    run(mismatch, "migrate", "--root", str(mismatch), "--note", "Do not overwrite mismatch", "--apply", expected=2)


def test_full_lifecycle(root: Path) -> None:
    run(root, "bootstrap", "--root", str(root), "--stage", "discovery", "--apply")
    project = root / "docs/project/PROJECT.md"
    decisions = root / "docs/project/DECISIONS.md"
    context = root / "CONTEXT.md"

    remove_markers(project)
    bypass = run(root, "validate", "--root", str(root), "--stage", "discovery", expected=1)
    assert any("содерж" in item["message"].casefold() for item in bypass["data"]["issues"])

    project.write_text(
        "# Сквозная бизнес-логика проекта\n\n"
        + "\n\n".join(
            f"## {heading}\n\n{heading}: подтверждённое бизнес-решение с владельцем, границей и наблюдаемым критерием."
            for heading in (
                "Результат и болезненная проблема", "Участники и ответственность", "Сквозной поток",
                "Состояния и переходы", "Бизнес-правила и инварианты", "Данные и владение",
                "Ошибки, исключения и ручная работа", "Первая версия", "Не входит",
                "Нефункциональные ограничения", "Критерии приёмки", "Открытые вопросы",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    fill_decisions(decisions)
    context.write_text(
        "# Domain language\n\nA precise glossary for the first release.\n\n## Language\n\n"
        "**Work item**:\nA customer request that moves through one complete accepted flow.\n_Avoid_: task, record\n",
        encoding="utf-8",
    )
    run(root, "validate", "--root", str(root), "--stage", "discovery")
    run(root, "approve", "--root", str(root), "--gate", "business", "--note", "Business flow approved", "--apply")

    state = json.loads((root / ".project-start/state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "foundation" and state["approvals"]["business"]["fingerprint"]

    run(root, "bootstrap", "--root", str(root), "--stage", "foundation", "--apply")
    for name in ("FOUNDATION.md", "CODEBASE.md", "QUALITY.md", "AUTHORITY.md", "AGENT-OPERATIONS.md"):
        fill_marked_template(root / "docs/project" / name, name)
    research = root / "docs/project/STACK-RESEARCH.md"
    research.write_text("Исследованы два поддерживаемых стека по официальной документации; источники, версии и риски сохранены.", encoding="utf-8")
    stack_decision = root / "docs/project/STACK-DECISION.md"
    stack_decision.write_text("Выбран Python 3.12 с PostgreSQL после сравнения простоты, тестируемости и цены выхода.", encoding="utf-8")
    fill_manifest(root / ".project-start/foundation.json", "docs/project/STACK-RESEARCH.md")
    write_verification(root / "docs/project/VERIFICATION.md", failed=True)

    record(root, "foundation-research", "docs/project/STACK-RESEARCH.md")
    original_research = research.read_text(encoding="utf-8")
    research.write_text(original_research + "\nизменено после фиксации\n", encoding="utf-8")
    assert run(root, "status", "--root", str(root))["status"] == "warning"
    run(root, "record", "--root", str(root), "--event", "foundation-stack", "--evidence", "docs/project/STACK-DECISION.md", "--note", "stale prior", "--apply", expected=2)
    research.write_text(original_research, encoding="utf-8")
    record(root, "foundation-stack", "docs/project/STACK-DECISION.md")
    record(root, "foundation-codebase", "docs/project/CODEBASE.md")
    record(root, "foundation-quality", "docs/project/QUALITY.md")
    blocked_review = root / "docs/project/FOUNDATION-REVIEW.md"
    valid_review = (
        "PROJECT-START-REVIEW: PASS\nCritical: 0\nHigh: 0\nReviewer: independent reviewer\n"
        "Reviewed-at: 2026-07-19T15:00:00+05:00\n\n"
        "## Область\nAll foundation contracts and commands were checked independently.\n\n"
        "## Замечания\nNo blocking findings remain after targeted verification.\n\n"
        "## Доказательства\nThe reviewer ran the canonical verify and architecture commands successfully.\n"
    )
    blocked_review.write_text(valid_review, encoding="utf-8")
    run(
        root,
        "record",
        "--root",
        str(root),
        "--event",
        "foundation-ready",
        "--evidence",
        "docs/project/FOUNDATION-REVIEW.md",
        "--note",
        "Review passed",
        "--apply",
        expected=2,
    )

    write_verification(root / "docs/project/VERIFICATION.md")
    blocked_review.write_text(
        (SCRIPT.parents[1] / "assets/templates/FOUNDATION-REVIEW.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    run(
        root, "record", "--root", str(root), "--event", "foundation-ready", "--evidence",
        "docs/project/FOUNDATION-REVIEW.md", "--note", "raw template", "--apply", expected=2,
    )
    blocked_review.write_text(valid_review, encoding="utf-8")
    record(root, "foundation-ready", "docs/project/FOUNDATION-REVIEW.md", "Independent review has no blocking findings")
    run(root, "validate", "--root", str(root), "--stage", "foundation")
    run(root, "approve", "--root", str(root), "--gate", "foundation", "--note", "Foundation approved", "--apply")

    original_project = project.read_text(encoding="utf-8")
    project.write_text(original_project + "\nmaterial drift\n", encoding="utf-8")
    drift = run(root, "validate", "--root", str(root), "--stage", "planning", expected=1)
    assert any("измен" in item["message"].casefold() for item in drift["data"]["issues"])
    status_drift = run(root, "status", "--root", str(root))
    assert status_drift["status"] == "warning" and status_drift["data"]["integrity_issues"]
    project.write_text(original_project, encoding="utf-8")
    original_decisions = decisions.read_text(encoding="utf-8")
    decisions.write_text(original_decisions + "\nmaterial decision drift\n", encoding="utf-8")
    assert run(root, "status", "--root", str(root))["status"] == "warning"
    decisions.write_text(original_decisions, encoding="utf-8")
    original_context = context.read_text(encoding="utf-8")
    context.write_text(original_context + "\n**New term**:\nA materially new domain definition.\n", encoding="utf-8")
    assert run(root, "status", "--root", str(root))["status"] == "warning"
    context.write_text(original_context, encoding="utf-8")
    run(root, "approve", "--root", str(root), "--gate", "business", "--note", "illegal regression", "--apply", expected=2)
    assert json.loads((root / ".project-start/state.json").read_text())["phase"] == "planning"

    run(root, "bootstrap", "--root", str(root), "--stage", "planning", "--apply")
    plan = root / "docs/project/PLAN.md"
    write_plan(plan, 1)
    run(root, "validate", "--root", str(root), "--stage", "planning", expected=1)
    write_plan(plan, 5)
    run(root, "validate", "--root", str(root), "--stage", "planning")
    run(root, "approve", "--root", str(root), "--gate", "plan", "--note", "Plan approved", "--apply")
    assert json.loads((root / ".project-start/state.json").read_text())["phase"] == "tickets"

    published = root / "docs/project/TICKETS.md"
    (root / "docs/project/issues").mkdir()
    (root / "docs/project/issues/01.md").write_text("# First ticket\n\nA verifiable vertical result.\n", encoding="utf-8")
    receipt = root / "docs/project/TICKETS-RECEIPT.md"
    receipt.write_text(
        "PROJECT-START-TRACKER-RECEIPT: VERIFIED\nTracker: local-markdown\n"
        "Captured-at: 2026-07-19T15:10:00+05:00\n- issues/01.md sha256:test-receipt\n",
        encoding="utf-8",
    )
    published.write_text(
        "PROJECT-START-TICKETS-PUBLISHED: YES\nTracker: local-markdown\n"
        "Published-at: 2026-07-19T15:10:00+05:00\nReceipt: TICKETS-RECEIPT.md\n"
        "- [First ticket](issues/01.md)\n",
        encoding="utf-8",
    )
    run(
        root, "record", "--root", str(root), "--event", "tickets-published", "--evidence",
        "docs/project/TICKETS.md", "--note", "wrong order", "--apply", expected=2,
    )
    approved = root / "docs/project/TICKETS-APPROVAL.md"
    approved.write_text(
        (SCRIPT.parents[1] / "assets/templates/TICKETS-APPROVAL.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    run(
        root, "record", "--root", str(root), "--event", "tickets-approved", "--evidence",
        "docs/project/TICKETS-APPROVAL.md", "--note", "raw template", "--apply", expected=2,
    )
    approved.write_text(
        "PROJECT-START-TICKETS-APPROVED: YES\nApproved-by: fixture-user\n"
        "Approved-at: 2026-07-19T15:09:00+05:00\n"
        "Scope: Пользователь одобрил размер и блокирующие связи пяти сквозных задач.\n",
        encoding="utf-8",
    )
    record(root, "tickets-approved", "docs/project/TICKETS-APPROVAL.md")
    valid_receipt = receipt.read_text(encoding="utf-8")
    receipt.write_text(valid_receipt.replace("issues/01.md", "unrelated fabricated prose"), encoding="utf-8")
    run(
        root, "record", "--root", str(root), "--event", "tickets-published", "--evidence",
        "docs/project/TICKETS.md", "--note", "unrelated receipt", "--apply", expected=2,
    )
    receipt.write_text(valid_receipt, encoding="utf-8")
    record(root, "tickets-published", "docs/project/TICKETS.md")
    assert json.loads((root / ".project-start/state.json").read_text())["phase"] == "execution"
    run(root, "validate", "--root", str(root), "--stage", "execution")

    run(root, "complete", "--root", str(root), "--note", "too early", "--apply", expected=2)
    run(
        root, "record", "--root", str(root), "--event", "implementation-evidence", "--evidence",
        "docs/project/VERIFICATION.md", "--note", "old evidence", "--apply", expected=2,
    )
    verification = root / "docs/project/VERIFICATION.md"
    verification.write_text(
        verification.read_text(encoding="utf-8")
        + "| 2026-07-19 | implementation | python -m tests | success | implemented ticket passed verify and smoke | 0 | docs/project/VERIFICATION.md | verifier |\n",
        encoding="utf-8",
    )
    record(root, "implementation-evidence", "docs/project/VERIFICATION.md", "Implementation verified")
    acceptance = root / "docs/project/ACCEPTANCE.md"
    acceptance.write_text(
        (SCRIPT.parents[1] / "assets/templates/ACCEPTANCE.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    run(
        root, "record", "--root", str(root), "--event", "user-acceptance", "--evidence",
        "docs/project/ACCEPTANCE.md", "--note", "raw template", "--apply", expected=2,
    )
    acceptance.write_text(
        "PROJECT-START-USER-ACCEPTANCE: YES\nAccepted-by: fixture-user\n"
        "Accepted-at: 2026-07-19T15:20:00+05:00\n"
        "Accepted-result: Пользователь принял согласованный сквозной результат.\n"
        "Verified-evidence: docs/project/VERIFICATION.md\nKnown-followups: Нет скрытых продолжений.\n",
        encoding="utf-8",
    )
    record(root, "user-acceptance", "docs/project/ACCEPTANCE.md", "User explicitly accepted result")
    run(root, "complete", "--root", str(root), "--note", "First goal accepted", "--apply")
    assert json.loads((root / ".project-start/state.json").read_text())["phase"] == "complete"

    run(root, "reopen", "--root", str(root), "--stage", "planning", "--note", "Change delivery order", "--apply")
    reopened = json.loads((root / ".project-start/state.json").read_text())
    assert reopened["phase"] == "planning"
    assert reopened["approvals"]["plan"] is None
    assert "tickets-published" not in reopened["records"]
    assert "foundation-ready" in reopened["records"]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="project-start-test-") as temporary:
        base = Path(temporary)
        test_path_safety(base)
        test_v1_migration(base)
        lifecycle = base / "lifecycle"
        lifecycle.mkdir()
        test_full_lifecycle(lifecycle)
    print("project-start adversarial self-test: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
