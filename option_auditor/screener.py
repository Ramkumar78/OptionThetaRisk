import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

SECTOR_NAMES = {
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}

SECTOR_COMPONENTS = {
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "TMUS", "DIS", "CMCSA", "VZ", "T", "CHTR"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "TJX", "BKNG", "LOW", "SBUX", "NKE", "MAR"],
    "XLP": ["WMT", "PG", "COST", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "TGT"],
    "XLE": ["XOM", "CVX", "COP", "WMB", "MPC", "EOG", "SLB", "PSX", "VLO", "KMI"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C"],
    "XLV": ["LLY", "JNJ", "ABBV", "UNH", "MRK", "ABT", "TMO", "ISRG", "AMGN", "BSX"],
    "XLI": ["GE", "CAT", "RTX", "UBER", "GEV", "BA", "ETN", "UNP", "HON", "DE"],
    "XLK": ["NVDA", "AAPL", "MSFT", "AVGO", "ORCL", "CRM", "ADBE", "AMD", "CSCO", "IBM"],
    "XLB": ["LIN", "NEM", "SHW", "ECL", "FCX", "APD", "NUE", "MLM", "VMC", "CTVA"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "PSA", "SPG", "DLR", "O", "CCI", "CBRE"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "AEP", "SRE", "VST", "PEG", "ED", "D"],
    "WATCH": [
        "PLTR", "SOFI", "MSTR", "COIN", "INTC", "MU", "QCOM", "AMAT", "TXN", "ARM",
        "SMCI", "DELL", "HPQ", "PANW", "SNOW", "NOW", "SHOP", "PYPL", "SQ", "HOOD",
        "DKNG", "RBLX", "SNAP", "PINS", "CVNA", "AFRM", "UPST", "AI", "MARA", "RIOT",
        "CLSK", "F", "GM", "RIVN", "LCID", "TSM", "BABA", "PDD", "NIO", "JD",
        "SPOT", "ABNB", "DASH", "CCL", "AAL", "PFE", "CVS", "GILD", "OXY", "LULU"
    ]
}

SECTOR_NAMES["WATCH"] = "High Interest / Growth"

TICKER_NAMES = {
    "ECL": "Ecolab Inc.",
    "LLY": "Eli Lilly and Company",
    "SPG": "Simon Property Group, Inc.",
    "CVX": "Chevron Corporation",
    "AVGO": "Broadcom Inc.",
    "SBUX": "Starbucks Corporation",
    "PEG": "Public Service Enterprise Group",
    "DLR": "Digital Realty Trust, Inc.",
    "MA": "Mastercard Incorporated",
    "APD": "Air Products and Chemicals, Inc",
    "AMD": "Advanced Micro Devices, Inc.",
    "MO": "Altria Group, Inc.",
    "CBRE": "CBRE Group Inc",
    "NUE": "Nucor Corporation",
    "JPM": "JP Morgan Chase & Co.",
    "ADBE": "Adobe Inc.",
    "PEP": "Pepsico, Inc.",
    "ABT": "Abbott Laboratories",
    "AMZN": "Amazon.com, Inc.",
    "EQIX": "Equinix, Inc.",
    "TGT": "Target Corporation",
    "NEM": "Newmont Corporation",
    "DIS": "Walt Disney Company (The)",
    "MDLZ": "Mondelez International, Inc.",
    "PG": "Procter & Gamble Company (The)",
    "TSLA": "Tesla, Inc.",
    "UNP": "Union Pacific Corporation",
    "V": "Visa Inc.",
    "VST": "Vistra Corp.",
    "DE": "Deere & Company",
    "TJX": "TJX Companies, Inc. (The)",
    "VZ": "Verizon Communications Inc.",
    "PSA": "Public Storage",
    "O": "Realty Income Corporation",
    "PLD": "Prologis, Inc.",
    "MS": "Morgan Stanley",
    "COST": "Costco Wholesale Corporation",
    "HD": "Home Depot, Inc. (The)",
    "SO": "Southern Company (The)",
    "BA": "Boeing Company (The)",
    "LOW": "Lowe's Companies, Inc.",
    "RTX": "RTX Corporation",
    "DUK": "Duke Energy Corporation (Holdin",
    "AMT": "American Tower Corporation (REI",
    "AXP": "American Express Company",
    "GE": "GE Aerospace",
    "TMUS": "T-Mobile US, Inc.",
    "UNH": "UnitedHealth Group Incorporated",
    "WFC": "Wells Fargo & Company",
    "KO": "Coca-Cola Company (The)",
    "AEP": "American Electric Power Company",
    "BKNG": "Booking Holdings Inc. Common St",
    "NFLX": "Netflix, Inc.",
    "MPC": "Marathon Petroleum Corporation",
    "ISRG": "Intuitive Surgical, Inc.",
    "FCX": "Freeport-McMoRan, Inc.",
    "GS": "Goldman Sachs Group, Inc. (The)",
    "GOOG": "Alphabet Inc.",
    "BSX": "Boston Scientific Corporation",
    "GOOGL": "Alphabet Inc.",
    "MRK": "Merck & Company, Inc.",
    "CRM": "Salesforce, Inc.",
    "CTVA": "Corteva, Inc.",
    "PSX": "Phillips 66",
    "CCI": "Crown Castle Inc.",
    "MAR": "Marriott International",
    "AAPL": "Apple Inc.",
    "COP": "ConocoPhillips",
    "WMB": "Williams Companies, Inc. (The)",
    "CMCSA": "Comcast Corporation",
    "CL": "Colgate-Palmolive Company",
    "PM": "Philip Morris International Inc",
    "WELL": "Welltower Inc.",
    "MLM": "Martin Marietta Materials, Inc.",
    "NEE": "NextEra Energy, Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "GEV": "GE Vernova Inc.",
    "CHTR": "Charter Communications, Inc.",
    "EOG": "EOG Resources, Inc.",
    "VMC": "Vulcan Materials Company (Holdi",
    "BAC": "Bank of America Corporation",
    "WMT": "Walmart Inc.",
    "UBER": "Uber Technologies, Inc.",
    "MCD": "McDonald's Corporation",
    "LIN": "Linde plc",
    "SHW": "Sherwin-Williams Company (The)",
    "CSCO": "Cisco Systems, Inc.",
    "T": "AT&T Inc.",
    "VLO": "Valero Energy Corporation",
    "TMO": "Thermo Fisher Scientific Inc",
    "SLB": "SLB Limited",
    "IBM": "International Business Machines",
    "BRK-B": "Berkshire Hathaway Inc. New",
    "JNJ": "Johnson & Johnson",
    "CAT": "Caterpillar, Inc.",
    "XOM": "Exxon Mobil Corporation",
    "CEG": "Constellation Energy Corporatio",
    "ABBV": "AbbVie Inc.",
    "HON": "Honeywell International Inc.",
    "D": "Dominion Energy, Inc.",
    "C": "Citigroup, Inc.",
    "NKE": "Nike, Inc.",
    "ETN": "Eaton Corporation, PLC",
    "KMI": "Kinder Morgan, Inc.",
    "META": "Meta Platforms, Inc.",
    "ED": "Consolidated Edison, Inc.",
    "ORCL": "Oracle Corporation",
    "SRE": "DBA Sempra",
    "AMGN": "Amgen Inc.",
}

def _screen_tickers(tickers: list, iv_rank_threshold: float, rsi_threshold: float, time_frame: str) -> list:
    """
    Internal helper to screen a list of tickers.
    """
    try:
        import pandas_ta as ta
    except ImportError as e:
        raise ImportError("The 'pandas_ta' library is required for the screener. Please install it with 'pip install pandas_ta'.") from e

    # Map time_frame to yfinance interval and resample rule
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False

    # Default period
    period = "1y"

    if time_frame == "49m":
        yf_interval = "5m"
        resample_rule = "49min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "98m":
        yf_interval = "5m"
        resample_rule = "98min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "196m":
        yf_interval = "5m"
        resample_rule = "196min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "1wk":
        yf_interval = "1wk"
        period = "2y" # Need more history for SMA50 on weekly
        is_intraday = False
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y" # Need more history for SMA50 on monthly
        is_intraday = False

    # Batch download result container
    batch_data = None

    # If daily, try batch download first (avoid for new multi-year/weekly intervals to be safe, or just allow it)
    # yfinance batch download is usually fine for daily/weekly.
    if not is_intraday and tickers:
        try:
            # group_by='ticker' ensures we get a MultiIndex with Ticker as level 0
            # auto_adjust=True to suppress warning
            batch_data = yf.download(tickers, period=period, interval=yf_interval, group_by='ticker', threads=True, progress=False, auto_adjust=True)
        except Exception:
            batch_data = None

    def process_symbol(symbol):
        try:
            df = pd.DataFrame()

            # Fetch Data
            # If batch data exists and has this symbol, use it
            if batch_data is not None and symbol in batch_data.columns.levels[0]:
                df = batch_data[symbol].copy()
            else:
                # Sequential fetch (Intraday or Batch Fallback)
                # auto_adjust=False for intraday to prevent KeyError(Timestamp) bug
                # Use dedicated thread for this call via executor
                df = yf.download(symbol, period=period, interval=yf_interval, progress=False, auto_adjust=not is_intraday)

            # Clean NaNs
            df = df.dropna(how='all')

            if df.empty:
                return None

            # Flatten multi-index columns if present (yfinance update)
            if isinstance(df.columns, pd.MultiIndex):
                try:
                    df.columns = df.columns.get_level_values(0)
                except Exception:
                    pass

            # Calculate % Change before resampling
            pct_change_1d = None
            pct_change_1w = None

            try:
                if is_intraday:
                    # Logic for Intraday Data
                    unique_dates = sorted(list(set(df.index.date)))

                    if len(unique_dates) > 1:
                        # Find the last bar of the previous trading day
                        prev_date = unique_dates[-2]
                        # Filter for prev date
                        prev_day_df = df[df.index.date == prev_date]
                        if not prev_day_df.empty:
                            prev_close = float(prev_day_df['Close'].iloc[-1])
                            curr_close = float(df['Close'].iloc[-1])
                            pct_change_1d = ((curr_close - prev_close) / prev_close) * 100

                    # 1W Change: Approx 5 trading days ago
                    if len(unique_dates) > 5:
                         week_ago_date = unique_dates[-6] # 5 days ago approx
                         week_df = df[df.index.date == week_ago_date]
                         if not week_df.empty:
                             week_close = float(week_df['Close'].iloc[-1])
                             curr_close = float(df['Close'].iloc[-1])
                             pct_change_1w = ((curr_close - week_close) / week_close) * 100
                else:
                    # Logic for Daily/Weekly/Monthly Data
                    # 1D Change: Last bar vs Previous bar
                    if len(df) >= 2:
                        prev_close = float(df['Close'].iloc[-2])
                        curr_close = float(df['Close'].iloc[-1])
                        pct_change_1d = ((curr_close - prev_close) / prev_close) * 100

                    # 1W Change: Look back 5 bars if daily, else relative
                    if yf_interval == "1d":
                        if len(df) >= 6:
                            week_close = float(df['Close'].iloc[-6])
                            curr_close = float(df['Close'].iloc[-1])
                            pct_change_1w = ((curr_close - week_close) / week_close) * 100
                    elif yf_interval == "1wk":
                         # For weekly, pct_change_1d is essentially 1W change
                         # pct_change_1w (meaning a longer lookback) could be 1 month?
                         # Let's keep logic simple: 1W change for weekly IS the 1D change
                         # But to fill the UI column "1W %", we might copy it?
                         # Let's leave pct_change_1w as None or try 4 weeks back?
                         if len(df) >= 5:
                             month_close = float(df['Close'].iloc[-5])
                             curr_close = float(df['Close'].iloc[-1])
                             pct_change_1w = ((curr_close - month_close) / month_close) * 100
                    elif yf_interval == "1mo":
                        # For monthly, pct_change_1d is 1 Month change
                        pass
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
            # Check length for SMA 50
            if len(df) < 50:
                # Can't calculate SMA 50
                return None

            rsi_series = ta.rsi(df['Close'], length=14)
            if rsi_series is None:
                return None
            df['RSI'] = rsi_series

            sma_series = ta.sma(df['Close'], length=50)
            if sma_series is None:
                return None
            df['SMA_50'] = sma_series

            atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 0.0

            current_price = float(df['Close'].iloc[-1])
            current_rsi = float(df['RSI'].iloc[-1])
            current_sma = float(df['SMA_50'].iloc[-1])

            # Fetch PE Ratio (Separate blocking call if not cached, risky inside thread but better than sequential)
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
                elif current_rsi < 30:
                    signal = "🔵 OVERSOLD"
            else:
                # Bearish Trend
                if current_rsi < 30:
                    signal = "🔵 OVERSOLD (Bearish)"
                elif current_rsi > 70:
                    signal = "🔴 OVERBOUGHT (Bearish)"

            # Use TICKER_NAMES if available
            company_name = TICKER_NAMES.get(symbol, symbol)

            return {
                "ticker": symbol,
                "company_name": company_name,
                "price": current_price,
                "pct_change_1d": pct_change_1d,
                "pct_change_1w": pct_change_1w,
                "rsi": current_rsi,
                "sma_50": current_sma,
                "trend": trend,
                "signal": signal,
                "is_green": is_green,
                "iv_rank": "N/A*",
                "atr": current_atr,
                "pe_ratio": pe_ratio
            }

        except Exception:
            return None

    results = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(process_symbol, sym): sym for sym in tickers}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                pass

    return results

def screen_market(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d") -> dict:
    """
    Screens the market for stocks grouped by sector.
    Returns:
        Dict[str, List[dict]]: Keys are 'Sector Name (Ticker)', Values are lists of ticker results.
    """
    all_tickers = []
    for t_list in SECTOR_COMPONENTS.values():
        all_tickers.extend(t_list)

    flat_results = _screen_tickers(list(set(all_tickers)), iv_rank_threshold, rsi_threshold, time_frame)

    # Index results by ticker for easy lookup
    result_map = {r['ticker']: r for r in flat_results}

    grouped_results = {}

    for sector_code, sector_name in SECTOR_NAMES.items():
        if sector_code not in SECTOR_COMPONENTS:
            continue

        display_name = f"{sector_name} ({sector_code})"
        components = SECTOR_COMPONENTS[sector_code]

        sector_rows = []
        for t in components:
            if t in result_map:
                sector_rows.append(result_map[t])

        if sector_rows:
            grouped_results[display_name] = sector_rows

    return grouped_results

def screen_sectors(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d") -> list:
    """
    Screens specific sectorial indices.
    """
    sectors = list(SECTOR_NAMES.keys())
    results = _screen_tickers(sectors, iv_rank_threshold, rsi_threshold, time_frame)

    # Enrich with full name
    for r in results:
        code = r['ticker']
        if code in SECTOR_NAMES:
            r['name'] = SECTOR_NAMES[code]
            r['company_name'] = SECTOR_NAMES[code]

    return results

def screen_turtle_setups(ticker_list: list = None) -> list:
    """
    Screens for Turtle Trading Setups (20-Day Breakouts).
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd

    if ticker_list is None:
        # Default liquid list if none provided
        ticker_list = [
            "SPY", "QQQ", "IWM", "GLD", "SLV", "USO", "TLT", # ETFs
            "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", # Tech
            "JPM", "BAC", "XOM", "CVX", "PFE", "KO", "DIS" # Blue Chips
        ]

        # Add Watchlist tickers
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # Additional names for ETFs not in TICKER_NAMES
    ETF_NAMES = {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000 ETF",
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "USO": "United States Oil Fund, LP",
        "TLT": "iShares 20+ Year Treasury Bond ETF",
    }

    results = []

    # Fetch data (enough for 20-day lookback + buffer)
    # Download in bulk for speed
    try:
        data = yf.download(ticker_list, period="3mo", interval="1d", progress=False)
    except Exception:
        return []

    # Handle MultiIndex columns from yfinance bulk download
    # We iterate through tickers manually to handle the DataFrame structure

    for ticker in ticker_list:
        try:
            # Extract single ticker DF
            df = pd.DataFrame()
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    try:
                        # Try level 1 (Ticker) - standard yfinance download format (Price, Ticker)
                        if ticker in data.columns.get_level_values(1):
                            df = data.xs(ticker, axis=1, level=1).copy()
                        # Sometimes it's level 0 if group_by='ticker' was used
                        elif ticker in data.columns.get_level_values(0):
                            df = data.xs(ticker, axis=1, level=0).copy()
                    except Exception:
                        pass
                else:
                    # Single ticker or flat structure
                    df = data.copy()

            # Drop NaNs
            df.dropna(inplace=True)
            if len(df) < 21:
                continue

            # --- TURTLE CALCULATIONS ---

            # 1. Donchian Channels (20-day High/Low)
            # We use .shift(1) because we want the High of the PREVIOUS 20 days to define the breakout level
            df['20_High'] = df['High'].rolling(window=20).max().shift(1)
            df['20_Low'] = df['Low'].rolling(window=20).min().shift(1)

            # 2. ATR (Volatility 'N')
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)

            # 3. Current Values
            curr_close = float(df['Close'].iloc[-1])

            # Check if 20_High is NaN
            if pd.isna(df['20_High'].iloc[-1]) or pd.isna(df['ATR'].iloc[-1]):
                continue

            prev_high = float(df['20_High'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])

            # 4. Logic
            signal = "WAIT"
            buy_price = 0.0
            stop_loss = 0.0
            target = 0.0

            # Check for Breakout (Close > Previous 20-day High)
            # Or simpler: Price is near the high (within 1% of breakout)

            dist_to_breakout = (curr_close - prev_high) / prev_high

            if curr_close > prev_high:
                signal = "🚀 BREAKOUT (BUY)"
                buy_price = curr_close
                stop_loss = buy_price - (2 * atr) # 2N Rule
                target = buy_price + (4 * atr)    # 2:1 Reward Projection

            # "Near" Breakout (Watchlist) - Within 2% of high
            elif -0.02 <= dist_to_breakout <= 0:
                signal = "👀 WATCH (Near High)"
                buy_price = prev_high # Buy stop limit would be here
                stop_loss = prev_high - (2 * atr)
                target = prev_high + (4 * atr)

            if signal != "WAIT":
                # Get company name
                company_name = TICKER_NAMES.get(ticker, ETF_NAMES.get(ticker, ticker))

                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "signal": signal,
                    "breakout_level": prev_high,
                    "stop_loss": stop_loss,
                    "target": target,
                    "atr": atr,
                    "risk_per_share": buy_price - stop_loss
                })

        except Exception as e:
            # print(f"Error on {ticker}: {e}")
            continue

    return results
