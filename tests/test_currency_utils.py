import pytest
import pandas as pd
import unittest
from unittest.mock import patch, MagicMock
from option_auditor.common.data_utils import (
    get_currency_symbol,
    fetch_exchange_rate,
    convert_currency,
    FALLBACK_RATES
)

class TestCurrencyUtils(unittest.TestCase):

    def test_get_currency_symbol_all_suffixes(self):
        """Test currency symbol mapping for all supported suffixes."""
        # .L -> GBP
        self.assertEqual(get_currency_symbol("VOD.L"), "GBP")
        self.assertEqual(get_currency_symbol("BARC.L"), "GBP")

        # .NS / .BO -> INR
        self.assertEqual(get_currency_symbol("RELIANCE.NS"), "INR")
        self.assertEqual(get_currency_symbol("TCS.BO"), "INR")

        # .AS, .DE, .PA, .MC, .MI, .HE -> EUR
        self.assertEqual(get_currency_symbol("ASML.AS"), "EUR")
        self.assertEqual(get_currency_symbol("SAP.DE"), "EUR")
        self.assertEqual(get_currency_symbol("AIR.PA"), "EUR")
        self.assertEqual(get_currency_symbol("LVMH.MC"), "EUR")
        self.assertEqual(get_currency_symbol("RACE.MI"), "EUR")
        self.assertEqual(get_currency_symbol("NOKIA.HE"), "EUR")

        # Default -> USD
        self.assertEqual(get_currency_symbol("AAPL"), "USD")
        self.assertEqual(get_currency_symbol("GOOG"), "USD")
        self.assertEqual(get_currency_symbol("INVALID.XYZ"), "USD")
        self.assertEqual(get_currency_symbol(""), "USD")
        self.assertEqual(get_currency_symbol(None), "USD")

    @patch("option_auditor.common.data_utils.yf.Ticker")
    def test_fetch_exchange_rate_live_success(self, mock_ticker):
        """Test fetching live exchange rate successfully."""
        mock_instance = MagicMock()
        mock_ticker.return_value = mock_instance

        # Mock successful history
        mock_hist = pd.DataFrame({"Close": [1.30]}, index=[pd.Timestamp("2024-01-01")])
        mock_instance.history.return_value = mock_hist

        rate = fetch_exchange_rate("GBP", "USD")
        self.assertEqual(rate, 1.30)

        # Verify ticker construction for GBP/USD
        mock_ticker.assert_called_with("GBPUSD=X")

    @patch("option_auditor.common.data_utils.yf.Ticker")
    def test_fetch_exchange_rate_fallback(self, mock_ticker):
        """Test fallback to FALLBACK_RATES when live fetch fails."""
        mock_instance = MagicMock()
        mock_ticker.return_value = mock_instance

        # Mock failure (empty dataframe)
        mock_instance.history.return_value = pd.DataFrame()

        # GBP/USD is in FALLBACK_RATES
        expected_rate = FALLBACK_RATES[("GBP", "USD")]
        rate = fetch_exchange_rate("GBP", "USD")
        self.assertEqual(rate, expected_rate)

    @patch("option_auditor.common.data_utils.yf.Ticker")
    def test_fetch_exchange_rate_fallback_inverse(self, mock_ticker):
        """Test inverse fallback calculation."""
        mock_instance = MagicMock()
        mock_ticker.return_value = mock_instance

        # Mock failure
        mock_instance.history.return_value = pd.DataFrame()

        # Check USD to GBP which uses 1/rate logic or direct lookup if present
        # FALLBACK_RATES currently has ("USD", "GBP"): 1/1.27
        expected_rate = FALLBACK_RATES[("USD", "GBP")]
        rate = fetch_exchange_rate("USD", "GBP")
        self.assertEqual(rate, expected_rate)

    @patch("option_auditor.common.data_utils.fetch_exchange_rate")
    def test_convert_currency(self, mock_fetch):
        """Test convert_currency wrapper function."""
        mock_fetch.return_value = 1.2

        amount = 100.0
        expected_result = amount * 1.2

        result = convert_currency(amount, "EUR", "USD")

        self.assertEqual(result, expected_result)
        mock_fetch.assert_called_with("EUR", "USD")

    def test_fetch_exchange_rate_same_currency(self):
        """Test rate is 1.0 when currencies are the same."""
        self.assertEqual(fetch_exchange_rate("USD", "USD"), 1.0)
        self.assertEqual(fetch_exchange_rate("GBP", "GBP"), 1.0)
        self.assertEqual(fetch_exchange_rate("eur", "EUR"), 1.0)
