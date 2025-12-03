import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def screen_market(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0) -> list:
    """
    Screens the market for stocks with Bullish Trend and RSI < rsi_threshold.
    Note: IV Rank check is skipped as it's hard to get free via yfinance.

    Args:
        iv_rank_threshold: Minimum IV Rank (currently unused/manual check).
        rsi_threshold: Maximum RSI value for "Green Light".

    Returns:
        List of dictionaries containing ticker details.
    """
    try:
        import pandas_ta as ta
    except ImportError as e:
        raise ImportError("The 'pandas_ta' library is required for the screener. Please install it with 'pip install pandas_ta'.") from e

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

    for symbol in tickers:
        try:
            # 2. Get Data (1 Year of Daily Data)
            # Use progress=False to avoid cluttering stdout
            df = yf.download(symbol, period="1y", interval="1d", progress=False)

            if df.empty:
                continue

            # Flatten multi-index columns if present (yfinance update)
            if isinstance(df.columns, pd.MultiIndex):
                # We expect columns like ('Close', 'AAPL') or just 'Close'
                # If multi-index, we need to handle it.
                # yfinance>=0.2 usually returns multiindex if multiple tickers,
                # but single ticker might also be multiindex depending on version or params.
                # Here we download one by one, so usually it is single level or (Price, Ticker).
                # Let's try to standardize.
                try:
                    df.columns = df.columns.get_level_values(0)
                except Exception:
                    pass

            # 3. Calculate Indicators
            # RSI (14)
            # Ensure we have enough data
            if len(df) < 50:
                continue

            rsi_series = ta.rsi(df['Close'], length=14)
            if rsi_series is None:
                continue
            df['RSI'] = rsi_series

            # SMA (50)
            sma_series = ta.sma(df['Close'], length=50)
            if sma_series is None:
                continue
            df['SMA_50'] = sma_series

            # Get latest values
            current_price = float(df['Close'].iloc[-1])
            current_rsi = float(df['RSI'].iloc[-1])
            current_sma = float(df['SMA_50'].iloc[-1])

            # 4. Apply Rules
            # Rule 1: Bullish Trend (Price > 50 SMA)
            trend = "BULLISH" if current_price > current_sma else "BEARISH"

            # Rule 2: The Dip (RSI between 30 and rsi_threshold)
            # We want oversold but in an uptrend.
            signal = "WAIT"
            is_green = False

            if trend == "BULLISH":
                # User asked for "RSI less than field".
                # The original script had `30 <= current_rsi <= 50`.
                # If user sets rsi_threshold, we use `30 <= current_rsi <= rsi_threshold`.
                if 30 <= current_rsi <= rsi_threshold:
                    signal = "🟢 GREEN LIGHT (Buy Dip)"
                    is_green = True
                elif current_rsi > 70:
                    signal = "🔴 OVERBOUGHT"

            results.append({
                "ticker": symbol,
                "price": current_price,
                "rsi": current_rsi,
                "sma_50": current_sma,
                "trend": trend,
                "signal": signal,
                "is_green": is_green
            })

        except Exception as e:
            # print(f"Error processing {symbol}: {e}")
            pass

    return results
