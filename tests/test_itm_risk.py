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

        with patch('yfinance.Ticker') as mock_ticker:
            mock_inst = MagicMock()
            mock_inst.info = {'currentPrice': 390.0}
            mock_inst.fast_info = {'last_price': 390.0}
            mock_ticker.return_value = mock_inst

            # Since we are using Tickers object (plural)
            with patch('yfinance.Tickers') as mock_tickers:
                mock_tickers_inst = MagicMock()
                mock_tickers_inst.tickers = {'SPY': mock_inst}
                mock_tickers.return_value = mock_tickers_inst

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
                        print(f"DEBUG RESULT VERDICT: {result.get('verdict')}")

                        if "error" in result:
                            self.fail(f"Analysis failed with error: {result['error']}")

                        self.assertEqual(result['verdict'], "Red Flag: High Open Risk")
                        self.assertEqual(result['verdict_color'], "red")

                        # Verify open positions have risk alert
                        open_pos = result['open_positions']
                        self.assertTrue(any('risk_alert' in op for op in open_pos))
                        self.assertEqual(open_pos[0]['risk_alert'], "ITM Risk")

    def test_live_itm_risk_no_risk(self):
        # Setup: One open Short Put that is OTM
        # Symbol: SPY, Strike: 400, Type: Put, Qty: -1 (Short)
        # Current Price: 410 (OTM for Put)

        with patch('yfinance.Ticker') as mock_ticker:
            mock_inst = MagicMock()
            mock_inst.info = {'currentPrice': 410.0}
            mock_inst.fast_info = {'last_price': 410.0}
            mock_ticker.return_value = mock_inst

            with patch('yfinance.Tickers') as mock_tickers:
                mock_tickers_inst = MagicMock()
                mock_tickers_inst.tickers = {'SPY': mock_inst}
                mock_tickers.return_value = mock_tickers_inst

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
                        print(f"DEBUG RESULT VERDICT: {result.get('verdict')}")

                        self.assertNotEqual(result['verdict'], "Red Flag: High Open Risk")
                        # Should be Insufficient Data because no strategies
                        self.assertIn("Insufficient Data", result['verdict'])

if __name__ == '__main__':
    unittest.main()
