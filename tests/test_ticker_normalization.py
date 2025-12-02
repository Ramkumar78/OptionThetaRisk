import pandas as pd
from option_auditor.main_analyzer import analyze_csv, _normalize_ticker
from option_auditor.models import TradeGroup, Leg
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

class TestTickerNormalizationAndDataWarning(unittest.TestCase):
    def test_normalize_ticker(self):
        # Test common indices
        self.assertEqual(_normalize_ticker("SPX"), "^SPX")
        self.assertEqual(_normalize_ticker("VIX"), "^VIX")
        self.assertEqual(_normalize_ticker("DJX"), "^DJI")
        self.assertEqual(_normalize_ticker("NDX"), "^NDX")
        self.assertEqual(_normalize_ticker("RUT"), "^RUT")

        # Test futures
        self.assertEqual(_normalize_ticker("/ES"), "ES=F")
        self.assertEqual(_normalize_ticker("/CL"), "CL=F")

        # Test class shares
        self.assertEqual(_normalize_ticker("BRK/B"), "BRK-B")

        # Test standard
        self.assertEqual(_normalize_ticker("AAPL"), "AAPL")
        self.assertEqual(_normalize_ticker("spy"), "SPY")

    def test_missing_data_warning(self):
        # Setup: Open position on UNKNOWN symbol
        # We expect yfinance to return no data for this.

        with patch('option_auditor.main_analyzer._fetch_live_prices') as mock_fetch:
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
        # Mock _fetch_live_prices to expect ^SPX and return a price

        with patch('option_auditor.main_analyzer._fetch_live_prices') as mock_fetch:
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

                # Mock strategies to avoid min trades check overriding our check?
                # Actually, verdict logic priorities:
                # 1. High Open Risk
                # 2. Insufficient Data (if trades < MIN)
                # 3. ...
                # Wait, "Insufficient Data" overrides "Green Flag" but "High Open Risk" overrides everything.
                # "Amber: Data Unavailable" should probably override "Insufficient Data" or be high priority?
                # User instructions:
                # if itm_risk_flag: ...
                # elif missing_data_warning: ...

                # So missing data warning is checked if NO ITM Risk found.
                # But "Insufficient Data" check comes BEFORE ITM Risk check in the current code (lines 538-540 in original).
                # The user instructions snippet shows it after ITM Risk logic but inside the override block?
                # The snippet provided by user:
                # # OVERRIDE: ITM Risk Detection
                # verdict_details = None
                # if itm_risk_flag: ...
                # elif missing_data_warning: ...

                # So if I implement it as requested, it will override "Insufficient Data" verdict ONLY IF I place it after the "Insufficient Data" check.

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
                    # So it should fall through to "Insufficient Data" because we have 0 closed strategies.

                    # Wait, if we have insufficient data, does that take precedence over "Amber: Data Unavailable"?
                    # The user snippet implies "Data Integrity Warning" is part of the OVERRIDE block.
                    # The current code has "Insufficient Data" check (lines 538-540).
                    # Then "OVERRIDE: ITM Risk Detection" (lines 542...).
                    # So if I add the elif missing_data_warning there, it will override "Insufficient Data".

                    # However, in this specific test case, data IS available. So we expect "Insufficient Data" or "Green Flag" (if we had trades).
                    self.assertTrue("Insufficient Data" in result['verdict'])

                    # Verify _fetch_live_prices was called with correct normalized symbol
                    mock_fetch.assert_called_with(['^SPX'])
