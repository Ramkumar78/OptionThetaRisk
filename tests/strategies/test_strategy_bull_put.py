import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from option_auditor.screener import screen_bull_put_spreads
from datetime import date, timedelta

@patch('option_auditor.strategies.bull_put.yf.Ticker')
def test_screen_bull_put_valid(mock_ticker, mock_market_data):
    # Valid Bull Put:
    # 1. Price > SMA 50
    # 2. Options available ~45 DTE
    # 3. 30 Delta Put found
    # 4. ROI > Threshold

    # Mock History
    df = mock_market_data(days=250, price=100.0)
    # Ensure Price > SMA 50
    # SMA 50 approx 100. Price 105.
    df.iloc[-1, df.columns.get_loc('Close')] = 105.0
    # Force SMA 50 lower
    df.iloc[:-1, df.columns.get_loc('Close')] = 90.0 # Drag avg down

    mock_instance = MagicMock()
    mock_ticker.return_value = mock_instance
    mock_instance.history.return_value = df

    # Mock Options Chain
    target_date = (date.today() + timedelta(days=45)).strftime("%Y-%m-%d")
    mock_instance.options = [target_date]

    # Mock Puts DataFrame
    # Need columns: strike, bid, ask, lastPrice, impliedVolatility
    puts_data = {
        'strike': [90.0, 95.0, 100.0],
        'bid': [0.5, 1.5, 3.0],
        'ask': [0.6, 1.6, 3.1],
        'lastPrice': [0.55, 1.55, 3.05],
        'impliedVolatility': [0.2, 0.2, 0.2]
    }
    puts_df = pd.DataFrame(puts_data)

    mock_chain = MagicMock()
    mock_chain.puts = puts_df
    mock_instance.option_chain.return_value = mock_chain

    # We need _calculate_put_delta to return -0.30 for one of them
    # Instead of patching the math, let's patch the math function helper
    with patch('option_auditor.strategies.bull_put._calculate_put_delta') as mock_delta:
        # Return -0.30 for strike 95 (Short)
        # Return something else for others
        def delta_side_effect(S, K, T, r, sigma):
            if K == 95.0: return -0.30
            if K == 90.0: return -0.10
            return -0.50
        mock_delta.side_effect = delta_side_effect

        # Short 95 (Bid 1.5), Long 90 (Ask 0.6) -> Credit 0.9. Spread 5. Risk 4.1. ROI 21%.

        results = screen_bull_put_spreads(ticker_list=["BULLPUT"], check_mode=True)

        assert len(results) == 1
        res = results[0]
        assert res['short_strike'] == 95.0
        assert res['long_strike'] == 90.0
        assert res['roi_pct'] > 15.0

@patch('option_auditor.strategies.bull_put.yf.Ticker')
def test_screen_bull_put_bearish_trend(mock_ticker, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    # Price < SMA 50
    df.iloc[-1, df.columns.get_loc('Close')] = 80.0
    # SMA approx 100

    mock_instance = MagicMock()
    mock_instance.history.return_value = df
    mock_ticker.return_value = mock_instance

    results = screen_bull_put_spreads(ticker_list=["BEAR"], check_mode=False) # check_mode False enforces filters
    assert len(results) == 0

@patch('option_auditor.strategies.bull_put.yf.Ticker')
def test_screen_bull_put_no_options(mock_ticker, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_instance = MagicMock()
    mock_instance.history.return_value = df
    mock_instance.options = [] # No options
    mock_ticker.return_value = mock_instance

    results = screen_bull_put_spreads(ticker_list=["NOOPT"], check_mode=False)
    assert len(results) == 0
