"""Small executable oracle; import boundary is deliberately limited to this fixture."""

import ast
from pathlib import Path


def check_boundary(source: str) -> None:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
        else:
            continue
        if any(name == "payments._store" or name.startswith("payments._store.") for name in names):
            raise AssertionError("E1: notifications must use payments.public")


def main() -> None:
    check_boundary(Path(__file__).with_name("notifications.py").read_text())
    from notifications import render_payment

    assert render_payment(1) == "Payment: paid"
    assert render_payment(99) == "Payment: unknown"
    print("PASS: public-contract behavior and E1 import boundary")


if __name__ == "__main__":
    main()
