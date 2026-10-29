def make_state():
    return {
        "orders": {"order-1": {"account_id": "account-a", "status": "pending"}},
        "grants": [],
        "seen": set(),
    }


def process_event(state, event):
    order = state["orders"].get(event["order_id"])
    if order is None:
        return {"status": "unknown_order"}
    if order["account_id"] != event["account_id"]:
        return {"status": "forbidden"}
    if event["status"] != "paid":
        return {"status": "ignored"}
    order["status"] = "paid"
    state["grants"].append(event["order_id"])
    state["seen"].add(event["id"])
    return {"status": "applied"}
