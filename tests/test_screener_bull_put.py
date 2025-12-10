import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import date, timedelta
from option_auditor.screener import screen_bull_put_spreads, _calculate_put_delta

# Mock data for yfinance
def mock_yf_download(*args, **kwargs):
    # Create a DataFrame with a bullish trend
    dates = pd.date_range(end=date.today(), periods=60)
    data = {
        'Open': [100 + i for i in range(60)],
        'High': [102 + i for i in range(60)],
        'Low': [99 + i for i in range(60)],
        'Close': [101 + i for i in range(60)],
        'Volume': [1000000] * 60
    }
    df = pd.DataFrame(data, index=dates)
    return df

def mock_option_chain(*args, **kwargs):
    # Create a mock option chain
    puts_data = {
        'strike': [135, 140, 145, 150, 155], # Spot is around 160 (101+59)
        'lastPrice': [1.0, 1.5, 2.0, 3.0, 4.0],
        'bid': [1.0, 1.5, 2.0, 3.0, 4.0],
        'ask': [1.2, 1.7, 2.2, 3.2, 4.2],
        'impliedVolatility': [0.2, 0.2, 0.2, 0.2, 0.2],
        'volume': [100, 100, 100, 100, 100],
        'openInterest': [1000, 1000, 1000, 1000, 1000]
    }
    puts_df = pd.DataFrame(puts_data)

    mock_chain = MagicMock()
    mock_chain.puts = puts_df
    mock_chain.calls = pd.DataFrame()
    return mock_chain

@patch('yfinance.download', side_effect=mock_yf_download)
@patch('yfinance.Ticker')
def test_screen_bull_put_spreads(mock_ticker, mock_download):
    # Setup Mock Ticker
    mock_tk_instance = MagicMock()
    mock_ticker.return_value = mock_tk_instance

    # Mock Options Dates (approx 45 days away)
    target_date = date.today() + timedelta(days=45)
    mock_tk_instance.options = [target_date.strftime("%Y-%m-%d")]

    # Mock Option Chain
    mock_tk_instance.option_chain.side_effect = mock_option_chain

    # Run Screener
    results = screen_bull_put_spreads(ticker_list=["TEST"])

    # Verify Results
    assert len(results) == 1
    res = results[0]
    assert res['ticker'] == "TEST"
    assert res['strategy'] == "Bull Put Spread"
    assert res['trend'] == "Bullish (>SMA50)"

    # Check strikes logic (This will depend on delta calc which depends on price)
    # Price is 160.
    # Strikes: 135, 140, 145, 150, 155
    # Short Strike should be around 30 delta.
    # At 160 spot, 150 strike Put is OTM.
    # Let's check if we got a result.
    assert 'short_strike' in res
    assert 'long_strike' in res
    assert res['long_strike'] == res['short_strike'] - 5.0
    assert res['credit'] > 0
    assert res['roi_pct'] > 0

def test_calculate_put_delta():
    # Test ATM Put Delta (approx -0.5)
    delta = _calculate_put_delta(S=100, K=100, T=0.1, r=0.05, sigma=0.2)
    assert -0.6 < delta < -0.4

    # Test Deep OTM Put Delta (approx 0)
    delta = _calculate_put_delta(S=120, K=100, T=0.1, r=0.05, sigma=0.2)
    assert -0.1 < delta < 0.0

    # Test Deep ITM Put Delta (approx -1.0)
    delta = _calculate_put_delta(S=80, K=100, T=0.1, r=0.05, sigma=0.2)
    assert -1.0 <= delta < -0.9
