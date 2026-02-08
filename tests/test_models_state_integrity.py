import unittest
from datetime import datetime, timedelta
import pandas as pd
from option_auditor.models import Leg, TradeGroup

class TestModelsStateIntegrity(unittest.TestCase):
    def setUp(self):
        self.base_ts = pd.Timestamp("2024-01-01 10:00:00")
        self.group = TradeGroup(
            contract_id="TEST", symbol="TEST", expiry=None, strike=None, right=None
        )

    def test_accumulation_many_legs(self):
        # 1. Adding multiple legs (e.g., 50) and verifying accumulation
        expected_pnl = 0.0
        expected_fees = 0.0
        expected_qty = 0.0

        for i in range(50):
            qty = 1.0 if i % 2 == 0 else -1.0
            price = 100.0 + i
            fees = 0.5
            proceeds = -(qty * price) # buying positive qty costs money (negative proceeds)

            leg = Leg(ts=self.base_ts, qty=qty, price=price, fees=fees, proceeds=proceeds)
            self.group.add_leg(leg)

            expected_pnl += proceeds
            expected_fees += fees
            expected_qty += qty

        self.assertAlmostEqual(self.group.pnl, expected_pnl, places=7)
        self.assertAlmostEqual(self.group.fees, expected_fees, places=7)
        self.assertAlmostEqual(self.group.qty_net, expected_qty, places=7)

    def test_is_closed_floating_point_arithmetic(self):
        # 2. is_closed with small floating-point quantities resulting from arithmetic
        # Scenario: 0.1 added 10 times then subtract 1.0.
        # This often results in a tiny non-zero float.
        for _ in range(10):
            self.group.add_leg(Leg(ts=self.base_ts, qty=0.1, price=10.0, fees=0.0, proceeds=0.0))

        self.assertFalse(self.group.is_closed, "Should not be closed yet (qty=1.0)")

        self.group.add_leg(Leg(ts=self.base_ts, qty=-1.0, price=10.0, fees=0.0, proceeds=0.0))

        # Verify it handles the precision issue
        self.assertTrue(self.group.is_closed, f"Should be closed. Qty is {self.group.qty_net}")
        self.assertLess(abs(self.group.qty_net), 1e-9)

    def test_check_overtrading_boundaries(self):
        # 3. check_overtrading with counts above/below default (10)
        # 0 legs
        self.group.check_overtrading()
        self.assertFalse(self.group.is_overtraded)

        # 10 legs (boundary)
        for _ in range(10):
            self.group.add_leg(Leg(ts=self.base_ts, qty=1, price=1, fees=0, proceeds=0))
        self.group.check_overtrading()
        self.assertFalse(self.group.is_overtraded)

        # 11 legs (over)
        self.group.add_leg(Leg(ts=self.base_ts, qty=1, price=1, fees=0, proceeds=0))
        self.group.check_overtrading()
        self.assertTrue(self.group.is_overtraded)

    def test_entry_exit_ts_ordering(self):
        # 4. entry_ts and exit_ts regardless of order
        t1 = self.base_ts
        t2 = self.base_ts + timedelta(hours=1)
        t3 = self.base_ts + timedelta(hours=2)

        # Add middle
        self.group.add_leg(Leg(ts=t2, qty=1, price=1, fees=0, proceeds=0))
        self.assertEqual(self.group.entry_ts, t2)
        self.assertEqual(self.group.exit_ts, t2)

        # Add earliest (should update entry, not exit)
        self.group.add_leg(Leg(ts=t1, qty=1, price=1, fees=0, proceeds=0))
        self.assertEqual(self.group.entry_ts, t1)
        self.assertEqual(self.group.exit_ts, t2)

        # Add latest (should update exit, not entry)
        self.group.add_leg(Leg(ts=t3, qty=1, price=1, fees=0, proceeds=0))
        self.assertEqual(self.group.entry_ts, t1)
        self.assertEqual(self.group.exit_ts, t3)

        # New group for random order
        group2 = TradeGroup(contract_id="TEST2", symbol="TEST", expiry=None, strike=None, right=None)
        # Add latest
        group2.add_leg(Leg(ts=t3, qty=1, price=1, fees=0, proceeds=0))
        # Add earliest
        group2.add_leg(Leg(ts=t1, qty=1, price=1, fees=0, proceeds=0))
        # Add middle
        group2.add_leg(Leg(ts=t2, qty=1, price=1, fees=0, proceeds=0))

        self.assertEqual(group2.entry_ts, t1)
        self.assertEqual(group2.exit_ts, t3)
