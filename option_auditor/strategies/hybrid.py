import logging
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta

from option_auditor.common.screener_utils import (
    resolve_region_tickers
)
from option_auditor.common.constants import SECTOR_COMPONENTS, TICKER_NAMES
from option_auditor.common.data_utils import (
    fetch_batch_data_safe,
    get_cached_market_data,
    _calculate_trend_breakout_date
)
from option_auditor.strategies.math_utils import calculate_dominant_cycle

logger = logging.getLogger(__name__)

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
            cycle_data = calculate_dominant_cycle(self.df['Close'].tolist())
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
             except Exception as e:
                 logger.debug(f"RSI calc failed: {e}")

        if rsi_val is None or pd.isna(rsi_val): return "NEUTRAL"

        if rsi_val < 30: return "OVERSOLD"
        if rsi_val > 70: return "OVERBOUGHT"
        return "NEUTRAL"

def _process_hybrid_ticker(ticker, df, time_frame, check_mode):
    try:
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

        cycle_data = calculate_dominant_cycle(closes)

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
            except Exception as e:
                logger.debug(f"Pct change calc failed: {e}")

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

def screen_hybrid_strategy(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Robust Hybrid Screener with CHUNKING to prevent API Timeouts.
    Combines ISA Trend Following with Fourier Cycle Analysis.
    """
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
        except Exception as e:
            logger.debug(f"Hybrid check failed for {ticker}: {e}")
            continue

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def screen_confluence_scan(ticker_list: list = None, region: str = "us", check_mode: bool = False, time_frame: str = "1d") -> list:
    """
    Runs ALL strategies on the dataset to find CONFLUENCE.
    Formerly screen_master_convergence (renamed to avoid conflict with Fortress Master).
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
                except Exception as e:
                    logger.debug(f"Pct change calc failed: {e}")

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

        except Exception as e:
            logger.debug(f"Confluence check failed for {ticker}: {e}")
            continue

    results.sort(key=lambda x: x['confluence_score'], reverse=True)
    return results
