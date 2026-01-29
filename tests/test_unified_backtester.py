import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.unified_backtester import UnifiedBacktester

@pytest.fixture
def mock_yf_download():
    with patch("option_auditor.unified_backtester.yf.download") as mock:
        yield mock

def create_mock_df():
    # Create 3 years of data (approx 750 days)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=750, freq='B')

    # Create a stepped uptrend to ensure breakouts occur
    # Price stays flat then jumps, then flat then jumps
    price = []
    base = 100
    for i in range(500):
        if i % 25 == 0: base += 5 # Jump every 25 days
        price.append(base + np.random.normal(0, 0.5)) # Add noise

    # Downtrend
    for i in range(250):
        if i % 25 == 0: base -= 5
        price.append(base + np.random.normal(0, 0.5))

    # Ensure we have 750 points
    price = price[:750]
    while len(price) < 750: price.append(base)

    # Make Highs/Lows tight so Price > High_20 is easier
    # High is just slightly above Close, Low slightly below
    high = [p + 0.5 for p in price]
    low = [p - 0.5 for p in price]
    open_p = [p - 0.1 for p in price] # Open slightly below close (Green candles)

    # Create SPY (Bullish Regime)
    spy_price = np.linspace(300, 450, 750)

    # Create VIX (Low Vol)
    vix_price = np.random.uniform(15, 20, 750)

    data = {
        ('Close', 'TEST'): price,
        ('High', 'TEST'): high,
        ('Low', 'TEST'): low,
        ('Open', 'TEST'): open_p,
        ('Volume', 'TEST'): [1000000] * 750,
        ('Close', 'SPY'): spy_price,
        ('Close', '^VIX'): vix_price,
        ('High', 'SPY'): spy_price, # Dummy
        ('Low', 'SPY'): spy_price, # Dummy
        ('Volume', 'SPY'): [1] * 750, # Dummy
        ('Open', 'SPY'): spy_price, # Dummy
    }

    # MultiIndex Columns as expected by yfinance
    columns = pd.MultiIndex.from_tuples(data.keys())
    df = pd.DataFrame(data, index=dates)
    df.columns = columns

    return df

def create_reentry_mock_df():
    # Create ~3 years of data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=800, freq='B')

    # Construct a price series that:
    # 1. Establishes a strong trend (Price > 50 > 150 > 200)
    # 2. Pulls back below SMA 20 but stays above SMA 50/200
    # 3. Crosses back above SMA 20 (Re-Entry Trigger)
    # 4. But stays below previous High 20 (No Breakout Trigger)

    # Base trend
    x = np.linspace(0, 800, 800)
    base_trend = 100 + (x * 0.2) # Steady uptrend from 100 to ~260

    # Add a dip and recovery near the end
    price = base_trend.copy()

    # Last 50 days: Dip then Recover
    # Day 750-770: Dip
    price[750:770] -= 10
    # Day 770-800: Recover slightly (cross SMA 20) but not new High
    price[770:] -= 5

    high = price + 2
    low = price - 2
    open_p = price # Simple open = close for this test

    # SPY: Bullish
    spy = np.linspace(300, 500, 800)
    # VIX: Low
    vix = np.full(800, 15)

    data = {
        ('Close', 'TEST'): price,
        ('High', 'TEST'): high,
        ('Low', 'TEST'): low,
        ('Open', 'TEST'): open_p,
        ('Volume', 'TEST'): [1000000] * 800,
        ('Close', 'SPY'): spy,
        ('Close', '^VIX'): vix,
        # Dummy cols for SPY/VIX extra levels
        ('High', 'SPY'): spy,
        ('Low', 'SPY'): spy,
        ('Open', 'SPY'): spy,
        ('Volume', 'SPY'): [1] * 800,
    }

    columns = pd.MultiIndex.from_tuples(data.keys())
    df = pd.DataFrame(data, index=dates)
    df.columns = columns
    return df

def create_sine_wave_df():
    # Helper from extended tests: perfect sine wave for mean reversion/cycling tests
    end_date = pd.Timestamp.now()
    dates = pd.date_range(end=end_date, periods=500, freq="D")

    # SINE WAVE + TREND
    x = np.linspace(0, 4 * np.pi, 500)
    sine = np.sin(x) * 20
    trend = np.linspace(100, 200, 500)
    close = trend + sine

    # Add a sharp jump for Breakouts at mid-point
    close[250] += 10

    # High/Low envelopes
    high = close + 2
    low = close - 2
    open_p = close - 1
    volume = np.random.randint(1000000, 5000000, 500)

    spy_price = close # Highly correlated
    vix_price = np.full(500, 15.0)

    data = {
        ('Close', 'TEST'): close,
        ('High', 'TEST'): high,
        ('Low', 'TEST'): low,
        ('Open', 'TEST'): open_p,
        ('Volume', 'TEST'): volume,
        ('Close', 'SPY'): spy_price,
        ('Close', '^VIX'): vix_price,
        ('High', 'SPY'): spy_price,
        ('Low', 'SPY'): spy_price,
        ('Volume', 'SPY'): volume,
        ('Open', 'SPY'): spy_price
    }

    columns = pd.MultiIndex.from_tuples(data.keys())
    df = pd.DataFrame(data, index=dates)
    df.columns = columns
    return df

# --- Tests from Base ---

def test_fetch_data_success(mock_yf_download):
    mock_df = create_mock_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="master")
    df = bt.fetch_data()

    assert df is not None
    assert not df.empty
    assert "Close" in df.columns
    assert "Spy" in df.columns
    assert "Vix" in df.columns
    assert "Open" in df.columns

def test_fetch_data_failure(mock_yf_download):
    mock_yf_download.side_effect = Exception("API Error")

    bt = UnifiedBacktester("TEST")
    df = bt.fetch_data()

    assert df is None

def test_calculate_indicators():
    # We can use fetch_data output simulation
    dates = pd.date_range(end=pd.Timestamp.now(), periods=250, freq='B') # 1 year
    df = pd.DataFrame({
        'Close': np.linspace(100, 150, 250),
        'High': np.linspace(102, 152, 250),
        'Low': np.linspace(98, 148, 250),
        'Open': np.linspace(99, 149, 250),
        'Volume': [1000] * 250,
        'Spy': np.linspace(300, 400, 250),
        'Vix': [15] * 250
    }, index=dates)

    # Test Grandmaster (default)
    bt = UnifiedBacktester("TEST")
    enriched = bt.calculate_indicators(df.copy())
    assert 'sma200' in enriched.columns
    assert 'sma50' in enriched.columns
    assert 'atr' in enriched.columns
    assert 'high_20' in enriched.columns
    # Grandmaster doesn't need low_10

    # Test Turtle
    bt_turtle = UnifiedBacktester("TEST", strategy_type="turtle")
    enriched_turtle = bt_turtle.calculate_indicators(df.copy())
    assert 'low_10' in enriched_turtle.columns
    assert 'high_20' in enriched_turtle.columns

def test_run_master_strategy(mock_yf_download):
    mock_df = create_mock_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="master")
    result = bt.run()

    assert "error" not in result
    assert result["ticker"] == "TEST"
    assert result["strategy"] == "MASTER"
    assert "trades" in result
    assert "win_rate" in result

def test_run_turtle_strategy(mock_yf_download):
    mock_df = create_mock_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="turtle")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "TURTLE"
    assert result["trades"] > 0

def test_run_isa_strategy(mock_yf_download):
    mock_df = create_mock_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="isa")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "ISA"
    assert result["trades"] > 0

def test_run_no_data(mock_yf_download):
    mock_yf_download.return_value = pd.DataFrame() # Empty

    bt = UnifiedBacktester("TEST")
    result = bt.run()

    assert "error" in result
    assert result["error"] == "No data found"

# --- Tests from New (Ported) ---

def test_backtest_duration_calculation(mock_yf_download):
    ticker = "TEST"
    backtester = UnifiedBacktester(ticker)

    dates = pd.date_range(end=pd.Timestamp.now(), periods=1000, freq='D')
    close = np.linspace(100, 200, 1000)
    close[-10:] = 100

    data = pd.DataFrame({
        'Close': close,
        'High': close + 5,
        'Low': close - 5,
        'Open': close,
        'Volume': np.ones(1000) * 1000000
    }, index=dates)

    columns = pd.MultiIndex.from_product([['Close', 'High', 'Low', 'Open', 'Volume'], [ticker, 'SPY', '^VIX']])
    mock_df = pd.DataFrame(np.tile(data.values, (1, 3)), index=dates, columns=columns)

    mock_yf_download.return_value = mock_df

    result = backtester.run()

    assert 'buy_hold_days' in result
    assert 'avg_days_held' in result
    assert 'log' in result
    assert result['buy_hold_days'] >= 728

    if result['log']:
        for trade in result['log']:
            assert 'days' in trade
            if trade['type'] == 'SELL':
                 assert isinstance(trade['days'], int)

def test_backtest_avg_days_held(mock_yf_download):
    ticker = "TEST"
    backtester = UnifiedBacktester(ticker)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=1000, freq='D')
    close = np.linspace(100, 200, 1000)
    data = pd.DataFrame({
        'Close': close,
        'High': close + 5,
        'Low': close - 5,
        'Open': close,
        'Volume': np.ones(1000) * 1000000
    }, index=dates)
    columns = pd.MultiIndex.from_product([['Close', 'High', 'Low', 'Open', 'Volume'], [ticker, 'SPY', '^VIX']])
    mock_df = pd.DataFrame(np.tile(data.values, (1, 3)), index=dates, columns=columns)
    mock_yf_download.return_value = mock_df

    result = backtester.run()

    assert isinstance(result['avg_days_held'], int)
    assert isinstance(result['buy_hold_days'], int)

# --- Tests from V2 (Ported) ---

def test_reentry_logic_master(mock_yf_download):
    mock_df = create_reentry_mock_df()
    mock_yf_download.return_value = mock_df
    bt = UnifiedBacktester("TEST", strategy_type="master")
    result = bt.run()
    assert "error" not in result
    assert result["strategy"] == "MASTER"
    assert result["trades"] >= 0
    assert "buy_hold_return" in result
    assert isinstance(result["buy_hold_return"], float)

def test_exact_date_alignment(mock_yf_download):
    mock_df = create_reentry_mock_df()
    mock_yf_download.return_value = mock_df
    bt = UnifiedBacktester("TEST", strategy_type="master")
    result = bt.run()
    assert "start_date" in result
    assert "end_date" in result

def test_isa_reentry_logic(mock_yf_download):
    mock_df = create_reentry_mock_df()
    mock_yf_download.return_value = mock_df
    bt = UnifiedBacktester("TEST", strategy_type="isa")
    result = bt.run()
    assert result["strategy"] == "ISA"
    assert result["trades"] >= 0

def test_fetch_data_multiindex_handling(mock_yf_download):
    mock_df = create_reentry_mock_df()
    mock_yf_download.return_value = mock_df
    bt = UnifiedBacktester("TEST")
    df = bt.fetch_data()
    assert isinstance(df, pd.DataFrame)
    assert 'Close' in df.columns
    assert 'Spy' in df.columns

# --- Merged from Extended ---

def test_market_strategy_backtest(mock_yf_download):
    mock_df = create_sine_wave_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="market")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "MARKET"
    # Market strategy uses RSI dip in trend, sine wave should provide this
    assert result["trades"] >= 0

def test_ema_strategy_backtest(mock_yf_download):
    mock_df = create_sine_wave_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="ema_5_13")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "EMA_5_13"

def test_darvas_strategy_backtest(mock_yf_download):
    mock_df = create_sine_wave_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="darvas")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "DARVAS"

def test_fourier_strategy_backtest(mock_yf_download):
    mock_df = create_sine_wave_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="fourier")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "FOURIER"
    assert result["trades"] >= 0

def test_hybrid_strategy_backtest(mock_yf_download):
    mock_df = create_sine_wave_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="hybrid")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "HYBRID"
    assert result["trades"] >= 0

def test_master_convergence_strategy_backtest(mock_yf_download):
    mock_df = create_sine_wave_df()
    mock_yf_download.return_value = mock_df

    bt = UnifiedBacktester("TEST", strategy_type="master_convergence")
    result = bt.run()

    assert "error" not in result
    assert result["strategy"] == "MASTER_CONVERGENCE"

def test_edge_case_regime_red(mock_yf_download):
    # Create data where Vix is HIGH (Red Regime)
    mock_df = create_sine_wave_df()
    # Need to manipulate Vix in the multiindex structure if possible or just use the generator's internal structure
    # The generator returns a DataFrame with MultiIndex columns.
    # We can modify it.

    # Locate VIX column
    # The helper `create_sine_wave_df` sets VIX to 15.0.

    idx = pd.IndexSlice
    # We can't easily use loc with MultiIndex columns for setting efficiently if names not set,
    # but we can assume column order or names from helper.
    # Helper: ('Close', '^VIX')

    # Let's create a new one with High VIX
    # We'll just patch the helper or copy logic:
    df = mock_df.copy()
    # Find column with level 1 == '^VIX'
    # Or just use the known tuple
    df[('Close', '^VIX')] = 40.0

    mock_yf_download.return_value = df

    bt = UnifiedBacktester("TEST", strategy_type="grandmaster")
    result = bt.run()

    assert "error" not in result
    # Grandmaster is long only, so should be 0 trades in RED regime
    assert result["trades"] == 0
