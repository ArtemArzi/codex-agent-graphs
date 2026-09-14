from ._store import LABELS


def payment_label(payment_id: int) -> str:
    return LABELS.get(payment_id, "unknown")
