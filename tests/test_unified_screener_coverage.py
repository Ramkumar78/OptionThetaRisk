import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from option_auditor.unified_screener import screen_universal_dashboard

class TestUnifiedScreenerCoverage(unittest.TestCase):

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.isa.IsaStrategy.analyze')
    def test_unified_screener_run_basic(self, mock_isa, mock_fetch):
        # Setup
        # Create a DataFrame with DateTime index to avoid resampling issues or other pandas warnings
        dates = pd.date_range("2023-01-01", periods=60)
        mock_fetch.return_value = pd.DataFrame({'Close': [100.0] * 60}, index=dates)

        mock_isa.return_value = {'signal': 'BUY', 'verdict': 'BULLISH'}

        # We need to mock other strategies or ensure they handle the data

        with patch('option_auditor.strategies.fourier.FourierStrategy.analyze') as mock_fourier, \
             patch('option_auditor.strategies.turtle.TurtleStrategy.analyze') as mock_turtle, \
             patch('option_auditor.screener.enrich_with_fundamentals') as mock_enrich:

             mock_fourier.return_value = {'signal': 'BUY'}
             mock_turtle.return_value = {'signal': 'BUY'}
             mock_enrich.side_effect = lambda x: x # Identity

             # Also need to patch psutil check if environment is restricted
             with patch('option_auditor.unified_screener.check_memory_usage', return_value=False):

                 results = screen_universal_dashboard(["AAPL"])

                 self.assertIsInstance(results, list)
                 if results:
                     self.assertEqual(results[0]['ticker'], 'AAPL')
                     self.assertEqual(results[0]['confluence_score'], "3/3")

    def test_confluence_logic_implicit(self):
        # Since logic is inside process_ticker which is nested in screen_universal_dashboard,
        # we test via the main function with different mock returns.
        pass

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.isa.IsaStrategy.analyze')
    @patch('option_auditor.strategies.fourier.FourierStrategy.analyze')
    @patch('option_auditor.strategies.turtle.TurtleStrategy.analyze')
    @patch('option_auditor.screener.enrich_with_fundamentals')
    @patch('option_auditor.unified_screener.check_memory_usage')
    def test_scoring_logic_mixed(self, mock_mem, mock_enrich, mock_turtle, mock_fourier, mock_isa, mock_fetch):
        mock_mem.return_value = False
        mock_enrich.side_effect = lambda x: x

        # Data
        dates = pd.date_range("2023-01-01", periods=60)
        mock_fetch.return_value = pd.DataFrame({'Close': [100.0] * 60}, index=dates)

        # Scenario: 2/3 Confluence
        mock_turtle.return_value = {'signal': 'BUY'}
        mock_isa.return_value = {'signal': 'HOLD'} # Counts as positive
        mock_fourier.return_value = {'signal': 'NEUTRAL'}

        results = screen_universal_dashboard(["AAPL"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['confluence_score'], "2/3")
        self.assertIn("BUY", results[0]['master_verdict'])

    @patch('option_auditor.common.data_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.isa.IsaStrategy.analyze')
    @patch('option_auditor.strategies.fourier.FourierStrategy.analyze')
    @patch('option_auditor.strategies.turtle.TurtleStrategy.analyze')
    @patch('option_auditor.screener.enrich_with_fundamentals')
    @patch('option_auditor.unified_screener.check_memory_usage')
    def test_scoring_logic_sell(self, mock_mem, mock_enrich, mock_turtle, mock_fourier, mock_isa, mock_fetch):
        mock_mem.return_value = False
        mock_enrich.side_effect = lambda x: x

        dates = pd.date_range("2023-01-01", periods=60)
        mock_fetch.return_value = pd.DataFrame({'Close': [100.0] * 60}, index=dates)

        # Scenario: Strong Sell
        mock_turtle.return_value = {'signal': 'SELL'}
        mock_isa.return_value = {'signal': 'EXIT'}
        mock_fourier.return_value = {'signal': 'SELL'}

        results = screen_universal_dashboard(["AAPL"])

        self.assertEqual(len(results), 1)
        self.assertIn("SELL", results[0]['master_verdict'])
