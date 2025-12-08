import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import _get_currency_symbol, _screen_tickers, screen_turtle_setups

class TestCurrencyDisplay(unittest.TestCase):
    def test_get_currency_symbol(self):
        self.assertEqual(_get_currency_symbol('AAPL'), '$')
        self.assertEqual(_get_currency_symbol('AZN.L'), '£')
        self.assertEqual(_get_currency_symbol('MC.PA'), '€')
        self.assertEqual(_get_currency_symbol('RELIANCE.NS'), '₹')

    @patch('option_auditor.screener.yf.download')
    @patch('option_auditor.screener.yf.Ticker')
    def test_uk_price_conversion(self, mock_ticker, mock_download):
        # Mock data for AZN.L (in GBp)
        dates = pd.date_range(start='2023-01-01', periods=60)
        mock_data = pd.DataFrame({
            'Open': [10000.0] * 60,
            'High': [10100.0] * 60,
            'Low': [9900.0] * 60,
            'Close': [10000.0] * 60,
            'Volume': [1000] * 60
        }, index=dates)

        # Mock data for AAPL
        mock_data_us = pd.DataFrame({
            'Open': [150.0] * 60,
            'High': [155.0] * 60,
            'Low': [145.0] * 60,
            'Close': [150.0] * 60,
            'Volume': [1000] * 60
        }, index=dates)

        # Configure side_effect for multiple calls
        # 1. Batch download for AZN.L -> Raise (force sequential)
        # 2. Sequential download for AZN.L -> Return mock_data
        # 3. Batch download for AAPL -> Raise
        # 4. Sequential download for AAPL -> Return mock_data_us
        mock_download.side_effect = [Exception("Batch fail"), mock_data, Exception("Batch fail"), mock_data_us]

        # Mock Ticker info
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {'trailingPE': 15.0}
        mock_ticker.return_value = mock_ticker_instance

        # Test AZN.L
        results = _screen_tickers(['AZN.L'], 30.0, 70.0, '1d')

        self.assertTrue(len(results) > 0)
        res = results[0]

        # Check conversion: 10000 GBp -> 100.00 GBP
        self.assertEqual(res['price'], 100.0)
        self.assertEqual(res['currency_symbol'], '£')

        # Test AAPL
        results_us = _screen_tickers(['AAPL'], 30.0, 70.0, '1d')
        self.assertTrue(len(results_us) > 0)
        res_us = results_us[0]
        self.assertEqual(res_us['price'], 150.0)
        self.assertEqual(res_us['currency_symbol'], '$')

    @patch('option_auditor.screener.yf.download')
    def test_turtle_screener_currency(self, mock_download):
        # Mock data for Turtle
        dates = pd.date_range(start='2023-01-01', periods=30)
        mock_data = pd.DataFrame({
            'Open': [10000.0] * 30,
            'High': [10100.0] * 30,
            'Low': [9900.0] * 30,
            'Close': [10200.0] * 30,
            'Volume': [1000] * 30
        }, index=dates)

        # Turtle screener does batch download then _prepare_data_for_ticker
        # _prepare_data_for_ticker handles both.
        # Let's make batch fail to force simple path in _prepare_data_for_ticker if it uses it,
        # but actually screen_turtle_setups does batch download itself.
        # It calls yf.download(ticker_list, ...)

        # If we return a simple DF, _prepare_data_for_ticker might fail if it expects MultiIndex for batch
        # screen_turtle_setups logic:
        # data = yf.download(..., group_by='ticker'?? No, it doesn't specify group_by in screen_turtle_setups defaults which is 'column' usually for multiple? No wait.
        # Let's check screen_turtle_setups implementation.
        # It calls yf.download(ticker_list, ...). If len(ticker_list) > 1, yfinance returns MultiIndex.
        # If len(ticker_list) == 1, it returns DataFrame.

        # Here we pass ['AZN.L'], so it returns DataFrame.
        # _prepare_data_for_ticker handles single DF.

        mock_download.return_value = mock_data

        results = screen_turtle_setups(['AZN.L'], '1d')

        self.assertTrue(len(results) > 0)
        res = results[0]

        # Should be converted to GBP
        self.assertEqual(res['price'], 102.0)
        self.assertEqual(res['currency_symbol'], '£')

if __name__ == '__main__':
    unittest.main()
