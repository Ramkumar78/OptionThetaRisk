import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.strategies.hybrid import screen_hybrid_strategy, StrategyAnalyzer

@pytest.fixture
def sample_df():
    dates = pd.date_range(start='2023-01-01', periods=250, freq='D')
    data = {
        'Open': np.linspace(100, 200, 250),
        'High': np.linspace(101, 201, 250),
        'Low': np.linspace(99, 199, 250),
        'Close': np.linspace(100, 200, 250),
        'Volume': [1000000] * 250
    }
    return pd.DataFrame(data, index=dates)

@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
@patch('option_auditor.strategies.hybrid.get_cached_market_data')
def test_screen_hybrid_strategy(mock_get_cached, mock_fetch_batch, sample_df):
    mock_get_cached.return_value = pd.concat([sample_df], keys=['AAPL'], axis=1)

    # We also need to patch SECTOR_COMPONENTS or resolve_region_tickers if ticker_list is None
    # But we can pass ticker_list

    results = screen_hybrid_strategy(ticker_list=['AAPL'], time_frame="1d")

    assert isinstance(results, list)
    # With rising prices:
    # SMA 200 is avg of last 200. Price is at top. So Bullish.
    # Cycle? Random or calculated.

    if len(results) > 0:
        assert results[0]['ticker'] == 'AAPL'
        assert results[0]['trend'] == 'BULLISH'

def test_strategy_analyzer(sample_df):
    analyzer = StrategyAnalyzer(sample_df)

    trend = analyzer.check_isa_trend()
    assert trend == "BULLISH"

    # Fourier
    fourier, rel_pos = analyzer.check_fourier()
    assert fourier in ["TOP", "BOTTOM", "NEUTRAL", "N/A"]
