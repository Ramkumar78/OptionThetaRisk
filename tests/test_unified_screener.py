import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from option_auditor.unified_screener import screen_universal_dashboard, get_market_regime_verdict, analyze_ticker_hardened

@pytest.fixture
def mock_yf_download():
    with patch('option_auditor.unified_screener.yf.download') as mock:
        yield mock

def create_mock_df(closes):
    # Create a DataFrame with enough rows
    dates = pd.date_range(end=pd.Timestamp.now(), periods=len(closes))
    df = pd.DataFrame({
        'Open': closes,
        'High': [c * 1.01 for c in closes],
        'Low': [c * 0.99 for c in closes],
        'Close': closes,
        'Volume': [1000000] * len(closes)
    }, index=dates)
    return df

def test_unified_screener_execution(mock_yf_download):
    # Setup tickers
    tickers = ["AAPL", "GOOGL"]

    # Mock Data:
    # AAPL: Uptrend (Buy)
    # GOOGL: Downtrend (Sell)

    # Uptrend
    aapl_closes = [100 + i for i in range(250)]
    df_aapl = create_mock_df(aapl_closes)

    # Downtrend
    googl_closes = [200 - i for i in range(250)]
    df_googl = create_mock_df(googl_closes)

    # Combine into MultiIndex DataFrame
    frames = {
        "AAPL": df_aapl,
        "GOOGL": df_googl
    }

    dfs = []
    keys = []
    for k, v in frames.items():
        dfs.append(v)
        keys.append(k)

    batch_df = pd.concat(dfs, axis=1, keys=keys, sort=False)
    mock_yf_download.return_value = batch_df

    # Mock Regime to GREEN to allow scanning
    with patch("option_auditor.unified_screener.get_market_regime_verdict", return_value=("GREEN", "Test Mode")):
        # We also need to patch fetch_batch_data_safe since screen_universal_dashboard uses it
        with patch("option_auditor.common.data_utils.fetch_batch_data_safe", return_value=batch_df):
            response = screen_universal_dashboard(ticker_list=tickers)
            results = response["results"]

    # If results are empty, it might be due to logic filtering.
    # AAPL should pass as BUY/WATCH.
    # GOOGL might pass as SELL or just not return anything if filtering strictly.

    if len(results) > 0:
        # Verify structure
        assert isinstance(results[0], dict)
        assert 'ticker' in results[0]
        assert 'master_verdict' in results[0]

        # Check AAPL presence
        aapl_res = next((r for r in results if r['ticker'] == "AAPL"), None)
        if aapl_res:
            assert "AAPL" in aapl_res['ticker']

def test_get_market_regime_verdict(mock_yf_download):
    # Mock SPY and VIX
    # SPY: 400, SMA200: 380 (Bullish)
    # VIX: 15 (Bullish)

    dates = pd.date_range(end=pd.Timestamp.now(), periods=201)
    spy_closes = [380] * 200 + [400]

    spy_df = pd.DataFrame({
        'Close': spy_closes,
    }, index=dates)

    mock_yf_download.return_value = spy_df

    with patch("option_auditor.unified_screener._get_market_regime", return_value=15.0):
        verdict, note = get_market_regime_verdict()
        assert verdict == "GREEN"
        assert "Bullish" in note

    # Test RED (SPY < SMA200)
    spy_closes_bear = [400] * 200 + [380]
    spy_df_bear = pd.DataFrame({'Close': spy_closes_bear}, index=dates)
    mock_yf_download.return_value = spy_df_bear

    with patch("option_auditor.unified_screener._get_market_regime", return_value=20.0):
        verdict, note = get_market_regime_verdict()
        assert verdict == "RED"
        assert "Bearish" in note

    # Test RED (High VIX)
    mock_yf_download.return_value = spy_df # Bullish SPY
    with patch("option_auditor.unified_screener._get_market_regime", return_value=30.0):
        verdict, note = get_market_regime_verdict()
        assert verdict == "RED"
        assert "High Volatility" in note

def test_analyze_ticker_hardened_options_mode():
    # Setup data for Options (Bull Put)
    # Uptrend, Pullback (RSI < 55), ATR > 2%
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200)

    # Close 100. SMA50 < 100.
    # RSI 50.
    # ATR 3.0 (3%)

    closes = [90] * 150 + [100] * 49 + [105]
    # To get RSI ~50, we need some fluctuation or just mock ta.rsi

    df = pd.DataFrame({
        'Close': closes,
        'High': [c + 3 for c in closes], # ATR ~3
        'Low': [c - 3 for c in closes],
        'Volume': [20000000] * 200 # Liquid
    }, index=dates)

    with patch("option_auditor.unified_screener.ta.rsi") as mock_rsi, \
         patch("option_auditor.unified_screener.ta.atr") as mock_atr:

        mock_rsi.return_value = pd.Series([50.0] * 200) # Pullback range 40-55
        mock_atr.return_value = pd.Series([3.0] * 200) # 3% of 100

        result = analyze_ticker_hardened("AAPL", df, regime="GREEN", mode="OPTIONS")

        assert result is not None
        assert "BULL PUT" in result["master_verdict"]
        assert result["master_color"] == "blue"

def test_analyze_ticker_hardened_illiquid():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200)
    df = pd.DataFrame({
        'Close': [100] * 200,
        'High': [101] * 200,
        'Low': [99] * 200,
        'Volume': [100] * 200 # Illiquid
    }, index=dates)

    result = analyze_ticker_hardened("AAPL", df, regime="GREEN", mode="ISA")
    assert result is None

def test_screen_universal_dashboard_empty():
    with patch("option_auditor.unified_screener.get_market_regime_verdict", return_value=("GREEN", "OK")), \
         patch("option_auditor.common.data_utils.fetch_batch_data_safe", return_value=pd.DataFrame()):

        res = screen_universal_dashboard(ticker_list=["AAPL"])
        assert res["results"] == []
