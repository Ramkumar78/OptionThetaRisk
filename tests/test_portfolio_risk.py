import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor import portfolio_risk
from option_auditor.common.constants import SECTOR_COMPONENTS, SECTOR_NAMES

class TestPortfolioRisk(unittest.TestCase):

    def setUp(self):
        self.positions = [
            {'ticker': 'NVDA', 'value': 5000},
            {'ticker': 'AMD', 'value': 5000},
            {'ticker': 'GOOG', 'value': 5000}
        ]

    def test_get_sector_map(self):
        sector_map = portfolio_risk._get_sector_map()
        self.assertEqual(sector_map['NVDA'], SECTOR_NAMES['XLK']) # Technology
        self.assertEqual(sector_map['GOOG'], SECTOR_NAMES['XLC']) # Comm Services

    @patch('option_auditor.portfolio_risk.get_cached_market_data')
    def test_analyze_portfolio_risk(self, mock_get_data):
        # Mock Market Data: 3 tickers, perfect correlation for NVDA/AMD, zero for GOOG
        dates = pd.date_range(start='2023-01-01', periods=100)

        # Create correlated data
        nvda = np.linspace(100, 200, 100)
        amd = np.linspace(50, 100, 100) # Perfect correlation
        goog = np.random.normal(100, 10, 100) # Random/Different

        df = pd.DataFrame({
            'NVDA': nvda,
            'AMD': amd,
            'GOOG': goog
        }, index=dates)

        # get_cached_market_data usually returns MultiIndex if multiple tickers, OR simple DF.
        # Logic handles both. Let's return simple DF where columns are tickers (Close prices only).
        # Actually, get_cached_market_data usually returns (Ticker, OHLC) multiindex or (OHLC) if single.
        # But for list, it returns (Ticker, OHLC).
        # So we should mock that structure to be safe, or see if logic handles simple df.
        # Logic:
        # closes = price_data.xs('Close', level=1, axis=1) if MultiIndex
        # else price_data['Close']...

        # Let's mock a MultiIndex DataFrame as returned by yfinance group_by='ticker'
        iterables = [['NVDA', 'AMD', 'GOOG'], ['Close']]
        index = pd.MultiIndex.from_product(iterables, names=['Ticker', 'Price'])
        # Create a DF with 100 rows and these columns

        # Wait, from_product gives (NVDA, Close), (AMD, Close)...
        # We need data aligned.
        data_dict = {
            ('NVDA', 'Close'): nvda,
            ('AMD', 'Close'): amd,
            ('GOOG', 'Close'): goog
        }
        mock_df = pd.DataFrame(data_dict, index=dates)
        mock_get_data.return_value = mock_df

        result = portfolio_risk.analyze_portfolio_risk(self.positions)

        self.assertEqual(result['total_value'], 15000)

        # Check Concentration: 33% each. > 15% warning.
        self.assertTrue(len(result['concentration_warnings']) >= 3)
        # Ticker order is not guaranteed in warnings due to set or dict iteration, so check ANY
        warnings_str = " ".join(result['concentration_warnings'])
        self.assertIn("NVDA", warnings_str)

        # Check Correlation
        # NVDA/AMD should be high
        pairs = result['high_correlation_pairs']
        pair_names = [p['pair'] for p in pairs]
        # "NVDA + AMD" or "AMD + NVDA"
        self.assertTrue(any("NVDA" in p and "AMD" in p for p in pair_names))

        # Check Sector Risk
        # NVDA(Tech) + AMD(Tech) = 66%. GOOG(Comm) = 33%.
        # Should warn about Tech
        tech_name = SECTOR_NAMES['XLK']
        self.assertTrue(any(tech_name in w for w in result['sector_warnings']))

        # Check Diversification Score
        # NVDA-AMD = 1.0. NVDA-GOOG ~ 0. AMD-GOOG ~ 0.
        # Avg ~ 0.33. Score ~ 66.
        self.assertGreater(result['diversification_score'], 0)
        self.assertLess(result['diversification_score'], 100)

    def test_analyze_empty(self):
        result = portfolio_risk.analyze_portfolio_risk([])
        self.assertEqual(result, {})

    def test_analyze_invalid(self):
        result = portfolio_risk.analyze_portfolio_risk([{'foo': 'bar'}])
        self.assertIn('error', result)



    def test_analyze_zero_total_value(self):
        # Case where total value sums to 0
        positions = [{'ticker': 'A', 'value': 0}, {'ticker': 'B', 'value': 0}]
        result = portfolio_risk.analyze_portfolio_risk(positions)
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Total portfolio value is zero.")

    def test_analyze_single_asset_diversification(self):
        # Single asset should range diversification score to 0
        positions = [{'ticker': 'NVDA', 'value': 10000}]
        # We need to mock get_cached_market_data to return data for NVDA
        with patch('option_auditor.portfolio_risk.get_cached_market_data') as mock_data:
            df = pd.DataFrame({'Close': [100, 101, 102]}, index=pd.date_range('2023-01-01', periods=3))
            # get_cached_market_data usually returns a simple DF for single ticker if configured that way,
            # but let's see how the code handles it.
            # Code: closes = price_data['Close'] if 'Close' in price_data.columns else price_data
            # So if we return a DF with 'Close' column, it works.
            mock_data.return_value = df
            
            result = portfolio_risk.analyze_portfolio_risk(positions)
            self.assertEqual(result['diversification_score'], 0)

    @patch('option_auditor.portfolio_risk.get_cached_market_data')
    def test_analyze_missing_market_data(self, mock_get_data):
        # Mock empty return from market data
        mock_get_data.return_value = pd.DataFrame()
        
        result = portfolio_risk.analyze_portfolio_risk(self.positions)
        
        # Should still return structure but with 0 div score and no correlation matrix
        self.assertEqual(result['diversification_score'], 0)
        self.assertEqual(result['correlation_matrix'], {})
        # Should still have concentration warnings because that depends on input, not market data
        self.assertTrue(len(result['concentration_warnings']) > 0)

if __name__ == '__main__':
    unittest.main()
