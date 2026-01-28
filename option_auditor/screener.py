import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from scipy.signal import hilbert, detrend
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
import traceback
try:
    import pandas_ta as ta # Moved to top level for global availability
except ImportError as e:
    raise ImportError("The 'pandas_ta' library is required. Please install it with 'pip install pandas_ta'.") from e

from option_auditor.quant_engine import QuantPhysicsEngine

# Configure logger
logger = logging.getLogger(__name__)

# Export centralized verdict logic for unified_screener
generate_human_verdict = QuantPhysicsEngine.generate_human_verdict

# Import Unified Screener (Lazy import inside function to avoid circular dep if needed, or top level)
# We will expose it via this module for backward compatibility/ease of use.
from option_auditor.unified_screener import screen_universal_dashboard

# Imports from common constants to avoid circular dependencies
from option_auditor.common.constants import SECTOR_NAMES, SECTOR_COMPONENTS, TICKER_NAMES, DEFAULT_ACCOUNT_SIZE, RISK_FREE_RATE
from option_auditor.common.data_utils import prepare_data_for_ticker as _prepare_data_for_ticker
from option_auditor.common.data_utils import fetch_data_with_retry, fetch_batch_data_safe, get_cached_market_data, _calculate_trend_breakout_date

# Import ticker lists from dedicated files
from option_auditor.uk_stock_data import get_uk_tickers, get_uk_euro_tickers
from option_auditor.india_stock_data import get_indian_tickers
from option_auditor.us_stock_data import get_united_states_stocks

try:
    from option_auditor.sp500_data import get_sp500_tickers
except ImportError:
    def get_sp500_tickers(): return []

# Import Refactored Utilities and Constants
from option_auditor.strategies.vertical_spreads import screen_vertical_put_spreads
from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.strategies.bull_put import screen_bull_put_spreads
from option_auditor.strategies.squeeze import screen_bollinger_squeeze
from option_auditor.strategies.liquidity import screen_liquidity_grabs, _identify_swings, _detect_fvgs
from option_auditor.strategies.fortress import screen_dynamic_volatility_fortress
from option_auditor.common.screener_utils import (
    ScreeningRunner,
    resolve_region_tickers,
    _get_filtered_sp500,
    DEFAULT_RSI_LENGTH,
    DEFAULT_ATR_LENGTH,
    DEFAULT_SMA_FAST,
    _norm_cdf,
    _calculate_put_delta,
    DEFAULT_SMA_SLOW,
    DEFAULT_EMA_FAST,
    DEFAULT_EMA_MED,
    DEFAULT_EMA_SLOW,
    DEFAULT_DONCHIAN_WINDOW
)

# Update with S&P 500 Names if available in constants?
# Constants.py updates TICKER_NAMES with SP500_NAMES already.

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

def _screen_tickers(tickers: list, iv_rank_threshold: float, rsi_threshold: float, time_frame: str) -> list:
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
                pass

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

def screen_turtle_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for Turtle Trading Setups (20-Day Breakouts).
    Supports multiple timeframes.
    DELEGATES TO: option_auditor/strategies/turtle.py
    """
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

    def strategy(ticker, df):
        return TurtleStrategy(ticker, df, check_mode=check_mode).analyze()

    return runner.run(strategy)

def screen_5_13_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for 5/13 and 5/21 EMA Crossovers (Momentum Breakouts).
    """
    try:
        import pandas_ta as ta
    except ImportError:
        return []

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

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

    def strategy(ticker, df):
        try:
            min_length = 22 if check_mode else 22 # Need 21 for EMA 21
            if len(df) < min_length: return None

            # --- EMA CALCULATIONS ---
            df['EMA_5'] = ta.ema(df['Close'], length=DEFAULT_EMA_FAST)
            df['EMA_13'] = ta.ema(df['Close'], length=DEFAULT_EMA_MED)
            df['EMA_21'] = ta.ema(df['Close'], length=DEFAULT_EMA_SLOW)

            # ATR for standard reporting
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
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
                except Exception:
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

            # Calculate Target based on 2R relative to EMA stop or 4 ATR
            # If long, target = price + (price - stop) * 2
            target_price = 0.0
            if "DUMP" in signal:
                risk = stop_loss - curr_close
                if risk > 0:
                     target_price = curr_close - (risk * 2)
                else:
                     target_price = curr_close - (4 * current_atr)
            else:
                risk = curr_close - stop_loss
                if risk > 0:
                     target_price = curr_close + (risk * 2)
                else:
                     target_price = curr_close + (4 * current_atr)

            if check_mode or signal != "WAIT":
                # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))
                return {
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
                    "target": round(target_price, 2),
                    "atr_value": round(current_atr, 2), # Key was different in 5/13, standardizing or adding both? Keeping original key 'atr_value' but adding 'atr' for unified UI
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d,
                    "volatility_pct": round(volatility_pct, 2),
                    "diff_pct": ((curr_5 - ema_slow)/ema_slow)*100,
                    "breakout_date": breakout_date
                }

        except Exception as e:
            logger.error(f"Error processing 5/13 setup for {ticker}: {e}")
            return None
        return None

    results = runner.run(strategy)
    # Sort by "Freshness" (Breakouts first)
    results.sort(key=lambda x: 0 if "FRESH" in x['signal'] else 1)
    return results

def screen_darvas_box(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for Darvas Box Breakouts.
    """
    import pandas_ta as ta
    import numpy as np

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

    ETF_NAMES = {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000 ETF",
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "USO": "United States Oil Fund, LP",
        "TLT": "iShares 20+ Year Treasury Bond ETF",
    }

    def strategy(ticker, df):
        try:
            min_length = 50 if check_mode else 50 # Darvas needs enough history for pivots
            if len(df) < min_length: return None

            curr_close = float(df['Close'].iloc[-1])
            curr_volume = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0

            # 1. 52-Week High Check (Momentum Filter)
            period_high = df['High'].max()
            if curr_close < period_high * 0.90 and not check_mode:
                pass # Just a filter, but we proceed to check boxes

            # 2. Identify Box (Ceiling & Floor)
            # We iterate back to find the most recent valid Box.
            ceiling = None
            floor = None

            # Convert to numpy for speed
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            volumes = df['Volume'].values if 'Volume' in df.columns else np.zeros(len(df))

            lookback = min(len(df), 60)
            found_top_idx = -1

            for i in range(len(df) - 4, len(df) - lookback, -1):
                if i < 3: break
                if i + 3 >= len(df): continue

                curr_h = highs[i]
                if (curr_h >= highs[i-1] and curr_h >= highs[i-2] and curr_h >= highs[i-3] and
                    curr_h >= highs[i+1] and curr_h >= highs[i+2] and curr_h >= highs[i+3]):

                    found_top_idx = i
                    ceiling = curr_h
                    break

            if found_top_idx == -1: return None

            found_bot_idx = -1

            for j in range(found_top_idx + 1, len(df) - 3):
                if j < 3: continue
                if j + 3 >= len(df): continue

                curr_l = lows[j]
                if curr_l >= ceiling: continue # Bottom must be below top

                if (curr_l <= lows[j-1] and curr_l <= lows[j-2] and curr_l <= lows[j-3] and
                    curr_l <= lows[j+1] and curr_l <= lows[j+2] and curr_l <= lows[j+3]):

                    found_bot_idx = j
                    floor = curr_l
                    break

            # Calc ATR, 52wk
            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH).iloc[-1] if len(df) >= DEFAULT_ATR_LENGTH else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            pct_change_1d = ((curr_close - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) >= 2 else 0.0
            
            # --- SIGNAL GENERATION ---
            signal = "WAIT"

            # 3. Check for Breakout
            if ceiling and floor:
                if closes[-1] > ceiling and closes[-2] <= ceiling:
                     signal = "📦 DARVAS BREAKOUT"

                elif closes[-1] < floor and closes[-2] >= floor:
                     signal = "📉 BOX BREAKDOWN"

                elif closes[-1] > ceiling:
                     if (closes[-1] - ceiling) / ceiling < 0.05:
                         signal = "🚀 MOMENTUM (Post-Breakout)"

            elif ceiling and not floor:
                pass

            if signal == "WAIT" and not check_mode:
                return None

            # 4. Volume Filter (for Breakouts)
            is_valid_volume = True
            vol_ma_ratio = 1.0
            if "BREAKOUT" in signal and not check_mode:
                vol_ma = np.mean(volumes[-21:-1]) if len(volumes) > 21 else np.mean(volumes)
                if vol_ma > 0:
                    vol_ma_ratio = curr_volume / vol_ma
                    if curr_volume < vol_ma * 1.2:
                        is_valid_volume = False

            if not is_valid_volume and not check_mode:
                return None

            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            stop_loss = floor if floor else (ceiling - 2*current_atr if ceiling else curr_close * 0.95)
            box_height = (ceiling - floor) if (ceiling and floor) else (4 * current_atr)
            target = ceiling + box_height if ceiling else curr_close * 1.2

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))
            breakout_date = _calculate_trend_breakout_date(df)

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
                "target": target,
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

    return runner.run(strategy)

# -------------------------------------------------------------------------
#  SMC / ICT HELPER FUNCTIONS
# -------------------------------------------------------------------------

def screen_mms_ote_setups(ticker_list: list = None, time_frame: str = "1h", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for ICT Market Maker Models + OTE (Optimal Trade Entry).
    """
    import pandas_ta as ta

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

    def strategy(ticker, df):
        try:
            min_length = 50 if check_mode else 50
            if len(df) < min_length: return None

            curr_close = float(df['Close'].iloc[-1])

            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            df = _identify_swings(df, lookback=3)

            last_swings_high = df[df['Swing_High'].notna()]
            last_swings_low = df[df['Swing_Low'].notna()]

            if last_swings_high.empty or last_swings_low.empty:
                return None

            signal = "WAIT"
            setup_details = {}

            peak_idx = df['High'].iloc[-40:].idxmax()
            peak_high = df.loc[peak_idx, 'High']

            after_peak = df.loc[peak_idx:]
            if len(after_peak) < 3: return None

            valley_idx = after_peak['Low'].idxmin()
            valley_low = df.loc[valley_idx, 'Low']

            range_size = peak_high - valley_low
            fib_62 = peak_high - (range_size * 0.618)
            fib_79 = peak_high - (range_size * 0.79)

            fvgs = _detect_fvgs(after_peak)
            bearish_fvgs = [f for f in fvgs if f['type'] == "BEARISH"]
            has_fvg = len(bearish_fvgs) > 0

            if has_fvg and (fib_79 <= curr_close <= fib_62):
                 before_peak = df.loc[:peak_idx].iloc[:-1]
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

            if signal == "WAIT":
                trough_idx = df['Low'].iloc[-40:].idxmin()
                trough_low = df.loc[trough_idx, 'Low']

                after_trough = df.loc[trough_idx:]

                if len(after_trough) >= 5:
                    peak_up_idx = after_trough['High'].idxmax()
                    peak_up_high = df.loc[peak_up_idx, 'High']

                    if peak_up_high > trough_low and curr_close < peak_up_high:

                        range_up = peak_up_high - trough_low
                        fib_62_up = trough_low + (range_up * 0.618)
                        fib_79_up = trough_low + (range_up * 0.79)

                        retracement_pct = (peak_up_high - curr_close) / range_up

                        if 0.618 <= retracement_pct <= 0.79:
                             before_trough = df.loc[:trough_idx].iloc[:-1]
                             valid_mss = False

                             if not before_trough.empty:
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

            breakout_date = _calculate_trend_breakout_date(df)

            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            
            if signal != "WAIT" or check_mode:
                pct_change_1d = None
                if len(df) >= 2:
                    try:
                        prev_close_px = float(df['Close'].iloc[-2])
                        pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                    except Exception:
                        pass

                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

                return {
                    "ticker": ticker,
                    "company_name": company_name,
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

    return runner.run(strategy)

# -------------------------------------------------------------------------
#  OPTIONS STRATEGY HELPERS
# -------------------------------------------------------------------------
import math
import numpy as np
from datetime import date, timedelta
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import logging
import time
import concurrent.futures

# logger = logging.getLogger(__name__)



def resolve_ticker(query: str) -> str:
    """
    Resolves a query (Ticker or Company Name) to a valid ticker symbol.
    Uses TICKER_NAMES for lookup.
    """
    if not query: return ""
    query = query.strip().upper()

    if query in TICKER_NAMES:
        return query

    if "." not in query:
        if f"{query}.L" in TICKER_NAMES: return f"{query}.L"
        if f"{query}.NS" in TICKER_NAMES: return f"{query}.NS"

    for k, v in TICKER_NAMES.items():
        if v.upper() == query:
            return k

    for k, v in TICKER_NAMES.items():
        if query in v.upper():
            return k

    return query

def screen_trend_followers_isa(ticker_list: list = None, risk_per_trade_pct: float = 0.01, region: str = "us", check_mode: bool = False, time_frame: str = "1d", account_size: float = DEFAULT_ACCOUNT_SIZE) -> list:
    """
    The 'Legendary Trend' Screener for ISA Accounts (Long Only).
    Supports Dynamic Position Sizing if account_size is provided.
    DELEGATES TO: option_auditor/strategies/isa.py
    """
    if not (0.001 <= risk_per_trade_pct <= 0.10):
        logger.warning(f"risk_per_trade_pct {risk_per_trade_pct} out of bounds (0.001-0.1). Resetting to 0.01.")
        risk_per_trade_pct = 0.01

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

    def strategy(ticker, df):
        return IsaStrategy(ticker, df, check_mode=check_mode, account_size=account_size, risk_per_trade_pct=risk_per_trade_pct).analyze()

    results = runner.run(strategy)

    # Sort by signal priority
    def sort_key(x):
        s = x.get('signal', '')
        if "ENTER" in s: return 0
        if "WATCH" in s: return 1
        return 2

    results.sort(key=sort_key)
    return results

# -------------------------------------------------------------------------
#  FOURIER / CYCLE ANALYSIS HELPERS
# -------------------------------------------------------------------------
import numpy as np

def _calculate_hilbert_phase(prices):
    """
    Calculates Instantaneous Phase using the Hilbert Transform.
    FIX: Replaces rigid FFT with Analytic Signal for non-stationary data.
    Returns:
        - phase: (-pi to +pi) where -pi/pi is a trough/peak.
        - strength: Magnitude of the cycle (Amplitude).
    """
    try:
        if len(prices) < 30: return None, None

        # 1. Log Returns to normalize magnitude
        # We work with price deviations, but log prices are safer for trends
        log_prices = np.log(prices)

        # 2. Detrend (Linear) to isolate oscillatory component
        # 'linear' detrending removes the primary trend so we see the cycle
        detrended = detrend(log_prices, type='linear')

        # 3. Apply Hilbert Transform to get Analytic Signal
        analytic_signal = hilbert(detrended)

        # 4. Extract Phase (Angle) and Amplitude (Abs)
        # Phase ranges from -pi to +pi radians
        phase = np.angle(analytic_signal)[-1]
        amplitude = np.abs(analytic_signal)[-1]

        return phase, amplitude

    except Exception:
        return None, None

def _calculate_dominant_cycle(prices):
    """
    Uses FFT to find the dominant cycle period (in days) of a price series.
    Returns: (period_days, current_phase_position)
    """
    N = len(prices)
    if N < 64: return None

    window_size = 64
    y = np.array(prices[-window_size:])
    x = np.arange(window_size)

    p = np.polyfit(x, y, 1)
    trend = np.polyval(p, x)
    detrended = y - trend

    windowed = detrended * np.hanning(window_size)

    fft_output = np.fft.rfft(windowed)
    frequencies = np.fft.rfftfreq(window_size)

    amplitudes = np.abs(fft_output)

    peak_idx = np.argmax(amplitudes[1:]) + 1

    dominant_freq = frequencies[peak_idx]
    period = 1.0 / dominant_freq if dominant_freq > 0 else 0

    current_val = detrended[-1]
    cycle_range = np.max(detrended) - np.min(detrended)

    rel_pos = current_val / (cycle_range / 2.0) if cycle_range > 0 else 0

    return round(period, 1), rel_pos

def screen_fourier_cycles(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for Cyclical Turns using Instantaneous Phase (Hilbert Transform).
    FIX: Removed fixed period limits (5-60d). Now detects geometric turns.
    """
    import pandas as pd
    import numpy as np # Ensure numpy is imported

    if ticker_list is None:
        ticker_list = resolve_region_tickers(region)

    results = []

    # Batch fetch logic remains same ...
    try:
        data = fetch_batch_data_safe(ticker_list, period="1y", interval="1d", chunk_size=100)
    except:
        return []

    # Iterator setup ...
    if isinstance(data.columns, pd.MultiIndex):
        iterator = [(ticker, data[ticker]) for ticker in data.columns.unique(level=0)]
    else:
        iterator = [(ticker_list[0], data)] if len(ticker_list)==1 and not data.empty else []

    for ticker, df in iterator:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)

            df = df.dropna(how='all')
            if len(df) < 50: continue
            if ticker not in ticker_list: continue

            # --- DSP PHYSICS CALCULATION ---
            # Use 'Close' series values
            closes = df['Close'].values

            phase, strength = _calculate_hilbert_phase(closes)

            if phase is None: continue

            # --- SIGNAL LOGIC (Based on Radians) ---
            # Phase -3.14 (or 3.14) is the TROUGH (Bottom)
            # Phase 0 is the ZERO CROSSING (Midpoint/Trend)
            # Phase 1.57 (pi/2) is the PEAK (Top)

            # Normalize phase for display (-1 to 1 scale roughly)
            norm_phase = phase / np.pi

            signal = "WAIT"
            verdict_color = "gray"

            # Sine Wave Cycle logic:
            # We want to catch the turn UP from the bottom.
            # Bottom is +/- pi. As it crosses from negative to positive?
            # Actually, Hilbert Phase moves continuously.
            # Deep cycle low is typically near +/- pi boundaries depending on convention.

            # DEFINITION:
            # Phase close to +/- Pi = Trough (Oversold Cycle)
            # Phase close to 0 = Peak (Overbought Cycle) in some implementations,
            # BUT standard Hilbert on detrended data:
            # Real part max = Peak, Real part min = Trough.
            # Phase transitions align with the wave.

            # Simplify: If Phase is turning from Negative to Positive (Sine wave bottom)

            if 0.8 <= abs(norm_phase) <= 1.0:
                signal = "🌊 CYCLICAL LOW (Bottoming)"
                verdict_color = "green"
            elif 0.0 <= abs(norm_phase) <= 0.2:
                signal = "🏔️ CYCLICAL HIGH (Topping)"
                verdict_color = "red"

            # Filter weak cycles (Noise)
            if strength < 0.02: # 2% Amplitude threshold
                signal = "WAIT (Weak Cycle)"
                verdict_color = "gray"

            pct_change_1d = None
            if len(df) >= 2:
                pct_change_1d = ((closes[-1] - closes[-2]) / closes[-2]) * 100

            # Calculate dominant period for context
            period, rel_pos = _calculate_dominant_cycle(closes) or (0, 0)

            # ATR for Stop/Target
            if 'ATR' not in df.columns:
                 df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0

            # Mean Reversion Logic: Stop 2 ATR, Target 2 ATR
            curr_price = float(closes[-1])
            if "LOW" in signal:
                stop_loss = curr_price - (2 * current_atr)
                target = curr_price + (2 * current_atr)
            elif "HIGH" in signal:
                stop_loss = curr_price + (2 * current_atr)
                target = curr_price - (2 * current_atr)
            else:
                stop_loss = curr_price - (2 * current_atr)
                target = curr_price + (2 * current_atr)

            breakout_date = _calculate_trend_breakout_date(df)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            results.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": float(closes[-1]),
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "cycle_phase": f"{phase:.2f} rad",
                "cycle_strength": f"{strength*100:.1f}%", # Volatility of the cycle
                "verdict_color": verdict_color,
                "method": "Hilbert (Non-Stationary)",
                "cycle_period": f"{period} days", # Legacy compatibility for tests
                "breakout_date": breakout_date,
                "atr_value": round(current_atr, 2),
                "atr": round(current_atr, 2)
            })

        except Exception:
            continue

    results.sort(key=lambda x: x.get('cycle_strength', 0), reverse=True)
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

        rsi_val = None
        if 'RSI_14' in self.df.columns:
             rsi_val = self.df['RSI_14'].iloc[-1]
        elif 'RSI' in self.df.columns:
             rsi_val = self.df['RSI'].iloc[-1]
        else:
             try:
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
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd
    import numpy as np

    if ticker_list is None:
        ticker_list = resolve_region_tickers(region)
    
    if ticker_list:
        ticker_list = [t.upper() for t in ticker_list]
        
    results = []

    is_large_scan = False
    if ticker_list and len(ticker_list) > 100: is_large_scan = True

    cache_name = "watchlist_scan"
    if region == "india":
         cache_name = "market_scan_india"
    elif region == "uk":
         cache_name = "market_scan_uk"
    elif region == "uk_euro":
         cache_name = "market_scan_europe"
    elif is_large_scan:
         cache_name = "market_scan_v1"

    if check_mode:
        all_data = fetch_batch_data_safe(ticker_list, period="2y", interval=time_frame)
    elif time_frame == "1d":
        all_data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_name)
    else:
        all_data = fetch_batch_data_safe(ticker_list, period="5d", interval=time_frame)

    # Optimized Iteration
    if isinstance(all_data.columns, pd.MultiIndex):
        iterator = [(ticker, all_data[ticker]) for ticker in all_data.columns.unique(level=0)]
    else:
        # Fallback for single or flat
        if not all_data.empty and len(ticker_list) == 1:
            iterator = [(ticker_list[0], all_data)]
        else:
            iterator = []

    for ticker, df in iterator:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)

            if ticker not in ticker_list: continue

            df = df.dropna(how='all')
            min_length = 50 if check_mode else 200
            if len(df) < min_length: continue

            # Process logic
            res = _process_hybrid_ticker(ticker, df, time_frame, check_mode)
            if res: results.append(res)
        except Exception: continue

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def _process_hybrid_ticker(ticker, df, time_frame, check_mode):
    try:
        import pandas_ta as ta
        import pandas as pd
        import numpy as np

        curr_close = float(df['Close'].iloc[-1])
        closes = df['Close'].tolist()

        sma_200 = df['Close'].rolling(200).mean().iloc[-1]
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
        low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()

        trend_verdict = "NEUTRAL"
        if curr_close > sma_200:
            trend_verdict = "BULLISH"
        else:
            trend_verdict = "BEARISH"

        is_breakout = curr_close >= high_50

        cycle_data = _calculate_dominant_cycle(closes)

        cycle_state = "NEUTRAL"
        cycle_score = 0.0
        period = 0

        if cycle_data:
            period, rel_pos = cycle_data
            cycle_score = rel_pos

            if rel_pos <= -0.7:
                cycle_state = "BOTTOM"
            elif rel_pos >= 0.7:
                cycle_state = "TOP"
            else:
                cycle_state = "MID"

        if time_frame == "1d" and not check_mode:
            watch_list = SECTOR_COMPONENTS.get("WATCH", [])
            if ticker not in watch_list:
                if 'Volume' in df.columns:
                    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                    if avg_vol < 500000:
                        return None

        today_open = float(df['Open'].iloc[-1])
        yesterday_low = float(df['Low'].iloc[-2])

        is_green_candle = curr_close > today_open

        if 'ATR' not in df.columns:
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        current_atr = 0.0
        if 'ATR' in df.columns and not df['ATR'].empty:
                current_atr = df['ATR'].iloc[-1]
        if pd.isna(current_atr): current_atr = 0.0

        volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

        daily_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
        is_panic_selling = daily_range > (2.0 * current_atr) if current_atr > 0 else False

        is_making_lower_lows = curr_close < yesterday_low

        pct_change_1d = None
        if len(df) >= 2:
            try:
                prev_close_px = float(df['Close'].iloc[-2])
                pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
            except Exception:
                pass

        final_signal = "WAIT"
        color = "gray"
        score = 0

        stop_loss_price = curr_close - (3 * current_atr)
        target_price = curr_close + (2 * current_atr)

        potential_reward = target_price - curr_close
        potential_risk = curr_close - stop_loss_price
        rr_ratio = potential_reward / potential_risk if potential_risk > 0 else 0

        rr_verdict = "✅ GOOD" if rr_ratio >= 1.5 else "⚠️ POOR R/R"

        if trend_verdict == "BULLISH" and cycle_state == "BOTTOM":
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
                final_signal = "🚀 PERFECT BUY (Confirmed Turn)"
                color = "green"
                score = 95

        elif trend_verdict == "BULLISH" and is_breakout:
            if cycle_state == "TOP":
                final_signal = "⚠️ MOMENTUM BUY (Cycle High)"
                color = "orange"
                score = 75
            else:
                final_signal = "✅ BREAKOUT BUY"
                color = "green"
                score = 85

        elif trend_verdict == "BEARISH" and cycle_state == "TOP":
            final_signal = "📉 PERFECT SHORT (Rally in Downtrend)"
            color = "red"
            score = 90

        elif trend_verdict == "BULLISH" and cycle_state == "TOP":
            final_signal = "🛑 WAIT (Extended)"
            color = "yellow"
        elif trend_verdict == "BEARISH" and cycle_state == "BOTTOM":
            final_signal = "🛑 WAIT (Oversold Downtrend)"
            color = "yellow"

        base_ticker = ticker.split('.')[0]
        company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

        breakout_date = _calculate_trend_breakout_date(df)

        return {
            "ticker": ticker,
            "company_name": company_name,
            "price": curr_close,
            "verdict": final_signal,
            "trend": trend_verdict,
            "cycle": f"{cycle_state} ({cycle_score:.2f})",
            "period_days": 0, # Placeholder or calc
            "score": score,
            "color": color,
            "signal": final_signal,
            "pct_change_1d": pct_change_1d,
            "stop_loss": round(stop_loss_price, 2),
            "target": round(target_price, 2),
            "rr_ratio": f"{rr_ratio:.2f} ({rr_verdict})",
            "atr_value": round(current_atr, 2),
            "volatility_pct": round(volatility_pct, 2),
            "breakout_date": breakout_date,
            "atr": round(current_atr, 2),
            "52_week_high": round(high_52wk, 2) if high_52wk else None,
            "52_week_low": round(low_52wk, 2) if low_52wk else None,
            "sector_change": pct_change_1d
        }
    except Exception: return None

def screen_master_convergence(ticker_list: list = None, region: str = "us", check_mode: bool = False, time_frame: str = "1d") -> list:
    """
    Runs ALL strategies on the dataset to find CONFLUENCE.
    """
    if ticker_list is None:
        if region == "us" or region is None:
             # Default Master Screener only checks WATCH list to save resources (high compute)
             ticker_list = SECTOR_COMPONENTS.get("WATCH", [])
        else:
             # For other regions (or explicit sp500 request), use standard resolution
             ticker_list = resolve_region_tickers(region)

    is_large = len(ticker_list) > 100 or region == "sp500"

    cache_name = "watchlist_scan"
    if region == "india":
         cache_name = "market_scan_india"
    elif region == "uk":
         cache_name = "market_scan_uk"
    elif region == "uk_euro":
         cache_name = "market_scan_europe"
    elif is_large:
         cache_name = "market_scan_v1"

    try:
        if check_mode:
             all_data = fetch_batch_data_safe(ticker_list, period="2y", interval="1d")
        else:
            all_data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_name)
    except Exception as e:
        logger.error(f"Master screener data fetch failed: {e}")
        return []

    results = []

    if all_data.empty:
        return []

    if isinstance(all_data.columns, pd.MultiIndex):
        valid_tickers = [t for t in ticker_list if t in all_data.columns.levels[0]]
        iterator = [(ticker, all_data[ticker]) for ticker in all_data.columns.unique(level=0)]
    else:
        valid_tickers = ticker_list if not all_data.empty else []
        iterator = [(ticker_list[0], all_data)] if len(ticker_list)==1 else []

    watch_list = SECTOR_COMPONENTS.get("WATCH", [])

    for ticker, df in iterator:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)

            if ticker not in valid_tickers: continue

            df = df.dropna(how='all')
            if len(df) < 200: continue

            if region == "sp500" and ticker not in watch_list:
                if 'Volume' in df.columns:
                     avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                     if avg_vol < 500000: continue

            # --- RUN ALL STRATEGIES ---
            analyzer = StrategyAnalyzer(df)

            isa_trend = analyzer.check_isa_trend()
            fourier, f_score = analyzer.check_fourier()
            momentum = analyzer.check_momentum()

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

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            curr_price = df['Close'].iloc[-1]
            if pd.isna(curr_price): continue

            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_price - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            import pandas_ta as ta
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / curr_price * 100) if curr_price > 0 else 0.0

            breakout_date = _calculate_trend_breakout_date(df)

            # Standard Confluence Stop/Target (3 ATR Stop, 5 ATR Target)
            stop_loss = curr_price - (3 * current_atr) if isa_trend == "BULLISH" else curr_price + (3 * current_atr)
            target = curr_price + (5 * current_atr) if isa_trend == "BULLISH" else curr_price - (5 * current_atr)

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
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "breakout_date": breakout_date,
                "atr": round(current_atr, 2)
            })

        except Exception: continue

    results.sort(key=lambda x: x['confluence_score'], reverse=True)
    return results

def screen_monte_carlo_forecast(ticker: str, days: int = 30, sims: int = 1000):
    """
    Project stock price 30 days out using Monte Carlo with Historical Bootstrapping.
    FIX: Replaces Gaussian GBM with Bootstrapping to capture Fat Tails.
    """
    import numpy as np
    import pandas as pd
    import yfinance as yf

    try:
        # Fetch sufficient history to capture tail events (2 years minimum)
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty or len(df) < 100: return None

        if isinstance(df.columns, pd.MultiIndex):
            try:
                if ticker in df.columns.levels[0]:
                    df = df[ticker].copy()
                else:
                    df.columns = df.columns.get_level_values(0)
            except: pass

        # Calculate Log Returns
        log_returns = np.log(df['Close'] / df['Close'].shift(1)).dropna()
        if log_returns.empty: return None

        last_price = float(df['Close'].iloc[-1])

        # BOOTSTRAPPING: Sample from ACTUAL past returns with replacement.
        # This preserves skewness and kurtosis (fat tails).
        random_returns = np.random.choice(log_returns, size=(days, sims), replace=True)

        # Reconstruct Price Paths
        # Cumulative sum of log returns -> cumulative product of price
        price_paths = last_price * np.exp(np.cumsum(random_returns, axis=0))

        final_prices = price_paths[-1]

        # Probability of Drop > 10%
        # Measures how many simulation paths ended below 90% of current price
        prob_drop_10pct = np.mean(final_prices < (last_price * 0.90)) * 100

        median_forecast = np.median(final_prices)

        # Annualized Volatility for context
        vol_annual = log_returns.std() * np.sqrt(252)

        return {
            "ticker": ticker,
            "current": last_price,
            "median_forecast": median_forecast,
            "prob_drop_10pct": f"{prob_drop_10pct:.1f}%",
            "volatility_annual": f"{vol_annual * 100:.1f}%",
            "method": "Historical Bootstrapping (Fat Tails)"
        }
    except Exception:
        return None

# --- CRITICAL FIX: Sanitize Function ---
def sanitize(val):
    """
    Converts NaN, Infinity, and -Infinity to None (JSON null).
    Also converts numpy floats to standard Python floats.
    This prevents the 'Out of range float values are not JSON compliant' error.
    """
    try:
        if val is None: return None
        # Handle numpy types and standard floats
        if isinstance(val, (float, np.floating)):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val) # Force conversion to python float
        return val
    except:
        return None

def screen_quantum_setups(ticker_list: list = None, region: str = "us", time_frame: str = "1d") -> list:
    # ... (Keep existing imports and LIQUID_OPTION_TICKERS logic) ...
    try:
        from option_auditor.common.constants import LIQUID_OPTION_TICKERS
    except ImportError:
        LIQUID_OPTION_TICKERS = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL"] # Fallback

    # 1. Resolve Ticker List based on Region
    if ticker_list is None:
        if region == "us":
            ticker_list = LIQUID_OPTION_TICKERS
        else:
            ticker_list = resolve_region_tickers(region)

    # Resolve tickers (Fix for Ticker Resolution Failure)
    if ticker_list:
        # Apply region-specific suffixes if missing
        if region == 'india':
            ticker_list = [t if t.endswith('.NS') else f"{t}.NS" for t in ticker_list]
        elif region == 'uk':
            ticker_list = [t if t.endswith('.L') else f"{t}.L" for t in ticker_list]

        ticker_list = [resolve_ticker(t) for t in ticker_list]

    # 2. Determine appropriate cache name
    cache_name = "market_scan_us_liquid"
    if region == "uk":
        cache_name = "market_scan_uk"
    elif region == "india":
        cache_name = "market_scan_india"
    elif region == "uk_euro":
        cache_name = "market_scan_europe"
    elif region == "sp500":
        cache_name = "market_scan_v1" # S&P 500 uses v1

    try:
        all_data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_name)
    except Exception as e:
        logger.warning(f"Cache fetch failed for Quantum: {e}")
        all_data = pd.DataFrame()

    # Fallback to Live Data if Cache Missing/Empty
    if all_data.empty:
        try:
            logger.info("Quantum: Falling back to live batch download...")
            all_data = fetch_batch_data_safe(ticker_list, period="2y", interval="1d")
        except Exception as e:
            logger.error(f"Live fetch failed for Quantum: {e}")
            return []

    if all_data.empty: return []

    # FIX 3: Robust Multi-Ticker vs Flat Data Handling
    # Use a helper to normalize the dataframe structure
    valid_tickers = []

    # Logic to ensure we have a list of (ticker, df) tuples
    ticker_data_map = {}

    if isinstance(all_data.columns, pd.MultiIndex):
        # Standard Batch Result
        for t in all_data.columns.levels[0]:
            if t in ticker_list:
                ticker_data_map[t] = all_data[t]
    else:
        # Flat Result (Single Ticker or Identity Ambiguity)
        if len(ticker_list) == 1:
            ticker_data_map[ticker_list[0]] = all_data
        else:
            # Ambiguous: We asked for 10, got 1 flat DF.
            # Safe Failover: Skip batch, try to match columns?
            # Or just fail gracefully.
            logger.warning("Quantum Screener received ambiguous flat data for multiple tickers. Skipping.")
            return []

    valid_tickers = list(ticker_data_map.keys())

    def process_ticker(ticker):
        try:
            df = ticker_data_map.get(ticker)
            if df is None or df.empty: return None

            # Clean Data
            df = df.dropna(how='all')
            # Check Hurst Requirement (120 days)
            if len(df) < 120: return None

            close = df['Close']
            curr_price = float(close.iloc[-1])

            # --- PHYSICS ENGINE CALLS ---
            hurst = QuantPhysicsEngine.calculate_hurst(close)

            # Fast Failover: If Hurst failed (e.g. flat line), skip
            if hurst is None: return None

            entropy = QuantPhysicsEngine.shannon_entropy(close)
            kalman = QuantPhysicsEngine.kalman_filter(close)

            # --- FIX 4: Correct Slope Calculation (Percentage) ---
            # We compare current Kalman value vs 10 days ago
            lookback = 10
            k_slope = 0.0

            if len(kalman) > lookback:
                curr_k = float(kalman.iloc[-1])
                prev_k = float(kalman.iloc[-1 - lookback])

                # Avoid div by zero
                if prev_k > 0:
                    k_slope = (curr_k - prev_k) / prev_k
                else:
                    k_slope = 0.0

            # --- VERDICT GENERATION ---
            ai_verdict, ai_rationale = QuantPhysicsEngine.generate_human_verdict(hurst, entropy, k_slope, curr_price)

            # Colors
            verdict_color = "gray"
            if "BUY" in ai_verdict: verdict_color = "green"
            elif "SHORT" in ai_verdict: verdict_color = "red"
            elif "RANDOM" in ai_verdict: verdict_color = "gray" # Explicitly Gray out casino zone

            # --- RISK MANAGEMENT (ATR) ---
            import pandas_ta as ta
            # Calculate ATR locally if not present
            atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = atr_series.iloc[-1] if atr_series is not None else (curr_price * 0.01)

            # Set Stops/Targets based on Regime
            stop_loss = 0.0
            target_price = 0.0

            if "BUY" in ai_verdict:
                stop_loss = curr_price - (2.5 * current_atr) # Wider stop for trends
                target_price = curr_price + (4.0 * current_atr)
            elif "SHORT" in ai_verdict:
                stop_loss = curr_price + (2.5 * current_atr)
                target_price = curr_price - (4.0 * current_atr)
            else:
                # Default brackets for context
                stop_loss = curr_price - (2.0 * current_atr)
                target_price = curr_price + (2.0 * current_atr)

            # --- SCORING (For Sorting) ---
            score = 50
            if "Strong" in ai_verdict: score = 90
            elif "BUY" in ai_verdict: score = 80
            elif "SHORT" in ai_verdict: score = 80
            elif "REVERSAL" in ai_verdict: score = 60
            elif "RANDOM" in ai_verdict: score = 0 # Push to bottom

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            breakout_date = _calculate_trend_breakout_date(df)

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": sanitize(curr_price),
                "hurst": sanitize(hurst),
                "entropy": sanitize(entropy),
                "kalman_diff": sanitize(k_slope), # Returns decimal (e.g. 0.015)
                "human_verdict": ai_verdict,
                "rationale": ai_rationale,
                "verdict_color": verdict_color,
                "score": score,
                "ATR": sanitize(round(current_atr, 2)),
                "Stop Loss": sanitize(round(stop_loss, 2)),
                "Target": sanitize(round(target_price, 2)),
                "stop_loss": sanitize(round(stop_loss, 2)), # Lowercase alias
                "target": sanitize(round(target_price, 2)), # Lowercase alias
                "volatility_pct": sanitize(round((current_atr/curr_price)*100, 2)),
                "breakout_date": breakout_date,
                "atr": sanitize(round(current_atr, 2))
            }

        except Exception as e:
            # logger.error(f"Error processing {ticker}: {e}")
            return None

    # Threaded Execution
    with ThreadPoolExecutor(max_workers=4) as executor:
        temp_results = list(executor.map(process_ticker, valid_tickers))

    # Filter None results
    results = [r for r in temp_results if r is not None]

    # Sort: High Scores first
    results.sort(key=lambda x: (x.get('score', 0)), reverse=True)

    return results

def screen_alpha_101(ticker_list: list = None, region: str = "us", time_frame: str = "1d") -> list:
    """
    Implements Alpha#101: ((close - open) / ((high - low) + .001))
    Paper Source: 101 Formulaic Alphas (Kakushadze, 2015)
    Logic: Delay-1 Momentum. If stock runs up intraday (Close >> Open), go Long.
    """
    import pandas_ta as ta

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region)

    def strategy(ticker, df):
        try:
            if len(df) < 5: return None

            # --- ALPHA #101 CALCULATION ---
            # Formula: ((close - open) / ((high - low) + 0.001))
            # We use the most recent completed day
            curr_row = df.iloc[-1]

            c = float(curr_row['Close'])
            o = float(curr_row['Open'])
            h = float(curr_row['High'])
            l = float(curr_row['Low'])

            denom = (h - l) + 0.001
            alpha_val = (c - o) / denom

            # --- SIGNAL LOGIC ---
            # Thresholds: > 0.5 implies strong closing strength (Marubozu-like)
            signal = "WAIT"
            color = "gray"

            if alpha_val > 0.5:
                signal = "🚀 STRONG BUY (Alpha > 0.5)"
                color = "green"
            elif alpha_val > 0.25:
                signal = "📈 BULLISH MOMENTUM"
                color = "blue"
            elif alpha_val < -0.5:
                signal = "📉 STRONG SELL (Alpha < -0.5)"
                color = "red"
            elif alpha_val < -0.25:
                signal = "⚠️ BEARISH PRESSURE"
                color = "orange"

            # Filter: Only show active signals to reduce noise?
            if abs(alpha_val) < 0.25:
                return None

            # --- METRICS ---
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (c * 0.01)

            # Risk Management (Paper suggests holding 1-6 days)
            # We use a tight stop below the low of the signal day
            stop_loss = l - (atr * 0.5) if alpha_val > 0 else h + (atr * 0.5)
            target = c + (atr * 2) if alpha_val > 0 else c - (atr * 2)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            pct_change_1d = 0.0
            if len(df) >= 2:
                prev_c = float(df['Close'].iloc[-2])
                pct_change_1d = ((c - prev_c) / prev_c) * 100

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(c, 2),
                "alpha_101": round(alpha_val, 4),
                "signal": signal,
                "verdict": signal, # Alias for UI
                "pct_change_1d": pct_change_1d,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr": round(atr, 2),
                "score": round(abs(alpha_val) * 100, 1), # Sort by intensity
                "breakout_date": _calculate_trend_breakout_date(df)
            }

        except Exception as e:
            return None

    results = runner.run(strategy)
    # Sort by Alpha Value (Positive/Strongest first)
    results.sort(key=lambda x: x['alpha_101'], reverse=True)
    return results

def screen_my_strategy(ticker_list: list = None, region: str = "us") -> list:
    """
    My Strategy: Combines ISA Trend (Macro) + Alpha #101 (Micro).
    1. Filter: Price > 200 SMA & Price > 50 SMA (Trend).
    2. Trigger: Alpha #101 > 0.5 (Momentum).
    """
    import pandas_ta as ta

    # 2y period for 200 SMA
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame="1d", region=region)

    def strategy(ticker, df):
        try:
            if len(df) < 200: return None # Need 200 SMA

            # --- 1. MACRO DATA (ISA TREND) ---
            curr_close = float(df['Close'].iloc[-1])
            curr_open = float(df['Open'].iloc[-1])
            curr_high = float(df['High'].iloc[-1])
            curr_low = float(df['Low'].iloc[-1])

            sma_50 = df['Close'].rolling(DEFAULT_SMA_FAST).mean().iloc[-1]
            sma_200 = df['Close'].rolling(DEFAULT_SMA_SLOW).mean().iloc[-1]

            # 50-Day High (Breakout Level)
            high_50 = df['High'].rolling(DEFAULT_SMA_FAST).max().shift(1).iloc[-1]

            # ATR (Volatility)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (curr_close * 0.01)

            # Trend Check
            is_trend_up = (curr_close > sma_200) and (curr_close > sma_50)

            if not is_trend_up:
                return None # Strict Filter: Only Bullish Trends

            # --- 2. MICRO DATA (ALPHA #101) ---
            # Formula: (Close - Open) / ((High - Low) + 0.001)
            denom = (curr_high - curr_low) + 0.001
            alpha_val = (curr_close - curr_open) / denom

            # --- 3. COMBINED VERDICT ---
            signal = "WAIT"
            color = "gray"
            score = 50

            # Breakout Check
            dist_to_breakout = (curr_close - high_50) / high_50

            if alpha_val > 0.5:
                # Strong Intraday buying in a Bull Trend
                signal = "🚀 SNIPER ENTRY (Alpha > 0.5)"
                color = "green"
                score = 95
            elif alpha_val < -0.5:
                # Strong Selling in a Bull Trend (Pullback or Exit?)
                signal = "⚠️ SELLING PRESSURE"
                color = "orange"
                score = 40
            elif curr_close > high_50:
                 signal = "✅ BREAKOUT (Trend)"
                 color = "blue"
                 score = 80
            elif dist_to_breakout > -0.05:
                 signal = "👀 WATCH (Near Breakout)"
                 color = "yellow"
                 score = 60

            # --- 4. RISK MANAGEMENT (Populate Fields) ---
            if alpha_val > 0.5:
                stop_loss = curr_low - (atr * 0.5)
            else:
                stop_loss = curr_close - (3 * atr)

            risk = curr_close - stop_loss
            target = curr_close + (risk * 2) if risk > 0 else curr_close + (5 * atr)

            breakout_date = _calculate_trend_breakout_date(df)
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            if signal == "WAIT": return None

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(curr_close, 2),
                "verdict": signal, # UI uses this for main badge
                "signal": signal,
                "alpha_101": round(alpha_val, 2),
                "breakout_level": round(high_50, 2), # 50-Day High
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr_value": round(atr, 2),
                "breakout_date": breakout_date,
                "score": score,
                "color": color, # For UI Badge
                # Extra stats
                "pct_change_1d": round(((curr_close - df['Close'].iloc[-2])/df['Close'].iloc[-2])*100, 2)
            }

        except Exception as e:
            return None

    results = runner.run(strategy)
    # Sort by Score (Best Setups first)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def screen_options_only_strategy(region: str = "us", limit: int = 75) -> list:
    """
    THALAIVA'S OPTIONS ONLY PROTOCOL (Optimized for Speed)
    ------------------------------------------------------
    Fixes:
    - Reduced history fetch to 5 days (faster liquidity check).
    - Added strict limit to prevent Worker Timeouts.
    - Aggressive error handling for yfinance 404s.
    """
    import pandas as pd
    import numpy as np
    import yfinance as yf
    import os
    from datetime import date, timedelta
    from scipy.stats import norm
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # --- 1. LOAD TICKERS ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'data', 'us_sectors.csv')

    ticker_list = []
    try:
        if os.path.exists(csv_path):
            df_tickers = pd.read_csv(csv_path)
            # Robust reading: find the first column that looks like tickers
            col_to_use = df_tickers.columns[0]
            raw_list = df_tickers[col_to_use].dropna().astype(str).tolist()
            ticker_list = [t.strip().upper() for t in raw_list if t.strip().isalpha() and len(t) < 6]
            ticker_list = list(set(ticker_list))
        else:
            # Fallback List (The Liquid Kings)
            ticker_list = [
                "SPY", "QQQ", "IWM", "NVDA", "AMD", "TSLA", "AAPL", "MSFT",
                "AMZN", "GOOGL", "META", "NFLX", "COIN", "MSTR", "PLTR",
                "MARA", "RIOT", "DKNG", "HOOD", "UBER", "ABNB", "BA"
            ]
    except Exception as e:
        ticker_list = ["SPY", "QQQ", "IWM"]

    # --- SAFETY LIMIT ---
    # Randomly sample or take top N to prevent server timeout
    if len(ticker_list) > limit:
        # Prefer specific high liquid ones if present, else just slice
        # Just slicing for speed now
        ticker_list = ticker_list[:limit]

    # Constants
    MIN_ROC = 20.0
    TARGET_DTE = 45
    MIN_DTE = 30
    MAX_DTE = 60
    TARGET_DELTA = -0.30
    SPREAD_WIDTH = 5.0
    MIN_TURNOVER = 15_000_000 # Lowered slightly for more hits

    def process_ticker(ticker):
        try:
            tk = yf.Ticker(ticker)

            # --- PHASE 1: FAST LIQUIDITY CHECK ---
            # Only fetch 5 days. If it fails, abort immediately.
            try:
                hist = tk.history(period="5d")
            except:
                return None

            if hist.empty or len(hist) < 2: return None

            curr_price = hist['Close'].iloc[-1]
            avg_vol = hist['Volume'].mean()
            turnover = curr_price * avg_vol

            if turnover < MIN_TURNOVER: return None

            # --- PHASE 2: EARNINGS CHECK (Safe Mode) ---
            earnings_date = None
            try:
                # yfinance often fails here, catch it silently
                cal = tk.calendar
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    earnings_date = cal['Earnings Date'][0]
                elif isinstance(cal, pd.DataFrame):
                    if not cal.empty:
                        # Attempt to find any date object
                        earnings_date = cal.iloc[0, 0]

                if earnings_date:
                    # Fix: Robust parsing
                    dt_val = pd.to_datetime(earnings_date, errors='coerce')
                    if not pd.isna(dt_val):
                        earnings_date = dt_val.date()
                    else:
                        earnings_date = None
            except Exception:
                # If we can't find earnings, assume safe but flag in UI if needed?
                # For now, just proceed.
                earnings_date = None

            # --- PHASE 3: EXPIRATIONS ---
            try:
                expirations = tk.options
            except:
                return None

            if not expirations: return None

            target_exp = None
            best_diff = 999
            actual_dte = 0
            today = date.today()

            for exp in expirations:
                # Basic string format check
                try:
                    dt_exp = pd.to_datetime(exp, errors='coerce')
                    if pd.isna(dt_exp): continue
                    exp_date = dt_exp.date()
                except:
                    continue

                dte = (exp_date - today).days

                if MIN_DTE <= dte <= MAX_DTE:
                    diff = abs(dte - TARGET_DTE)
                    if diff < best_diff:
                        best_diff = diff
                        target_exp = exp
                        actual_dte = dte

            if not target_exp: return None

            # Earnings Logic
            earnings_risk = False
            days_to_earnings = "N/A"
            if earnings_date:
                days_gap = (earnings_date - today).days
                days_to_earnings = str(days_gap)
                if days_gap <= actual_dte:
                    earnings_risk = True

            # --- PHASE 4: CHAIN ANALYSIS ---
            try:
                chain = tk.option_chain(target_exp)
                puts = chain.puts
            except:
                return None

            if puts.empty: return None

            # Quick Delta Calculation
            T_years = actual_dte / 365.0

            # Use 'impliedVolatility' from API
            puts['calc_delta'] = puts.apply(
                lambda x: _calculate_put_delta(curr_price, x['strike'], T_years, RISK_FREE_RATE, x['impliedVolatility'] if x['impliedVolatility'] > 0 else 0.5),
                axis=1
            )

            # Filter OTM
            otm_puts = puts[puts['strike'] < curr_price].copy()
            if otm_puts.empty: return None

            # Find Short Strike (~30 Delta)
            short_leg = otm_puts.iloc[(otm_puts['calc_delta'] - TARGET_DELTA).abs().argsort()[:1]]
            if short_leg.empty: return None
            short_leg = short_leg.iloc[0]

            short_strike = short_leg['strike']
            short_bid = short_leg['bid']
            short_delta = short_leg['calc_delta']

            # Find Long Strike ($5 Wide)
            target_long = short_strike - SPREAD_WIDTH
            long_leg_candidates = puts.iloc[(puts['strike'] - target_long).abs().argsort()[:1]]
            if long_leg_candidates.empty: return None
            long_leg = long_leg_candidates.iloc[0]

            long_strike = long_leg['strike']
            long_ask = long_leg['ask']

            if abs(short_strike - long_strike) < 2.0: return None # Width too small

            # --- PHASE 5: VERDICT ---
            credit = short_bid - long_ask
            if credit <= 0:
                # Fallback to LastPrice if bid/ask is missing (Market Closed)
                credit = short_leg['lastPrice'] - long_leg['lastPrice']

            width = short_strike - long_strike
            max_risk = width - credit

            if credit < 0.10 or max_risk <= 0: return None

            roc = (credit / max_risk) * 100

            verdict = "WAIT"
            if earnings_risk:
                verdict = "🛑 EARNINGS"
            elif roc >= MIN_ROC:
                verdict = "🟢 GREEN LIGHT"

            # Filter output
            if verdict == "WAIT": return None

            return {
                "ticker": ticker,
                "price": round(curr_price, 2),
                "verdict": verdict,
                "setup_name": f"Bull Put {int(short_strike)}/{int(long_strike)}",
                "short_put": int(short_strike),
                "long_put": int(long_strike),
                "expiry_date": target_exp,
                "dte": actual_dte,
                "credit": round(credit * 100, 0),
                "risk": round(max_risk * 100, 0),
                "roc": round(roc, 1),
                "earnings_gap": days_to_earnings,
                "delta": round(short_delta, 2)
            }

        except Exception:
            # Swallow all errors for this ticker to prevent thread crash
            return None

    # --- EXECUTION ---
    results = []
    # Increase workers for IO bound tasks, but not too high to hit API limits
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(process_ticker, t): t for t in ticker_list}
        for future in as_completed(future_to_ticker):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except:
                pass

    results.sort(key=lambda x: (1 if "GREEN" in x['verdict'] else 0, x['roc']), reverse=True)
    return results

def screen_rsi_divergence(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for RSI Divergences (Regular).
    Bullish: Price Lower Low, RSI Higher Low.
    Bearish: Price Higher High, RSI Lower High.
    """
    import pandas_ta as ta
    import numpy as np
    from scipy.signal import argrelextrema

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region)

    def _find_divergence(price, rsi, lookback=30, order=3):
        # Find peaks (Highs)
        # argrelextrema returns indices of local maxima/minima
        # order=3 means it must be the max of 3 neighbors on each side

        if len(price) < lookback: return None, None

        high_idx = argrelextrema(price.values, np.greater, order=order)[0]
        low_idx = argrelextrema(price.values, np.less, order=order)[0]

        current_idx = len(price) - 1
        relevant_highs = [i for i in high_idx if (current_idx - i) < lookback]
        relevant_lows = [i for i in low_idx if (current_idx - i) < lookback]

        signal = None
        div_type = None

        # BEARISH DIVERGENCE CHECK (Higher Highs in Price, Lower Highs in RSI)
        if len(relevant_highs) >= 2:
            p2_idx = relevant_highs[-1] # Most recent peak
            p1_idx = relevant_highs[-2] # Previous peak

            # Check if recent peak is very recent (within last 5 bars)
            if (current_idx - p2_idx) <= 5:
                price_p2 = price.iloc[p2_idx]
                price_p1 = price.iloc[p1_idx]

                rsi_p2 = rsi.iloc[p2_idx]
                rsi_p1 = rsi.iloc[p1_idx]

                # Price made Higher High, RSI made Lower High
                if price_p2 > price_p1 and rsi_p2 < rsi_p1:
                    signal = "🐻 BEARISH DIVERGENCE"
                    div_type = "Bearish"

        # BULLISH DIVERGENCE CHECK (Lower Lows in Price, Higher Lows in RSI)
        if len(relevant_lows) >= 2:
            p2_idx = relevant_lows[-1]
            p1_idx = relevant_lows[-2]

            # Check if recent valley is very recent
            if (current_idx - p2_idx) <= 5:
                price_p2 = price.iloc[p2_idx]
                price_p1 = price.iloc[p1_idx]

                rsi_p2 = rsi.iloc[p2_idx]
                rsi_p1 = rsi.iloc[p1_idx]

                # Price made Lower Low, RSI made Higher Low
                if price_p2 < price_p1 and rsi_p2 > rsi_p1:
                    signal = "🐂 BULLISH DIVERGENCE"
                    div_type = "Bullish"

        return signal, div_type

    def strategy(ticker, df):
        try:
            if len(df) < 50: return None
            if 'Close' not in df.columns: return None

            # Calc RSI
            rsi = ta.rsi(df['Close'], length=DEFAULT_RSI_LENGTH)
            if rsi is None: return None
            df['RSI'] = rsi

            # Find Div
            signal, div_type = _find_divergence(df['Close'], df['RSI'])

            if signal:
                curr_price = df['Close'].iloc[-1]
                curr_rsi = df['RSI'].iloc[-1]

                # ATR for stop/target
                df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
                atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (curr_price * 0.01)

                stop_loss = curr_price - (3*atr) if div_type == "Bullish" else curr_price + (3*atr)
                target = curr_price + (5*atr) if div_type == "Bullish" else curr_price - (5*atr)

                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

                pct_change_1d = 0.0
                if len(df) >= 2:
                    pct_change_1d = ((curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100

                return {
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": round(curr_price, 2),
                    "pct_change_1d": round(pct_change_1d, 2),
                    "signal": signal,
                    "verdict": signal,
                    "rsi": round(curr_rsi, 2),
                    "atr": round(atr, 2),
                    "atr_value": round(atr, 2),
                    "stop_loss": round(stop_loss, 2),
                    "target": round(target, 2),
                    "breakout_date": _calculate_trend_breakout_date(df),
                    "score": 90
                }
        except Exception as e:
            return None
        return None

    return runner.run(strategy)
