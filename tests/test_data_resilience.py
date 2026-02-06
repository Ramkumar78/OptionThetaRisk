import pytest
from unittest.mock import patch, MagicMock
from option_auditor.backtest_data_loader import BacktestDataLoader
import requests

class TestDataResilience:
    @patch('time.sleep')  # Mock sleep to speed up test
    @patch('option_auditor.backtest_data_loader.yf.download')
    def test_fetch_data_retry_logic(self, mock_download, mock_sleep):
        """
        Simulate 'Connection Timeout' and 'Rate Limit Reached' errors.
        Ensure retries happen 3 times (total 4 attempts) before failing.
        """
        # Define the side effects: Timeout, Rate Limit, Timeout, Rate Limit
        # We want to ensure it retries.
        mock_download.side_effect = [
            requests.exceptions.Timeout("Connection Timeout"),
            requests.exceptions.HTTPError("Rate Limit Reached"),
            requests.exceptions.Timeout("Connection Timeout"),
            requests.exceptions.HTTPError("Rate Limit Reached"), # 4th attempt fails
        ]

        # Force disable CI/Mock mode to ensure we hit the mocked yfinance
        with patch.dict('os.environ', {'CI': 'false', 'USE_MOCK_DATA': 'false'}):
            loader = BacktestDataLoader()
            result = loader.fetch_data("AAPL")

        assert result is None
        assert mock_download.call_count == 4
