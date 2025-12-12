
import pandas as pd
import pandas_ta as ta
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to import option_auditor
sys.path.append(os.getcwd())

from option_auditor.screener import screen_trend_followers_isa

def mock_yfinance_download(*args, **kwargs):
    # Create a mock dataframe with necessary columns
    # We need 200+ rows for SMA 200
    dates = pd.date_range(start="2023-01-01", periods=300, freq="D")
    data = {
        "Open": [100.0] * 300,
        "High": [105.0] * 300,
        "Low": [95.0] * 300,
        "Close": [100.0] * 300,
        "Volume": [1000000] * 300
    }

    # Make the last close price higher to trigger a trend
    data["Close"][-1] = 120.0 # Above SMA 200 (~100)
    data["High"][-1] = 125.0
    data["Low"][-1] = 115.0

    # Simulate a breakout: Current High > 50-day High
    # We need to vary the data slightly so rolling calculations work nicely
    import numpy as np
    data["Close"] = np.linspace(100, 150, 300) # Uptrend
    data["High"] = data["Close"] + 5
    data["Low"] = data["Close"] - 5

    df = pd.DataFrame(data, index=dates)

    # Structure for batch download (MultiIndex if group_by='ticker')
    # But screen_trend_followers_isa handles single or batch.
    # If we pass a list, it expects batch.

    # Create a MultiIndex DataFrame for batch result
    ticker = "TEST"
    columns = pd.MultiIndex.from_product([[ticker], df.columns])
    df_batch = pd.DataFrame(df.values, index=df.index, columns=columns)

    return df_batch

def mock_fetch_retry(*args, **kwargs):
    # Same as above but for single ticker fallback
    dates = pd.date_range(start="2023-01-01", periods=300, freq="D")
    import numpy as np
    close = np.linspace(100, 150, 300)
    data = {
        "Open": close,
        "High": close + 5,
        "Low": close - 5,
        "Close": close,
        "Volume": [1000000] * 300
    }
    df = pd.DataFrame(data, index=dates)
    return df

@patch("yfinance.download", side_effect=mock_yfinance_download)
@patch("option_auditor.screener.fetch_data_with_retry", side_effect=mock_fetch_retry)
def run_test(mock_fetch, mock_download):
    print("Running screen_trend_followers_isa...")
    results = screen_trend_followers_isa(ticker_list=["TEST"])

    if not results:
        print("No results returned.")
    else:
        print(f"Results found: {len(results)}")
        first = results[0]
        print("Keys in result:", first.keys())
        print("First result:", first)

if __name__ == "__main__":
    run_test()
