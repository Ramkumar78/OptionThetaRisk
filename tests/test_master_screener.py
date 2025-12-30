import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.master_screener import MasterScreener

@pytest.fixture
def mock_yf_download():
    with patch('option_auditor.master_screener.yf.download') as mock:
        yield mock

@pytest.fixture
def screener():
    return MasterScreener(["AAPL"], ["BP.L"])

def create_mock_df(length=300, price=100.0, trend="flat", vol=2000000):
    """Helper to create a DataFrame with OHLCV data."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

    if trend == "up":
        prices = np.linspace(price * 0.8, price * 1.2, length)
    elif trend == "down":
        prices = np.linspace(price * 1.2, price * 0.8, length)
    else:
        prices = np.full(length, price)

    # Add some noise
    prices += np.random.normal(0, price * 0.01, length)

    df = pd.DataFrame({
        'Open': prices,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.full(length, vol)
    }, index=dates)

    return df

def test_initialization(screener):
    assert "AAPL" in screener.tickers_us
    assert "BP.L" in screener.tickers_uk
    assert screener.market_regime == "NEUTRAL"

def test_fetch_market_regime_bullish(screener, mock_yf_download):
    # Mock SPY and VIX data
    dates = pd.date_range(periods=600, end="2023-01-01") # 2 years approx

    # Create DataFrame structure matching yf.download result
    data = pd.DataFrame(index=dates)

    # SPY Data (Bullish: Price > SMA)
    spy_prices = np.linspace(300, 400, 600)
    data[('Close', 'SPY')] = spy_prices

    # VIX Data (Low)
    data[('Close', '^VIX')] = np.full(600, 15.0)

    # Since the code checks if isinstance(data.columns, pd.MultiIndex), we need to ensure that.
    data.columns = pd.MultiIndex.from_tuples(data.columns)

    mock_yf_download.return_value = data

    screener._fetch_market_regime()
    assert screener.market_regime == "BULLISH"

def test_fetch_market_regime_bearish_vix(screener, mock_yf_download):
    dates = pd.date_range(periods=600, end="2023-01-01")
    data = pd.DataFrame(index=dates)

    # SPY Data (Uptrend but High VIX panic)
    spy_prices = np.linspace(300, 400, 600)
    data[('Close', 'SPY')] = spy_prices

    # VIX Data (Panic)
    data[('Close', '^VIX')] = np.full(600, 30.0)

    data.columns = pd.MultiIndex.from_tuples(data.columns)
    mock_yf_download.return_value = data

    screener._fetch_market_regime()
    assert screener.market_regime == "BEARISH"

def test_fetch_market_regime_bearish_trend(screener, mock_yf_download):
    dates = pd.date_range(periods=600, end="2023-01-01")
    data = pd.DataFrame(index=dates)

    # SPY Data (Downtrend: Price < SMA)
    spy_prices = np.linspace(400, 300, 600)
    data[('Close', 'SPY')] = spy_prices

    # VIX Data (High)
    data[('Close', '^VIX')] = np.full(600, 26.0)

    data.columns = pd.MultiIndex.from_tuples(data.columns)
    mock_yf_download.return_value = data

    screener._fetch_market_regime()
    assert screener.market_regime == "BEARISH"

def test_fetch_market_regime_cautious(screener, mock_yf_download):
    dates = pd.date_range(periods=600, end="2023-01-01")
    data = pd.DataFrame(index=dates)

    # SPY Data (Downtrend)
    spy_prices = np.linspace(400, 300, 600)
    data[('Close', 'SPY')] = spy_prices

    # VIX Data (Low - mixed signal)
    data[('Close', '^VIX')] = np.full(600, 20.0)

    data.columns = pd.MultiIndex.from_tuples(data.columns)
    mock_yf_download.return_value = data

    screener._fetch_market_regime()
    assert screener.market_regime == "CAUTIOUS"

def test_process_stock_liquidity_fail_us(screener):
    # US Ticker with low volume
    df = create_mock_df(vol=500000) # Below 1M
    result = screener._process_stock("AAPL", df)
    assert result is None

def test_process_stock_liquidity_fail_uk(screener):
    # UK Ticker with low volume
    df_uk = create_mock_df(vol=100000) # Below 200k
    result = screener._process_stock("BP.L", df_uk)
    assert result is None

def test_process_stock_isa_buy(screener):
    # Setup for ISA Buy: Uptrend, Near Highs, RSI 50-75
    length = 300
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

    # Create uptrend price series
    # Start at 100, End at 150
    prices = np.linspace(100, 150, length)

    # Make sure we are near highs (last price is high)
    # And RSI is moderate (handled by mocking ta.rsi)

    df = pd.DataFrame({
        'Open': prices,
        'High': prices, # High is close to Close
        'Low': prices * 0.99,
        'Close': prices,
        'Volume': np.full(length, 2000000)
    }, index=dates)

    with patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch('option_auditor.master_screener.ta.atr') as mock_atr:

        # Mock RSI to be 60 (Sweet spot)
        mock_rsi.return_value = pd.Series(np.full(length, 60.0), index=dates)
        # Mock ATR
        mock_atr.return_value = pd.Series(np.full(length, 2.0), index=dates)

        result = screener._process_stock("AAPL", df)

        assert result is not None
        assert result['Type'] == "ISA_BUY"
        assert result['Setup'] == "Trend Leader"

def test_process_stock_opt_sell(screener):
    # Setup for Opt Sell: US, Uptrend, Oversold (RSI < 55), High Vol
    length = 300
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

    # Uptrend but recent dip
    prices = np.linspace(100, 150, length)

    df = pd.DataFrame({
        'Open': prices,
        'High': prices,
        'Low': prices * 0.95,
        'Close': prices,
        'Volume': np.full(length, 2000000)
    }, index=dates)

    with patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch('option_auditor.master_screener.ta.atr') as mock_atr:

        # Mock RSI to be 40 (Oversold)
        mock_rsi.return_value = pd.Series(np.full(length, 40.0), index=dates)
        # Mock ATR to be high (> 2% of price 150 -> > 3.0)
        mock_atr.return_value = pd.Series(np.full(length, 5.0), index=dates)

        result = screener._process_stock("AAPL", df)

        assert result is not None
        assert result['Type'] == "OPT_SELL"
        assert result['Setup'] == "High Vol Put"

def test_run_bearish_regime(screener, mock_yf_download):
    # Mock Market Regime as Bearish via _fetch_market_regime logic
    dates = pd.date_range(periods=600, end="2023-01-01")
    data = pd.DataFrame(index=dates)

    # Bearish signals
    data[('Close', 'SPY')] = np.linspace(400, 300, 600)
    data[('Close', '^VIX')] = np.full(600, 30.0)

    data.columns = pd.MultiIndex.from_tuples(data.columns)
    mock_yf_download.return_value = data

    results = screener.run()

    assert len(results) == 1
    assert results[0]['Ticker'] == "MARKET"
    assert results[0]['Type'] == "WARNING"

def test_run_normal(screener, mock_yf_download):
    # 1. First call is for Market Regime (SPY, VIX)
    # 2. Second call is for Tickers (AAPL, BP.L)

    dates = pd.date_range(periods=600, end="2023-01-01")

    # Regime Data (Bullish)
    regime_data = pd.DataFrame(index=dates)
    regime_data[('Close', 'SPY')] = np.linspace(300, 400, 600)
    regime_data[('Close', '^VIX')] = np.full(600, 15.0)
    regime_data.columns = pd.MultiIndex.from_tuples(regime_data.columns)

    # Ticker Data
    # MultiIndex with (Ticker, OHLCV)
    # Tickers are AAPL and BP.L
    # Level 0 = Ticker, Level 1 = Price Type
    # Note: yf.download(group_by='ticker') returns Level 0 = Ticker, Level 1 = Price Type

    iterables = [['AAPL', 'BP.L'], ['Open', 'High', 'Low', 'Close', 'Volume']]
    ticker_cols = pd.MultiIndex.from_product(iterables, names=['Ticker', 'Price'])
    ticker_data = pd.DataFrame(index=dates, columns=ticker_cols)

    # Fill AAPL (ISA Buy)
    prices = np.linspace(100, 150, 600)
    ticker_data[('AAPL', 'Close')] = prices
    ticker_data[('AAPL', 'High')] = prices
    ticker_data[('AAPL', 'Low')] = prices * 0.99
    ticker_data[('AAPL', 'Open')] = prices
    ticker_data[('AAPL', 'Volume')] = 2000000

    # Fill BP.L (Low volume -> Fail)
    ticker_data[('BP.L', 'Close')] = prices
    ticker_data[('BP.L', 'High')] = prices
    ticker_data[('BP.L', 'Low')] = prices
    ticker_data[('BP.L', 'Open')] = prices
    ticker_data[('BP.L', 'Volume')] = 100000 # Fail

    def side_effect(*args, **kwargs):
        # Determine if this is the regime check or the ticker check
        # Arg 0 usually tickers list
        tickers = args[0] if args else kwargs.get('tickers')

        if "SPY" in tickers:
            return regime_data
        else:
            return ticker_data

    mock_yf_download.side_effect = side_effect

    with patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch('option_auditor.master_screener.ta.atr') as mock_atr:

        mock_rsi.return_value = pd.Series(np.full(600, 60.0), index=dates)
        mock_atr.return_value = pd.Series(np.full(600, 2.0), index=dates)

        results = screener.run()

        assert len(results) == 1
        assert results[0]['Ticker'] == "AAPL"
        assert results[0]['Type'] == "ISA_BUY"

