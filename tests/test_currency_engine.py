import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from option_auditor.common.data_utils import (
    get_currency_symbol,
    fetch_exchange_rate,
    convert_currency,
    FALLBACK_RATES
)

class TestCurrencyEngine(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. get_currency_symbol Tests
    # -------------------------------------------------------------------------

    def test_get_currency_symbol_gbp(self):
        """Test .L suffix returns GBP."""
        self.assertEqual(get_currency_symbol("LLOY.L"), "GBP")
        self.assertEqual(get_currency_symbol("VOD.L"), "GBP")

    def test_get_currency_symbol_inr(self):
        """Test .NS and .BO suffixes return INR."""
        self.assertEqual(get_currency_symbol("RELIANCE.NS"), "INR")
        self.assertEqual(get_currency_symbol("TCS.BO"), "INR")

    def test_get_currency_symbol_eur(self):
        """Test EUR suffixes (.AS, .DE, .PA, .MC, .MI, .HE)."""
        suffixes = ['.AS', '.DE', '.PA', '.MC', '.MI', '.HE']
        for suffix in suffixes:
            ticker = f"TEST{suffix}"
            self.assertEqual(get_currency_symbol(ticker), "EUR", f"Failed for suffix {suffix}")

    def test_get_currency_symbol_default(self):
        """Test default returns USD for other inputs."""
        self.assertEqual(get_currency_symbol("AAPL"), "USD")
        self.assertEqual(get_currency_symbol(""), "USD")
        self.assertEqual(get_currency_symbol(None), "USD")
        self.assertEqual(get_currency_symbol("NONEXISTENT.XYZ"), "USD")

    # -------------------------------------------------------------------------
    # 2. fetch_exchange_rate Tests
    # -------------------------------------------------------------------------

    @patch('option_auditor.common.data_utils.yf.Ticker')
    def test_fetch_exchange_rate_success_usdinr(self, mock_ticker_cls):
        """Test successful live fetch for USD->INR uses correct ticker and returns rate."""
        # Mock Ticker instance
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        # Mock history DataFrame with specific close price
        # Using 83.50 for USDINR example
        df = pd.DataFrame({'Close': [83.50]}, index=[pd.Timestamp('2024-01-01')])
        mock_ticker.history.return_value = df

        rate = fetch_exchange_rate('USD', 'INR')

        # Verify call uses the special case override if present in code
        mock_ticker_cls.assert_called_with("USDINR=X")
        self.assertEqual(rate, 83.50)

    @patch('option_auditor.common.data_utils.yf.Ticker')
    def test_fetch_exchange_rate_success_gbpusd(self, mock_ticker_cls):
        """Test successful live fetch for GBP->USD."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        df = pd.DataFrame({'Close': [1.27]}, index=[pd.Timestamp('2024-01-01')])
        mock_ticker.history.return_value = df

        rate = fetch_exchange_rate('GBP', 'USD')

        mock_ticker_cls.assert_called_with("GBPUSD=X")
        self.assertEqual(rate, 1.27)

    @patch('option_auditor.common.data_utils.yf.Ticker')
    def test_fetch_exchange_rate_empty_history(self, mock_ticker_cls):
        """Test empty history triggers fallback to FALLBACK_RATES."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        mock_ticker.history.return_value = pd.DataFrame() # Empty

        # USD -> INR fallback is 83.50 in code
        rate = fetch_exchange_rate('USD', 'INR')
        self.assertEqual(rate, 83.50)

    @patch('option_auditor.common.data_utils.yf.Ticker')
    def test_fetch_exchange_rate_exception(self, mock_ticker_cls):
        """Test exception triggers fallback."""
        mock_ticker_cls.side_effect = Exception("Connection Error")

        rate = fetch_exchange_rate('GBP', 'USD')
        # GBP -> USD fallback is 1.27
        self.assertEqual(rate, 1.27)

    @patch('option_auditor.common.data_utils.yf.Ticker')
    def test_fetch_exchange_rate_inverse_fallback(self, mock_ticker_cls):
        """Test inverse fallback logic specifically (A->B not found, but B->A found)."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        mock_ticker.history.return_value = pd.DataFrame()

        # Define a custom fallback map where (B, A) exists but (A, B) does not.
        custom_fallbacks = {("CURR_B", "CURR_A"): 2.0}

        with patch.dict('option_auditor.common.data_utils.FALLBACK_RATES', custom_fallbacks, clear=True):
            # Request A -> B. Should find B -> A = 2.0, so result = 1.0 / 2.0 = 0.5
            rate = fetch_exchange_rate('CURR_A', 'CURR_B')
            self.assertEqual(rate, 0.5)

    def test_fetch_exchange_rate_same_currency(self):
        """Test same currency returns 1.0 immediately."""
        self.assertEqual(fetch_exchange_rate('USD', 'USD'), 1.0)
        self.assertEqual(fetch_exchange_rate('GBP', 'GBP'), 1.0)

    @patch('option_auditor.common.data_utils.yf.Ticker')
    def test_fetch_exchange_rate_total_failure(self, mock_ticker_cls):
        """Test total failure (no live data, no fallback) returns 1.0."""
        mock_ticker_cls.side_effect = Exception("Fail")

        # Use a pair not in FALLBACK_RATES at all
        with patch.dict('option_auditor.common.data_utils.FALLBACK_RATES', {}, clear=True):
            rate = fetch_exchange_rate('XXX', 'YYY')
            self.assertEqual(rate, 1.0)

    # -------------------------------------------------------------------------
    # 3. convert_currency Tests
    # -------------------------------------------------------------------------

    @patch('option_auditor.common.data_utils.fetch_exchange_rate')
    def test_convert_currency(self, mock_fetch):
        """Test currency conversion math using mocked rate."""
        mock_fetch.return_value = 1.5
        amount = 100
        result = convert_currency(amount, 'AAA', 'BBB')
        self.assertEqual(result, 150.0)
        mock_fetch.assert_called_with('AAA', 'BBB')

if __name__ == '__main__':
    unittest.main()
