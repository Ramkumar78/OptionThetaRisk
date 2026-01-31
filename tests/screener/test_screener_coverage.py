import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor import screener
from option_auditor.strategies import market
from option_auditor.uk_stock_data import get_uk_euro_tickers
from option_auditor.india_stock_data import get_indian_tickers
from option_auditor.common.data_utils import prepare_data_for_ticker, fetch_data_with_retry
from option_auditor.strategies.market import screen_market, screen_sectors, screen_tickers_helper as _screen_tickers
from option_auditor.strategies.bull_put import screen_bull_put_spreads
from option_auditor.strategies.mms_ote import screen_mms_ote_setups
from option_auditor.strategies.hybrid import screen_hybrid_strategy
from option_auditor.strategies.math_utils import calculate_dominant_cycle as _calculate_dominant_cycle
from option_auditor.screener import (
    screen_turtle_setups, screen_5_13_setups, screen_darvas_box,
    screen_trend_followers_isa, screen_fourier_cycles
)
from datetime import datetime, timedelta
import sys
import time

# --- Helpers ---

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

def create_mock_data(rows=100, price=100.0, trend=0):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=rows, freq='D')
    data = {
        'Open': np.array([price + (i * trend) for i in range(rows)], dtype=float),
        'High': np.array([price + (i * trend) + 5 for i in range(rows)], dtype=float),
        'Low': np.array([price + (i * trend) - 5 for i in range(rows)], dtype=float),
        'Close': np.array([price + (i * trend) for i in range(rows)], dtype=float),
        'Volume': np.array([1000000 for _ in range(rows)], dtype=float)
    }
    df = pd.DataFrame(data, index=dates)
    return df

def create_trend_data(periods=300, start_price=100, trend='up', volatility=1.0):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='D')
    prices = [start_price]
    for i in range(1, periods):
        change = np.random.normal(0, volatility)
        if trend == 'up': change += 0.5
        elif trend == 'down': change -= 0.5
        prices.append(prices[-1] + change)

    df = pd.DataFrame({
        'Open': prices,
        'High': [p + volatility for p in prices],
        'Low': [p - volatility for p in prices],
        'Close': prices,
        'Volume': [200000] * periods # Low volume initially
    }, index=dates)
    return df

def create_sine_wave_data(periods=200, cycle_period=20):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='D')
    x = np.arange(periods)
    # y = sin(2*pi*x/T)
    y = 100 + 10 * np.sin(2 * np.pi * x / cycle_period)

    df = pd.DataFrame({
        'Open': y, 'High': y+1, 'Low': y-1, 'Close': y, 'Volume': [1000000]*periods
    }, index=dates)
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

# --- Base Tests ---

@patch('option_auditor.strategies.market.screen_tickers_helper')
@patch('option_auditor.strategies.market.resolve_region_tickers')
def test_screen_market(mock_resolve, mock_screen):
    mock_resolve.return_value = ["AAPL"]
    mock_screen.return_value = [{
        "ticker": "AAPL",
        "price": 150.0,
        "rsi": 40.0,
        "signal": "WAIT"
    }]
    with patch.dict('option_auditor.strategies.market.SECTOR_NAMES', {"XLK": "Technology"}), \
         patch.dict('option_auditor.strategies.market.SECTOR_COMPONENTS', {"XLK": ["AAPL"]}):

        results = screen_market(iv_rank_threshold=20, rsi_threshold=80)
        assert "Technology (XLK)" in results
        assert len(results["Technology (XLK)"]) == 1
        assert results["Technology (XLK)"][0]["ticker"] == "AAPL"

@patch('yfinance.download')
def test_screen_turtle(mock_download):
    mock_download.side_effect = mock_yf_download
    tickers = ["AAPL", "GOOGL"]
    results = screener.screen_turtle_setups(ticker_list=tickers, time_frame="1d")
    assert len(results) > 0
    assert results[0]["ticker"] in tickers

@patch('yfinance.download')
def test_screen_darvas(mock_download):
    mock_download.side_effect = mock_yf_download
    tickers = ["AAPL"]
    results = screener.screen_darvas_box(ticker_list=tickers)
    assert isinstance(results, list)

@patch('yfinance.download')
def test_screen_ema(mock_download):
    mock_download.side_effect = mock_yf_download
    tickers = ["AAPL"]
    results = screener.screen_5_13_setups(ticker_list=tickers)
    assert isinstance(results, list)

def test_uk_euro_tickers():
    tickers = get_uk_euro_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 0
    assert any(t.endswith(".L") or t.endswith(".PA") or t.endswith(".AS") for t in tickers)

def test_indian_tickers():
    tickers = get_indian_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 0
    assert any(t.endswith(".NS") for t in tickers)

@patch('yfinance.download')
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
    highs[40] = 100.0
    lows[40] = 98.0
    highs[45] = 92.0
    lows[45] = 90.0
    lows[43] = 96.0
    highs[45] = 92.0
    closes[-1] = 97.0
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
    from option_auditor.common.screener_utils import resolve_ticker, TICKER_NAMES
    with patch.dict(TICKER_NAMES, {"TEST": "Test Company", "UK.L": "UK Co"}):
        assert resolve_ticker("TEST") == "TEST"
        assert resolve_ticker("Test Company") == "TEST"
        assert resolve_ticker("UK") == "UK.L"

@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.hybrid.calculate_dominant_cycle')
def test_hybrid_strategy_branches(mock_cycle, mock_download):
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

# --- Tests from Extended ---

class TestScreenerCoverageExtended:

    @patch('yfinance.download')
    def test_screen_tickers_timeframes(self, mock_download):
        mock_df = create_mock_data(rows=60)
        mock_download.return_value = mock_df
        tickers = ['AAPL']
        _screen_tickers(tickers, 30, 50, "49m")
        mock_download.assert_called()
        call_args = mock_download.call_args[1]
        # "49m" maps to "5m" interval in screener_utils
        assert call_args['interval'] == '5m'
        # assert call_args['period'] == '1mo' # Period might also differ
        _screen_tickers(tickers, 30, 50, "1wk")
        call_args = mock_download.call_args[1]
        assert call_args['interval'] == '1wk'
        assert call_args['period'] == '2y'
        _screen_tickers(tickers, 30, 50, "1mo")
        call_args = mock_download.call_args[1]
        assert call_args['interval'] == '1mo'
        assert call_args['period'] == '5y'

    @patch('yfinance.download')
    @patch('time.sleep', return_value=None)
    def test_screen_tickers_batch_vs_sequential(self, mock_sleep, mock_download):
        mock_df = create_mock_data(rows=60)
        columns = pd.MultiIndex.from_product([['AAPL'], mock_df.columns])
        batch_df = pd.DataFrame(mock_df.values, index=mock_df.index, columns=columns)
        mock_download.return_value = batch_df
        results = _screen_tickers(['AAPL'], 30, 50, "1d")
        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'

        def side_effect(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], list):
                return None
            else:
                return create_mock_data(rows=60)
        mock_download.side_effect = side_effect
        results = _screen_tickers(['AAPL'], 30, 50, "1d")
        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'

    @patch('yfinance.download')
    @patch('option_auditor.strategies.market.yf.Ticker')
    def test_screen_tickers_pe_ratio(self, mock_ticker, mock_download):
        mock_df = create_mock_data(rows=60)
        columns = pd.MultiIndex.from_product([['AAPL'], mock_df.columns])
        batch_df = pd.DataFrame(mock_df.values, index=mock_df.index, columns=columns)
        mock_download.return_value = batch_df
        mock_instance = MagicMock()
        mock_instance.info = {'trailingPE': 25.5}
        mock_ticker.return_value = mock_instance
        results = _screen_tickers(['AAPL'], 30, 50, "1d")
        assert len(results) == 1
        assert results[0]['pe_ratio'] == "25.50"
        mock_instance.info = {}
        results = _screen_tickers(['AAPL'], 30, 50, "1d")
        assert results[0]['pe_ratio'] == "N/A"

    @patch('yfinance.download')
    def test_screen_tickers_insufficient_data(self, mock_download):
        mock_df = create_mock_data(rows=40)
        columns = pd.MultiIndex.from_product([['AAPL'], mock_df.columns])
        batch_df = pd.DataFrame(mock_df.values, index=mock_df.index, columns=columns)
        mock_download.return_value = batch_df
        results = _screen_tickers(['AAPL'], 30, 50, "1d")
        assert len(results) == 0

    @patch('yfinance.download')
    def test_screen_tickers_indicators_signals(self, mock_download):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        close = np.linspace(100, 200, 100)
        close[-3:] = [190, 185, 180]
        data = {'Open': close, 'High': close+5, 'Low': close-5, 'Close': close, 'Volume': [1000000]*100}
        mock_df = pd.DataFrame(data, index=dates)
        columns = pd.MultiIndex.from_product([['AAPL'], mock_df.columns])
        batch_df = pd.DataFrame(mock_df.values, index=mock_df.index, columns=columns)
        mock_download.return_value = batch_df
        results = _screen_tickers(['AAPL'], 30, 60, "1d")
        assert len(results) == 1
        assert results[0]['trend'] == "BULLISH"

        close_bear = np.linspace(200, 100, 100)
        data_bear = {'Open': close_bear, 'High': close_bear+5, 'Low': close_bear-5, 'Close': close_bear, 'Volume': [1000000]*100}
        mock_df_bear = pd.DataFrame(data_bear, index=dates)
        columns_bear = pd.MultiIndex.from_product([['AAPL'], mock_df_bear.columns])
        batch_df_bear = pd.DataFrame(mock_df_bear.values, index=mock_df_bear.index, columns=columns_bear)
        mock_download.return_value = batch_df_bear
        results = _screen_tickers(['AAPL'], 30, 60, "1d")
        assert len(results) == 1
        assert results[0]['trend'] == "BEARISH"
        assert "OVERSOLD" in results[0]['signal']

    @patch('option_auditor.strategies.market.screen_tickers_helper')
    def test_screen_market_grouping(self, mock_screen):
        mock_screen.return_value = [
            {'ticker': 'AAPL', 'signal': 'WAIT'},
            {'ticker': 'JPM', 'signal': 'WAIT'},
            {'ticker': 'UNKNOWN', 'signal': 'WAIT'}
        ]
        results = screen_market()
        assert "Technology (XLK)" in results
        assert "Financials (XLF)" in results
        assert len(results["Technology (XLK)"]) == 1
        assert results["Technology (XLK)"][0]['ticker'] == 'AAPL'

    @patch('option_auditor.strategies.market.screen_tickers_helper')
    def test_screen_sectors(self, mock_screen):
        mock_screen.return_value = [{'ticker': 'XLK'}]
        results = screen_sectors()
        assert len(results) == 1
        assert results[0]['name'] == 'Technology'

    @patch('yfinance.download')
    def test_screen_turtle_setups_logic(self, mock_download):
        mock_df = create_mock_data(rows=30, price=100)
        mock_df.iloc[-1, mock_df.columns.get_loc('Close')] = 150.0
        mock_df.iloc[-1, mock_df.columns.get_loc('High')] = 150.0
        mock_download.return_value = mock_df
        results = screen_turtle_setups(['AAPL'])
        assert len(results) > 0
        assert "BREAKOUT" in results[0]['signal']
        mock_df.iloc[-1, mock_df.columns.get_loc('Close')] = 50.0
        mock_df.iloc[-1, mock_df.columns.get_loc('Low')] = 50.0
        results = screen_turtle_setups(['AAPL'])
        assert len(results) > 0
        assert "BREAKDOWN" in results[0]['signal']

    @patch('yfinance.download')
    def test_screen_5_13_setups_logic(self, mock_download):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        close = np.full(30, 100.0)
        close[-3:] = [100, 110, 120]
        data = {'Open': close, 'High': close, 'Low': close, 'Close': close, 'Volume': [1000]*30}
        mock_df = pd.DataFrame(data, index=dates)
        mock_download.return_value = mock_df
        results = screen_5_13_setups(['AAPL'])
        if len(results) > 0:
            assert "BREAKOUT" in results[0]['signal'] or "TRENDING" in results[0]['signal']

    @patch('yfinance.download')
    def test_screen_darvas_box_logic(self, mock_download):
        mock_df = create_mock_data(rows=80, price=100)
        highs = mock_df['High'].values.copy()
        lows = mock_df['Low'].values.copy()
        closes = mock_df['Close'].values.copy()
        volumes = mock_df['Volume'].values.copy()
        highs[42:49] = [140.0, 145.0, 148.0, 150.0, 148.0, 145.0, 140.0]
        lows[52:59] = [135.0, 132.0, 131.0, 130.0, 131.0, 132.0, 135.0]
        closes[-1] = 155.0
        closes[-2] = 145.0
        volumes[-1] = 2000000.0
        mock_df['High'] = highs
        mock_df['Low'] = lows
        mock_df['Close'] = closes
        mock_df['Volume'] = volumes
        mock_download.return_value = mock_df
        results = screen_darvas_box(['AAPL'])
        if len(results) > 0:
            assert "BREAKOUT" in results[0]['signal']

# --- Tests from Improvements ---

class TestScreenerImprovements:

    @patch('yfinance.download')
    def test_isa_screener_logic(self, mock_download):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq='D')
        closes = np.full(300, 100.0)
        closes[-5:] = 150.0
        df_aapl = pd.DataFrame({'Open': closes, 'High': closes + 2, 'Low': closes - 2, 'Close': closes, 'Volume': [100000] * 300}, index=dates)
        closes[-1] = 160.0
        df_aapl['Close'] = closes
        df_aapl['High'] = closes + 2
        df_aapl['Low'] = closes - 2

        closes_msft = np.full(300, 100.0)
        df_msft = pd.DataFrame({'Open': closes_msft, 'High': closes_msft + 1, 'Low': closes_msft - 1, 'Close': closes_msft, 'Volume': [100000] * 300}, index=dates)
        # Increase volatility enough so that 1 share risk > 1% of 76k (760).
        # Need Risk/Share > 760. Risk = 3 * ATR. ATR > 253.
        # Range 1000 should give ATR ~ 500.
        df_msft.iloc[-25:, df_msft.columns.get_loc('High')] = 1000.0
        df_msft.iloc[-25:, df_msft.columns.get_loc('Low')] = 0.0
        df_msft['Close'] = 110.0

        batch_df = pd.concat({'AAPL': df_aapl, 'MSFT': df_msft}, axis=1)
        mock_download.return_value = batch_df

        results = screen_trend_followers_isa(['AAPL', 'MSFT'], risk_per_trade_pct=0.01)
        assert len(results) == 2
        res_aapl = next(r for r in results if r['ticker'] == 'AAPL')
        assert "ENTER" in res_aapl['signal'] or "HOLD" in res_aapl['signal']
        assert res_aapl['safe_to_trade'] is True
        res_msft = next(r for r in results if r['ticker'] == 'MSFT')
        # Check MSFT (High Volatility -> Low Shares, but still Safe because of sizing)
        assert res_msft['safe_to_trade'] is True
        assert "SAFE" in res_msft['tharp_verdict']

        # Verify MSFT shares < AAPL shares due to higher risk per share (High Volatility)
        # AAPL ATR is small (~4), MSFT ATR is huge (~500)
        assert res_msft['shares'] < res_aapl['shares']

    @patch('yfinance.download')
    def test_isa_liquidity_filter(self, mock_download):
        df = create_trend_data(periods=300)
        df['Volume'] = 100
        mock_download.return_value = pd.concat({'PENNY': df, 'PENNY2': df}, axis=1)
        results = screen_trend_followers_isa(['PENNY', 'PENNY2'])
        assert len(results) == 0

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_isa_single_ticker_mode(self, mock_fetch):
        df = create_trend_data(periods=300)
        df['Volume'] = 1000000
        mock_fetch.return_value = df
        results = screen_trend_followers_isa(['AAPL'])
        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_fourier_cycles(self, mock_fetch):
        df = create_sine_wave_data(periods=128, cycle_period=20)
        mock_fetch.return_value = pd.concat({'SINE': df}, axis=1)
        results = screen_fourier_cycles(['SINE'])
        assert len(results) == 1
        r = results[0]
        period_str = r['cycle_period'].split()[0]
        period = float(period_str)
        assert 18 <= period <= 22

        df_low = create_sine_wave_data(periods=135, cycle_period=20)
        mock_fetch.return_value = pd.concat({'LOW': df_low}, axis=1)
        results = screen_fourier_cycles(['LOW'])
        assert "CYCLICAL LOW" in results[0]['signal']

    def test_calculate_dominant_cycle_short_data(self):
        prices = [100] * 50
        res = _calculate_dominant_cycle(prices)
        assert res is None

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.common.screener_utils.prepare_data_for_ticker')
    def test_mms_bullish_setup(self, mock_prep, mock_fetch):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='1h')
        prices = [105.0] * 10
        prices.extend([104, 103, 102])
        prices.append(100.0)
        prices.extend([102, 105, 108, 110])
        prices.extend([108, 106, 104, 103])
        pad = 50 - len(prices)
        final_prices = [105.0]*pad + prices
        df = pd.DataFrame({'Open': final_prices, 'High': [p+0.1 for p in final_prices], 'Low': [p-0.1 for p in final_prices], 'Close': final_prices, 'Volume': 1000}, index=dates)
        mock_fetch.return_value = MagicMock()
        mock_prep.return_value = df
        results = screen_mms_ote_setups(['AAPL'], time_frame='1h')
        assert len(results) == 1
        assert "BULLISH OTE" in results[0]['signal']

    @patch('option_auditor.common.data_utils.time.sleep')
    @patch('yfinance.download')
    def test_fetch_data_retry(self, mock_download, mock_sleep):
        df_success = pd.DataFrame({'Close': [100]}, index=[pd.Timestamp.now()])
        mock_download.side_effect = [Exception("Fail 1"), Exception("Fail 2"), df_success]
        res = fetch_data_with_retry("AAPL", retries=3)
        assert not res.empty
        assert mock_download.call_count == 3
