import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from option_auditor.strategies.vertical_spreads import screen_vertical_put_spreads

# --- Helper to generate trend data ---
def create_mock_data(days=300, start_price=100.0, trend="up", vol=2000000):
    dates = pd.date_range(end=date.today(), periods=days, freq='B')
    # Ensure exact match in case pandas drops one (e.g. if today is weekend/holiday)
    actual_days = len(dates)

    # Determine slope based on trend
    slope = 0.0005 if trend == "up" else (-0.0005 if trend == "down" else 0)

    # Generate prices with oscillation (needed for HV calculation)
    # 1.001/0.999 oscillation provides variance for standard deviation
    prices = [
        start_price * (1.001 if i % 2 == 0 else 0.999) * (1 + (slope * i))
        for i in range(actual_days)
    ]

    df = pd.DataFrame({
        'Close': prices,
        'Volume': [vol] * actual_days
    }, index=dates)

    return df

# --- Tests ---

@patch('option_auditor.strategies.vertical_spreads.fetch_batch_data_safe')
def test_vertical_spread_trend_filter(mock_fetch):
    """
    Test Step 1 & 2: Trend Alignment and HV Check.
    """
    # 1. Reject Downtrend (Price < SMAs)
    # Generate data where price falls
    df_down = create_mock_data(trend="down")
    # Verify SMAs manually to be sure
    # sma_200 = df_down['Close'].rolling(200).mean().iloc[-1]
    # price = df_down['Close'].iloc[-1]
    # assert price < sma_200

    mock_fetch.return_value = df_down

    results = screen_vertical_put_spreads(["AAPL"])
    assert len(results) == 0, "Should reject downtrending stock"

    # 2. Accept Uptrend
    df_up = create_mock_data(trend="up")
    mock_fetch.return_value = df_up

    # We need to mock yf.Ticker to prevent it from crashing or doing real calls
    # If we don't mock it, it might try to fetch earnings and fail.
    with patch('option_auditor.strategies.vertical_spreads.yf.Ticker') as mock_ticker:
        # Mock Ticker to return nothing useful so it stops at earnings/options check
        # But we want to confirm it PASSED the trend check.
        # If it returns empty list at end, that's fine, as long as it TRIED to fetch ticker.
        mock_instance = mock_ticker.return_value
        mock_instance.options = [] # No options -> stops

        results = screen_vertical_put_spreads(["AAPL"])

        # It should have called Ticker("AAPL") because it passed trend check
        mock_ticker.assert_called_with("AAPL")
        assert len(results) == 0 # Because no options


@patch('option_auditor.strategies.vertical_spreads.fetch_batch_data_safe')
@patch('option_auditor.strategies.vertical_spreads.yf.Ticker')
def test_vertical_spread_earnings_check(mock_ticker_cls, mock_fetch):
    """
    Test Step 3: Earnings Avoidance (Next 21 days).
    """
    # Setup passing trend
    df_up = create_mock_data(trend="up")
    mock_fetch.return_value = df_up

    # Mock Ticker Instance
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker

    # Setup Expirations (Valid) to ensure we don't fail there
    mock_ticker.options = (
        (date.today() + timedelta(days=35)).strftime('%Y-%m-%d'),
    )

    # --- Scenario A: Earnings in 5 days (Fail) ---
    # Mock calendar. 'Earnings Date' can be list of Timestamps or Strings
    # Code: cal['Earnings Date'][0]
    upcoming_earnings = pd.Timestamp(date.today() + timedelta(days=5))

    # Mock property .calendar
    # Note: in yfinance, .calendar is often a dict or DataFrame.
    # The code handles dict or DF.
    mock_ticker.calendar = {'Earnings Date': [upcoming_earnings]}

    results = screen_vertical_put_spreads(["AAPL"])
    assert len(results) == 0, "Should reject if earnings in 5 days"

    # --- Scenario B: Earnings in 30 days (Pass) ---
    safe_earnings = pd.Timestamp(date.today() + timedelta(days=30))
    mock_ticker.calendar = {'Earnings Date': [safe_earnings]}

    # Need to mock option_chain to return empty to stop gracefully after earnings check
    mock_ticker.option_chain.return_value.puts = pd.DataFrame()

    screen_vertical_put_spreads(["AAPL"])

    # Verify we proceeded to check options (meaning earnings check passed)
    mock_ticker.option_chain.assert_called()


@patch('option_auditor.strategies.vertical_spreads.fetch_batch_data_safe')
@patch('option_auditor.strategies.vertical_spreads.yf.Ticker')
def test_vertical_spread_liquidity_check(mock_ticker_cls, mock_fetch):
    """
    Test Step 4 & 5: Option Liquidity (Vol/OI).
    """
    # Setup Trend
    mock_fetch.return_value = create_mock_data(trend="up")

    # Setup Ticker
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    mock_ticker.calendar = {'Earnings Date': [pd.Timestamp(date.today() + timedelta(days=30))]}

    target_date = date.today() + timedelta(days=35)
    target_str = target_date.strftime('%Y-%m-%d')
    mock_ticker.options = (target_str,)

    # --- Scenario A: Low Volume/OI (Fail) ---
    # Volume < 1000 sum
    low_liq_puts = pd.DataFrame({
        'volume': [100, 100],
        'openInterest': [100, 100],
        'strike': [90, 95],
        'impliedVolatility': [0.2, 0.2]
    })
    mock_ticker.option_chain.return_value.puts = low_liq_puts

    results = screen_vertical_put_spreads(["AAPL"])
    assert len(results) == 0, "Should reject low liquidity"

    # --- Scenario B: High Volume (Pass) ---
    high_liq_puts = pd.DataFrame({
        'volume': [1000, 2000],
        'openInterest': [5000, 5000],
        'strike': [90, 95],
        'impliedVolatility': [0.2, 0.2]
    })

    # Need to ensure IV check fails or passes.
    # Code checks: atm_iv < hv_20 -> return None.
    # hv_20 in our mock data is small/positive.
    # Let's make IV high (0.5 = 50%) to pass IV > HV check.
    high_liq_puts['impliedVolatility'] = 0.5

    mock_ticker.option_chain.return_value.puts = high_liq_puts

    # Assuming it proceeds to Greeks calculation and might fail there if columns missing
    # We just want to check that it didn't return due to liquidity.
    # But `screen_vertical_put_spreads` catches exceptions.
    # If we provide valid columns for later steps, we can check result.

    # Let's add columns needed for Greeks
    high_liq_puts['bid'] = 1.0
    high_liq_puts['ask'] = 1.2
    high_liq_puts['lastPrice'] = 1.1

    # It will likely fail at `short_leg` finding if we don't set strikes/deltas right.
    # But we only want to test liquidity filter here.

    # We can spy on `_calculate_put_delta` to see if it got called.
    with patch('option_auditor.strategies.vertical_spreads._calculate_put_delta') as mock_delta:
        screen_vertical_put_spreads(["AAPL"])
        assert mock_delta.called, "Should proceed to Greek calculation if liquidity is fine"


@patch('option_auditor.strategies.vertical_spreads.fetch_batch_data_safe')
@patch('option_auditor.strategies.vertical_spreads.yf.Ticker')
@patch('option_auditor.strategies.vertical_spreads._calculate_put_delta')
def test_vertical_spread_selection_logic(mock_delta, mock_ticker_cls, mock_fetch):
    """
    Test Step 6 & 7: Strike Selection and Credit/ROC.
    """
    # 1. Trend Data (Uptrend, Price ~150)
    df_up = create_mock_data(start_price=100.0, trend="up")
    # Last price will be around 150 (start * 1.5)
    curr_price = df_up['Close'].iloc[-1] # ~150
    mock_fetch.return_value = df_up

    # 2. Ticker Setup
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    mock_ticker.calendar = {'Earnings Date': [pd.Timestamp(date.today() + timedelta(days=90))]}
    target_date = date.today() + timedelta(days=35)
    target_str = target_date.strftime('%Y-%m-%d')
    mock_ticker.options = (target_str,)

    # 3. Option Chain Setup
    # We want Short Strike @ ~0.30 Delta.
    # Long Strike @ $5 lower.

    # Current price is approx 115.
    # OTM Puts must be < 115.

    # Let's target Short Strike 105 (-0.30 Delta) and Long Strike 100.

    puts_data = pd.DataFrame({
        'strike': [95, 100, 105, 110, 115],
        'volume': [5000] * 5,
        'openInterest': [5000] * 5,
        'impliedVolatility': [0.4] * 5, # 40% IV, > HV
        'bid': [0.5, 1.0, 2.5, 4.0, 6.0], # Mock prices
        'ask': [0.6, 1.1, 2.6, 4.1, 6.1],
        'lastPrice': [0.55, 1.05, 2.55, 4.05, 6.05]
    })
    mock_ticker.option_chain.return_value.puts = puts_data

    # 4. Mock Delta Calculation
    # The code iterates rows and calls _calculate_put_delta.
    # We need to map (strike) -> delta.

    def delta_side_effect(S, K, T, r, sigma):
        # Return specific deltas for our strikes
        if K == 105: return -0.30 # Perfect Target
        if K == 100: return -0.20
        if K == 110: return -0.40
        if K == 95: return -0.15
        if K == 115: return -0.50
        return -0.10

    mock_delta.side_effect = delta_side_effect

    # 5. Execute
    results = screen_vertical_put_spreads(["AAPL"])

    # 6. Verify
    assert len(results) == 1
    res = results[0]

    assert res['short_put'] == 105
    assert res['long_put'] == 100

    # Check Credit/ROC
    # Short Bid (105) = 2.5
    # Long Ask (100) = 1.1
    # Credit = 1.4
    # Width = 5
    # Risk = 3.6
    # ROC = (1.4 / 3.6) * 100 = 38.8%

    assert res['credit'] == 140.0 # 1.4 * 100
    assert res['risk'] == 360.0   # 3.6 * 100
    assert res['roc'] == 38.9     # Rounded 1 decimal
    assert res['setup_name'] == "Bull Put 105/100"
