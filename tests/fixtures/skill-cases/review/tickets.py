_rows = [
    {"id": 1, "status": "open"},
    {"id": 2, "status": "closed"},
    {"id": 3, "status": "open"},
]


def list_tickets(status=None):
    if status not in (None, "open", "closed"):
        raise ValueError("unknown status")
    return [dict(row) for row in _rows if status is None or row["status"] == status]
