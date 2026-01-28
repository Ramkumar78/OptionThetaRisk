import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.strategies.market import screen_market, screen_sectors, enrich_with_fundamentals

@pytest.fixture
def sample_df():
    # Create a DF with enough data for indicators (RSI 14, SMA 50)
    # 60 rows
    dates = pd.date_range(start='2023-01-01', periods=60, freq='D')
    data = {
        'Open': np.linspace(100, 110, 60),
        'High': np.linspace(101, 111, 60),
        'Low': np.linspace(99, 109, 60),
        'Close': np.linspace(100, 110, 60),
        'Volume': [1000000] * 60
    }
    return pd.DataFrame(data, index=dates)

@patch('option_auditor.strategies.market.ScreeningRunner')
@patch('option_auditor.strategies.market.resolve_region_tickers')
def test_screen_market(mock_resolve, mock_runner_cls, sample_df):
    mock_resolve.return_value = ['AAPL']

    mock_runner = mock_runner_cls.return_value

    def side_effect_run(strategy_func):
        # Run the strategy on sample data
        res = strategy_func('AAPL', sample_df)
        return [res] if res else []

    mock_runner.run.side_effect = side_effect_run

    # Mock is_intraday to False
    mock_runner.is_intraday = False
    mock_runner.yf_interval = "1d"

    results = screen_market()

    assert isinstance(results, dict)
    # Depending on sector grouping, AAPL might be in a sector or not.
    # If SECTOR_COMPONENTS has AAPL, it will be grouped.
    # If not, and since we mock resolve_region_tickers to only AAPL,
    # if AAPL is not in any sector in SECTOR_COMPONENTS (imported from constants), it might return empty dict?
    # screen_market logic:
    # grouped_results = {}
    # for sector_code...
    #   if t in components...

    # So if AAPL is not in known sectors, it returns empty.
    # Let's mock SECTOR_COMPONENTS too?
    # It is imported in market.py. We can patch it.

@patch('option_auditor.strategies.market.SECTOR_COMPONENTS', {'TECH': ['AAPL']})
@patch('option_auditor.strategies.market.SECTOR_NAMES', {'TECH': 'Technology'})
@patch('option_auditor.strategies.market.ScreeningRunner')
@patch('option_auditor.strategies.market.resolve_region_tickers')
def test_screen_market_with_sector(mock_resolve, mock_runner_cls, sample_df):
    mock_resolve.return_value = ['AAPL']
    mock_runner = mock_runner_cls.return_value
    mock_runner.is_intraday = False
    mock_runner.yf_interval = "1d"

    def side_effect_run(strategy_func):
        res = strategy_func('AAPL', sample_df)
        return [res] if res else []

    mock_runner.run.side_effect = side_effect_run

    results = screen_market()

    assert "Technology (TECH)" in results
    assert len(results["Technology (TECH)"]) == 1
    assert results["Technology (TECH)"][0]['ticker'] == 'AAPL'

@patch('option_auditor.strategies.market.yf.Ticker')
def test_enrich_with_fundamentals(mock_ticker):
    mock_info = {'trailingPE': 20.0, 'forwardPE': 25.0, 'sector': 'Tech'}
    mock_ticker.return_value.info = mock_info

    results = [{'ticker': 'AAPL', 'signal': 'BUY', 'verdict': 'BUY'}]
    enriched = enrich_with_fundamentals(results)

    assert enriched[0]['pe_ratio'] == '20.00'
    assert enriched[0]['sector'] == 'Tech'
