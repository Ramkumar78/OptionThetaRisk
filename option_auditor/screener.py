import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def screen_market(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d") -> list:
    """
    Screens the market for stocks with Bullish Trend and RSI < rsi_threshold.

    Args:
        iv_rank_threshold: Minimum IV Rank (currently unused/manual check).
        rsi_threshold: Maximum RSI value for "Green Light".
        time_frame: Time frame for analysis ("1d", "49m", "98m", "196m").

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

    # Map time_frame to yfinance interval and resample rule
    yf_interval = "1d"
    resample_rule = None

    if time_frame == "49m":
        yf_interval = "5m"
        resample_rule = "49min"
    elif time_frame == "98m":
        yf_interval = "5m"
        resample_rule = "98min"
    elif time_frame == "196m":
        yf_interval = "5m" # Or 15m/30m to save data? 5m is fine for 60d
        resample_rule = "196min"

    period = "1y" if yf_interval == "1d" else "59d" # 60d is max for 5m, use 59d to be safe

    for symbol in tickers:
        try:
            # 2. Get Data
            # Use progress=False to avoid cluttering stdout
            df = yf.download(symbol, period=period, interval=yf_interval, progress=False)

            if df.empty:
                continue

            # Flatten multi-index columns if present (yfinance update)
            if isinstance(df.columns, pd.MultiIndex):
                try:
                    df.columns = df.columns.get_level_values(0)
                except Exception:
                    pass

            # Resample if needed
            if resample_rule:
                # Resample logic
                # We need OHLC aggregation
                agg_dict = {
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }
                # Handle missing columns safely
                agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}

                # Resample
                df = df.resample(resample_rule).agg(agg_dict)
                # Drop NaN rows created by resampling gaps (e.g. overnight)
                df = df.dropna()

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

            # ATR (14)
            atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            # ATR can be NaN at start
            current_atr = atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 0.0

            # Get latest values
            current_price = float(df['Close'].iloc[-1])
            current_rsi = float(df['RSI'].iloc[-1])
            current_sma = float(df['SMA_50'].iloc[-1])

            # Fetch PE Ratio (Fundamental Data)
            # This requires a separate API call per ticker, which is slow.
            # We wrap it in try-except and accept it might slow down the loop.
            pe_ratio = "N/A"
            try:
                # Only fetch if 1d timeframe to save time on intraday scans?
                # User asked for it, so we fetch.
                ticker_obj = yf.Ticker(symbol)
                # .info triggers the request
                info = ticker_obj.info
                if info and 'trailingPE' in info and info['trailingPE'] is not None:
                    pe_ratio = f"{info['trailingPE']:.2f}"
            except Exception:
                pass

            # 4. Apply Rules
            # Rule 1: Bullish Trend (Price > 50 SMA)
            trend = "BULLISH" if current_price > current_sma else "BEARISH"

            # Rule 2: The Dip (RSI between 30 and rsi_threshold)
            # We want oversold but in an uptrend.
            signal = "WAIT"
            is_green = False

            if trend == "BULLISH":
                # User asked for "RSI less than field".
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
                "is_green": is_green,
                "iv_rank": "N/A*", # Placeholder for now
                "atr": current_atr,
                "pe_ratio": pe_ratio
            })

        except Exception as e:
            # print(f"Error processing {symbol}: {e}")
            pass

    return results
