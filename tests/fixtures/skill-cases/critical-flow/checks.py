import unittest

from handler import make_state, process_event


class SmokeTests(unittest.TestCase):
    def test_valid_paid_event(self):
        state = make_state()
        event = {"id": "event-1", "order_id": "order-1", "account_id": "account-a", "status": "paid"}
        self.assertEqual(process_event(state, event), {"status": "applied"})
        self.assertEqual(state["orders"]["order-1"]["status"], "paid")
        self.assertEqual(state["grants"], ["order-1"])


if __name__ == "__main__":
    unittest.main()
