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
        prices = np.linspace(price * 0.5, price, length)
    elif trend == "down":
        prices = np.linspace(price * 1.5, price, length)
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
    assert screener.regime == "NEUTRAL"

def test_check_market_regime_green(screener, mock_yf_download):
    # Mock SPY and VIX data
    dates = pd.date_range(periods=300, end="2023-01-01")

    # Construct MultiIndex DataFrame to simulate yf.download result
    # We need columns ('Close', 'SPY') and ('Close', '^VIX')
    # Because code does: yf.download(...)['Close']

    iterables = [['Close'], ['SPY', '^VIX']]
    columns = pd.MultiIndex.from_product(iterables, names=['Price', 'Ticker'])

    data = pd.DataFrame(index=dates, columns=columns)
    data[('Close', 'SPY')] = np.linspace(300, 400, 300) # Uptrend
    data[('Close', '^VIX')] = np.full(300, 15.0) # Low VIX

    # The code calls yf.download(...).
    # If we return this DF, doing ['Close'] on it works if 'Close' is level 0?
    # Actually yf.download returns columns as (Price, Ticker).
    # So df['Close'] returns a DF with columns (Ticker).
    # However, if I create it as above, df['Close'] works.

    # But wait, the code does: data = yf.download(...)['Close']
    # So my mock should return the full dataframe.

    # Let's verify pandas behavior for MultiIndex.
    # df['Close'] selects the level 0.

    mock_yf_download.return_value = data

    screener.check_market_regime()
    assert screener.regime == "GREEN"

def test_check_market_regime_yellow(screener, mock_yf_download):
    dates = pd.date_range(periods=300, end="2023-01-01")
    iterables = [['Close'], ['SPY', '^VIX']]
    columns = pd.MultiIndex.from_product(iterables, names=['Price', 'Ticker'])
    data = pd.DataFrame(index=dates, columns=columns)

    data[('Close', 'SPY')] = np.linspace(300, 400, 300) # Uptrend
    data[('Close', '^VIX')] = np.full(300, 22.0) # High VIX

    mock_yf_download.return_value = data

    screener.check_market_regime()
    assert screener.regime == "YELLOW"

def test_check_market_regime_red_price(screener, mock_yf_download):
    dates = pd.date_range(periods=300, end="2023-01-01")
    iterables = [['Close'], ['SPY', '^VIX']]
    columns = pd.MultiIndex.from_product(iterables, names=['Price', 'Ticker'])
    data = pd.DataFrame(index=dates, columns=columns)

    data[('Close', 'SPY')] = np.linspace(400, 300, 300) # Downtrend
    data[('Close', '^VIX')] = np.full(300, 15.0)

    mock_yf_download.return_value = data

    screener.check_market_regime()
    assert screener.regime == "RED"

def test_check_market_regime_red_panic(screener, mock_yf_download):
    dates = pd.date_range(periods=300, end="2023-01-01")
    iterables = [['Close'], ['SPY', '^VIX']]
    columns = pd.MultiIndex.from_product(iterables, names=['Price', 'Ticker'])
    data = pd.DataFrame(index=dates, columns=columns)

    data[('Close', 'SPY')] = np.linspace(300, 400, 300)
    data[('Close', '^VIX')] = np.full(300, 30.0) # Panic

    mock_yf_download.return_value = data

    screener.check_market_regime()
    assert screener.regime == "RED"

def test_physics_score(screener):
    # Test with a simple series
    series = pd.Series(np.linspace(10, 20, 100))
    score = screener._calculate_physics_score(series)
    assert score >= 0

    # Test with constant series (0 vol)
    series_const = pd.Series(np.full(100, 10))
    score_const = screener._calculate_physics_score(series_const)
    assert score_const == 0.0

def test_analyze_ticker_liquidity_fail(screener):
    # US Ticker with low volume
    df = create_mock_df(vol=500000) # Below 1M
    result = screener.analyze_ticker("AAPL", df)
    assert result is None

    # UK Ticker with low volume
    df_uk = create_mock_df(vol=100000) # Below 200k
    result = screener.analyze_ticker("BP.L", df_uk)
    assert result is None

def test_analyze_ticker_isa_buy_signal(screener):
    screener.regime = "GREEN"
    dates = pd.date_range(periods=300, end="2023-01-01")
    prices = np.linspace(100, 200, 300)

    df = pd.DataFrame({
        'Close': prices,
        'High': prices * 1.01,
        'Low': prices * 0.99,
        'Open': prices,
        'Volume': np.full(300, 2000000)
    }, index=dates)

    with patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch('option_auditor.master_screener.ta.atr') as mock_atr:

        mock_rsi.return_value = pd.Series(np.full(300, 60.0), index=dates)
        mock_atr.return_value = pd.Series(np.full(300, 2.0), index=dates)

        result = screener.analyze_ticker("AAPL", df)

        assert result is not None
        assert result['Type'] == "ISA_BUY"
        assert result['Setup'] == "Trend Leader"

def test_analyze_ticker_opt_sell_signal(screener):
    screener.regime = "GREEN"
    dates = pd.date_range(periods=300, end="2023-01-01")
    prices = np.linspace(100, 200, 300)
    prices[-10:] = prices[-10:] * 0.90

    df = pd.DataFrame({
        'Close': prices,
        'High': prices * 1.05,
        'Low': prices * 0.95,
        'Open': prices,
        'Volume': np.full(300, 2000000)
    }, index=dates)

    with patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch('option_auditor.master_screener.ta.atr') as mock_atr:

        mock_rsi.return_value = pd.Series(np.full(300, 40.0), index=dates)
        mock_atr.return_value = pd.Series(np.full(300, 5.0), index=dates)

        result = screener.analyze_ticker("AAPL", df)

        assert result is not None
        assert result['Type'] == "OPT_SELL"
        assert result['Setup'] == "Bull Put (High IV)"

def test_run_red_regime(screener, mock_yf_download, capsys):
    dates = pd.date_range(periods=300, end="2023-01-01")
    iterables = [['Close'], ['SPY', '^VIX']]
    columns = pd.MultiIndex.from_product(iterables, names=['Price', 'Ticker'])
    data = pd.DataFrame(index=dates, columns=columns)
    data[('Close', 'SPY')] = np.linspace(400, 300, 300) # Bear
    data[('Close', '^VIX')] = np.full(300, 15.0)

    mock_yf_download.return_value = data

    screener.run()

    captured = capsys.readouterr()
    assert "MARKET REGIME IS RED" in captured.out

def test_run_green_regime(screener, mock_yf_download, capsys):
    dates = pd.date_range(periods=300, end="2023-01-01")

    # Regime Data (MultiIndex)
    iterables = [['Close'], ['SPY', '^VIX']]
    columns = pd.MultiIndex.from_product(iterables, names=['Price', 'Ticker'])
    regime_data = pd.DataFrame(index=dates, columns=columns)
    regime_data[('Close', 'SPY')] = np.linspace(300, 400, 300)
    regime_data[('Close', '^VIX')] = np.full(300, 15.0)

    def side_effect(*args, **kwargs):
        arg0 = args[0] if args else kwargs.get('tickers')
        if isinstance(arg0, list) and "SPY" in arg0:
            return regime_data
        else:
            # Ticker Data: Dict of DataFrames or MultiIndex
            # If code uses `data[ticker]`, and group_by='ticker' is used,
            # yf returns a DF with top level columns as Tickers.

            # Let's verify what the code does:
            # data = yf.download(chunk, ..., group_by='ticker')
            # df = data[ticker]

            # So we return a DF with Tickers as top level columns.

            # Ticker columns: (Ticker, Price)
            # e.g. ('AAPL', 'Close')

            # Let's create a MultiIndex DF
            cols = pd.MultiIndex.from_product([screener.all_tickers, ['Open', 'High', 'Low', 'Close', 'Volume']])
            df_tickers = pd.DataFrame(np.random.randn(300, len(cols)), index=dates, columns=cols)

            # Populate with valid data to pass hygiene
            for t in screener.all_tickers:
                df_tickers[(t, 'Volume')] = 2000000
                df_tickers[(t, 'Close')] = 100
                df_tickers[(t, 'High')] = 105
                df_tickers[(t, 'Low')] = 95
                df_tickers[(t, 'Open')] = 100

            return df_tickers

    mock_yf_download.side_effect = side_effect

    with patch.object(screener, 'analyze_ticker') as mock_analyze:
        mock_analyze.return_value = {
            "Ticker": "AAPL",
            "Price": 100,
            "Regime": "GREEN",
            "Type": "ISA_BUY",
            "Setup": "Test Setup",
            "Stop Loss": 90,
            "Action": "Buy",
            "Metrics": "Test",
            "Warning": ""
        }

        screener.run()

    captured = capsys.readouterr()
    assert "SCANNING" in captured.out
    assert "AAPL" in captured.out
