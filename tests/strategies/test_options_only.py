import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import date
from option_auditor.strategies.options_only import screen_options_only_strategy

@patch('option_auditor.strategies.options_only.yf.Ticker')
@patch('option_auditor.strategies.options_only.os.path.exists')
def test_screen_options_only_green_light(mock_exists, mock_ticker):
    # Mock CSV existence (False to trigger fallback list)
    mock_exists.return_value = False

    # Mock Ticker object
    ticker_instance = MagicMock()
    mock_ticker.return_value = ticker_instance

    # 1. History (Liquidity check)
    # Price 100, Volume 1M -> Turnover 100M > 15M
    hist_df = pd.DataFrame({
        'Close': [100.0] * 5,
        'Volume': [1_000_000] * 5
    })
    ticker_instance.history.return_value = hist_df

    # 2. Earnings
    # Future earnings
    ticker_instance.calendar = {'Earnings Date': [pd.Timestamp("2026-12-01")]}

    # 3. Expirations
    # Need date ~45 days out
    today = date.today()
    exp_date = today + pd.Timedelta(days=45)
    exp_str = exp_date.strftime('%Y-%m-%d')
    ticker_instance.options = [exp_str]

    # 4. Chain
    # We need puts. Current Price 100.
    # Target Delta -0.30.
    # We need to ensure our mock puts calculate to ~-0.30 delta.
    # The strategy calculates delta using _calculate_put_delta.
    # We can patch _calculate_put_delta to be easier, or provide inputs that work.
    # Let's patch _calculate_put_delta in the module to simply return -0.30 for one strike.

    puts_df = pd.DataFrame({
        'strike': [90.0, 85.0],
        'bid': [1.5, 0.5],
        'ask': [1.6, 0.5], # Long ask is 0.5. Short bid 1.5. Credit 1.0.
        'lastPrice': [1.5, 0.5],
        'impliedVolatility': [0.2, 0.2]
    })

    chain_mock = MagicMock()
    chain_mock.puts = puts_df
    ticker_instance.option_chain.return_value = chain_mock

    # Patch calculate_delta to control logic
    with patch('option_auditor.strategies.options_only._calculate_put_delta') as mock_delta:
        # Return -0.30 for strike 90, and something else for 85
        def side_effect_delta(S, K, T, r, sigma):
            if K == 90.0: return -0.30
            return -0.10
        mock_delta.side_effect = side_effect_delta

        # Run with limit=1 to test just one cycle
        results = screen_options_only_strategy(limit=1)

    assert len(results) == 1
    res = results[0]
    assert "GREEN" in res['verdict']
    assert res['setup_name'] == "Bull Put 90/85"
    # Credit 1.0, Width 5.0, Risk 4.0. ROC = 25%
    assert res['roc'] == 25.0

@patch('option_auditor.strategies.options_only.yf.Ticker')
@patch('option_auditor.strategies.options_only.os.path.exists')
def test_screen_options_only_low_roc(mock_exists, mock_ticker):
    mock_exists.return_value = False
    ticker_instance = MagicMock()
    mock_ticker.return_value = ticker_instance

    hist_df = pd.DataFrame({'Close': [100.0]*5, 'Volume': [1_000_000]*5})
    ticker_instance.history.return_value = hist_df
    ticker_instance.calendar = {'Earnings Date': [pd.Timestamp("2026-12-01")]}

    today = date.today()
    exp_date = today + pd.Timedelta(days=45)
    exp_str = exp_date.strftime('%Y-%m-%d')
    ticker_instance.options = [exp_str]

    # Low Credit: Bid 0.6, Ask 0.5 -> Credit 0.1. Width 5. ROC = 0.1/4.9 ~ 2%
    puts_df = pd.DataFrame({
        'strike': [90.0, 85.0],
        'bid': [0.6, 0.5],
        'ask': [0.7, 0.5],
        'lastPrice': [0.6, 0.5],
        'impliedVolatility': [0.2, 0.2]
    })
    chain_mock = MagicMock()
    chain_mock.puts = puts_df
    ticker_instance.option_chain.return_value = chain_mock

    with patch('option_auditor.strategies.options_only._calculate_put_delta') as mock_delta:
        mock_delta.return_value = -0.30 # Simplify

        results = screen_options_only_strategy(limit=1)

    # Should be empty because VERDICT="WAIT" is filtered out
    assert len(results) == 0
