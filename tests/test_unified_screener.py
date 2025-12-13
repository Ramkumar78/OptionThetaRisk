import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from option_auditor.unified_screener import screen_universal_dashboard

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

    batch_df = pd.concat(dfs, axis=1, keys=keys)
    mock_yf_download.return_value = batch_df

    results = screen_universal_dashboard(ticker_list=tickers)

    assert len(results) == 2

    # Check AAPL
    aapl_res = next(r for r in results if r['ticker'] == "AAPL")
    # Should be at least 1 buy or watch from ISA/Turtle (Uptrend)
    # With a smooth linear uptrend, it might not be a 'Breakout' (High > Prev High might be true every day)
    # but could be 'Watch' if close to high.
    isa_sig = aapl_res['strategies']['isa']['signal']
    turtle_sig = aapl_res['strategies']['turtle']['signal']
    assert isa_sig in ["BUY", "WATCH", "HOLD", "ENTER LONG"] or turtle_sig in ["BUY", "WATCH", "HOLD"]
    assert "BUY" in aapl_res['master_verdict'] or "WATCH" in aapl_res['master_verdict']

    # Check GOOGL
    googl_res = next(r for r in results if r['ticker'] == "GOOGL")
    # Should be sell/avoid
    assert "SELL" in googl_res['master_verdict'] or "AVOID" in googl_res['master_verdict'] or "WAIT" in googl_res['master_verdict']
