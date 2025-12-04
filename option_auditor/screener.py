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
    is_intraday = False

    if time_frame == "49m":
        yf_interval = "5m"
        resample_rule = "49min"
        is_intraday = True
    elif time_frame == "98m":
        yf_interval = "5m"
        resample_rule = "98min"
        is_intraday = True
    elif time_frame == "196m":
        yf_interval = "5m"
        resample_rule = "196min"
        is_intraday = True

    # Intraday period reduced to '1mo' (approx 20 trading days) to avoid yfinance limits/bugs with '59d'
    # 20 days * 6.5 hours = 130 hours.
    # For 49m bars (approx 1 hour), we get ~130 bars. Enough for SMA(50) and RSI(14).
    period = "1y" if yf_interval == "1d" else "1mo"

    # Hybrid Approach: Batch for Daily, Sequential for Intraday (due to yfinance bugs with batch intraday)
    all_data = None

    if not is_intraday:
        try:
            # group_by='ticker' ensures we get a MultiIndex with Ticker as level 0
            # auto_adjust=True to suppress warning
            all_data = yf.download(tickers, period=period, interval=yf_interval, group_by='ticker', threads=True, progress=False, auto_adjust=True)
        except Exception:
            # Fallback to sequential if batch fails
            all_data = None

    for symbol in tickers:
        try:
            df = pd.DataFrame()

            # Fetch Data
            if all_data is not None and symbol in all_data.columns.levels[0]:
                # Extract from batch
                df = all_data[symbol].copy()
            else:
                # Sequential fetch (Intraday or Batch Fallback)
                # auto_adjust=False for intraday to prevent KeyError(Timestamp) bug in yfinance
                df = yf.download(symbol, period=period, interval=yf_interval, progress=False, auto_adjust=False)

            # Clean NaNs
            df = df.dropna(how='all')

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
                agg_dict = {
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }
                agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}

                df = df.resample(resample_rule).agg(agg_dict)
                df = df.dropna()

            # 3. Calculate Indicators
            if len(df) < 50:
                continue

            rsi_series = ta.rsi(df['Close'], length=14)
            if rsi_series is None:
                continue
            df['RSI'] = rsi_series

            sma_series = ta.sma(df['Close'], length=50)
            if sma_series is None:
                continue
            df['SMA_50'] = sma_series

            atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 0.0

            current_price = float(df['Close'].iloc[-1])
            current_rsi = float(df['RSI'].iloc[-1])
            current_sma = float(df['SMA_50'].iloc[-1])

            # Fetch PE Ratio
            pe_ratio = "N/A"
            try:
                t = yf.Ticker(symbol)
                info = t.info
                if info and 'trailingPE' in info and info['trailingPE'] is not None:
                    pe_ratio = f"{info['trailingPE']:.2f}"
            except Exception:
                pass

            # 4. Apply Rules
            trend = "BULLISH" if current_price > current_sma else "BEARISH"
            signal = "WAIT"
            is_green = False

            if trend == "BULLISH":
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
                "iv_rank": "N/A*",
                "atr": current_atr,
                "pe_ratio": pe_ratio
            })

        except Exception as e:
            # print(f"Error processing {symbol}: {e}")
            pass

    return results
