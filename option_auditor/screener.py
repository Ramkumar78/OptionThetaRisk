import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

# Configure logger
logger = logging.getLogger(__name__)

# Import Unified Screener (Lazy import inside function to avoid circular dep if needed, or top level)
# We will expose it via this module for backward compatibility/ease of use.
from option_auditor.unified_screener import screen_universal_dashboard

# Imports from common constants to avoid circular dependencies
from option_auditor.common.constants import SECTOR_NAMES, SECTOR_COMPONENTS, TICKER_NAMES
from option_auditor.common.data_utils import prepare_data_for_ticker as _prepare_data_for_ticker
from option_auditor.common.data_utils import fetch_data_with_retry, fetch_batch_data_safe, get_cached_market_data

try:
    from option_auditor.sp500_data import get_sp500_tickers
except ImportError:
    def get_sp500_tickers(): return []

# Update with S&P 500 Names if available in constants?
# Constants.py updates TICKER_NAMES with SP500_NAMES already.

def _calculate_trend_breakout_date(df: pd.DataFrame) -> str:
    """
    Calculates the start date of the current trend (ISA Logic: Breakout > 50d High, Exit < 20d Low).
    Returns "N/A" if not in a trend.
    """
    try:
        # Ensure we have enough data
        if df.empty or len(df) < 50: return "N/A"

        # Calculate indicators if missing
        # Work on a copy/slice to avoid modifying original if needed, but adding columns is fine
        subset = df.copy()

        if 'High_50' not in subset.columns:
            subset['High_50'] = subset['High'].rolling(50).max().shift(1)
        if 'Low_20' not in subset.columns:
            subset['Low_20'] = subset['Low'].rolling(20).min().shift(1)

        curr_close = subset['Close'].iloc[-1]
        low_20 = subset['Low_20'].iloc[-1]

        # Check if currently in a trend state
        # The ISA logic defines a trend as "Safe" if Close > Low_20.
        # If currently stopped out (Close <= Low_20), then no active trend.
        if pd.isna(curr_close) or pd.isna(low_20) or curr_close <= low_20:
            return "N/A"

        # Search backwards
        limit = min(len(subset), 400)
        subset = subset.iloc[-limit:]

        is_breakout = subset['Close'] >= subset['High_50']
        is_broken = subset['Close'] <= subset['Low_20']

        break_indices = subset.index[is_broken]
        last_break_idx = break_indices[-1] if not break_indices.empty else None

        breakout_indices = subset.index[is_breakout]

        if last_break_idx is not None:
             valid_breakouts = breakout_indices[breakout_indices > last_break_idx]
        else:
             valid_breakouts = breakout_indices

        if not valid_breakouts.empty:
             return valid_breakouts[0].strftime("%Y-%m-%d")

        return "N/A"
    except Exception:
        return "N/A"

def _resolve_region_tickers(region: str) -> list:
    """
    Helper to resolve ticker list based on region.
    Default: US (Sector Components + Watch)
    """
    if region == "uk_euro":
        return get_uk_euro_tickers()
    elif region == "uk":
        try:
            from option_auditor.uk_stock_data import get_uk_tickers
            return get_uk_tickers()
        except ImportError:
            # Fallback to UK/Euro or empty
            return get_uk_euro_tickers()
    elif region == "india":
        return get_indian_tickers()
    elif region == "sp500":
        # S&P 500 (Volume Filtered) + Watch List
        # Note: We use check_trend=False to get the universe.
        sp500 = _get_filtered_sp500(check_trend=False)
        watch_list = SECTOR_COMPONENTS.get("WATCH", [])
        return list(set(sp500 + watch_list))
    else: # us / combined default
        all_tickers = []
        for t_list in SECTOR_COMPONENTS.values():
            all_tickers.extend(t_list)
        return list(set(all_tickers))


def enrich_with_fundamentals(results_list: list) -> list:
    """
    Fetches PE Ratio and Sector data ONLY for the stocks that passed the screener.
    significantly faster than fetching for the whole universe.
    """
    import yfinance as yf

    for item in results_list:
        # Only enrich valid signals to save time
        # We look for "BUY", "SHORT", "GREEN", "BREAKOUT", "ENTER"
        signal = item.get('signal', '').upper()
        verdict = item.get('verdict', '').upper() # Hybrid uses verdict

        is_interesting = False
        if any(x in signal for x in ["BUY", "SELL", "SHORT", "ENTER", "BREAKOUT", "HOLD"]):
             is_interesting = True
        if any(x in verdict for x in ["BUY", "SELL", "SHORT"]):
             is_interesting = True

        if not is_interesting and "WAIT" in signal:
             item['pe_ratio'] = "-"
             continue

        try:
            ticker = item['ticker']
            # Fast fetch
            info = yf.Ticker(ticker).info

            pe = info.get('trailingPE', None)
            f_pe = info.get('forwardPE', None)
            sector = info.get('sector', 'Unknown')

            # Logic: Use Forward PE if Trailing is missing (growth stocks)
            final_pe = pe if pe else f_pe

            item['pe_ratio'] = f"{final_pe:.2f}" if final_pe else "N/A"
            item['sector'] = sector

            # Optional: Add "Overvalued" warning
            if final_pe:
                if final_pe > 50:
                    item['value_verdict'] = "EXPENSIVE"
                elif final_pe < 15:
                    item['value_verdict'] = "CHEAP"
                else:
                    item['value_verdict'] = "FAIR"
            else:
                 item['value_verdict'] = "N/A"

        except Exception:
            item['pe_ratio'] = "Err"

    return results_list

def _get_filtered_sp500(check_trend: bool = True) -> list:
    """
    Returns a filtered list of S&P 500 tickers based on Volume (>500k) and optionally Trend (>SMA200).
    """
    base_tickers = get_sp500_tickers()
    if not base_tickers:
        return []

    # Batch download 1y data for volume and sma using safe utility
    import pandas_ta as ta

    filtered_list = []

    # Use CACHED data to prevent timeouts and redundant downloads.
    # We use "market_scan_v1" which contains 2y data for S&P 500.
    # If the cache is missing, this will download it (heavy), but future calls will be instant.
    try:
        data = get_cached_market_data(base_tickers, period="2y", cache_name="market_scan_v1")
    except Exception as e:
        logger.error(f"Failed to get S&P 500 cache: {e}")
        data = pd.DataFrame()

    if data.empty:
        # Fallback to returning the base list if data unavailable, to allow scanning to proceed (albeit unfiltered)
        logger.warning("S&P 500 filter data unavailable. Returning raw list.")
        return base_tickers

    # Iterate through the downloaded data to check criteria
    # fetch_batch_data_safe returns a DataFrame where columns are usually MultiIndex (Ticker, Price) or flat if single ticker
    # But for multiple tickers it's MultiIndex.

    # We iterate base_tickers because they are the keys
    for ticker in base_tickers:
        try:
            df = pd.DataFrame()
            # Extract single DF safely
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data.columns.levels[0]:
                        df = data[ticker].copy()
            elif ticker in data.columns: # fallback
                    df = data[ticker].copy()
            else:
                continue # Ticker failed to download

            df = df.dropna(how='all')
            if len(df) < 20: continue

            # 1. Volume Filter (> 500k avg over last 20 days)
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if avg_vol < 500000: continue

            # 2. Trend Filter (> SMA 200)
            if check_trend:
                if len(df) < 200: continue
                sma_200 = df['Close'].rolling(200).mean().iloc[-1]
                curr_price = df['Close'].iloc[-1]
                if curr_price < sma_200: continue

            filtered_list.append(ticker)
        except:
            continue

    return filtered_list

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

    # If daily, try batch download first
    if not is_intraday and tickers:
        try:
            # Optimization: Try to load from "market_scan_v1" cache ONLY if the list is likely the S&P 500 set.
            # Blindly using it for any list > 50 is risky if the user scans e.g. Russell 2000 subset.
            # However, since we don't know the intent, we can check intersection coverage?
            # For now, we only use it if the cache covers the request.
            # But calculating coverage requires loading the cache.
            # Safe heuristics: If list > 400 (likely full scan) OR if we can verify coverage.

            # Revised Strategy:
            # 1. Try loading master cache if list is large.
            # 2. If loaded, check if it contains our tickers.
            # 3. If coverage is poor, discard and download fresh.

            if len(tickers) > 100:
                cached = get_cached_market_data(None, cache_name="market_scan_v1", lookup_only=True)
                if not cached.empty:
                    # Check coverage
                    # MultiIndex columns (Ticker, Price)
                    if isinstance(cached.columns, pd.MultiIndex):
                        available_tickers = cached.columns.levels[0]
                        # If more than 80% of requested tickers are in cache, use it
                        intersection = len(set(tickers).intersection(available_tickers))
                        if intersection / len(tickers) > 0.8:
                            batch_data = cached
                    else:
                        # Flat cache (single ticker?) unlikely for market_scan
                        pass

            # If no cache or cache empty/insufficient, fetch fresh
            if batch_data is None:
                batch_data = fetch_batch_data_safe(tickers, period=period, interval=yf_interval)
        except Exception as e:
            logger.error(f"Failed to batch download ticker data: {e}")
            batch_data = None

    def process_symbol(symbol):
        try:
            # Use shared helper
            df = _prepare_data_for_ticker(symbol, batch_data, time_frame, period, yf_interval, resample_rule, is_intraday)

            if df is None: return None

            # Volume Filter: If scanning daily/weekly (not intraday), skip illiquid stocks (< 500k avg volume)
            # This prevents wasting CPU on stocks we can't trade and reduces risk of stale data issues.
            if not is_intraday and len(df) >= 20:
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                if avg_vol < 500000:
                    return None

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
            except Exception as e:
                logger.debug(f"Error calculating % change for {symbol}: {e}")
                pass

            # Resample is handled in helper if resample_rule passed, but let's double check logic.
            # _prepare_data_for_ticker does resampling.

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
            volatility_pct = (current_atr / current_price * 100) if current_price > 0 else 0.0
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

            # Calculate Breakout Date (Trend Age)
            breakout_date = _calculate_trend_breakout_date(df)

            # Rate limiting sleep
            time.sleep(0.1)

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
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "pe_ratio": pe_ratio,
                "breakout_date": breakout_date
            }

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None

    results = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {executor.submit(process_symbol, sym): sym for sym in tickers}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                 logger.error(f"Thread execution error for {future_to_symbol[future]}: {e}")
                 pass

    return results

def screen_market(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d", region: str = "us") -> dict:
    """
    Screens the market for stocks grouped by sector.
    Returns:
        Dict[str, List[dict]]: Keys are 'Sector Name (Ticker)', Values are lists of ticker results.
    """
    all_tickers = []

    all_tickers = []

    if region != "us" and region is not None:
        # Use common helper for non-default regions
        all_tickers = _resolve_region_tickers(region)
    else:
        # Default US Sector Components
        for t_list in SECTOR_COMPONENTS.values():
            all_tickers.extend(t_list)

    flat_results = _screen_tickers(list(set(all_tickers)), iv_rank_threshold, rsi_threshold, time_frame)

    # Index results by ticker for easy lookup
    result_map = {r['ticker']: r for r in flat_results}

    grouped_results = {}

    if region == "sp500":
        # For S&P 500, we don't have explicit sector mapping in the input list.
        # We return a single group "S&P 500" or try to map if we had sector data.
        # Since we don't have sectors in sp500_data.py, we group all under "S&P 500".
        # However, check if any tickers are already in SECTOR_COMPONENTS to categorize them?
        # That would be nice but incomplete.
        # Let's try to categorize what we can, and put rest in "Other".

        # Build reverse map for known sectors
        ticker_to_sector = {}
        for scode, sname in SECTOR_NAMES.items():
            if scode in SECTOR_COMPONENTS:
                for t in SECTOR_COMPONENTS[scode]:
                    ticker_to_sector[t] = f"{sname} ({scode})"

        sp500_grouped = {}
        uncategorized = []

        for r in flat_results:
            t = r['ticker']
            if t in ticker_to_sector:
                sec = ticker_to_sector[t]
                if sec not in sp500_grouped: sp500_grouped[sec] = []
                sp500_grouped[sec].append(r)
            else:
                uncategorized.append(r)

        if uncategorized:
            sp500_grouped["S&P 500 (Uncategorized)"] = uncategorized

        return sp500_grouped

    else:
        # Default Sector Grouping
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
    # remove WATCH
    if "WATCH" in sectors: sectors.remove("WATCH")

    results = _screen_tickers(sectors, iv_rank_threshold, rsi_threshold, time_frame)

    # Enrich with full name
    for r in results:
        code = r['ticker']
        if code in SECTOR_NAMES:
            r['name'] = SECTOR_NAMES[code]
            r['company_name'] = SECTOR_NAMES[code]

    return results

UK_EURO_TICKERS = [
    # Top 50 FTSE (UK)
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "REL.L", "GSK.L", "DGE.L", "LSEG.L", "BATS.L", "GLEN.L", "BA.L", "CNA.L", "NG.L", "LLOY.L", "RR.L", "BARC.L", "CPG.L", "NWG.L", "RKT.L", "VOD.L", "AAL.L", "SGE.L", "HLN.L", "EXR.L", "TSCO.L", "SSE.L", "MNG.L", "ADM.L", "III.L", "ANTO.L", "SPX.L", "STAN.L", "IMB.L", "WTB.L", "SVT.L", "AUTO.L", "SN.L", "CRDA.L", "WPP.L", "SMIN.L", "DCC.L", "AV.L", "LGEN.L", "KGF.L", "SBRY.L", "MKS.L", "LAND.L", "PSON.L",
    # Liquid UK Mid-Caps
    "JD.L", "IAG.L", "EZJ.L", "AML.L", "IDS.L", "DLG.L", "ITM.L", "QQ.L", "GRG.L", "VTY.L", "BTRW.L", "BOO.L", "ASOS.L", "HBR.L", "ENOG.L", "TLW.L", "CWR.L", "GNC.L", "THG.L", "CURY.L", "DOM.L", "SFOR.L", "PETS.L", "MRO.L", "INVP.L", "OCDO.L", "IGG.L", "CMC.L", "PLUS.L", "EMG.L", "HWDN.L", "COST.L", "BEZ.L", "SGRO.L", "PSN.L", "TW.L", "BYG.L", "SAFE.L", "UTG.L", "BBOX.L", "MANG.L", "TPK.L", "HIK.L", "SRO.L", "FRES.L", "KAP.L", "WKP.L", "JMAT.L", "RS1.L", "PNN.L",
    # Top 50 Euro
    "ASML.AS", "MC.PA", "SAP.DE", "RMS.PA", "TTE.PA", "SIE.DE", "CDI.PA", "AIR.PA", "SAN.MC", "IBE.MC", "OR.PA", "ALV.DE", "SU.PA", "EL.PA", "AI.PA", "BNP.PA", "DTE.DE", "ENEL.MI", "DG.PA", "BBVA.MC", "CS.PA", "BAS.DE", "ADS.DE", "MUV2.DE", "IFX.DE", "SAF.PA", "ENI.MI", "INGA.AS", "ISP.MI", "KER.PA", "STLAP.PA", "AD.AS", "VOW3.DE", "BMW.DE", "MBG.DE", "BAYN.DE", "DB1.DE", "BN.PA", "RI.PA", "CRH.L", "G.MI", "PHIA.AS", "HEIA.AS", "NOKIA.HE", "VIV.PA", "ORA.PA", "KNEBV.HE", "UMG.AS", "HO.PA", "ABI.BR"
]

def get_uk_euro_tickers():
    """Returns normalized UK/Euro tickers list."""
    return list(set(UK_EURO_TICKERS))

INDIAN_TICKERS = [
    # Nifty 50
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK", "INFY", "HINDUNILVR", "SBIN", "ITC", "LTIM", "LT", "HCLTECH", "BAJFINANCE", "AXISBANK", "MARUTI", "ULTRACEMCO", "SUNPHARMA", "M&M", "TITAN", "KOTAKBANK", "ADANIENT", "TATAMOTORS", "NTPC", "TATASTEEL", "POWERGRID", "ASIANPAINT", "JSWSTEEL", "BAJAJFINSV", "NESTLEIND", "GRASIM", "ONGC", "TECHM", "HINDALCO", "ADANIPORTS", "CIPLA", "WIPRO", "SBILIFE", "DRREDDY", "BRITANNIA", "TATACONSUM", "COALINDIA", "APOLLOHOSP", "EICHERMOT", "INDUSINDBK", "DIVISLAB", "BAJAJ-AUTO", "HDFCLIFE", "HEROMOTOCO", "BEL", "SHRIRAMFIN",
    # Nifty Next 50
    "LICI", "HAL", "ADANIPOWER", "DMART", "VBL", "JIOFIN", "SIEMENS", "TRENT", "ZOMATO", "ADANIGREEN", "IOC", "DLF", "VEDL", "BANKBARODA", "GAIL", "AMBUJACEM", "CHOLAFIN", "HAVELLS", "ABB", "PIDILITIND", "GODREJCP", "DABUR", "SHREECEM", "PNB", "BPCL", "SBICARD", "SRF", "MOTHERSON", "ICICIPRULI", "MARICO", "BERGEPAINT", "ICICIGI", "TVSMOTOR", "NAUKRI", "LODHA", "BOSCHLTD", "INDIGO", "CANBK", "UNITDSPR", "TORNTPHARM", "PIIND", "UPL", "JINDALSTEL", "ALKEM", "ZYDUSLIFE", "COLPAL", "BAJAJHLDNG", "TATAPOWER", "IRCTC", "MUTHOOTFIN"
]

def get_indian_tickers():
    """Returns normalized Indian tickers list."""
    # Append .NS for NSE
    return [t + ".NS" for t in INDIAN_TICKERS]

def screen_turtle_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for Turtle Trading Setups (20-Day Breakouts).
    Supports multiple timeframes.
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd

    # If list is None, use default based on region
    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)

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

    # Timeframe logic
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False
    period = "3mo"

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
        period = "2y"
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y"

    results = []

    # Bulk download if not intraday
    data = None
    if not is_intraday:
        try:
            # Optimization: Check Master Cache coverage
            if len(ticker_list) > 100:
                 cached = get_cached_market_data(None, cache_name="market_scan_v1", lookup_only=True)
                 if not cached.empty:
                     # Verify coverage
                     if isinstance(cached.columns, pd.MultiIndex):
                         available = cached.columns.levels[0]
                         intersection = len(set(ticker_list).intersection(available))
                         if intersection / len(ticker_list) > 0.8:
                             data = cached

            if data is None:
                # Use safe batch fetch
                data = fetch_batch_data_safe(ticker_list, period=period, interval=yf_interval)
        except Exception as e:
            logger.error(f"Failed to bulk download for turtle setups: {e}")
            pass

    for ticker in ticker_list:
        try:
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            min_length = 21 if check_mode else 21 # Turtle needs 20 bars for Donchian
            if df is None or len(df) < min_length:
                continue

            # --- TURTLE & DARVAS CALCULATIONS ---
            # 1. Donchian Channels (20-day High/Low)
            df['20_High'] = df['High'].rolling(window=20).max().shift(1)
            df['20_Low'] = df['Low'].rolling(window=20).min().shift(1)

            # Darvas / 10-day Box for faster breakouts
            df['10_High'] = df['High'].rolling(window=10).max().shift(1)
            df['10_Low'] = df['Low'].rolling(window=10).min().shift(1)

            # 2. ATR (Volatility 'N')
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)

            curr_close = float(df['Close'].iloc[-1])

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception as e:
                    logger.debug(f"Error calc % change for {ticker}: {e}")

            if pd.isna(df['20_High'].iloc[-1]) or pd.isna(df['ATR'].iloc[-1]):
                continue

            prev_high = float(df['20_High'].iloc[-1])
            prev_low = float(df['20_Low'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])

            # 10-day values
            prev_high_10 = float(df['10_High'].iloc[-1]) if not pd.isna(df['10_High'].iloc[-1]) else prev_high
            prev_low_10 = float(df['10_Low'].iloc[-1]) if not pd.isna(df['10_Low'].iloc[-1]) else prev_low

            volatility_pct = (atr / curr_close) * 100 if curr_close > 0 else 0.0

            signal = "WAIT"
            buy_price = 0.0
            stop_loss = 0.0
            target = 0.0

            dist_to_breakout_high = (curr_close - prev_high) / prev_high

            # Buy Breakout (Turtle 20-Day)
            if curr_close > prev_high:
                signal = "🚀 BREAKOUT (BUY)"
                buy_price = curr_close
                stop_loss = buy_price - (2 * atr)
                target = buy_price + (4 * atr)

            # Sell Breakout (Short)
            elif curr_close < prev_low:
                signal = "📉 BREAKDOWN (SELL)"
                buy_price = curr_close
                stop_loss = buy_price + (2 * atr) # Stop above entry for short
                target = buy_price - (4 * atr)    # Target below entry

            # Near High (Turtle 20-Day only for now)
            elif -0.02 <= dist_to_breakout_high <= 0:
                signal = "👀 WATCH (Near High)"
                buy_price = prev_high
                stop_loss = prev_high - (2 * atr)
                target = prev_high + (4 * atr)

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            # Additional Calcs for Consistency
            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1] if len(df) >= 14 else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()

            # Risk/Reward calculation
            invalidation_level = stop_loss
            target_level = target
            potential_risk = curr_close - invalidation_level
            potential_reward = target_level - curr_close
            rr_ratio = potential_reward / potential_risk if potential_risk > 0 else 0.0

            if check_mode or signal != "WAIT":
                # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))
                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
                    "signal": signal,
                    "breakout_level": prev_high,
                    "stop_loss": invalidation_level,
                    "target": target_level,
                    "risk_reward": f"1:{rr_ratio:.2f}",
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d, # Returning stocks own change as placeholder for now as sector mapping requires fetching sector ticker
                    "trailing_exit_10d": round(prev_low_10, 2)
                })

        except Exception as e:
            logger.error(f"Error processing turtle setup for {ticker}: {e}")
            continue

    return results

def screen_5_13_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for 5/13 and 5/21 EMA Crossovers (Momentum Breakouts).
    """
    try:
        import pandas_ta as ta
    except ImportError:
        return []

    import yfinance as yf
    import pandas as pd

    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)

    # Additional names for ETFs not in TICKER_NAMES
    ETF_NAMES = {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000 ETF",
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "USO": "United States Oil Fund, LP",
        "TLT": "iShares 20+ Year Treasury Bond ETF",
        "BITO": "ProShares Bitcoin Strategy ETF",
    }

    # Timeframe logic
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False
    period = "3mo"

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
        period = "2y"
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y"

    results = []

    # Bulk download if not intraday
    data = None
    if not is_intraday:
        try:
            # Optimization: Check Master Cache coverage
            if len(ticker_list) > 100:
                 cached = get_cached_market_data(None, cache_name="market_scan_v1", lookup_only=True)
                 if not cached.empty:
                     if isinstance(cached.columns, pd.MultiIndex):
                         available = cached.columns.levels[0]
                         intersection = len(set(ticker_list).intersection(available))
                         if intersection / len(ticker_list) > 0.8:
                             data = cached

            if data is None:
                # Use safe batch fetch
                data = fetch_batch_data_safe(ticker_list, period=period, interval=yf_interval)
        except Exception as e:
            logger.error(f"Failed to bulk download for 5/13 setups: {e}")
            pass

    for ticker in ticker_list:
        try:
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            min_length = 22 if check_mode else 22 # Need 21 for EMA 21
            if df is None or len(df) < min_length:
                continue

            # --- EMA CALCULATIONS ---
            df['EMA_5'] = ta.ema(df['Close'], length=5)
            df['EMA_13'] = ta.ema(df['Close'], length=13)
            df['EMA_21'] = ta.ema(df['Close'], length=21)

            # ATR for standard reporting
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0

            # Current & Previous values
            curr_5 = df['EMA_5'].iloc[-1]
            curr_13 = df['EMA_13'].iloc[-1]
            curr_21 = df['EMA_21'].iloc[-1]

            prev_5 = df['EMA_5'].iloc[-2]
            prev_13 = df['EMA_13'].iloc[-2]
            prev_21 = df['EMA_21'].iloc[-2]

            curr_close = float(df['Close'].iloc[-1])
            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            # Calc ATR, 52wk
            # current_atr is already calculated above
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            
            # --- SIGNAL GENERATION ---
            signal = "WAIT"
            status_color = "gray"
            stop_loss = 0.0
            ema_slow = curr_13 # Default to 13

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception as e:
                    logger.debug(f"Error calculating pct change for {ticker}: {e}")
                    pass

            # Logic Priority:
            # 1. Fresh 5/21 Breakout (Stronger/Rarer)
            # 2. Fresh 5/13 Breakout
            # 3. Trending 5/21 (Trend strength)
            # 4. Trending 5/13

            # 1. Fresh Breakouts
            if curr_5 > curr_21 and prev_5 <= prev_21:
                signal = "🚀 FRESH 5/21 BREAKOUT"
                status_color = "green"
                ema_slow = curr_21
                stop_loss = curr_21 * 0.99

            elif curr_5 > curr_13 and prev_5 <= prev_13:
                signal = "🚀 FRESH 5/13 BREAKOUT"
                status_color = "green"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            # 2. Trending (Held for >1 day)
            elif curr_5 > curr_21:
                 signal = "📈 5/21 TRENDING"
                 status_color = "blue"
                 ema_slow = curr_21
                 stop_loss = curr_21 * 0.99

            elif curr_5 > curr_13:
                # Check how far extended?
                dist = (curr_close - curr_13) / curr_13
                if dist < 0.01: # Price is pulling back to 13 EMA (Buy Support)
                    signal = "✅ 5/13 TREND (Buy Support)"
                    status_color = "blue"
                else:
                    signal = "📈 5/13 TRENDING"
                    status_color = "blue"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            # 3. Bearish Cross (Sell)
            if curr_5 < curr_13 and prev_5 >= prev_13:
                signal = "❌ 5/13 DUMP (Sell Signal)"
                status_color = "red"
                ema_slow = curr_13
                stop_loss = curr_13 * 1.01 # Stop above

            elif curr_5 < curr_21 and prev_5 >= prev_21:
                signal = "❌ 5/21 DUMP (Sell Signal)"
                status_color = "red"
                ema_slow = curr_21
                stop_loss = curr_21 * 1.01

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)
            
            # Additional Calcs for Consistency
            # current_atr is already calculated above
            # high_52wk and low_52wk are already calculated above

            if check_mode or signal != "WAIT":
                # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))
                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
                    "signal": signal,
                    "color": status_color,
                    "ema_5": curr_5,
                    "ema_13": curr_13,
                    "ema_21": curr_21,
                    # Stop Loss usually strictly below the slow EMA line
                    "stop_loss": stop_loss,
                    "atr_value": round(current_atr, 2), # Key was different in 5/13, standardizing or adding both? Keeping original key 'atr_value' but adding 'atr' for unified UI
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d,
                    "volatility_pct": round(volatility_pct, 2),
                    "diff_pct": ((curr_5 - ema_slow)/ema_slow)*100,
                    "breakout_date": breakout_date
                })

        except Exception as e:
            logger.error(f"Error processing 5/13 setup for {ticker}: {e}")
            continue
    # Sort by "Freshness" (Breakouts first)
    results.sort(key=lambda x: 0 if "FRESH" in x['signal'] else 1)
    return results

def screen_darvas_box(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for Darvas Box Breakouts.
    Strategy:
    1. Trend: Stock near 52-week High.
    2. Box: Price breaks above a "Ceiling" established by a recent high (3-day non-penetration).
    3. Volume: Spike on breakout.
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd
    import numpy as np

    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)

    ETF_NAMES = {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000 ETF",
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "USO": "United States Oil Fund, LP",
        "TLT": "iShares 20+ Year Treasury Bond ETF",
    }

    # Timeframe logic
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False
    period = "1y" # Need longer history for 52-week high

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
        period = "2y"
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y"

    results = []

    # Bulk download if not intraday
    data = None
    if not is_intraday:
        try:
            # Optimization: Check Master Cache coverage
            if len(ticker_list) > 100:
                 cached = get_cached_market_data(None, cache_name="market_scan_v1", lookup_only=True)
                 if not cached.empty:
                     if isinstance(cached.columns, pd.MultiIndex):
                         available = cached.columns.levels[0]
                         intersection = len(set(ticker_list).intersection(available))
                         if intersection / len(ticker_list) > 0.8:
                             data = cached

            if data is None:
                # Use safe batch fetch
                data = fetch_batch_data_safe(ticker_list, period=period, interval=yf_interval)
        except Exception as e:
            logger.error(f"Failed to bulk download for Darvas screener: {e}")
            pass

    def _process_darvas(ticker):
        try:
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            min_length = 50 if check_mode else 50 # Darvas needs enough history for pivots
            if df is None or len(df) < min_length:
                return None

            curr_close = float(df['Close'].iloc[-1])
            curr_volume = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0

            # 1. 52-Week High Check (Momentum Filter)
            # If intraday, we might not have full 52-week data in `df` (only 1mo).
            # So we rely on the data we have. For proper Darvas, 1y daily is best.
            # If intraday, we assume the user accepts the "local" high as the filter or we skip.
            # Let's use the max of the available data.
            period_high = df['High'].max()
            # If we are within 5% of the high
            if curr_close < period_high * 0.90 and not check_mode:
                # Darvas requires new highs. If we are deep in drawdown, ignore.
                # Exception: Early stage breakout from a base might be slightly lower.
                # Strictest rule: Must be making a new high.
                # Let's relax to: Near High (> 90%).
                pass # Just a filter, but we proceed to check boxes

            # 2. Identify Box (Ceiling & Floor)
            # We iterate back to find the most recent valid Box.
            # A valid box has a Ceiling (Top) and a Floor (Bottom).

            # Logic:
            # Find the most recent "Pivot High" (Ceiling).
            # A Top at index T is valid if High[T] >= High[T-3...T-1] AND High[T] >= High[T+1...T+3].

            # Optimization: We only need the last established box.
            # We scan backwards from T-3.

            ceiling = None
            floor = None

            # Convert to numpy for speed
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            volumes = df['Volume'].values if 'Volume' in df.columns else np.zeros(len(df))

            # Look back window: last 60 bars (approx 3 months)
            lookback = min(len(df), 60)

            # Find potential Tops
            # We iterate backwards
            found_top_idx = -1

            for i in range(len(df) - 4, len(df) - lookback, -1):
                # Check for Pivot High at i
                # Left neighbors (i-3 to i-1)
                if i < 3: break

                # Check if High[i] is >= High[i-1] AND High[i] >= High[i-2] AND High[i] >= High[i-3] AND
                # High[i] >= High[i+1] AND High[i] >= High[i+2] AND High[i] >= High[i+3]
                # Note: i+3 must exist.
                if i + 3 >= len(df): continue

                curr_h = highs[i]
                if (curr_h >= highs[i-1] and curr_h >= highs[i-2] and curr_h >= highs[i-3] and
                    curr_h >= highs[i+1] and curr_h >= highs[i+2] and curr_h >= highs[i+3]):

                    found_top_idx = i
                    ceiling = curr_h
                    break

            if found_top_idx == -1:
                return None # No defined top recently

            # Find Floor (Bottom) AFTER the Top
            # Darvas: "The point where it stops dropping... becomes the bottom"
            # So we look for a Pivot Low in the range (found_top_idx + 1 ... Today)
            # But the pivot low also needs 3 days confirmation.

            found_bot_idx = -1

            for j in range(found_top_idx + 1, len(df) - 3):
                # Check for Pivot Low at j
                # Left neighbors?
                # Actually, Darvas establishes the floor *after* the ceiling.
                # Condition: Low[j] <= Low[j-3...j-1] AND Low[j] <= Low[j+1...j+3]
                # And Low[j] < Ceiling

                if j < 3: continue
                if j + 3 >= len(df): continue

                curr_l = lows[j]
                if curr_l >= ceiling: continue # Bottom must be below top

                if (curr_l <= lows[j-1] and curr_l <= lows[j-2] and curr_l <= lows[j-3] and
                    curr_l <= lows[j+1] and curr_l <= lows[j+2] and curr_l <= lows[j+3]):

                    found_bot_idx = j
                    floor = curr_l
                    # We take the *first* valid bottom after top? Or the lowest?
                    # Darvas boxes are usually defined by the first consolidation range.
                    # Let's assume the first valid pivot low establishes the floor.
                    break

            if floor is None:
                # We have a Top but no confirmed Floor yet.
                # We are likely "In Formation".
                pass

            # Calc ATR, 52wk
            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1] if len(df) >= 14 else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            pct_change_1d = ((curr_close - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) >= 2 else 0.0
            
            # --- SIGNAL GENERATION ---
            signal = "WAIT"

            # 3. Check for Breakout
            # If we have a valid Box [Floor, Ceiling]
            if ceiling and floor:
                # Check if we are breaking out NOW (last bar)
                # Breakout: Close > Ceiling
                if closes[-1] > ceiling and closes[-2] <= ceiling:
                     signal = "📦 DARVAS BREAKOUT"

                # Check for Breakdown (Stop Loss)
                elif closes[-1] < floor and closes[-2] >= floor:
                     signal = "📉 BOX BREAKDOWN"

                elif closes[-1] > ceiling:
                     # Already broken out, sustaining high?
                     if (closes[-1] - ceiling) / ceiling < 0.05:
                         signal = "🚀 MOMENTUM (Post-Breakout)"

            elif ceiling and not floor:
                # Setup phase?
                # Price is between Top and (undefined) Bottom.
                pass

            if signal == "WAIT" and not check_mode:
                return None

            # 4. Volume Filter (for Breakouts)
            is_valid_volume = True
            vol_ma_ratio = 1.0
            if "BREAKOUT" in signal and not check_mode:
                # Volume > 150% of 20-day MA
                vol_ma = np.mean(volumes[-21:-1]) if len(volumes) > 21 else np.mean(volumes)
                if vol_ma > 0:
                    vol_ma_ratio = curr_volume / vol_ma
                    if curr_volume < vol_ma * 1.2: # Relaxed to 1.2x
                        # signal += " (Low Vol)"
                        # Maybe filter it out strictly?
                        # Darvas insisted on volume.
                        is_valid_volume = False

            if not is_valid_volume and not check_mode:
                return None

            # 52-Week High check (Strict for Entry)
            if "BREAKOUT" in signal and not check_mode:
                if curr_close < period_high * 0.95:
                     # Breakout of a box, but far from 52w high?
                     # Might be a recovery box. Darvas preferred ATH.
                     # We label it differently?
                     pass

            # Calculate metrics
            # pct_change_1d is already calculated above

            # atr is already calculated as current_atr
            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            stop_loss = floor if floor else (ceiling - 2*current_atr if ceiling else curr_close * 0.95)
            # Target = Breakout + Box Height
            box_height = (ceiling - floor) if (ceiling and floor) else (4 * current_atr)
            target = ceiling + box_height if ceiling else curr_close * 1.2

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            # Rate limiting sleep
            time.sleep(0.1)

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": curr_close,
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "breakout_level": ceiling,
                "floor_level": floor,
                "stop_loss": stop_loss,
                "target_price": target,
                "high_52w": period_high,
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "volume_ratio": round(vol_ma_ratio, 2),
                "breakout_date": breakout_date,
                "atr": round(current_atr, 2),
                "52_week_high": round(high_52wk, 2) if high_52wk else None,
                "52_week_low": round(low_52wk, 2) if low_52wk else None,
                "sector_change": pct_change_1d
            }

        except Exception as e:
            logger.error(f"Error processing Darvas for {ticker}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {executor.submit(_process_darvas, sym): sym for sym in ticker_list}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                logger.error(f"Darvas thread error for {future_to_symbol[future]}: {e}")
                pass

    return results

# -------------------------------------------------------------------------
#  SMC / ICT HELPER FUNCTIONS
# -------------------------------------------------------------------------

def _identify_swings(df: pd.DataFrame, lookback: int = 2) -> pd.DataFrame:
    """
    Identifies fractal Swing Highs and Swing Lows.
    A swing high is a high surrounded by lower highs on both sides.
    """
    df = df.copy()
    # Swing High
    df['Swing_High'] = df['High'][
        (df['High'] > df['High'].shift(1)) &
        (df['High'] > df['High'].shift(-1))
    ]
    # Swing Low
    df['Swing_Low'] = df['Low'][
        (df['Low'] < df['Low'].shift(1)) &
        (df['Low'] < df['Low'].shift(-1))
    ]
    return df

def _detect_fvgs(df: pd.DataFrame) -> list:
    """
    Detects unmitigated Fair Value Gaps (FVGs) in the last 20 candles.
    Returns a list of dicts: {'type': 'bull/bear', 'top': float, 'bottom': float, 'index': datetime}
    """
    fvgs = []
    # Iterate through recent candles (last 50 is enough for active setups)
    # We need index access, so we convert to records or iterate by index
    # Logic:
    # Bearish FVG: Low of candle[i-2] > High of candle[i]. Gap is between them.
    # Bullish FVG: High of candle[i-2] < Low of candle[i]. Gap is between them.

    if len(df) < 3:
        return []

    highs = df['High'].values
    lows = df['Low'].values
    times = df.index

    # Check last 30 candles
    start_idx = max(2, len(df) - 30)

    for i in range(start_idx, len(df)):
        # Bearish FVG (Down move)
        # Candle i (current), i-1 (displacement), i-2 (high anchor)
        # Gap exists if Low[i-2] > High[i]
        if lows[i-2] > highs[i]:
            gap_size = lows[i-2] - highs[i]
            # Filter tiny gaps (noise) - e.g., < 0.02% price
            if gap_size > (highs[i] * 0.0002):
                fvgs.append({
                    "type": "BEARISH",
                    "top": lows[i-2],
                    "bottom": highs[i],
                    "ts": times[i-1] # Timestamp of the big candle
                })

        # Bullish FVG (Up move)
        # Gap exists if High[i-2] < Low[i]
        if highs[i-2] < lows[i]:
            gap_size = lows[i] - highs[i-2]
            if gap_size > (lows[i] * 0.0002):
                fvgs.append({
                    "type": "BULLISH",
                    "top": lows[i],
                    "bottom": highs[i-2],
                    "ts": times[i-1]
                })
    return fvgs

def screen_mms_ote_setups(ticker_list: list = None, time_frame: str = "1h", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for ICT Market Maker Models + OTE (Optimal Trade Entry).

    Strategy:
    1.  Bias: Daily Trend.
    2.  Setup:
        -   Price Sweeps a Swing High/Low (Liquidity Raid).
        -   Reverses with DISPLACEMENT (leaving an FVG).
        -   Breaks Structure (MSS).
    3.  Trigger: Price is currently retracing into the OTE Zone (62-79% Fib).
    """
    import pandas as pd
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)

    # For OTE, we usually want Intraday data to see the displacement clearly.
    # 1h (60m) is a good balance for Swing Trading this model.
    yf_interval = "1h"
    period = "60d" # Max 60d for 1h data in yfinance
    is_intraday = True

    # Override for different timeframes
    if time_frame == "15m":
        yf_interval = "15m"
        period = "1mo" # Max 1mo for 15m
    elif time_frame == "1d":
        yf_interval = "1d"
        period = "1y"
        is_intraday = False

    resample_rule = None

    # Bulk download
    data = None
    try:
        # Use safe batch fetch
        data = fetch_batch_data_safe(ticker_list, period=period, interval=yf_interval)
    except Exception as e:
        logger.error(f"Failed to batch download for OTE: {e}")
        return []

    results = []

    def _process_ote(ticker):
        try:
            # Prepare data from batch
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            min_length = 50 if check_mode else 50 # OTE needs enough history for swings and fibs
            if df is None or len(df) < min_length:
                return None

            curr_close = float(df['Close'].iloc[-1])

            # Calc ATR
            import pandas_ta as ta
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            # 2. Identify Structure (Swings)
            df = _identify_swings(df, lookback=3)

            # Get last valid Swing High and Low
            last_swings_high = df[df['Swing_High'].notna()]
            last_swings_low = df[df['Swing_Low'].notna()]

            if last_swings_high.empty or last_swings_low.empty:
                return None

            # ---------------------------------------------------------
            # BEARISH SETUP (Market Maker Sell Model)
            # ---------------------------------------------------------
            # Logic:
            # A. Find the Highest High in recent window (Liquidity Pool)
            # B. Check if price swept it and rejected.
            # C. Check for displacement down.

            signal = "WAIT"
            setup_details = {}

            # Look at the last major swing high (e.g., from 10-50 bars ago)
            # We want a sweep of a SIGNIFICANT level, not just the last candle.

            recent_highs = last_swings_high.tail(5) # Get last 5 swing highs

            # Iterate backwards to find a setup
            # We look for a "Leg" that created a High, then broke a Low.

            # Simplified Logic for Screener:
            # 1. Find the highest point in the last 40 bars (extended from 20 to catch session highs).
            peak_idx = df['High'].iloc[-40:].idxmax()
            peak_high = df.loc[peak_idx, 'High']

            # 2. Verify displacement AFTER peak
            # Find lowest low AFTER the peak
            after_peak = df.loc[peak_idx:]
            if len(after_peak) < 3: return None # Too fresh

            valley_idx = after_peak['Low'].idxmin()
            valley_low = df.loc[valley_idx, 'Low']

            # 3. Calculate Fibonacci of this range (High -> Low)
            # Range for Bearish OTE: We draw Fib from High to Low.
            # OTE is retracement back UP to 62-79%.
            range_size = peak_high - valley_low
            fib_62 = peak_high - (range_size * 0.618)
            fib_79 = peak_high - (range_size * 0.79)

            # 4. Check if current price is IN the OTE zone
            # Bearish OTE: Price is between 62% and 79% retracement
            # (Which means it is HIGHER than the low)

            # Also check for FVG in the down leg
            fvgs = _detect_fvgs(after_peak)
            bearish_fvgs = [f for f in fvgs if f['type'] == "BEARISH"]
            has_fvg = len(bearish_fvgs) > 0

            if has_fvg and (fib_79 <= curr_close <= fib_62):
                 # One more check: Did we break structure?
                 # Ideally, the 'valley_low' should be lower than a PREVIOUS swing low (MSS)
                 # Find swing low BEFORE peak
                 before_peak = df.loc[:peak_idx].iloc[:-1] # exclude peak itself
                 if not before_peak.empty:
                     prev_swing_lows = before_peak[before_peak['Swing_Low'].notna()]
                     if not prev_swing_lows.empty:
                         last_structural_low = prev_swing_lows['Low'].iloc[-1]

                         if valley_low < last_structural_low:
                             signal = "🐻 BEARISH OTE (Sell)"
                             setup_details = {
                                 "stop": peak_high,
                                 "entry_zone": f"{fib_62:.2f} - {fib_79:.2f}",
                                 "target": valley_low - range_size # -1.0 extension
                             }

            # ---------------------------------------------------------
            # BULLISH SETUP (Market Maker Buy Model)
            # ---------------------------------------------------------
            if signal == "WAIT":
                # 1. Find the lowest low (The "Turtle Soup" / Raid) in the last 40 bars
                trough_idx = df['Low'].iloc[-40:].idxmin()
                trough_low = df.loc[trough_idx, 'Low']

                # 2. Find the Highest High *AFTER* that low (The Displacement High)
                # We need a rally that has essentially "finished" and is now pulling back
                after_trough = df.loc[trough_idx:]

                if len(after_trough) >= 5: # Need enough data for Low -> High -> Pullback
                    peak_up_idx = after_trough['High'].idxmax()
                    peak_up_high = df.loc[peak_up_idx, 'High']

                    # 3. Valid Setup Check: The High must be significantly above the Low
                    # and the *current* price must be below that High (Pullback phase)
                    if peak_up_high > trough_low and curr_close < peak_up_high:

                        # 4. Fibs (Low to High)
                        range_up = peak_up_high - trough_low
                        fib_62_up = trough_low + (range_up * 0.618)
                        fib_79_up = trough_low + (range_up * 0.79)

                        # 5. Check OTE Zone (Price is between 62% and 79% down from high)
                        # Note: In bullish OTE, we buy when price drops TO these levels.
                        # Price should be > 79% level (stop) and < 62% level (entry start)
                        # Correct Logic: We want price to be LOW (near 79%), but not below 100%.
                        # Usually OTE entry is defined as retracing *at least* 62%.

                        # Current Price <= 61.8% Retracement Price (Cheap)
                        # Current Price >= 79% Retracement Price (Not broken)

                        # Fix the fib comparison logic:
                        # 62% retracement means price dropped 0.62 of the range?
                        # No, usually OTE means price is at the 0.618 to 0.786 retracement level.
                        # So for Buy: Entry is at (Low + 0.382*Range) ??
                        # ICT OTE is measured from Low to High.
                        # Retracement down 62% = Price is at (High - 0.62*Range) = (Low + 0.38*Range)
                        # WAIT! Standard Fib tool draws 0 at High, 1 at Low for pullbacks?
                        # Let's stick to price levels:
                        # We want a DEEP pullback.
                        # Deep pullback means price is closer to Low than High.

                        retracement_pct = (peak_up_high - curr_close) / range_up

                        if 0.618 <= retracement_pct <= 0.79:
                             # 6. Check MSS (Did we break a prior High?)
                             # We look for a swing high *before* the trough that is LOWER than our new peak
                             before_trough = df.loc[:trough_idx].iloc[:-1]
                             valid_mss = False

                             if not before_trough.empty:
                                 # Find the most recent significant high before the crash
                                 # Simply: Was the peak_up_high higher than the high immediately preceding the low?
                                 last_pre_crash_high = before_trough['High'].tail(10).max()
                                 if peak_up_high > last_pre_crash_high:
                                     valid_mss = True

                             if valid_mss:
                                 signal = "🐂 BULLISH OTE (Buy)"
                                 setup_details = {
                                     "stop": trough_low,
                                     "entry_zone": f"{fib_62_up:.2f} - {fib_79_up:.2f}",
                                     "target": peak_up_high + range_up
                                 }

            # Rate limiting sleep
            time.sleep(0.1)

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            # Additional Calcs for Consistency
            # current_atr is already calculated above
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            
            if signal != "WAIT" or check_mode:
                # Calculate % Change
                pct_change_1d = None
                if len(df) >= 2:
                    try:
                        prev_close_px = float(df['Close'].iloc[-2])
                        pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                    except Exception:
                        pass

                return {
                    "ticker": ticker,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
                    "signal": signal,
                    "stop_loss": setup_details.get('stop', 0.0),
                    "ote_zone": setup_details.get('entry_zone', "N/A"),
                    "target": setup_details.get('target', 0.0),
                    "fvg_detected": "Yes",
                    "atr_value": round(current_atr, 2),
                    "volatility_pct": round(volatility_pct, 2),
                    "breakout_date": breakout_date,
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d
                }

        except Exception as e:
            logger.error(f"Error processing OTE for {ticker}: {e}")
            return None
        return None

    # Threaded execution
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {executor.submit(_process_ote, sym): sym for sym in ticker_list}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                logger.error(f"OTE thread error for {future_to_symbol[future]}: {e}")
                pass

    return results

# -------------------------------------------------------------------------
#  OPTIONS STRATEGY HELPERS (Add to option_auditor/screener.py)
# -------------------------------------------------------------------------
import math
from datetime import date

def _norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def _calculate_put_delta(S, K, T, r, sigma):
    """
    Estimates Put Delta using Black-Scholes.
    S: Spot Price, K: Strike, T: Time to Expiry (years), r: Risk-free rate, sigma: IV
    """
    if T <= 0 or sigma <= 0: return -0.5 # Fallback
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1) - 1.0

def screen_bull_put_spreads(ticker_list: list = None, min_roi: float = 0.15, region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for 45 DTE, 30-Delta Bull Put Spreads ($5 Wide).

    Logic:
    1. Filter for Bullish Trend (Price > SMA 50).
    2. Find Expiry closest to 45 DTE.
    3. Calculate Deltas to find Short Strike (~0.30 Delta).
    4. Find Long Strike ($5 lower).
    5. Calculate ROI (Credit / Collateral).
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd

    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)

    results = []

    # Risk-free rate approx
    RISK_FREE_RATE = 0.045
    TARGET_DTE = 45
    SPREAD_WIDTH = 5.0
    TARGET_DELTA = -0.30 # Puts have negative delta

    def _process_spread(ticker):
        try:
            # 1. Trend Filter (Fast Fail)
            # Create Ticker object (Thread-safe usage compared to yf.download batch issues)
            tk = yf.Ticker(ticker)

            # We need ~6 months of data for SMA 50 and stability check
            df = tk.history(period="6mo", interval="1d", auto_adjust=True)
            if df.empty: return None

            min_length = 50 if check_mode else 50 # Need 50 bars for SMA 50
            if len(df) < min_length: return None

            # Flatten columns if needed (history usually returns simple index but just in case)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            curr_price = float(df['Close'].iloc[-1])
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]

            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / curr_price * 100) if curr_price > 0 else 0.0

            # Trend Check: Only sell puts if stock is above SMA 50 (Bullish/Neutral)
            if curr_price < sma_50 and not check_mode:
                return None

            # 2. Get Option Dates
            expirations = tk.options
            if not expirations: return None

            # Find date closest to 45 DTE
            today = date.today()
            best_date = None
            min_diff = 999

            for exp_str in expirations:
                exp_date = pd.to_datetime(exp_str).date()
                dte = (exp_date - today).days
                diff = abs(dte - TARGET_DTE)
                if diff < min_diff:
                    min_diff = diff
                    best_date = exp_str

            # Filter: Ensure DTE is reasonably close (e.g. 30 to 60 days)
            actual_dte = (pd.to_datetime(best_date).date() - today).days
            if not (25 <= actual_dte <= 75) and not check_mode: return None

            # 3. Get Option Chain for that Date
            chain = tk.option_chain(best_date)
            puts = chain.puts

            if puts.empty: return None

            # 4. Find 30 Delta Strike
            # yfinance gives us 'impliedVolatility'. We calculate delta ourselves.
            # T in years
            T_years = actual_dte / 365.0

            # Calculate Delta for each row
            puts['calc_delta'] = puts.apply(
                lambda row: _calculate_put_delta(
                    curr_price, row['strike'], T_years, RISK_FREE_RATE, row['impliedVolatility']
                ), axis=1
            )

            # Find the row closest to -0.30
            # Sort by distance to target delta
            puts['delta_dist'] = (puts['calc_delta'] - TARGET_DELTA).abs()
            short_leg_row = puts.loc[puts['delta_dist'].idxmin()]

            short_strike = short_leg_row['strike']
            short_bid = short_leg_row['bid'] # We sell at bid (conservatively) or mid
            short_delta = short_leg_row['calc_delta']

            # 5. Find Long Strike ($5 Lower)
            long_strike_target = short_strike - SPREAD_WIDTH

            # Find strike closest to target (exact match preferred)
            puts['strike_dist'] = (puts['strike'] - long_strike_target).abs()
            long_leg_row = puts.loc[puts['strike_dist'].idxmin()]

            long_strike = long_leg_row['strike']
            long_ask = long_leg_row['ask'] # We buy at ask

            # Check if we actually found a $5 wide spread (allow small variance for weird strikes)
            actual_width = short_strike - long_strike
            if abs(actual_width - SPREAD_WIDTH) > 1.0 and not check_mode:
                return None # Could not find the defined spread width

            # 6. Calc Metrics
            # Credit = Price Sold - Price Bought
            # Note: yfinance data can be delayed/wide. We use midpoint if bid/ask is messy,
            # but strictly: Credit = Short_Bid - Long_Ask

            # Fallback to lastPrice if bid/ask is zero (market closed/illiquid)
            s_price = short_bid if short_bid > 0 else short_leg_row['lastPrice']
            l_price = long_ask if long_ask > 0 else long_leg_row['lastPrice']

            credit = s_price - l_price

            # Max Risk = Width - Credit
            risk = actual_width - credit

            if (risk <= 0 or credit <= 0) and not check_mode: return None # Yield too low

            roi = credit / risk

            if roi < min_roi and not check_mode: return None # Yield too low

            # Rate limiting sleep
            time.sleep(0.1)

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_price - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            # Additional Calcs for Consistency
            # current_atr is already calculated above
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()

            return {
                "ticker": ticker,
                "price": curr_price,
                "pct_change_1d": pct_change_1d,
                "strategy": "Bull Put Spread",
                "expiry": best_date,
                "dte": actual_dte,
                "short_strike": short_strike,
                "short_delta": round(short_delta, 2),
                "long_strike": long_strike,
                "credit": round(credit, 2),
                "max_risk": round(risk, 2),
                "roi_pct": round(roi * 100, 1),
                "trend": "Bullish (>SMA50)",
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "breakout_date": breakout_date,
                "atr": round(current_atr, 2),
                "52_week_high": round(high_52wk, 2) if high_52wk else None,
                "52_week_low": round(low_52wk, 2) if low_52wk else None,
                "sector_change": pct_change_1d
            }

        except Exception as e:
            logger.error(f"Error processing bull put spread for {ticker}: {e}")
            return None

    # Multi-threaded Execution
    import concurrent.futures
    final_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_process_spread, t): t for t in ticker_list}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: final_list.append(res)

    # Sort by ROI
    final_list.sort(key=lambda x: x['roi_pct'], reverse=True)
    return final_list

def resolve_ticker(query: str) -> str:
    """
    Resolves a query (Ticker or Company Name) to a valid ticker symbol.
    Uses TICKER_NAMES for lookup.
    """
    if not query: return ""
    query = query.strip().upper()

    # 1. Exact Ticker Match
    if query in TICKER_NAMES:
        return query

    # 2. Check suffix variations (.L, .NS)
    # If query has no suffix, check if query.L or query.NS exists in TICKER_NAMES
    if "." not in query:
        if f"{query}.L" in TICKER_NAMES: return f"{query}.L"
        if f"{query}.NS" in TICKER_NAMES: return f"{query}.NS"

    # 3. Name Search (Exact then Partial)
    # Exact Name
    for k, v in TICKER_NAMES.items():
        if v.upper() == query:
            return k

    # Partial Name
    for k, v in TICKER_NAMES.items():
        if query in v.upper():
            return k

    # 4. Fallback: Assume it is a valid ticker if no match found
    return query

def screen_trend_followers_isa(ticker_list: list = None, risk_per_trade_pct: float = 0.01, region: str = "us", check_mode: bool = False) -> list:
    """
    The 'Legendary Trend' Screener for ISA Accounts (Long Only).
    Based on Seykota/Dennis (Breakouts) and Tharp (Risk).

    Rules:
    1. Trend: Price > 200 SMA.
    2. Entry: Price >= 50-Day High.
    3. Exit/Stop: Trailing 3x ATR or 20-Day Low.
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd

    # Input Validation: Ensure risk_per_trade_pct is within sane bounds (0.1% to 10%)
    if not (0.001 <= risk_per_trade_pct <= 0.10):
        logger.warning(f"risk_per_trade_pct {risk_per_trade_pct} out of bounds (0.001-0.1). Resetting to 0.01.")
        risk_per_trade_pct = 0.01

    # Default to a mix of US and UK liquid stocks if none provided
    if ticker_list is None:
        if region == "uk_euro":
            ticker_list = get_uk_euro_tickers()
        elif region == "uk":
            from option_auditor.uk_stock_data import get_uk_tickers
            ticker_list = get_uk_tickers()
        elif region == "india":
            ticker_list = get_indian_tickers()
        elif region == "sp500":
             # S&P 500 filtered
             # For S&P 500, we specifically return filtered S&P 500 stocks.
             # We might add Watch list as well if requested, but separation implies purity.
             sp500 = _get_filtered_sp500(check_trend=True)
             # Also include WATCH list as per global logic "Always scan High Interest"
             watch_list = SECTOR_COMPONENTS.get("WATCH", [])
             ticker_list = list(set(sp500 + watch_list))
        else: # us / combined default
            # "US Market" = High Liquid Sector Components + Watch List
            all_tickers = []
            for t_list in SECTOR_COMPONENTS.values():
                all_tickers.extend(t_list)
            ticker_list = list(set(all_tickers))

    results = []

    # 1. Fetch Data
    # Use cached loader with region-specific key to prevent bans (especially India)
    cache_key = f"market_scan_{region}"
    data = pd.DataFrame()

    try:
        if len(ticker_list) > 50:
            # Use robust cached loader for large lists (handles chunking/sleep)
            data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_key)
        else:
            # Small lists can go direct, ensuring threads=True and grouping
            data = yf.download(ticker_list, period="2y", progress=False, threads=True, auto_adjust=True, group_by='ticker')

    except Exception as e:
        logger.error(f"Failed to load data for {region}: {e}")
        return []
    
    if data.empty:
        # Only log error if list wasn't empty to begin with
        if ticker_list:
            logger.error("❌ Yahoo returned NO DATA. You might be rate limited.")
        return []

    for ticker in ticker_list:
        try:
            # Robust extraction using shared utility
            df = _prepare_data_for_ticker(ticker, data, "1d", "2y", "1d", None, False)

            if df is None or df.empty: continue

            # Clean and validate
            df = df.dropna(how='all')
            # If check_mode is ON, we relax length requirements strictly for basic data
            min_length = 50 if check_mode else 200
            if len(df) < min_length: continue

            # Get latest price
            curr_close = float(df['Close'].iloc[-1])
            
            # Additional Calcs
            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1] if len(df) >= 14 else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            pct_change_1d = ((curr_close - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) >= 2 else 0.0

            # Liquidity Filter: Average Daily Dollar Volume > $5M
            # (Simons says: Liquidity First)
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if not check_mode and (avg_vol * curr_close) < 5_000_000:
                continue

            # Trend Filter: 200 SMA
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]

            # Breakout Levels: 50-Day High (Entry) & 20-Day Low (Exit)
            # Shift(1) because we want the high of the *previous* window to compare against today
            # We calculate rolling series for Breakout Date logic later
            df['High_50'] = df['High'].rolling(50).max().shift(1)
            df['Low_20'] = df['Low'].rolling(20).min().shift(1)

            high_50 = df['High_50'].iloc[-1]
            low_20 = df['Low_20'].iloc[-1]

            # Volatility: ATR 20
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)
            atr_20 = float(df['ATR'].iloc[-1])

            # 3. Apply The "Legend" Rules
            signal = "WAIT"

            # RULE 1: Long Term Trend
            if curr_close > sma_200:

                # RULE 2: Breakout Entry (Donchian Channel)
                if curr_close >= high_50:
                    signal = "🚀 ENTER LONG (50d Breakout)"

                # Watchlist: Price is near breakout (within 2%)
                elif curr_close >= high_50 * 0.98:
                    signal = "👀 WATCH (Near Breakout)"

                # Holding: Price is above exit
                elif curr_close > low_20:
                    signal = "✅ HOLD (Trend Active)"

                # Rule 3: Exit (Trailing Stop)
                elif curr_close <= low_20:
                    signal = "🛑 EXIT (Stop Hit)"
            else:
                signal = "❌ SELL/AVOID (Downtrend)"

            # 4. Van Tharp Risk Calculation
            # Stop Loss is 3 ATRs below price
            stop_price = curr_close - (3 * atr_20)

            # If entering, stop is 3 ATR below ENTRY (current price)
            # If holding, user should use trailing stop (low_20) OR 3 ATR?
            # The prompt says: "Exit... Trailing Stop. If price closes below the 20-Day Low... Initial Stop Loss = 3 x ATR"
            # So for New Entries, we report 3 ATR stop. For existing, we report 20d Low?
            # Let's report both or the relevant one.
            # We will return the 3ATR stop for the "Setup".

            risk_per_share = curr_close - stop_price

            # Distance from Stop
            # If entering, we look at Initial Stop (3 ATR).
            # If holding, we look at Trailing Stop (20d Low).
            effective_stop = stop_price
            if "HOLD" in signal or "EXIT" in signal:
                effective_stop = low_20

            dist_to_stop_pct = 0.0
            if curr_close > 0:
                dist_to_stop_pct = ((curr_close - effective_stop) / curr_close) * 100

            # --- VAN THARP SIZING CHECK ---
            # User Rule: Fixed 4% Position Sizing
            position_size_pct = 0.04

            # How much total equity is at risk?
            # Risk = Position Size * Distance to Stop
            risk_dist = max(0.0, dist_to_stop_pct)
            total_equity_risk_pct = position_size_pct * (risk_dist / 100.0)

            # Tharp's Limit: Never risk more than 1% of total equity on a trade
            is_tharp_safe = bool(total_equity_risk_pct <= 0.01)

            tharp_verdict = "✅ SAFE" if is_tharp_safe else f"⚠️ RISKY (Risks {total_equity_risk_pct*100:.1f}% Equity)"
            if dist_to_stop_pct <= 0:
                 tharp_verdict = "🛑 STOPPED OUT"

            suggested_size_val = 0.0
            if risk_dist > 0:
                 suggested_size_val = min(4.0, 1.0 / (risk_dist / 100.0))
            else:
                 suggested_size_val = 4.0

            max_position_size_str = f"{suggested_size_val:.1f}%"

            # Position Sizing Logic (The 4% Rule)
            # This is calculated by caller or frontend, but we provide metrics.

            volatility_pct = (atr_20 / curr_close) * 100

            # Additional: 1D Change
            # pct_change_1d is already calculated above

            # --- Breakout Date Logic ---
            breakout_date = _calculate_trend_breakout_date(df)


            # Filter results?
            # We return ENTER, WATCH, HOLD, and EXIT signals.
            # We skip AVOID (Downtrend) to reduce noise, unless explicitly requested?
            # The user wants to know "whether i should hold now".
            # If the stock is in a downtrend (AVOID) or Stop Hit (EXIT), it should be shown if the user searches for it.
            # However, showing 500 "AVOID" stocks is clutter.
            # We will include EXIT signals.
            # We will also include AVOID signals but flag them clearly.
            # Actually, let's include all so the user can audit any stock in the list.

            # Identify name
            # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            results.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": curr_close,
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "trend_200sma": "Bullish", # We filtered for this inside the signal logic
                "breakout_level": round(high_50, 2),
                "stop_loss_3atr": round(stop_price, 2),
                "trailing_exit_20d": round(low_20, 2),
                "volatility_pct": round(volatility_pct, 2),
                "atr_20": round(atr_20, 2),
                "atr_value": round(atr_20, 2),
                "risk_per_share": round(risk_per_share, 2),
                "dist_to_stop_pct": round(dist_to_stop_pct, 2),
                "tharp_verdict": tharp_verdict,
                "max_position_size": max_position_size_str,
                "breakout_date": breakout_date,
                "safe_to_trade": is_tharp_safe,
                "atr": round(current_atr, 2),
                "52_week_high": round(high_52wk, 2) if high_52wk else None,
                "52_week_low": round(low_52wk, 2) if low_52wk else None,
                "sector_change": pct_change_1d
            })

        except Exception as e:
            logger.error(f"ISA screener error for {ticker}: {e}")
            continue

    # Sort by signal priority
    # ENTER first, then WATCH, then HOLD
    def sort_key(x):
        s = x['signal']
        if "ENTER" in s: return 0
        if "WATCH" in s: return 1
        return 2

    results.sort(key=sort_key)
    return results

# -------------------------------------------------------------------------
#  FOURIER / CYCLE ANALYSIS HELPERS
# -------------------------------------------------------------------------
import numpy as np

def _calculate_dominant_cycle(prices):
    """
    Uses FFT to find the dominant cycle period (in days) of a price series.
    Returns: (period_days, current_phase_position)

    current_phase_position:
       0.0 = Bottom (Trough) -> Ideal Buy
       0.5 = Top (Peak)      -> Ideal Sell
       (Approximate sine wave mapping)
    """
    # 1. Prepare Data
    # We need a fixed window. Let's look at the last 64 or 128 days (power of 2 is faster for FFT)
    N = len(prices)
    if N < 64: return None

    # Use most recent 64 days for cycle detection (short-term cycles)
    # or 128/256 for longer cycles.
    window_size = 64
    y = np.array(prices[-window_size:])
    x = np.arange(window_size)

    # 2. Detrend (Remove the linear trend so we just see waves)
    # Simple linear regression detrending
    p = np.polyfit(x, y, 1)
    trend = np.polyval(p, x)
    detrended = y - trend

    # Apply a window function (Hanning) to reduce edge leakage
    windowed = detrended * np.hanning(window_size)

    # 3. FFT
    fft_output = np.fft.rfft(windowed)
    frequencies = np.fft.rfftfreq(window_size)

    # 4. Find Dominant Frequency (ignore DC component at index 0)
    # We look for the peak amplitude
    amplitudes = np.abs(fft_output)

    # Skip low frequencies (trends) and very high frequencies (noise)
    # We want cycles between 3 days and 30 days usually.
    # Index 0 is trend.
    peak_idx = np.argmax(amplitudes[1:]) + 1

    dominant_freq = frequencies[peak_idx]
    period = 1.0 / dominant_freq if dominant_freq > 0 else 0

    # 5. Determine Phase (Where are we now?)
    # Reconstruct the dominant wave
    # Sine wave: A * sin(2*pi*f*t + phase)
    # We check the phase of the last point (t = window_size - 1)

    # Simple Heuristic: Check the detrended value relative to recent range
    # If detrended[-1] is near the minimum of the last cycle, we are at trough.

    current_val = detrended[-1]
    cycle_range = np.max(detrended) - np.min(detrended)

    # Normalized position (-1.0 to 1.0)
    rel_pos = current_val / (cycle_range / 2.0) if cycle_range > 0 else 0

    return round(period, 1), rel_pos

def screen_fourier_cycles(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for stocks at the BOTTOM of their dominant time cycle (Fourier).
    Best for 'Swing Trading' in sideways or gently trending markets.
    """
    import yfinance as yf
    import pandas as pd

    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)

    results = []

    # Fetch Data (Need history for FFT)
    try:
        # Use safe batch fetch
        data = fetch_batch_data_safe(ticker_list, period="1y", interval="1d", chunk_size=100)
    except:
        return []

    for ticker in ticker_list:
        try:
            df = pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data.columns.levels[0]:
                    df = data[ticker].copy()
            else:
                df = data.copy()

            df = df.dropna(how='all')
            if len(df) < 100: continue

            closes = df['Close'].tolist()

            import pandas_ta as ta
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / float(closes[-1]) * 100) if float(closes[-1]) > 0 else 0.0

            # --- FOURIER CALC ---
            cycle_data = _calculate_dominant_cycle(closes)
            if not cycle_data: continue

            period, rel_pos = cycle_data

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    curr_close = float(df['Close'].iloc[-1])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            # Interpret Result
            # Period: Length of cycle (e.g., 14.2 days)
            # Rel Pos: -1.0 (Bottom) to 1.0 (Top)

            signal = "WAIT"
            verdict_color = "gray"

            # Trading Rules:
            # 1. Cycle must be actionable (e.g., 5 to 40 days).
            #    If period is 2 days, it's noise. If 200 days, it's a trend.
            if 5 <= period <= 60:
                if rel_pos <= -0.8:
                    signal = "🌊 CYCLICAL LOW (Buy)"
                    verdict_color = "green"
                elif rel_pos >= 0.8:
                    signal = "🏔️ CYCLICAL HIGH (Sell)"
                    verdict_color = "red"
                elif -0.2 <= rel_pos <= 0.2:
                    signal = "➡️ MID-CYCLE (Neutral)"
            else:
                # Cycle is too short (noise) or too long (trend) to trade as a cycle
                continue

            # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            results.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": float(closes[-1]),
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "cycle_period": f"{period} Days",
                "cycle_position": f"{rel_pos:.2f} (-1 Low, +1 High)",
                "verdict_color": verdict_color,
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "breakout_date": breakout_date
            })

        except Exception:
            continue

    # Sort: Buys first
    results.sort(key=lambda x: x['cycle_position'])
    return results

class StrategyAnalyzer:
    """
    Runs multiple strategies on a single dataframe to verify confluence.
    """
    def __init__(self, df):
        self.df = df
        try:
            self.close = df['Close'].iloc[-1]
            self.len = len(df)
        except Exception:
            self.len = 0

    def check_isa_trend(self):
        if self.len < 200: return "N/A"
        try:
            sma_200 = self.df['Close'].rolling(200).mean().iloc[-1]
            return "BULLISH" if self.close > sma_200 else "BEARISH"
        except Exception:
            return "N/A"

    def check_fourier(self):
        if self.len < 64: return "N/A", 0.0
        try:
            # Use the existing helper function
            cycle_data = _calculate_dominant_cycle(self.df['Close'].tolist())
            if not cycle_data: return "N/A", 0.0
            period, rel_pos = cycle_data

            if rel_pos <= -0.8: return "BOTTOM", rel_pos
            if rel_pos >= 0.8: return "TOP", rel_pos
            return "NEUTRAL", rel_pos
        except Exception:
            return "N/A", 0.0

    def check_momentum(self):
        if self.len < 14: return "NEUTRAL"
        # Simple RSI check
        import pandas_ta as ta
        # Check if RSI column exists, if not calculate
        # We need to be careful not to modify the original df if it is used elsewhere without copying
        # But here we pass a copy usually.

        # Check if 'RSI_14' or 'RSI' exists
        rsi_val = None
        if 'RSI_14' in self.df.columns:
             rsi_val = self.df['RSI_14'].iloc[-1]
        elif 'RSI' in self.df.columns:
             rsi_val = self.df['RSI'].iloc[-1]
        else:
             try:
                 # Calculate temp
                 rsi_s = ta.rsi(self.df['Close'], length=14)
                 if rsi_s is not None and not rsi_s.empty:
                    rsi_val = rsi_s.iloc[-1]
             except Exception:
                 pass

        if rsi_val is None or pd.isna(rsi_val): return "NEUTRAL"

        if rsi_val < 30: return "OVERSOLD"
        if rsi_val > 70: return "OVERBOUGHT"
        return "NEUTRAL"

def screen_hybrid_strategy(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Robust Hybrid Screener with CHUNKING to prevent API Timeouts.
    Combines ISA Trend Following with Fourier Cycle Analysis.
    Goal: Find 'Buy the Dip' opportunities in strong uptrends.
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd
    import numpy as np

    if ticker_list is None:
        ticker_list = _resolve_region_tickers(region)
    
    # Ensure tickers are uppercase to match yfinance index
    if ticker_list:
        ticker_list = [t.upper() for t in ticker_list]
        
    results = []

    # Sort out Cache Logic
    is_large_scan = False
    if ticker_list and len(ticker_list) > 100: is_large_scan = True

    print(f"DEBUG: screen_hybrid_strategy region={region} ticker_len={len(ticker_list) if ticker_list else 0}", flush=True)

    cache_name = "watchlist_scan"
    if region == "india":
         cache_name = "market_scan_india"
    elif region == "uk":
         cache_name = "market_scan_uk"
    elif region == "uk_euro":
         cache_name = "market_scan_europe"
    elif is_large_scan:
         cache_name = "market_scan_v1"

    print(f"DEBUG: using cache_name={cache_name}", flush=True)

    # Only use cache for daily timeframe (intraday needs fresh data)
    if check_mode:
        # Force fresh fetch for individual checks
        all_data = fetch_batch_data_safe(ticker_list, period="2y", interval=time_frame)
    elif time_frame == "1d":
        all_data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_name)
    else:
        # Intraday
        all_data = fetch_batch_data_safe(ticker_list, period="5d", interval=time_frame)

    print(f"DEBUG: all_data type={type(all_data)} empty={all_data.empty if isinstance(all_data, pd.DataFrame) else 'N/A'}", flush=True)
    if isinstance(all_data, pd.DataFrame):
         print(f"DEBUG: all_data columns={all_data.columns}", flush=True)

    # Process Data
    # Get list of successfully downloaded tickers
    if isinstance(all_data.columns, pd.MultiIndex):
        valid_tickers = all_data.columns.levels[0].intersection(ticker_list)
    else:
        # Fallback if only 1 ticker in list or flat structure
        if not all_data.empty:
             val_tickers = [] # placeholder
             # If flat and we requested multiple, it might be weird.
             # But if we requested 1 ticker, it is flat.
             # If we requested multiple and only 1 came back, it might be flat or multi.
             # yfinance usually returns MultiIndex for >1 ticker.
             # If only 1 ticker in the list passed to download, it returns flat.
             # Here we accumulate.
             valid_tickers = ticker_list if len(ticker_list) == 1 else []
        else:
             valid_tickers = []

    for ticker in valid_tickers:
        try:
            df = pd.DataFrame()
            if isinstance(all_data.columns, pd.MultiIndex):
                if ticker in all_data.columns.levels[0]:
                    df = all_data[ticker].copy()
            else:
                # If only one ticker was requested/returned
                df = all_data.copy()

            df = df.dropna(how='all')
            
            # If check_mode is ON, we relax length requirements strictly for basic data
            min_length = 50 if check_mode else 200
            if len(df) < min_length: continue

            curr_close = float(df['Close'].iloc[-1])
            closes = df['Close'].tolist()

            # --- STEP 1: ISA TREND ANALYSIS ---
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]
            high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]

            # New Metrics for User
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            
            # Simple Sector Change Placeholder (future enhancement: map real sector performance)
            # For now, just return this stock's change as a proxy or null if unknown
            sector_change_pct = None
            
            trend_verdict = "NEUTRAL"
            if curr_close > sma_200:
                trend_verdict = "BULLISH"
            else:
                trend_verdict = "BEARISH"

            # Check Breakout status
            is_breakout = curr_close >= high_50

            # --- STEP 2: FOURIER CYCLE ANALYSIS ---
            cycle_data = _calculate_dominant_cycle(closes) # Re-using your helper

            cycle_state = "NEUTRAL"
            cycle_score = 0.0 # -1.0 (Low) to 1.0 (High)
            period = 0

            if cycle_data:
                period, rel_pos = cycle_data
                cycle_score = rel_pos

                # Define Cycle States
                if rel_pos <= -0.7:
                    cycle_state = "BOTTOM"
                elif rel_pos >= 0.7:
                    cycle_state = "TOP"
                else:
                    cycle_state = "MID"

            # Volume Filter (Anti-Double-Tap Fix):
            # If scanning daily (1d), ensure we aren't wasting time on illiquid stocks (<500k avg vol).
            # Skip this check for WATCH list items (High Interest) OR if check_mode is ON.
            if time_frame == "1d" and not check_mode:
                watch_list = SECTOR_COMPONENTS.get("WATCH", [])
                if ticker not in watch_list:
                    # Calculate 20-day Avg Volume
                    if 'Volume' in df.columns:
                        avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                        if avg_vol < 500000:
                            continue

            # --- STEP 3: SAFETY CHECKS (The "Anti-Falling Knife" Logic) ---

            # 1. Get Price Action Data
            today_open = float(df['Open'].iloc[-1])
            yesterday_close = float(df['Close'].iloc[-2])
            yesterday_low = float(df['Low'].iloc[-2])

            # 2. Falling Knife Guards
            # Guard 1: The "Green Candle" Rule (Buyers must step in)
            is_green_candle = curr_close > today_open

            # Guard 2: The "Panic" Rule (ATR)
            # If today's range is huge (> 2x ATR), it's a crash/panic.
            # Ensure ATR is calculated first
            if 'ATR' not in df.columns:
                df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

            current_atr = 0.0
            if 'ATR' in df.columns and not df['ATR'].empty:
                 current_atr = df['ATR'].iloc[-1]
            if pd.isna(current_atr): current_atr = 0.0

            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            daily_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
            is_panic_selling = daily_range > (2.0 * current_atr) if current_atr > 0 else False

            # Guard 3: Momentum Hook
            # Don't buy if we made a lower low than yesterday and closed near it
            is_making_lower_lows = curr_close < yesterday_low

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            # --- STEP 4: SYNTHESIZE VERDICT ---
            final_signal = "WAIT"
            color = "gray"
            score = 0 # 0 to 100 confidence

            # --- STEP 5: CALCULATE EXITS (Risk Management) ---

            stop_loss_price = curr_close - (3 * current_atr) # 3 ATR below entry

            # Cycle Target (Projected)
            target_price = curr_close + (2 * current_atr)

            # Risk/Reward Ratio Check
            potential_reward = target_price - curr_close
            potential_risk = curr_close - stop_loss_price
            rr_ratio = potential_reward / potential_risk if potential_risk > 0 else 0

            rr_verdict = "✅ GOOD" if rr_ratio >= 1.5 else "⚠️ POOR R/R"

            # Scenario A: Bullish Trend + Cycle Bottom (High Probability Setup)
            if trend_verdict == "BULLISH" and cycle_state == "BOTTOM":
                # Apply Safety Checks
                if is_panic_selling:
                    final_signal = "🛑 CRASH DETECTED (High Volatility) - WAIT"
                    color = "red"
                    score = 20
                elif is_making_lower_lows:
                    final_signal = "⚠️ WAIT (Falling Knife - Making Lower Lows)"
                    color = "orange"
                    score = 40
                elif not is_green_candle:
                    final_signal = "⏳ WATCHING (Waiting for Green Candle)"
                    color = "yellow"
                    score = 60
                else:
                    # Confirmed Turn
                    final_signal = "🚀 PERFECT BUY (Confirmed Turn)"
                    color = "green"
                    score = 95

            # Scenario B: Bullish Trend + Breakout (Momentum Buy)
            elif trend_verdict == "BULLISH" and is_breakout:
                # If breakout but cycle is TOP, it's risky but still a buy
                if cycle_state == "TOP":
                    final_signal = "⚠️ MOMENTUM BUY (Cycle High)"
                    color = "orange"
                    score = 75
                else:
                    final_signal = "✅ BREAKOUT BUY"
                    color = "green"
                    score = 85

            # Scenario C: Bearish Trend + Cycle Top (Perfect Short)
            elif trend_verdict == "BEARISH" and cycle_state == "TOP":
                final_signal = "📉 PERFECT SHORT (Rally in Downtrend)"
                color = "red"
                score = 90

            # Scenario D: Conflicts
            elif trend_verdict == "BULLISH" and cycle_state == "TOP":
                final_signal = "🛑 WAIT (Extended)"
                color = "yellow"
            elif trend_verdict == "BEARISH" and cycle_state == "BOTTOM":
                final_signal = "🛑 WAIT (Oversold Downtrend)"
                color = "yellow"

            # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            results.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": curr_close,
                "verdict": final_signal,
                "trend": trend_verdict,
                "cycle": f"{cycle_state} ({cycle_score:.2f})",
                "period_days": period,
                "score": score,
                "color": color,
                "signal": final_signal, # For frontend compatibility with 'signal' key
                "pct_change_1d": pct_change_1d,
                "stop_loss": round(stop_loss_price, 2),   # <--- THE STOP
                "target": round(target_price, 2),         # <--- THE TARGET
                "rr_ratio": f"{rr_ratio:.2f} ({rr_verdict})", # <--- IS IT WORTH IT?
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "breakout_date": breakout_date,
                "atr": round(current_atr, 2),
                "52_week_high": round(high_52wk, 2) if high_52wk else None,
                "52_week_low": round(low_52wk, 2) if low_52wk else None,
                "sector_change": pct_change_1d
            })

        except Exception as e:
            # logger.debug(f"Hybrid screener error for {ticker}: {e}")
            continue

    # Sort by 'Score' descending (best setups first)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def screen_master_convergence(ticker_list: list = None, region: str = "us", check_mode: bool = False) -> list:
    """
    Runs ALL strategies on the dataset to find CONFLUENCE.
    Uses Caching to prevent timeouts on S&P 500 scans.
    """
    # 1. Determine Ticker List
    if ticker_list is None:
        if region == "sp500":
             # OPTIMIZATION: Avoid _get_filtered_sp500 as it triggers a synchronous download.
             # Instead, get ALL S&P 500 tickers and rely on get_cached_market_data to serve from cache.
             # Filtering will happen inside the loop below.
             base_tickers = get_sp500_tickers()

             # Also include WATCH list
             watch_list = SECTOR_COMPONENTS.get("WATCH", [])
             ticker_list = list(set(base_tickers + watch_list))
        else:
             ticker_list = SECTOR_COMPONENTS.get("WATCH", [])

    # 2. Download Data (CACHE IMPLEMENTATION)
    # Using 'market_scan_v1' cache ensures we reuse the data fetched by the background worker
    # Logic update: Use list length or region
    is_large = len(ticker_list) > 100 or region == "sp500"
    cache_name = "market_scan_v1" if is_large else "watchlist_scan"

    try:
        if check_mode:
             all_data = fetch_batch_data_safe(ticker_list, period="2y", interval="1d")
        else:
            # This replaces the entire slow "chunking" loop you had before
            # Note: If region=sp500, we are requesting ~500 tickers.
            # get_cached_market_data will check cache "market_scan_v1".
            # This cache is populated by refresh_cache.py with get_sp500_tickers().
            # So it should be a hit.
            all_data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_name)
    except Exception as e:
        logger.error(f"Master screener data fetch failed: {e}")
        return []

    results = []

    # Handle empty data
    if all_data.empty:
        return []

    # 3. Process Data (Existing Logic)
    if isinstance(all_data.columns, pd.MultiIndex):
        # Intersect with ticker_list to ensure we only process what we asked for
        valid_tickers = [t for t in ticker_list if t in all_data.columns.levels[0]]
    else:
        valid_tickers = ticker_list if not all_data.empty else []

    watch_list = SECTOR_COMPONENTS.get("WATCH", [])

    for ticker in valid_tickers:
        try:
            df = pd.DataFrame()
            if isinstance(all_data.columns, pd.MultiIndex):
                if ticker in all_data.columns.levels[0]:
                    df = all_data[ticker].copy()
            else:
                df = all_data.copy()

            df = df.dropna(how='all')
            if len(df) < 200: continue

            # Volume Filter (Optimization):
            # If region is S&P 500, we skipped pre-filtering. So we filter here.
            # Skip for WATCH list items.
            if region == "sp500" and ticker not in watch_list:
                if 'Volume' in df.columns:
                     avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                     if avg_vol < 500000: continue

            # --- RUN ALL STRATEGIES ---
            analyzer = StrategyAnalyzer(df)

            isa_trend = analyzer.check_isa_trend()
            fourier, f_score = analyzer.check_fourier()
            momentum = analyzer.check_momentum()

            # Confluence Score
            score = 0
            signals = []

            if isa_trend == "BULLISH": score += 1
            if fourier == "BOTTOM":
                score += 2
                signals.append("Cycle Bottom")
            if momentum == "OVERSOLD" and isa_trend == "BULLISH":
                score += 1
                signals.append("Dip Buy")

            final_verdict = "WAIT"
            if score >= 3: final_verdict = "🔥 STRONG BUY"
            elif score == 2: final_verdict = "✅ BUY"
            elif isa_trend == "BEARISH" and fourier == "TOP": final_verdict = "📉 STRONG SELL"

            # Identify name
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            # Extract price safely
            curr_price = df['Close'].iloc[-1]
            if pd.isna(curr_price): continue

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_price - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            # Calculate ATR for reporting
            import pandas_ta as ta
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / curr_price * 100) if curr_price > 0 else 0.0

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            results.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": float(curr_price),
                "pct_change_1d": pct_change_1d,
                "isa_trend": isa_trend,
                "fourier": f"{fourier} ({f_score:.2f})",
                "momentum": momentum,
                "confluence_score": score,
                "verdict": final_verdict,
                "signals": ", ".join(signals),
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "breakout_date": breakout_date
            })

        except Exception: continue

    results.sort(key=lambda x: x['confluence_score'], reverse=True)
    return results

def screen_monte_carlo_forecast(ticker: str, days: int = 30, sims: int = 100):
    """
    Project stock price 30 days out using Monte Carlo (GBM).
    Useful for seeing if a 'Short Put' strike is safe.
    """
    import numpy as np
    import yfinance as yf

    try:
        # Get historical volatility
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty or len(df) < 30: return None

        # Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            try:
                if ticker in df.columns.levels[0]:
                    df = df[ticker].copy()
                else:
                    df.columns = df.columns.get_level_values(0)
            except: pass

        returns = df['Close'].pct_change().dropna()
        if returns.empty: return None

        last_price = float(df['Close'].iloc[-1])

        # Calculate daily drift and volatility
        mu = returns.mean()
        sigma = returns.std()

        # Simulation
        # Price_t = Price_0 * exp( (mu - 0.5*sigma^2)t + sigma * W_t )
        # Generate random paths
        # Shape: (days, sims)
        daily_returns = np.random.normal(mu, sigma, (days, sims)) + 1
        price_paths = last_price * daily_returns.cumprod(axis=0)

        # Outcomes
        final_prices = price_paths[-1]
        prob_below_90pct = np.mean(final_prices < (last_price * 0.90)) * 100

        return {
            "ticker": ticker,
            "current": last_price,
            "median_forecast": np.median(final_prices),
            "prob_drop_10pct": f"{prob_below_90pct:.1f}%",
            "volatility_annual": f"{sigma * np.sqrt(252) * 100:.1f}%"
        }
    except Exception as e:
        logger.debug(f"Monte Carlo forecast error for {ticker}: {e}")
        return None

def screen_dynamic_volatility_fortress(ticker_list: list = None) -> list:
    """
    YIELD-OPTIMIZED STRATEGY:
    - Tightens strikes in low VIX regimes to ensure decent premiums.
    - FILTERS OUT low-volatility stocks (Dead Money).
    - Focuses on High Beta names where implied volatility pays well.
    """
    import pandas as pd
    import pandas_ta as ta
    import yfinance as yf
    from datetime import datetime, timedelta
    from option_auditor.common.data_utils import get_cached_market_data
    from option_auditor.common.constants import LIQUID_OPTION_TICKERS

    # --- 1. GET VIX & REGIME ---
    try:
        vix_df = yf.download("^VIX", period="5d", progress=False)
        current_vix = float(vix_df['Close'].iloc[-1])
    except:
        current_vix = 14.0 # Default to "Low-ish" if fail

    # --- 2. THE NEW "YIELD" MATH ---
    # In low VIX, we must get closer to the fire to feel the heat (premium).
    # Floor at 1.5x ATR, Cap at 3.0x ATR.
    safety_k = 1.5 + ((current_vix - 12) / 15.0)

    # Clamping
    if safety_k < 1.5: safety_k = 1.5  # Never get closer than 1.5 ATR (Gamma Risk)
    if safety_k > 3.0: safety_k = 3.0  # Cap max distance

    # --- 3. FILTER UNIVERSE ---
    if ticker_list is None:
        ticker_list = LIQUID_OPTION_TICKERS

    all_data = get_cached_market_data(ticker_list, period="1y", cache_name="market_scan_us_liquid")
    results = []

    today = datetime.now()
    manage_date = today + timedelta(days=24)

    # MultiIndex Handler
    if isinstance(all_data.columns, pd.MultiIndex):
        valid_tickers = all_data.columns.levels[0]
    else:
        valid_tickers = ticker_list

    for ticker in valid_tickers:
        try:
            df = pd.DataFrame()
            if isinstance(all_data.columns, pd.MultiIndex):
                if ticker in all_data.columns.levels[0]:
                    df = all_data[ticker].copy()
            else:
                df = all_data.copy()

            df = df.dropna(how='all')
            if len(df) < 100: continue

            curr_close = df['Close'].iloc[-1]

            # --- CRITICAL FILTER: DEAD MONEY CHECK ---
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            atr = df['ATR'].iloc[-1]

            atr_pct = (atr / curr_close) * 100

            # IF STOCK IS TOO BORING (<2% Volatility), OPTIONS ARE WORTHLESS. SKIP IT.
            if atr_pct < 2.0 and current_vix < 20:
                continue

            # Trend Check (Only Bullish)
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]

            trend_status = "Bullish" if curr_close > sma_200 else "Neutral" # Or specific based on SMA

            # Relaxed Trend: Price > SMA50 (Momentum) is enough for 45DTE trades
            if curr_close < sma_50: continue

            # --- STRIKE CALCULATION ---
            # Using EMA(20) as it tracks price tighter than SMA
            ema_20 = ta.ema(df['Close'], length=20).iloc[-1]

            # Strike Floor
            safe_floor = ema_20 - (safety_k * atr)

            if safe_floor >= curr_close: continue

            # Rounding to actionable strikes
            if curr_close < 100:
                short_strike = float(int(safe_floor)) # Round down to nearest $1
                spread_width = 1.0 # Tight spread for cheap stocks
            elif curr_close < 300:
                short_strike = float(int(safe_floor / 2.5) * 2.5) # Nearest $2.50
                spread_width = 5.0
            else:
                short_strike = float(int(safe_floor / 5) * 5) # Nearest $5
                spread_width = 10.0

            long_strike = short_strike - spread_width

            # --- SCORING ---
            # We score by "Juice" (Volatility)
            score = atr_pct * 10

            # Bonus for strong uptrend (Price > SMA200 too)
            if curr_close > sma_200: score += 15

            results.append({
                "ticker": ticker,
                "price": round(curr_close, 2),
                "vix_ref": round(current_vix, 2),
                "volatility_pct": f"{atr_pct:.1f}%", # Show me the juice
                "safety_mult": f"{safety_k:.1f}x",
                "sell_strike": short_strike,
                "buy_strike": long_strike,
                "dist_pct": f"{((curr_close - short_strike)/curr_close)*100:.1f}%",
                "score": round(score, 1),
                "trend": trend_status
            })

        except Exception: continue

    # Sort by Score (High Volatility First) -> The ones that actually pay money
    results.sort(key=lambda x: x['score'], reverse=True)
    return results
def sanitize(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, float):
        return round(val, 2)
    return val

def screen_quantum_setups(ticker_list: list = None, region: str = "us") -> list:
    """
    Screens for 'Quantum' setups using Physics-based metrics (Hurst, Entropy, Kalman).
    """
    # Imports inside function to avoid circular deps if needed, but QuantPhysicsEngine is needed
    from option_auditor.quant_engine import QuantPhysicsEngine
    import pandas_ta as ta

    # ... (Keep existing imports and setup logic) ...
    try:
        from option_auditor.common.constants import LIQUID_OPTION_TICKERS
    except ImportError:
        LIQUID_OPTION_TICKERS = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL"]

    if ticker_list is None:
        if region == "us":
            ticker_list = LIQUID_OPTION_TICKERS
        else:
             ticker_list = _resolve_region_tickers(region)

    # Fetch Data
    # Use 200 days minimum for Hurst/Entropy
    # Batch fetch
    try:
        data = fetch_batch_data_safe(ticker_list, period="2y", interval="1d")
    except Exception as e:
        logger.error(f"Quantum screener fetch failed: {e}")
        return []

    results = []

    # Helper for batch data processing
    if isinstance(data.columns, pd.MultiIndex):
        valid_tickers = [t for t in ticker_list if t in data.columns.levels[0]]
    else:
        valid_tickers = ticker_list if not data.empty else []

    # ... inside process_ticker(ticker): ...
    def process_ticker(ticker):
        try:
            # ... (Existing data extraction code) ...
            df = pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data.columns.levels[0]:
                    df = data[ticker].copy()
            else:
                df = data.copy()

            if df is None or df.empty: return None

            df = df.dropna(how='all')
            if len(df) < 200: return None

            close = df['Close']
            curr_price = float(close.iloc[-1])

            # --- PHYSICS ENGINE ---
            hurst = QuantPhysicsEngine.calculate_hurst(close)
            if hurst is None: return None

            entropy = QuantPhysicsEngine.shannon_entropy(close)
            kalman = QuantPhysicsEngine.kalman_filter(close)
            phase = QuantPhysicsEngine.instantaneous_phase(close)

            # --- FIX 1: SMOOTHER SLOPE CALCULATION ---
            # Old: (iloc[-1] - iloc[-3]) / 2.0 (Too sensitive)
            # New: 10-day Lookback for robust trend direction
            lookback = 10
            if len(kalman) > lookback:
                k_slope = (kalman.iloc[-1] - kalman.iloc[-1 - lookback]) / float(lookback)
            else:
                k_slope = 0.0

            # --- SCORING LOGIC ---
            score = 50
            kalman_signal = "FLAT"

            if k_slope > 0:
                kalman_signal = "UPTREND"
            elif k_slope < 0:
                kalman_signal = "DOWNTREND"

            if hurst > 0.60: score += 20 # Updated threshold
            if entropy < 0.8: score += 15
            if k_slope > 0: score += 15
            elif k_slope < 0: score -= 15

            if hurst < 0.40:
                score = 65

            # --- HUMAN VERDICT ---
            ai_verdict, ai_rationale = QuantPhysicsEngine.generate_human_verdict(hurst, entropy, k_slope, curr_price)

            verdict_color = "gray"
            if "BUY" in ai_verdict:
                verdict_color = "green"
            elif "SHORT" in ai_verdict:
                verdict_color = "red"
            elif "REVERSAL" in ai_verdict:
                verdict_color = "yellow"

            # --- FIX 2: ADD ATR, TARGET, STOP LOSS ---
            # import pandas_ta as ta # already imported
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0

            # Default to 0.0
            stop_loss = 0.0
            target_price = 0.0

            # Calculate Targets based on Direction
            if "BUY" in ai_verdict:
                # Long: Stop below, Target above
                stop_loss = curr_price - (2.0 * current_atr)
                target_price = curr_price + (3.0 * current_atr)
            elif "SHORT" in ai_verdict:
                # Short: Stop above, Target below
                stop_loss = curr_price + (2.0 * current_atr)
                target_price = curr_price - (3.0 * current_atr)
            else:
                # Neutral/Wait - just show levels relative to price for reference
                stop_loss = curr_price - (2.0 * current_atr)
                target_price = curr_price + (3.0 * current_atr)

            volatility_pct = (current_atr / curr_price * 100) if curr_price > 0 else 0.0

            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_price - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            breakout_date = _calculate_trend_breakout_date(df)
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": sanitize(curr_price),
                "hurst": sanitize(hurst),
                "entropy": sanitize(entropy),
                "kalman_signal": kalman_signal,
                "kalman_diff": sanitize(k_slope),
                "phase": sanitize(phase),
                "score": sanitize(score),
                "human_verdict": ai_verdict,
                "signal": ai_verdict,
                "rationale": ai_rationale,
                "verdict_color": verdict_color,

                # --- NEW COLUMNS ---
                "atr_value": sanitize(round(current_atr, 2)),  # Existing key
                "ATR": sanitize(round(current_atr, 2)),        # Requested key
                "Stop Loss": sanitize(round(stop_loss, 2)),    # Requested key
                "Target": sanitize(round(target_price, 2)),    # Requested key

                "volatility_pct": sanitize(round(volatility_pct, 2)),
                "pct_change_1d": sanitize(pct_change_1d),
                "breakout_date": breakout_date
            }
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            return None

    # Thread Pool
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ticker = {executor.submit(process_ticker, t): t for t in valid_tickers}
        for future in as_completed(future_to_ticker):
             res = future.result()
             if res: results.append(res)

    # Sort by score
    results.sort(key=lambda x: x['score'] if x and x['score'] else 0, reverse=True)
    return results
