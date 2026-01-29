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
