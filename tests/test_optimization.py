import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.optimization import PortfolioOptimizer

class TestPortfolioOptimizer(unittest.TestCase):

    @patch('option_auditor.optimization.yf.download')
    def test_fetch_data_and_optimize(self, mock_download):
        # Mock yf.download to return a DataFrame with 3 tickers, highly correlated
        # Tickers: A, B, C
        dates = pd.date_range(start='2023-01-01', periods=100)

        # A and B are identical (perf correlation), C is inverse
        data_a = np.linspace(100, 200, 100) # steady uptrend
        data_b = np.linspace(100, 200, 100) # same as A
        data_c = np.linspace(200, 100, 100) # downtrend

        # Add some noise to make covariance calculation valid (singular matrix avoidance)
        np.random.seed(42)
        data_a += np.random.normal(0, 1, 100)
        data_b += np.random.normal(0, 1, 100)
        data_c += np.random.normal(0, 1, 100)

        # Create a MultiIndex DataFrame as yfinance does with group_by='ticker'
        # Levels: Ticker, Price Type
        arrays = [
            ['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B', 'C', 'C', 'C', 'C', 'C'],
            ['Open', 'High', 'Low', 'Close', 'Volume'] * 3
        ]
        tuples = list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples, names=['Ticker', 'Price'])

        # Create data dict
        data_dict = {}
        for t, d in zip(['A', 'B', 'C'], [data_a, data_b, data_c]):
            data_dict[(t, 'Open')] = d
            data_dict[(t, 'High')] = d
            data_dict[(t, 'Low')] = d
            data_dict[(t, 'Close')] = d
            data_dict[(t, 'Volume')] = d

        df = pd.DataFrame(data_dict, index=dates)
        df.columns = index # Set MultiIndex

        mock_download.return_value = df

        optimizer = PortfolioOptimizer(tickers=['A', 'B', 'C'])
        optimizer.fetch_data()

        # Check if cov_matrix is calculated
        self.assertIsNotNone(optimizer.cov_matrix)
        self.assertEqual(optimizer.cov_matrix.shape, (3, 3))

        # Check Optimization
        # Case 1: Max Sharpe (No target return)
        # Given A and B are uptrending, C is downtrending.
        # Expect high weight on A or B, low on C.

        # We supply expected returns to guide it clearly
        exp_ret = {'A': 0.20, 'B': 0.20, 'C': -0.10}

        allocations = optimizer.optimize_weights(expected_returns_map=exp_ret)

        print("Allocations Max Sharpe:", allocations)

        self.assertTrue('A' in allocations or 'B' in allocations)
        # Weights sum to 1
        total_weight = sum(allocations.values())
        self.assertAlmostEqual(total_weight, 1.0, places=4)

        # Case 2: Target Return
        # If we demand 10% return, it should be feasible.
        allocations_tgt = optimizer.optimize_weights(expected_returns_map=exp_ret, target_return=0.10)
        print("Allocations Target 10%:", allocations_tgt)

        # We check within 3 places due to float issues
        self.assertAlmostEqual(sum(allocations_tgt.values()), 1.0, places=3)

    @patch('option_auditor.optimization.yf.download')
    def test_single_ticker_optimization(self, mock_download):
        # Single ticker optimization is trivial (weight 1.0)
        dates = pd.date_range(start='2023-01-01', periods=50)
        data = pd.DataFrame({'Close': np.random.rand(50)}, index=dates)

        # Single ticker structure (not multiindex usually, or column is just Close)
        # But our fetch_data handles MultiIndex.
        # Let's mock simple structure.
        mock_download.return_value = pd.DataFrame({'Close': np.linspace(100, 110, 50)}, index=dates)
        # Note: fetch_data logic for single ticker needs checking.
        # If group_by='ticker' is used, yfinance usually returns MultiIndex even for one ticker IF we passed a list.
        # But if we pass list of 1, it might just return flat.
        # Let's adjust mock to match what fetch_data expects for single ticker if flat.

        optimizer = PortfolioOptimizer(tickers=['SPY'])

        # Override fetch_data logic internally or just test that it handles flat DF
        # In fetch_data:
        # if ticker in data.columns (flat): close_prices[ticker] = data[ticker]
        # But we pass 'Close' column.
        # Wait, the code says:
        # if ticker in data.columns: close_prices[ticker] = data[ticker]
        # If flat df has columns ['Open', 'Close'...], 'SPY' is not in columns.

        # Let's adjust the code to handle Single Ticker Flat DF properly.
        # Re-reading optimization.py:
        # if "Close" in data.columns and len(self.tickers) == 1:
        #     close_prices[self.tickers[0]] = data['Close']

        optimizer.fetch_data()
        self.assertIsNotNone(optimizer.cov_matrix)

        allocations = optimizer.optimize_weights()
        self.assertEqual(allocations, {'SPY': 1.0})

if __name__ == '__main__':
    unittest.main()
