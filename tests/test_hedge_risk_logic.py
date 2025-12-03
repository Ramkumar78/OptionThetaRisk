
import pandas as pd
from option_auditor.main_analyzer import analyze_csv, _check_itm_risk
from option_auditor.models import TradeGroup, Leg
import unittest
from unittest.mock import patch, MagicMock

class TestHedgeRiskLogic(unittest.TestCase):

    def test_vertical_spread_logic(self):
        """
        Verify that a Vertical Spread (Short ITM Put + Long OTM Put) reduces risk
        compared to a Naked Short Put.
        """
        # Scenario:
        # Price: 390
        # Short Put 400 (ITM by 10). Intrinsic Liability: $1000 per contract.
        # Long Put 390 (ATM/OTM). Intrinsic Asset: $0.
        # WAIT! If Price is 390.
        # Short Put 400: (400-390) = 10. Liab $1000.
        # Long Put 390: (390-390) = 0. Asset $0.
        # Net Risk: -$1000. This IS risky because the hedge (390) hasn't kicked in yet intrinsic-wise.

        # Let's try a deeper ITM scenario where hedge helps.
        # Price: 380.
        # Short Put 400: (400-380)=20. Liab $2000.
        # Long Put 390: (390-380)=10. Asset $1000.
        # Net Risk: -$1000.
        # Still risky (> $500 threshold).

        # Let's try a tighter spread that is FULLY blown.
        # Price: 300.
        # Short Put 400: Liab $10,000.
        # Long Put 390: Asset $9,000.
        # Net Risk: -$1,000.

        # Let's try a SAFE spread (Narrow width).
        # Short Put 100. Long Put 96. Width 4.
        # Price: 50.
        # Short Put 100: Liab $5000.
        # Long Put 96: Asset $4600.
        # Net Risk: -$400.
        # Threshold is -$500. So this should be SAFE.

        price_map = {"ABC": 50.0}

        # Short Put 100
        g1 = TradeGroup("s1", "ABC", pd.Timestamp("2025-01-01"), 100.0, "P")
        g1.qty_net = -1.0

        # Long Put 96
        g2 = TradeGroup("l1", "ABC", pd.Timestamp("2025-01-01"), 96.0, "P")
        g2.qty_net = 1.0

        open_groups = [g1, g2]

        risky, exposure, details = _check_itm_risk(open_groups, price_map)

        self.assertFalse(risky, "Narrow spread (Risk $400) should be under $500 threshold and thus SAFE")
        self.assertEqual(exposure, 0.0, "Exposure should be 0 if not risky")

    def test_naked_put_logic(self):
        """
        Verify that the same Short Put 100 without the hedge is RISKY.
        """
        price_map = {"ABC": 50.0}

        # Short Put 100
        g1 = TradeGroup("s1", "ABC", pd.Timestamp("2025-01-01"), 100.0, "P")
        g1.qty_net = -1.0

        open_groups = [g1]

        risky, exposure, details = _check_itm_risk(open_groups, price_map)

        self.assertTrue(risky, "Naked Short Put should be RISKY")
        # Exposure: (100 - 50) * 100 = 5000
        self.assertEqual(exposure, 5000.0)
        self.assertIn("Net ITM Exposure -$5,000", details[0])

    def test_covered_call_logic(self):
        """
        Verify Covered Call: Long Stock + Short ITM Call.
        """
        # Price: 110.
        # Short Call 100. ITM by 10. Liab $1000.
        # Long Stock (100 shares). Asset Value: 110 * 100 = $11,000.
        # Net Liquidation Value: $11,000 - $1,000 = $10,000 (Positive).
        # SAFE.

        price_map = {"XYZ": 110.0}

        # Short Call 100
        g1 = TradeGroup("c1", "XYZ", pd.Timestamp("2025-01-01"), 100.0, "C")
        g1.qty_net = -1.0

        # Long Stock 100 shares
        g2 = TradeGroup("stk", "XYZ", None, None, None) # Stock has no strike/right
        g2.qty_net = 100.0 # 100 shares? Wait, is qty for stock 1 = 1 share or 100?
        # Parsers set multiplier=1 for STOCK.
        # And usually quantity in TradeGroup is raw quantity.
        # The risk logic says: net_intrinsic_val += current_price * qty
        # If I own 100 shares, I have 100 qty.
        # Short Call has qty -1 (representing 100 shares).
        # Wait, standard option multiplier is 100.
        # Short Call (-1) * 100 multiplier * (Price - Strike) = Intrinsic Liability.
        # Stock (100) * Price = Asset Value.

        # Let's check Parser logic for STOCK.
        # TastytradeParser: "qty" = qty_raw * sign.
        # If I buy 100 shares, qty is 100.

        g2.qty_net = 100.0

        open_groups = [g1, g2]

        risky, exposure, details = _check_itm_risk(open_groups, price_map)

        self.assertFalse(risky, "Covered Call should be SAFE")

        # What if Stock is barely enough?
        # Price 110.
        # Short 2 Calls 100. Liab $2000.
        # Long 100 Shares. Asset $11,000.
        # Net: +$9000. Safe.

        # Risk logic sums Liquidation Values.
        # It doesn't check "Coveredness" explicitly, just Net Equity.
        # If Net Equity < -$500, it's risky.
        # As long as Stock Value > Option Liability, it's positive.

    def test_deep_itm_covered_call_logic(self):
        # Even if deep ITM.
        # Price 200. Short Call 100. Liab (200-100)*100 = $10,000.
        # Stock 100 shares. Asset 200*100 = $20,000.
        # Net: +$10,000. Safe.
        pass

    def test_broken_wing_butterfly_logic(self):
        """
        Verify complex multi-leg interaction.
        Short 2x 100 Puts.
        Long 1x 105 Put.
        Long 1x 80 Put.
        Price: 90.
        """
        # Short 2x 100 Puts: (100-90)*2*100 = Liab $2000.
        # Long 1x 105 Put: (105-90)*1*100 = Asset $1500.
        # Long 1x 80 Put: OTM. Asset $0.

        # Net: +1500 - 2000 = -$500.
        # Threshold is < -$500. This is exactly -500.
        # Logic is `if net < -500`. So -500 is NOT < -500. It is SAFE.

        price_map = {"BWB": 90.0}

        g1 = TradeGroup("s1", "BWB", pd.Timestamp("2025-01-01"), 100.0, "P")
        g1.qty_net = -2.0

        g2 = TradeGroup("l1", "BWB", pd.Timestamp("2025-01-01"), 105.0, "P")
        g2.qty_net = 1.0

        g3 = TradeGroup("l2", "BWB", pd.Timestamp("2025-01-01"), 80.0, "P")
        g3.qty_net = 1.0

        open_groups = [g1, g2, g3]

        risky, exposure, details = _check_itm_risk(open_groups, price_map)

        self.assertFalse(risky, "Exact -$500 exposure should be boundary safe")

        # Move price to 89.
        # Short 2x 100: (100-89)*200 = 11*200 = 2200.
        # Long 1x 105: (105-89)*100 = 16*100 = 1600.
        # Net: 1600 - 2200 = -600.
        # Risky.
        price_map["BWB"] = 89.0
        risky, exposure, details = _check_itm_risk(open_groups, price_map)
        self.assertTrue(risky, "-$600 exposure should be RISKY")
        self.assertEqual(exposure, 600.0)

if __name__ == '__main__':
    unittest.main()
