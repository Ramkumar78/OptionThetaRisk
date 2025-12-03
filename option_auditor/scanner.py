
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

def run_screener(iv_rank_threshold=30, rsi_threshold=50):
    """
    Scans the defined universe of liquid stocks/ETFs for candidates matching:
    1. Bullish Trend (Price > 50 SMA)
    2. RSI between 30 and rsi_threshold
    """

    # 1. Define Universe
    tickers = [
        "SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "XLE", "XLV", "XLF", "FXI", "EEM", # ETFs
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "AMD", "TSLA", "META", # Tech
        "JPM", "BAC", "C", "WFC", # Banks
        "KO", "PEP", "MCD", "SBUX", # Consumer
        "XOM", "CVX", "KMI", # Energy
        "PFE", "MRK", "JNJ", # Pharma
        "SOFI", "PLTR", "UBER", "F", "T" # Retail Favs
    ]

    results = []

    # Convert thresholds to correct types if they are strings
    try:
        rsi_threshold = float(rsi_threshold)
    except (ValueError, TypeError):
        rsi_threshold = 50.0

    # Batched download for performance
    # Using group_by='ticker' makes the returned DataFrame have a MultiIndex (Ticker, OHLC)
    # period='1y' to ensure enough data for SMA 50
    try:
        data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False, threads=True)
    except Exception as e:
        # Fallback to empty if download fails completely
        return []

    for symbol in tickers:
        try:
            # Extract dataframe for this symbol
            # yfinance with group_by='ticker' returns a MultiIndex column level 0 = Ticker
            # If only one ticker, it might be flat, but with list it's usually MultiIndex.

            if isinstance(data.columns, pd.MultiIndex):
                try:
                    df = data[symbol].copy()
                except KeyError:
                    # Symbol not found in data
                    continue
            else:
                # If for some reason it's flat (e.g. only 1 ticker in list effectively)
                df = data.copy()

            if df.empty:
                continue

            # Check for NaN in 'Close' which implies bad download for this ticker
            if df['Close'].isnull().all():
                continue

            # Drop rows with NaN in Close to clean up
            df = df.dropna(subset=['Close'])

            # 3. Calculate Indicators
            # RSI (14)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            # SMA (50)
            df['SMA_50'] = ta.sma(df['Close'], length=50)

            # Get latest values (last row)
            if df.empty:
                continue

            last_row = df.iloc[-1]
            current_price = last_row['Close']
            current_rsi = last_row['RSI']
            current_sma = last_row['SMA_50']

            # Check for NaN in indicators (e.g. not enough history)
            if pd.isna(current_price) or pd.isna(current_rsi) or pd.isna(current_sma):
                continue

            # 4. Apply "Thalaiva Rules"
            # Rule 1: Bullish Trend (Price > 50 SMA)
            trend = "BULLISH" if current_price > current_sma else "BEARISH"

            # Rule 2: The Dip (RSI between 30 and rsi_threshold)
            signal = "WAIT"
            if trend == "BULLISH":
                if 30 <= current_rsi <= rsi_threshold:
                    signal = "🟢 GREEN LIGHT"
                elif current_rsi > 70:
                    signal = "🔴 OVERBOUGHT"

            # Prepare result object
            if "GREEN" in signal:
                results.append({
                    "symbol": symbol,
                    "price": round(float(current_price), 2),
                    "rsi": round(float(current_rsi), 2),
                    "trend": trend,
                    "signal": signal,
                    "sma_50": round(float(current_sma), 2)
                })

        except Exception as e:
            # print(f"Error processing {symbol}: {e}")
            continue

    return results
