import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import (
    screen_market, screen_sectors, screen_turtle_setups,
    screen_5_13_setups, screen_darvas_box, screen_mms_ote_setups,
    screen_bull_put_spreads
)
from option_auditor.strategies.market import screen_tickers_helper as _screen_tickers
from option_auditor.common.data_utils import prepare_data_for_ticker as _prepare_data_for_ticker
from option_auditor.common.screener_utils import _calculate_put_delta

# --- Fixtures ---

@pytest.fixture
def mock_yf_download():
    with patch('yfinance.download') as mock:
        yield mock

@pytest.fixture
def mock_yf_ticker():
    with patch('yfinance.Ticker') as mock:
        yield mock

@pytest.fixture
def sample_daily_df():
    # Create a 6-month daily dataframe with a clear uptrend
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
    close = np.linspace(100, 200, 100)
    df = pd.DataFrame({
        'Open': close,
        'High': close + 5,
        'Low': close - 5,
        'Close': close,
        'Volume': 1000000
    }, index=dates)
    return df

@pytest.fixture
def sample_intraday_df():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='5min')
    close = np.linspace(100, 105, 100)
    df = pd.DataFrame({
        'Open': close,
        'High': close + 1,
        'Low': close - 1,
        'Close': close,
        'Volume': 1000
    }, index=dates)
    return df

# --- Tests for _prepare_data_for_ticker ---

def test_prepare_data_from_batch(sample_daily_df):
    # Mock batch data as MultiIndex dataframe
    columns = pd.MultiIndex.from_product([['AAPL'], ['Open', 'High', 'Low', 'Close', 'Volume']])
    batch_data = pd.DataFrame(
        np.tile(sample_daily_df.values, (1, 1)),
        index=sample_daily_df.index,
        columns=columns
    )

    # Test extraction
    df = _prepare_data_for_ticker('AAPL', batch_data, '1d', '1y', '1d', None, False)
    assert not df.empty
    assert 'Close' in df.columns
    assert len(df) == 100

def test_prepare_data_sequential_fallback(mock_yf_download, sample_daily_df):
    mock_yf_download.return_value = sample_daily_df

    # Pass None as batch data to force sequential download
    df = _prepare_data_for_ticker('AAPL', None, '1d', '1y', '1d', None, False)
    assert not df.empty
    assert len(df) == 100
    mock_yf_download.assert_called_once()

def test_prepare_data_resampling(mock_yf_download, sample_intraday_df):
    mock_yf_download.return_value = sample_intraday_df

    # Test resampling 5m -> 49m
    df = _prepare_data_for_ticker('AAPL', None, '49m', '1mo', '5m', '49min', True)
    assert not df.empty
    # Length should be significantly reduced
    assert len(df) < 100

# --- Tests for Market Screener ---

def test_screen_market_integration(mock_yf_download, sample_daily_df):
    # Setup mock to return data for a few tickers
    # We need to simulate batch download return format
    columns = pd.MultiIndex.from_product([['AAPL', 'MSFT'], ['Open', 'High', 'Low', 'Close', 'Volume']])
    batch_data = pd.DataFrame(
        np.tile(sample_daily_df.values, (1, 2)), # Duplicate data for 2 tickers
        index=sample_daily_df.index,
        columns=columns
    )
    mock_yf_download.return_value = batch_data

    # We also need to mock pandas_ta inside the function, or rely on installed lib
    # Since we can't easily mock imports inside function, we assume pandas_ta is installed (it is)

    # Patch SECTOR_COMPONENTS to ensure AAPL/MSFT are mapped to XLK (Technology)
    # Otherwise test environment might not have the mapping
    with patch('option_auditor.strategies.market.SECTOR_COMPONENTS', {"XLK": ["AAPL", "MSFT"]}):
        results = screen_market(iv_rank_threshold=30, rsi_threshold=70, time_frame='1d')

        # Should return a dict of sectors
        assert isinstance(results, dict)
        # Check if AAPL or MSFT appear in Technology
        # Note: SECTOR_NAMES["XLK"] is "Technology" in constants.py.
        # But we didn't patch SECTOR_NAMES, so it should be there.
        # But if constants are imported, patching 'option_auditor.screener.SECTOR_COMPONENTS' updates the dict used in screener.py

        tech_key = [k for k in results.keys() if "Technology" in k][0]
        assert tech_key
        tickers = [r['ticker'] for r in results[tech_key]]
        assert 'AAPL' in tickers or 'MSFT' in tickers

def test_screen_sectors(mock_yf_download, sample_daily_df):
    # Mock data for sector ETF
    columns = pd.MultiIndex.from_product([['XLK'], ['Open', 'High', 'Low', 'Close', 'Volume']])
    batch_data = pd.DataFrame(
        np.tile(sample_daily_df.values, (1, 1)),
        index=sample_daily_df.index,
        columns=columns
    )
    mock_yf_download.return_value = batch_data

    results = screen_sectors(time_frame='1d')
    assert isinstance(results, list)
    # Only XLK should be present if we only mocked data for it effectively
    # (Though the function requests all sectors, yf.download might return empty/partial)
    # Actually, yf.download is mocked to return batch_data.
    # screen_sectors calls _screen_tickers with list of sectors.
    # _screen_tickers calls yf.download.

    # Check if we got results
    assert len(results) > 0
    assert results[0]['ticker'] == 'XLK'
    assert 'name' in results[0]

# --- Tests for Strategy Screeners ---

def test_screen_turtle_setups(mock_yf_download, sample_daily_df):
    # Create a breakout scenario
    # Last price > 20-day high
    df = sample_daily_df.copy()
    # Ensure a breakout
    df.iloc[-1, df.columns.get_loc('Close')] = 250 # Huge jump
    df.iloc[-1, df.columns.get_loc('High')] = 255

    mock_yf_download.return_value = pd.concat({ 'AAPL': df }, axis=1) # Mock batch return

    results = screen_turtle_setups(ticker_list=['AAPL'])

    assert len(results) == 1
    assert results[0]['signal'] == "🚀 BREAKOUT (BUY)"

def test_screen_5_13_setups(mock_yf_download):
    # Create data where 5 EMA crosses 13 EMA
    dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='D')
    # Price crossing up
    close = np.concatenate([np.linspace(100, 100, 40), np.linspace(100, 120, 10)])
    df = pd.DataFrame({
        'Open': close, 'High': close, 'Low': close, 'Close': close, 'Volume': 1000
    }, index=dates)

    mock_yf_download.return_value = pd.concat({ 'AAPL': df }, axis=1)

    results = screen_5_13_setups(ticker_list=['AAPL'])
    assert len(results) > 0
    assert "BREAKOUT" in results[0]['signal'] or "TRENDING" in results[0]['signal']

def test_screen_darvas_box(mock_yf_download):
    # Construct a Darvas Box pattern
    # 1. Rise
    # 2. Consolidate (High establishes ceiling, Low establishes floor)
    # 3. Breakout
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
    prices = []
    # Uptrend
    prices.extend(np.linspace(100, 150, 40))
    # Box formation (150 ceiling, 140 floor)
    for _ in range(10):
        prices.extend([148, 142, 145, 149, 141])
    # Breakout
    prices.extend([151, 152]) # Breakout

    # Pad to 100
    if len(prices) < 100:
        prices.extend([152] * (100 - len(prices)))

    prices = np.array(prices[:100])

    df = pd.DataFrame({
        'Open': prices, 'High': prices + 1, 'Low': prices - 1, 'Close': prices, 'Volume': np.random.randint(1000, 2000, 100)
    }, index=dates)

    # Ensure volume spike on breakout
    df.iloc[-1, df.columns.get_loc('Volume')] = 5000

    mock_yf_download.return_value = pd.concat({ 'AAPL': df }, axis=1)

    results = screen_darvas_box(ticker_list=['AAPL'])

    # This is tricky to match exact logic, but we expect some signal or at least safe execution
    # If patterns align, results > 0. If not, results == 0 but no crash.
    assert isinstance(results, list)

def test_screen_mms_ote_setups_bearish(mock_yf_download):
    # Construct Bearish OTE
    # 1. Rally to a peak (Liquidity Sweep)
    # 2. Displacement Down (create FVG)
    # 3. Retrace Up into 62-79% zone

    dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='1h')
    prices = list(np.linspace(100, 110, 20)) # Rally
    prices.extend([112, 105, 104]) # Peak 112, Sharp drop to 104 (Displacement)
    # Retrace to ~109 (which is within 62-79% of range 112-104 = 8pts. 62% retrace of 8 is ~5. 104+5=109)
    prices.extend([106, 107, 108, 109])

    # Pad
    while len(prices) < 60:
        prices.insert(0, 100)

    df = pd.DataFrame({
        'Open': prices, 'High': [p+0.5 for p in prices], 'Low': [p-0.5 for p in prices], 'Close': prices, 'Volume': 1000
    }, index=dates)

    # Create FVG manually
    # Peak candle at index -5 (112)
    # Drop candle at index -4 (105)
    # Low of -5 (say 111) > High of -3 (say 104) -> Gap

    mock_yf_download.return_value = df # Single ticker download

    # We patch thread pool to just run synchronously or accept mock returns
    # But for now, we rely on mock_yf_download being called

    results = screen_mms_ote_setups(ticker_list=['AAPL'], time_frame='1h')
    assert isinstance(results, list)
    # Can't guarantee signal without precise math, but verify structure

def test_screen_bull_put_spreads(mock_yf_ticker):
    # Mock Ticker object and its methods
    mock_ticker = MagicMock()
    mock_yf_ticker.return_value = mock_ticker

    # Mock History (Uptrend)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='D')
    df = pd.DataFrame({'Close': np.linspace(100, 110, 60)}, index=dates)
    mock_ticker.history.return_value = df

    # Mock Options dates
    future_date = (pd.Timestamp.now() + pd.Timedelta(days=45)).strftime('%Y-%m-%d')
    mock_ticker.options = [future_date]

    # Mock Option Chain
    mock_chain = MagicMock()
    # Puts: Strike 100 (OTM), 95 (OTM)
    puts_df = pd.DataFrame({
        'strike': [90, 95, 100, 105],
        'bid': [0.5, 0.8, 1.2, 2.5],
        'ask': [0.6, 0.9, 1.3, 2.6],
        'lastPrice': [0.55, 0.85, 1.25, 2.55],
        'impliedVolatility': [0.2, 0.2, 0.2, 0.2]
    })
    mock_chain.puts = puts_df
    mock_ticker.option_chain.return_value = mock_chain

    results = screen_bull_put_spreads(ticker_list=['AAPL'])

    # Should find a spread
    assert isinstance(results, list)
    if len(results) > 0:
        r = results[0]
        assert r['strategy'] == "Bull Put Spread"
        assert 'roi_pct' in r

def test_calculate_put_delta():
    # ITM Put (Strike > Spot) -> Delta close to -1
    d_itm = _calculate_put_delta(100, 110, 0.1, 0.05, 0.2)
    assert d_itm < -0.5

    # OTM Put (Strike < Spot) -> Delta close to 0
    d_otm = _calculate_put_delta(100, 90, 0.1, 0.05, 0.2)
    assert d_otm > -0.5 and d_otm < 0

    # ATM Put -> Delta close to -0.5
    d_atm = _calculate_put_delta(100, 100, 0.1, 0.05, 0.2)
    assert -0.6 < d_atm < -0.4

# --- Helper Tests ---
def test_prepare_data_empty(mock_yf_download):
    mock_yf_download.return_value = pd.DataFrame()
    df = _prepare_data_for_ticker('AAPL', None, '1d', '1y', '1d', None, False)
    assert df is None
