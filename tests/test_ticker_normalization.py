import pandas as pd
from option_auditor.main_analyzer import analyze_csv
from option_auditor.common.price_utils import normalize_ticker
from option_auditor.models import TradeGroup, Leg
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

class TestTickerNormalizationAndDataWarning(unittest.TestCase):
    def test_normalize_ticker(self):
        # Test common indices
        self.assertEqual(normalize_ticker("SPX"), "^SPX")
        self.assertEqual(normalize_ticker("VIX"), "^VIX")
        self.assertEqual(normalize_ticker("DJX"), "^DJI")
        self.assertEqual(normalize_ticker("NDX"), "^NDX")
        self.assertEqual(normalize_ticker("RUT"), "^RUT")

        # Test futures
        self.assertEqual(normalize_ticker("/ES"), "ES=F")
        self.assertEqual(normalize_ticker("/CL"), "CL=F")

        # Test class shares
        self.assertEqual(normalize_ticker("BRK/B"), "BRK-B")

        # Test standard
        self.assertEqual(normalize_ticker("AAPL"), "AAPL")
        self.assertEqual(normalize_ticker("spy"), "SPY")

    def test_missing_data_warning(self):
        # Setup: Open position on UNKNOWN symbol
        # We expect yfinance to return no data for this.

        with patch('option_auditor.main_analyzer.fetch_live_prices') as mock_fetch:
            mock_fetch.return_value = {} # Return empty map, simulating failure

            with patch('option_auditor.main_analyzer._group_contracts_with_open') as mock_group:
                tg = TradeGroup(
                    contract_id="999",
                    symbol="UNKNOWN",
                    expiry=pd.Timestamp("2024-12-20"),
                    strike=100.0,
                    right="P"
                )
                tg.qty_net = -1.0
                tg.entry_ts = pd.Timestamp("2024-01-01")
                tg.legs = [Leg(ts=pd.Timestamp("2024-01-01"), qty=-1.0, price=5.0, fees=0.0, proceeds=500.0)]

                mock_group.return_value = ([], [tg])

                manual_data = [{
                    "date": "2024-01-01 10:00:00",
                    "symbol": "UNKNOWN",
                    "action": "Sell to Open",
                    "qty": 1,
                    "price": 5.0,
                    "fees": 1.0,
                    "expiry": "2024-12-20",
                    "strike": 100.0,
                    "right": "P"
                }]

                with patch('option_auditor.main_analyzer.build_strategies') as mock_strat:
                    mock_strat.return_value = []

                    result = analyze_csv(manual_data=manual_data)

                    self.assertEqual(result['verdict'], "Amber: Data Unavailable")
                    self.assertEqual(result['verdict_color'], "yellow")
                    self.assertIn("Could not fetch live prices for: UNKNOWN", result.get('verdict_details', ''))

    def test_ticker_normalization_flow(self):
        # Setup: Open position on SPX (needs mapping to ^SPX)
        # Mock fetch_live_prices to expect ^SPX and return a price

        with patch('option_auditor.main_analyzer.fetch_live_prices') as mock_fetch:
            # The mock should receive ['^SPX']
            mock_fetch.return_value = {'^SPX': 4500.0}

            with patch('option_auditor.main_analyzer._group_contracts_with_open') as mock_group:
                tg = TradeGroup(
                    contract_id="888",
                    symbol="SPX",
                    expiry=pd.Timestamp("2024-12-20"),
                    strike=4000.0,
                    right="P"
                )
                tg.qty_net = -1.0
                tg.entry_ts = pd.Timestamp("2024-01-01")
                # SPX 4000 Put, Price 4500 -> OTM, Safe.

                mock_group.return_value = ([], [tg])

                manual_data = [{
                    "date": "2024-01-01 10:00:00",
                    "symbol": "SPX",
                    "action": "Sell to Open",
                    "qty": 1,
                    "price": 50.0,
                    "fees": 1.0,
                    "expiry": "2024-12-20",
                    "strike": 4000.0,
                    "right": "P"
                }]

                with patch('option_auditor.main_analyzer.build_strategies') as mock_strat:
                    mock_strat.return_value = [] # 0 trades -> Insufficient Data

                    result = analyze_csv(manual_data=manual_data)

                    # Since we return a price for ^SPX, we expect NO missing data warning.
                    # And since it's OTM, no ITM risk.
                    # It should fall through to "Insufficient Data" because we have 0 closed strategies.
                    self.assertTrue("Insufficient Data" in result['verdict'])

                    # Verify fetch_live_prices was called with correct normalized symbol
                    mock_fetch.assert_called_with(['^SPX'])
