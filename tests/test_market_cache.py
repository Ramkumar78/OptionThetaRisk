import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
from option_auditor.common.data_utils import get_cached_market_data, save_atomic, CACHE_DIR

class TestMarketCache(unittest.TestCase):

    def setUp(self):
        # Create a dummy dataframe for testing
        self.dummy_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        self.cache_name = "test_cache"
        self.tickers = ["AAPL"]

    @patch('option_auditor.common.data_utils.optimize_dataframe')
    @patch('pandas.DataFrame.to_parquet')
    @patch('os.replace')
    def test_save_atomic_success(self, mock_replace, mock_to_parquet, mock_optimize):
        """Test save_atomic correctly handles .tmp file and calls optimize."""
        mock_optimize.return_value = self.dummy_df
        file_path = "test_path.parquet"
        tmp_path = "test_path.parquet.tmp"

        save_atomic(self.dummy_df, file_path)

        mock_optimize.assert_called_once_with(self.dummy_df)
        mock_to_parquet.assert_called_once_with(tmp_path)
        mock_replace.assert_called_once_with(tmp_path, file_path)

    @patch('option_auditor.common.data_utils.optimize_dataframe')
    @patch('pandas.DataFrame.to_parquet')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_save_atomic_failure(self, mock_exists, mock_remove, mock_to_parquet, mock_optimize):
        """Test save_atomic cleans up tmp file on failure."""
        mock_optimize.return_value = self.dummy_df
        mock_to_parquet.side_effect = Exception("Write failed")
        mock_exists.return_value = True # Tmp file exists
        file_path = "test_path.parquet"
        tmp_path = "test_path.parquet.tmp"

        save_atomic(self.dummy_df, file_path)

        mock_to_parquet.assert_called_once_with(tmp_path)
        mock_remove.assert_called_once_with(tmp_path)

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('pandas.read_parquet')
    @patch('os.path.getmtime')
    @patch('os.path.exists')
    def test_get_cached_market_data_valid(self, mock_exists, mock_getmtime, mock_read_parquet, mock_fetch):
        """Test retrieving valid cache."""
        mock_exists.return_value = True
        # 1 hour old file
        mock_getmtime.return_value = (datetime.now() - timedelta(hours=1)).timestamp()
        mock_read_parquet.return_value = self.dummy_df

        result = get_cached_market_data(self.tickers, cache_name=self.cache_name)

        mock_read_parquet.assert_called_once()
        mock_fetch.assert_not_called()
        self.assertFalse(result.empty)

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('pandas.read_parquet')
    @patch('os.path.getmtime')
    @patch('os.path.exists')
    def test_get_cached_market_data_stale_but_usable(self, mock_exists, mock_getmtime, mock_read_parquet, mock_fetch):
        """Test retrieving stale but usable cache (between validity and 48h)."""
        mock_exists.return_value = True
        # 25 hours old (validity is 24h for market_scan, 4h for others).
        # Let's use 'market_scan' in name to trigger 24h validity.
        cache_name = "market_scan_test"
        mock_getmtime.return_value = (datetime.now() - timedelta(hours=25)).timestamp()
        mock_read_parquet.return_value = self.dummy_df

        result = get_cached_market_data(self.tickers, cache_name=cache_name)

        mock_read_parquet.assert_called_once()
        mock_fetch.assert_not_called()
        self.assertFalse(result.empty)

    @patch('option_auditor.common.data_utils.save_atomic')
    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('pandas.read_parquet')
    @patch('os.path.getmtime')
    @patch('os.path.exists')
    def test_get_cached_market_data_expired(self, mock_exists, mock_getmtime, mock_read_parquet, mock_fetch, mock_save):
        """Test expired cache triggers refresh."""
        mock_exists.return_value = True
        # 50 hours old (expired for all)
        mock_getmtime.return_value = (datetime.now() - timedelta(hours=50)).timestamp()
        mock_fetch.return_value = self.dummy_df

        result = get_cached_market_data(self.tickers, cache_name=self.cache_name)

        mock_fetch.assert_called_once()
        mock_save.assert_called_once()
        mock_read_parquet.assert_not_called() # Should not read if expired > 48h (logic: age < 48 is stale/usable)

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('pandas.read_parquet')
    @patch('os.path.getmtime')
    @patch('os.path.exists')
    def test_get_cached_market_data_lookup_only_valid(self, mock_exists, mock_getmtime, mock_read_parquet, mock_fetch):
        """Test lookup_only returns data if valid."""
        mock_exists.return_value = True
        mock_getmtime.return_value = (datetime.now() - timedelta(hours=1)).timestamp()
        mock_read_parquet.return_value = self.dummy_df

        result = get_cached_market_data(self.tickers, cache_name=self.cache_name, lookup_only=True)

        mock_read_parquet.assert_called_once()
        mock_fetch.assert_not_called()
        self.assertFalse(result.empty)

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('os.path.getmtime')
    @patch('os.path.exists')
    def test_get_cached_market_data_lookup_only_expired(self, mock_exists, mock_getmtime, mock_fetch):
        """Test lookup_only returns empty if expired."""
        mock_exists.return_value = True
        # 50 hours old
        mock_getmtime.return_value = (datetime.now() - timedelta(hours=50)).timestamp()

        result = get_cached_market_data(self.tickers, cache_name=self.cache_name, lookup_only=True)

        self.assertTrue(result.empty)
        mock_fetch.assert_not_called()

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('os.path.exists')
    def test_get_cached_market_data_lookup_only_missing(self, mock_exists, mock_fetch):
        """Test lookup_only returns empty if cache missing."""
        mock_exists.return_value = False

        result = get_cached_market_data(self.tickers, cache_name=self.cache_name, lookup_only=True)

        self.assertTrue(result.empty)
        mock_fetch.assert_not_called()

    @patch('option_auditor.common.data_utils.save_atomic')
    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('os.path.getmtime')
    @patch('os.path.exists')
    def test_get_cached_market_data_force_refresh(self, mock_exists, mock_getmtime, mock_fetch, mock_save):
        """Test force_refresh ignores valid cache."""
        mock_exists.return_value = True
        mock_getmtime.return_value = (datetime.now() - timedelta(hours=1)).timestamp()
        mock_fetch.return_value = self.dummy_df

        result = get_cached_market_data(self.tickers, cache_name=self.cache_name, force_refresh=True)

        mock_fetch.assert_called_once()
        mock_save.assert_called_once()

if __name__ == '__main__':
    unittest.main()
