import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor import screener
from option_auditor.strategies import market
from option_auditor.uk_stock_data import get_uk_euro_tickers
from option_auditor.india_stock_data import get_indian_tickers
from option_auditor.common.data_utils import prepare_data_for_ticker
from option_auditor.strategies.market import screen_market, screen_sectors
from option_auditor.strategies.bull_put import screen_bull_put_spreads
from option_auditor.strategies.mms_ote import screen_mms_ote_setups
from option_auditor.strategies.hybrid import screen_hybrid_strategy
from datetime import datetime, timedelta

# Helper to create mock dataframe
def create_mock_df(periods=100, trend='flat', volume=1000000):
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    if trend == 'up':
        closes = np.linspace(100, 200, periods)
    elif trend == 'down':
        closes = np.linspace(200, 100, periods)
    else:
        closes = np.full(periods, 100.0)

    data = {
        'Open': closes,
        'High': closes + 5,
        'Low': closes - 5,
        'Close': closes,
        'Volume': np.full(periods, volume)
    }
    df = pd.DataFrame(data, index=dates)
    return df

def mock_yf_download(*args, **kwargs):
    # Determine the tickers being requested
    tickers = args[0] if args else kwargs.get('tickers')
    if isinstance(tickers, str):
        tickers = tickers.split()

    periods = 60
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')

    data = {}
    for ticker in tickers:
        # Create a price series
        closes = [100.0 + i for i in range(periods)]

        # Trigger Turtle Breakout at the end
        closes[-1] = closes[-2] + 20

        highs = [c + 5 for c in closes]
        lows = [c - 5 for c in closes]
        opens = [c for c in closes]

        data[(ticker, 'Close')] = closes
        data[(ticker, 'High')] = highs
        data[(ticker, 'Low')] = lows
        data[(ticker, 'Open')] = opens
        data[(ticker, 'Volume')] = [1000000 for _ in range(periods)]

    df = pd.DataFrame(data, index=dates)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df

@patch('option_auditor.strategies.market.screen_tickers_helper')
@patch('option_auditor.strategies.market.resolve_region_tickers')
def test_screen_market(mock_resolve, mock_screen):
    # Mocking resolve to return some tickers
    mock_resolve.return_value = ["AAPL"]

    # Mocking screen_tickers_helper to return results
    mock_screen.return_value = [{
        "ticker": "AAPL",
        "price": 150.0,
        "rsi": 40.0,
        "signal": "WAIT"
    }]

    # We mock SECTOR_NAMES/COMPONENTS usage via patch.dict on common.constants if needed,
    # but screen_market uses them from imported constants.
    with patch.dict('option_auditor.strategies.market.SECTOR_NAMES', {"XLK": "Technology"}), \
         patch.dict('option_auditor.strategies.market.SECTOR_COMPONENTS', {"XLK": ["AAPL"]}):

        results = screen_market(iv_rank_threshold=20, rsi_threshold=80)

        # Should be grouped
        assert "Technology (XLK)" in results
        assert len(results["Technology (XLK)"]) == 1
        assert results["Technology (XLK)"][0]["ticker"] == "AAPL"

@patch('option_auditor.common.screener_utils.yf.download')
def test_screen_turtle(mock_download):
    mock_download.side_effect = mock_yf_download

    tickers = ["AAPL", "GOOGL"]
    # We call the wrapper in screener.py which delegates to strategies/turtle.py
    # TurtleStrategy uses ScreeningRunner which uses fetch_batch_data_safe -> yf.download
    # We patch yf.download in screener_utils because ScreeningRunner is in screener_utils.

    results = screener.screen_turtle_setups(ticker_list=tickers, time_frame="1d")

    assert len(results) > 0
    assert results[0]["ticker"] in tickers

@patch('option_auditor.common.screener_utils.yf.download')
def test_screen_darvas(mock_download):
    mock_download.side_effect = mock_yf_download
    tickers = ["AAPL"]
    results = screener.screen_darvas_box(ticker_list=tickers)
    assert isinstance(results, list)

@patch('option_auditor.common.screener_utils.yf.download')
def test_screen_ema(mock_download):
    mock_download.side_effect = mock_yf_download
    tickers = ["AAPL"]
    results = screener.screen_5_13_setups(ticker_list=tickers)
    assert isinstance(results, list)

def test_uk_euro_tickers():
    tickers = get_uk_euro_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 0
    # Check if suffixes are correct
    assert any(t.endswith(".L") or t.endswith(".PA") or t.endswith(".AS") for t in tickers)

def test_indian_tickers():
    tickers = get_indian_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 0
    assert any(t.endswith(".NS") for t in tickers)

@patch('option_auditor.common.data_utils.yf.download')
def test_prepare_data_for_ticker(mock_download):
    mock_df = pd.DataFrame({
        "Close": [100]*10,
        "High": [105]*10,
        "Low": [95]*10,
        "Open": [100]*10,
        "Volume": [1000]*10
    }, index=pd.date_range("2023-01-01", periods=10, freq="h"))
    mock_download.return_value = mock_df

    df = prepare_data_for_ticker("AAPL", None, "1h", "1d", "1h", None, True)
    assert not df.empty
    assert "Close" in df.columns

@patch('option_auditor.strategies.market.screen_tickers_helper')
def test_screen_sectors_coverage(mock_screen):
     mock_screen.return_value = [{"ticker": "TEST", "price": 100}]
     with patch.dict('option_auditor.strategies.market.SECTOR_NAMES', {"TEST": "Test Sector"}):
         results = screen_sectors()
         assert len(results) == 1
         assert results[0]["ticker"] == "TEST"

# Tests migrated from test_screener_coverage_new.py

@patch('option_auditor.strategies.bull_put.yf.Ticker')
def test_screen_bull_put_spreads_logic(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    mock_ticker.history.return_value = create_mock_df(periods=250, trend='up')

    today = datetime.today()
    dte_45 = today + timedelta(days=45)
    mock_ticker.options = [dte_45.strftime("%Y-%m-%d")]

    # Mock Option Chain
    mock_puts = pd.DataFrame({
        'strike': [190.0, 185.0, 180.0],
        'bid': [2.0, 1.0, 0.5],
        'ask': [2.2, 1.2, 0.7],
        'lastPrice': [2.1, 1.1, 0.6],
        'impliedVolatility': [0.2, 0.2, 0.2]
    })
    mock_chain = MagicMock()
    mock_chain.puts = mock_puts
    mock_ticker.option_chain.return_value = mock_chain

    # Correct place to patch _calculate_put_delta is in bull_put.py
    with patch('option_auditor.strategies.bull_put._calculate_put_delta') as mock_delta:
        def delta_side_effect(S, K, T, r, sigma):
            if K == 190.0: return -0.30
            if K == 185.0: return -0.20
            return -0.10
        mock_delta.side_effect = delta_side_effect

        results = screen_bull_put_spreads(["TEST"])
        assert len(results) == 1
        assert results[0]['ticker'] == "TEST"

@patch('option_auditor.common.screener_utils.yf.Ticker')
def test_screen_mms_ote_bearish(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker

    periods = 60
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='h')
    highs = np.full(periods, 95.0)
    lows = np.full(periods, 90.0)
    closes = np.full(periods, 92.0)

    # Peak
    highs[40] = 100.0
    lows[40] = 98.0
    # Displacement
    highs[45] = 92.0
    lows[45] = 90.0
    # FVG
    lows[43] = 96.0
    highs[45] = 92.0
    # Retracement
    closes[-1] = 97.0

    # MSS Logic helper
    highs[39] = 99.0
    highs[41] = 99.0
    lows[30] = 91.0 # Swing Low

    df = pd.DataFrame({
        'Open': closes, 'High': highs, 'Low': lows, 'Close': closes,
        'Volume': np.full(periods, 1000)
    }, index=dates)

    mock_ticker.history.return_value = df
    results = screen_mms_ote_setups(["BEAR"])
    assert isinstance(results, list)

def test_resolve_ticker():
    # resolve_ticker is in common/screener_utils
    from option_auditor.common.screener_utils import resolve_ticker, TICKER_NAMES

    with patch.dict(TICKER_NAMES, {"TEST": "Test Company", "UK.L": "UK Co"}):
        assert resolve_ticker("TEST") == "TEST"
        assert resolve_ticker("Test Company") == "TEST"
        assert resolve_ticker("UK") == "UK.L"

@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.hybrid.calculate_dominant_cycle')
def test_hybrid_strategy_branches(mock_cycle, mock_download):
    # Test "PERFECT BUY"
    periods = 200
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    closes = np.linspace(100, 200, periods)

    mock_cycle.return_value = (20.0, -0.9) # Bottom

    opens = closes - 1.0
    df = pd.DataFrame({'Close': closes, 'High': closes+5, 'Low': closes-5, 'Open': opens, 'Volume': 600000}, index=dates)
    mock_download.return_value = df

    results = screen_hybrid_strategy(["HYBRID"])
    assert len(results) == 1
    assert "PERFECT BUY" in results[0]['verdict']
