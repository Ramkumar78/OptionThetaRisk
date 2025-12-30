import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.master_screener import MasterScreener

class TestMasterScreenerRefinement(unittest.TestCase):

    def setUp(self):
        # Create a dummy MasterScreener instance
        # We patch yf.download in tests anyway
        self.screener = MasterScreener(["AAPL"], ["LLOY.L"])

    def create_mock_df(self, length=300, price=100.0, trend="flat", breakout_idx=None):
        """
        Creates a mock dataframe with specific trend and breakout characteristics.
        """
        dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

        # Base price series
        if trend == "flat":
            prices = np.full(length, price)
        elif trend == "uptrend":
            prices = np.linspace(price * 0.5, price, length)

        # Create OHLCV
        df = pd.DataFrame(index=dates)
        df['Close'] = prices
        # Add some noise for High/Low
        df['High'] = df['Close'] * 1.01
        df['Low'] = df['Close'] * 0.99
        df['Open'] = df['Close']
        df['Volume'] = 5_000_000 # Higher Default volume to pass Liquidity Check

        # Inject Breakout
        if breakout_idx is not None:
            # Create a "base" before breakout
            # Breakout happens at -breakout_idx from end

            break_loc = length - breakout_idx

            # Make previous 20 days (before break_loc) have a high ceiling
            pivot_high = price * 0.95

            # Adjust historical prices to be below pivot
            # From break_loc - 30 to break_loc
            start_base = max(0, break_loc - 30)
            df.iloc[start_base:break_loc, df.columns.get_loc('High')] = pivot_high
            df.iloc[start_base:break_loc, df.columns.get_loc('Close')] = pivot_high * 0.98

            # On breakout day
            df.iloc[break_loc, df.columns.get_loc('Close')] = pivot_high * 1.02 # Breakout!
            df.iloc[break_loc, df.columns.get_loc('High')] = pivot_high * 1.03

            # Volume spike on breakout
            df.iloc[break_loc, df.columns.get_loc('Volume')] = 15_000_000 # Big spike

        return df

    def test_find_breakout_fresh(self):
        """Test detection of a fresh breakout (e.g. 1 days ago)"""
        # Create data where breakout was 1 day ago
        df = self.create_mock_df(length=300, price=100, trend="uptrend", breakout_idx=2)

        # Manually verify find_breakout
        date_str, days_since = self.screener._find_breakout(df, lookback_days=10)

        self.assertIsNotNone(date_str)
        # breakout_idx=2 -> 1 day ago
        self.assertEqual(days_since, 1)

    def test_find_breakout_stale(self):
        """Test detection of a stale breakout (e.g. 20 days ago)"""
        # Create data where breakout was 20 days ago
        df = self.create_mock_df(length=300, price=100, trend="uptrend", breakout_idx=20)

        # Lookback is 10 days in _process_stock logic, but the function takes an arg.
        # If we look back 15 days, we shouldn't find it if it was 20 days ago.
        date_str, days_since = self.screener._find_breakout(df, lookback_days=15)

        # Should return None because it's outside the window
        self.assertIsNone(date_str)

    def test_find_breakout_none(self):
        """Test no breakout in consolidation"""
        df = self.create_mock_df(length=300, price=100, trend="flat")
        # Ensure highs are consistent so no breakout
        df['High'] = 100.0
        df['Close'] = 99.0

        date_str, days_since = self.screener._find_breakout(df, lookback_days=15)
        self.assertIsNone(date_str)

    def test_process_stock_logic(self):
        """Test full processing logic including volume and staleness filters"""
        # Mock Ticker and DF
        ticker = "TEST"

        # Case 1: Perfect Fresh Breakout
        df = self.create_mock_df(length=300, price=150, trend="uptrend", breakout_idx=3)

        # Ensure 'Current Volume' is higher than average to pass `vol_spike` check
        # create_mock_df default vol is 5M. Breakout vol is 15M (2 days ago).
        # Avg vol ~ (19*5 + 15)/20 = 5.5M.
        # Current vol (today) is 5M.
        # 5M > 5.5M is False.
        # We need to boost current volume to pass the check.
        df.iloc[-1, df.columns.get_loc('Volume')] = 10_000_000

        # Ensure price is high enough to pass Liquidity Check if applicable
        # Default price=150 is > 0.
        # Liquidity Check uses AVG VOL.
        # 5M > 2M. Should pass.

        # Ensure Trend Alignment
        # curr > 50 > 150 > 200
        # SMA50 ~ 143. SMA150 ~ 131. SMA200 ~ 125.
        # 150 > 143... Should be True.

        # Ensure extension < 20%
        # (150 - 143)/143 ~ 4%. OK.

        res = self.screener._process_stock(ticker, df)

        self.assertIsNotNone(res)
        self.assertEqual(res['Type'], "ISA_BUY")
        self.assertIn("Breakout (2d ago)", res['Setup'])

    def test_volume_filter(self):
        """Test that low volume on breakout fails the signal"""
        # Breakout 3 days ago
        df = self.create_mock_df(length=300, price=150, trend="uptrend", breakout_idx=3)

        # Ensure current volume is LOW
        # Avg ~ 5.5M.
        # Current vol = 1M.
        df.iloc[-1, df.columns.get_loc('Volume')] = 1_000_000

        res = self.screener._process_stock("TEST", df)

        # Should return None because vol_spike is false
        self.assertIsNone(res)

    def test_staleness_filter(self):
        """Test that old breakout (15 days ago) is filtered out even if trend is good"""
        # Breakout 15 days ago
        df = self.create_mock_df(length=300, price=150, trend="uptrend", breakout_idx=15)

        # Logic: days_ago <= 12
        res = self.screener._process_stock("TEST", df)

        # Should be None (or OPT_SELL if conditions met)
        self.assertIsNone(res)

    @patch('option_auditor.master_screener.yf.download')
    def test_run_bearish_regime(self, mock_download):
        """Test that bearish regime returns WARNING"""
        # Mock Market Data to be Bearish
        # SPY < SMA200 and VIX > 25

        mock_data = pd.DataFrame({
            ('Close', 'SPY'): [400] * 300,
            ('Close', '^VIX'): [30] * 300 # High VIX
        })
        # Set recent SPY low to drag MA down? No, we want SPY < MA.
        # So SPY was 500, now 400.
        prices = np.linspace(500, 400, 300)
        mock_data[('Close', 'SPY')] = prices
        mock_data.columns = pd.MultiIndex.from_tuples([('Close', 'SPY'), ('Close', '^VIX')])

        mock_download.return_value = mock_data

        results = self.screener.run()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Type'], "WARNING")
        self.assertEqual(results[0]['Regime'], "RED")

if __name__ == '__main__':
    unittest.main()
