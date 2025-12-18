import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import pandas as pd
import asyncio
from option_auditor.common.data_utils import fetch_data_with_retry, fetch_batch_data_safe, async_fetch_data_with_retry

class TestDataUtils(unittest.TestCase):

    @patch('option_auditor.common.data_utils.yf.download')
    @patch('option_auditor.common.data_utils.time.sleep')
    def test_fetch_data_with_retry_success(self, mock_sleep, mock_download):
        # Setup
        # Note: fetch_data_with_retry uses yf.download, NOT yf.Ticker if we check the code.
        # Wait, the code: df = data_api_breaker.call(yf.download, ticker, ...)

        mock_download.return_value = pd.DataFrame({'Close': [100.0]})

        # Execute
        df = fetch_data_with_retry("AAPL")

        # Verify
        self.assertFalse(df.empty)
        # Checking values on single element DataFrame works simply
        self.assertEqual(float(df['Close'].iloc[0]), 100.0)
        mock_sleep.assert_not_called()

    @patch('option_auditor.common.data_utils.yf.download')
    @patch('option_auditor.common.data_utils.time.sleep')
    def test_fetch_data_with_retry_failure(self, mock_sleep, mock_download):
        # Setup failure
        mock_download.side_effect = Exception("API Error")

        # Execute
        df = fetch_data_with_retry("AAPL", retries=2)

        # Verify
        self.assertTrue(df.empty)
        # Retries loop runs 'retries' times.
        # attempt 0 -> fail -> sleep (if 0 < 1)
        # attempt 1 -> fail -> no sleep (if 1 < 1 False)
        # So sleeps 1 time for 2 retries.
        self.assertEqual(mock_sleep.call_count, 1)

    @patch('option_auditor.common.data_utils.yf.download')
    @patch('option_auditor.common.data_utils.time.sleep')
    def test_fetch_batch_data_safe(self, mock_sleep, mock_download):
        # Setup
        tickers = ["AAPL", "MSFT"]
        mock_df = pd.DataFrame({
            ('Close', 'AAPL'): [150.0],
            ('Close', 'MSFT'): [300.0]
        })
        mock_download.return_value = mock_df

        # Execute
        df = fetch_batch_data_safe(tickers)

        # Verify
        self.assertFalse(df.empty)
        # Should call download once for chunk
        mock_download.assert_called_once()

    @patch('option_auditor.common.data_utils.yf.download')
    @patch('option_auditor.common.data_utils.time.sleep')
    def test_fetch_batch_data_safe_empty(self, mock_sleep, mock_download):
        mock_download.return_value = pd.DataFrame()
        df = fetch_batch_data_safe(["INVALID"])
        self.assertTrue(df.empty)

def test_async_fetch_success():
    # Helper to run async test without pytest-asyncio plugin if needed
    async def run_test():
        with patch('option_auditor.common.data_utils.yf.download') as mock_download, \
             patch('option_auditor.common.data_utils.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:

            mock_df = pd.DataFrame({'Close': [100.0]})
            mock_to_thread.return_value = mock_df

            df = await async_fetch_data_with_retry("AAPL")

            assert not df.empty
            assert float(df['Close'].iloc[0]) == 100.0

    asyncio.run(run_test())
