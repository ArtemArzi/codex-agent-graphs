from tickets import _rows


def render_tickets(status=None):
    selected = _rows if status is None else [row for row in _rows if row["status"] == status]
    return "\n".join(str(row["id"]) for row in selected)
