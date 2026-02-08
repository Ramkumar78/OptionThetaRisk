import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import os
from option_auditor.common.data_utils import optimize_dataframe, save_atomic, prepare_data_for_ticker

class TestDataUtilsOptimization(unittest.TestCase):

    def test_optimize_dataframe(self):
        """Verify optimize_dataframe downcasts float64 to float32."""
        df = pd.DataFrame({
            'float_col': [1.0, 2.0, 3.0],
            'int_col': [1, 2, 3],
            'str_col': ['a', 'b', 'c']
        })

        # Verify initial types
        self.assertEqual(df['float_col'].dtype, 'float64')
        self.assertEqual(df['int_col'].dtype, 'int64')

        original_str_dtype = df['str_col'].dtype

        optimized_df = optimize_dataframe(df)

        # Verify optimized types
        self.assertEqual(optimized_df['float_col'].dtype, 'float32')
        self.assertEqual(optimized_df['int_col'].dtype, 'int64')
        self.assertEqual(optimized_df['str_col'].dtype, original_str_dtype)

        # Verify values preserved
        pd.testing.assert_series_equal(optimized_df['float_col'].astype('float64'), df['float_col'], check_dtype=False)

    @patch('option_auditor.common.data_utils.optimize_dataframe')
    @patch('pandas.DataFrame.to_parquet')
    @patch('os.replace')
    def test_save_atomic_success(self, mock_replace, mock_to_parquet, mock_optimize):
        """Test save_atomic correctly handles .tmp file and calls optimize."""
        df = pd.DataFrame({'col1': [1, 2]})
        mock_optimize.return_value = df
        file_path = "test_path.parquet"
        tmp_path = "test_path.parquet.tmp"

        save_atomic(df, file_path)

        mock_optimize.assert_called_once_with(df)
        mock_to_parquet.assert_called_once_with(tmp_path)
        mock_replace.assert_called_once_with(tmp_path, file_path)

    @patch('option_auditor.common.data_utils.optimize_dataframe')
    @patch('pandas.DataFrame.to_parquet')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_save_atomic_failure_cleanup(self, mock_exists, mock_remove, mock_to_parquet, mock_optimize):
        """Test save_atomic cleans up tmp file on failure."""
        df = pd.DataFrame({'col1': [1, 2]})
        mock_optimize.return_value = df
        mock_to_parquet.side_effect = IOError("Write failed")
        mock_exists.return_value = True # Tmp file exists
        file_path = "test_path.parquet"
        tmp_path = "test_path.parquet.tmp"

        # Should catch exception and cleanup
        save_atomic(df, file_path)

        mock_to_parquet.assert_called_once_with(tmp_path)
        mock_remove.assert_called_once_with(tmp_path)

    def test_prepare_data_multiindex_level_0(self):
        """Test prepare_data_for_ticker extracts correct data from MultiIndex level 0 (Ticker first)."""
        # Create MultiIndex: (Ticker, Attribute)
        idx = pd.MultiIndex.from_product([['AAPL'], ['Open', 'Close']], names=['Ticker', 'Attribute'])
        df = pd.DataFrame([[100, 101], [102, 103]], columns=idx, index=pd.date_range('2024-01-01', periods=2))

        result = prepare_data_for_ticker('AAPL', df, None, '1y', '1d', None, False)

        self.assertIsNotNone(result)
        self.assertListEqual(list(result.columns), ['Open', 'Close'])
        self.assertEqual(result['Open'].iloc[0], 100)

    def test_prepare_data_multiindex_level_1(self):
        """Test prepare_data_for_ticker extracts correct data from MultiIndex level 1 (Attribute first)."""
        # Create MultiIndex: (Attribute, Ticker) - less common but possible depending on group_by
        idx = pd.MultiIndex.from_product([['Open', 'Close'], ['AAPL']], names=['Attribute', 'Ticker'])
        df = pd.DataFrame([[100, 101], [102, 103]], columns=idx, index=pd.date_range('2024-01-01', periods=2))

        result = prepare_data_for_ticker('AAPL', df, None, '1y', '1d', None, False)

        self.assertIsNotNone(result)
        # Note: If level 1 is ticker, extracting xs(ticker, level=1) drops that level, leaving level 0 (Attribute) as columns
        self.assertListEqual(sorted(list(result.columns)), ['Close', 'Open'])
        self.assertEqual(result['Open'].iloc[0], 100)

    def test_prepare_data_resampling(self):
        """Test prepare_data_for_ticker handles resampling correctly."""
        dates = pd.date_range('2024-01-01', periods=14, freq='D')
        df = pd.DataFrame({
            'Open': range(14),
            'High': range(14),
            'Low': range(14),
            'Close': range(14),
            'Volume': [100]*14
        }, index=dates)

        # Resample to Weekly 'W'
        result = prepare_data_for_ticker('TEST', df, None, '1y', '1d', 'W', False)

        self.assertIsNotNone(result)
        # 14 days should result in approx 2 weeks (depending on start day)
        self.assertTrue(len(result) <= 3)
        # Verify aggregation (High is max, Low is min)
        # The first week likely contains 0-6
        # Resampling is tricky with dates, but just checking it returned a resampled frame is key.
        self.assertNotEqual(len(result), 14)

    @patch('option_auditor.common.data_utils.fetch_data_with_retry')
    def test_prepare_data_fallback_fetch(self, mock_fetch):
        """Test prepare_data_for_ticker falls back to fetch if source is None/Empty."""
        mock_df = pd.DataFrame({'Close': [100]}, index=pd.date_range('2024-01-01', periods=1))
        mock_fetch.return_value = mock_df

        result = prepare_data_for_ticker('AAPL', None, None, '1y', '1d', None, False)

        mock_fetch.assert_called_once()
        self.assertIsNotNone(result)
        self.assertFalse(result.empty)

if __name__ == '__main__':
    unittest.main()
