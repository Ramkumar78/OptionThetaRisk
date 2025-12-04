import pandas as pd
from option_auditor.main_analyzer import analyze_csv
from option_auditor.models import TradeGroup, Leg
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

class TestITMRisk(unittest.TestCase):
    def test_live_itm_risk(self):
        # Setup: One open Short Put that is ITM
        # Symbol: SPY, Strike: 400, Type: Put, Qty: -1 (Short)
        # Current Price: 390 (ITM for Put)
        # Intrinsic: (400 - 390) * 1 * 100 = $1000 Exposure

        # We must mock yf.download because _fetch_live_prices now uses batch download first
        with patch('yfinance.download') as mock_download:
            # Create a mock DataFrame for SINGLE SYMBOL (Standard columns, not MultiIndex)
            # because the analyzer checks len(symbols) == 1
            mock_df = pd.DataFrame({'Close': [390.0]})
            mock_download.return_value = mock_df

            with patch('option_auditor.main_analyzer._group_contracts_with_open') as mock_group:
                tg = TradeGroup(
                    contract_id="123",
                    symbol="SPY",
                    expiry=pd.Timestamp("2024-12-20"),
                    strike=400.0,
                    right="P"
                )
                tg.qty_net = -1.0
                tg.entry_ts = pd.Timestamp("2024-01-01")
                tg.legs = [Leg(ts=pd.Timestamp("2024-01-01"), qty=-1.0, price=5.0, fees=0.0, proceeds=500.0)]

                mock_group.return_value = ([], [tg])

                manual_data = [{
                    "date": "2024-01-01 10:00:00",
                    "symbol": "SPY",
                    "action": "Sell to Open",
                    "qty": 1,
                    "price": 5.0,
                    "fees": 1.0,
                    "expiry": "2024-12-20",
                    "strike": 400.0,
                    "right": "P"
                }]

                with patch('option_auditor.main_analyzer.build_strategies') as mock_strat:
                    mock_strat.return_value = []

                    result = analyze_csv(manual_data=manual_data)

                    self.assertEqual(result['verdict'], "Red Flag: High Open Risk")
                    self.assertEqual(result['verdict_color'], "red")

                    details = result.get('verdict_details', '')
                    self.assertIn("Warning: 1 positions are deep ITM", details)
                    self.assertIn("Total Intrinsic Exposure: -$1,000.00", details)

    def test_live_itm_risk_no_risk(self):
        # Setup: One open Short Put that is OTM
        # Symbol: SPY, Strike: 400, Type: Put, Qty: -1 (Short)
        # Current Price: 410 (OTM for Put)

        with patch('yfinance.download') as mock_download:
            # Single symbol mock
            mock_df = pd.DataFrame({'Close': [410.0]})
            mock_download.return_value = mock_df

            with patch('option_auditor.main_analyzer._group_contracts_with_open') as mock_group:
                tg = TradeGroup(
                    contract_id="123",
                    symbol="SPY",
                    expiry=pd.Timestamp("2024-12-20"),
                    strike=400.0,
                    right="P"
                )
                tg.qty_net = -1.0
                tg.entry_ts = pd.Timestamp("2024-01-01")
                tg.legs = [Leg(ts=pd.Timestamp("2024-01-01"), qty=-1.0, price=5.0, fees=0.0, proceeds=500.0)]

                mock_group.return_value = ([], [tg])

                manual_data = [{
                    "date": "2024-01-01 10:00:00",
                    "symbol": "SPY",
                    "action": "Sell to Open",
                    "qty": 1,
                    "price": 5.0,
                    "fees": 1.0,
                    "expiry": "2024-12-20",
                    "strike": 400.0,
                    "right": "P"
                }]

                with patch('option_auditor.main_analyzer.build_strategies') as mock_strat:
                    mock_strat.return_value = []

                    result = analyze_csv(manual_data=manual_data)

                    self.assertNotEqual(result['verdict'], "Red Flag: High Open Risk")
                    self.assertIsNone(result.get('verdict_details'))

if __name__ == '__main__':
    unittest.main()
