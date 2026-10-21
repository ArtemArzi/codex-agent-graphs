from tickets import list_tickets


def render_tickets(status=None):
    return "\n".join(str(row["id"]) for row in list_tickets(status))
