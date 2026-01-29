import logging
import pandas_ta as ta
import yfinance as yf
from option_auditor.common.screener_utils import (
    ScreeningRunner,
    resolve_region_tickers,
    DEFAULT_RSI_LENGTH,
    DEFAULT_ATR_LENGTH,
    DEFAULT_SMA_FAST
)
from option_auditor.common.constants import (
    SECTOR_NAMES,
    SECTOR_COMPONENTS,
    TICKER_NAMES
)
from option_auditor.common.data_utils import _calculate_trend_breakout_date

logger = logging.getLogger(__name__)

def enrich_with_fundamentals(results_list: list) -> list:
    """
    Fetches PE Ratio and Sector data ONLY for the stocks that passed the screener.
    significantly faster than fetching for the whole universe.
    """
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

def screen_tickers_helper(tickers: list, iv_rank_threshold: float, rsi_threshold: float, time_frame: str) -> list:
    """
    Internal helper to screen a list of tickers using ScreeningRunner.
    """
    runner = ScreeningRunner(ticker_list=tickers, time_frame=time_frame, region="us") # Region param mainly for resolution, but tickers already resolved

    def strategy(symbol, df):
        try:
            # Volume Filter: If scanning daily/weekly (not intraday), skip illiquid stocks (< 500k avg volume)
            if not runner.is_intraday and len(df) >= 20:
                if 'Volume' in df.columns:
                    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                    if avg_vol < 500000:
                        return None

            # Calculate % Change
            pct_change_1d = None
            pct_change_1w = None

            try:
                curr_close = float(df['Close'].iloc[-1])

                if runner.is_intraday:
                    unique_dates = sorted(list(set(df.index.date)))
                    if len(unique_dates) > 1:
                        prev_date = unique_dates[-2]
                        prev_day_df = df[df.index.date == prev_date]
                        if not prev_day_df.empty:
                            prev_close = float(prev_day_df['Close'].iloc[-1])
                            pct_change_1d = ((curr_close - prev_close) / prev_close) * 100

                    if len(unique_dates) > 5:
                         week_ago_date = unique_dates[-6]
                         week_df = df[df.index.date == week_ago_date]
                         if not week_df.empty:
                             week_close = float(week_df['Close'].iloc[-1])
                             pct_change_1w = ((curr_close - week_close) / week_close) * 100
                else:
                    if len(df) >= 2:
                        prev_close = float(df['Close'].iloc[-2])
                        pct_change_1d = ((curr_close - prev_close) / prev_close) * 100

                    # 1 Week change approximation based on interval
                    if runner.yf_interval == "1d" and len(df) >= 6:
                        week_close = float(df['Close'].iloc[-6])
                        pct_change_1w = ((curr_close - week_close) / week_close) * 100
                    elif runner.yf_interval == "1wk" and len(df) >= 5:
                         month_close = float(df['Close'].iloc[-5])
                         pct_change_1w = ((curr_close - month_close) / month_close) * 100

            except Exception as e:
                logger.debug(f"Pct change calc failed: {e}")

            # 3. Calculate Indicators
            if len(df) < 50:
                return None

            rsi_series = ta.rsi(df['Close'], length=DEFAULT_RSI_LENGTH)
            if rsi_series is None: return None
            df['RSI'] = rsi_series

            sma_series = ta.sma(df['Close'], length=DEFAULT_SMA_FAST)
            if sma_series is None: return None
            df['SMA_50'] = sma_series

            atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            current_atr = atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 0.0

            current_price = float(df['Close'].iloc[-1])
            volatility_pct = (current_atr / current_price * 100) if current_price > 0 else 0.0
            current_rsi = float(df['RSI'].iloc[-1])
            current_sma = float(df['SMA_50'].iloc[-1])

            # Fetch PE Ratio (Separate blocking call if not cached)
            # This is slow inside a thread pool of 4, but let's keep it for parity
            pe_ratio = "N/A"
            try:
                t = yf.Ticker(symbol)
                info = t.info
                if info and 'trailingPE' in info and info['trailingPE'] is not None:
                    pe_ratio = f"{info['trailingPE']:.2f}"
            except Exception as e:
                logger.debug(f"PE ratio fetch failed: {e}")

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
                if current_rsi < 30:
                    signal = "🔵 OVERSOLD (Bearish)"
                elif current_rsi > 70:
                    signal = "🔴 OVERBOUGHT (Bearish)"

            company_name = TICKER_NAMES.get(symbol, symbol)
            breakout_date = _calculate_trend_breakout_date(df)

            stop_loss = current_price - (2 * current_atr) if trend == "BULLISH" else current_price + (2 * current_atr)
            target_price = current_price + (4 * current_atr) if trend == "BULLISH" else current_price - (4 * current_atr)

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
                "stop_loss": round(stop_loss, 2),
                "target": round(target_price, 2),
                "atr": current_atr,
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "pe_ratio": pe_ratio,
                "breakout_date": breakout_date
            }
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None

    return runner.run(strategy)

def screen_market(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d", region: str = "us") -> dict:
    """
    Screens the market for stocks grouped by sector.
    Returns:
        Dict[str, List[dict]]: Keys are 'Sector Name (Ticker)', Values are lists of ticker results.
    """
    all_tickers = resolve_region_tickers(region)

    flat_results = screen_tickers_helper(list(set(all_tickers)), iv_rank_threshold, rsi_threshold, time_frame)

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

    results = screen_tickers_helper(sectors, iv_rank_threshold, rsi_threshold, time_frame)

    # Enrich with full name
    for r in results:
        code = r['ticker']
        if code in SECTOR_NAMES:
            r['name'] = SECTOR_NAMES[code]
            r['company_name'] = SECTOR_NAMES[code]

    return results

def analyze_breakout(ticker, df):
    """
    Analyzes if a stock has broken out of a 6-month range and when.
    """
    # 1. Ensure we have enough data (approx 126 trading days in 6 months)
    if len(df) < 120:
        return {"signal": False, "breakout_date": None}

    # 2. Define the "Lookback" vs "Recent" window
    # We look for a breakout that happened in the last 30 days
    # relative to the high of the prior 5 months.
    recent_window = 30
    historical_window = len(df) - recent_window

    # Get the data subsets
    history_df = df.iloc[:historical_window]
    recent_df = df.iloc[historical_window:]

    # 3. Calculate the Resistance Level (Max High of the previous period)
    resistance_level = history_df['Close'].max()

    # 4. Check for Breakout in the recent window
    # Find days where Close > Resistance Level
    breakout_mask = recent_df['Close'] > resistance_level

    if not breakout_mask.any():
        return {"signal": False, "breakout_date": None}

    # 5. Find the FIRST date the breakout occurred in this recent window
    breakout_dates = recent_df[breakout_mask].index
    first_breakout_date = breakout_dates[0]

    # Calculate days since breakout
    days_since = (df.index[-1] - first_breakout_date).days

    return {
        "signal": True,
        "breakout_date": first_breakout_date.strftime('%Y-%m-%d'), # Format date string
        "days_since": days_since,
        "resistance_level": resistance_level,
        "current_price": df['Close'].iloc[-1]
    }
