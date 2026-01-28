import pandas as pd
import logging
from datetime import datetime, timedelta
from option_auditor.common.data_utils import get_cached_market_data
from option_auditor.common.constants import LIQUID_OPTION_TICKERS, TICKER_NAMES
from option_auditor.common.screener_utils import _get_market_regime, _calculate_trend_breakout_date

logger = logging.getLogger(__name__)

def screen_dynamic_volatility_fortress(ticker_list: list = None, time_frame: str = "1d") -> list:
    """
    YIELD-OPTIMIZED STRATEGY:
    """
    try:
        import pandas_ta as ta
    except ImportError:
        logger.error("pandas_ta not installed")
        return []

    # --- 1. GET VIX & REGIME ---
    current_vix = _get_market_regime()

    # --- 2. THE NEW "YIELD" MATH ---
    safety_k = 1.5 + ((current_vix - 12) / 15.0)

    if safety_k < 1.5: safety_k = 1.5
    if safety_k > 3.0: safety_k = 3.0

    # --- 3. FILTER UNIVERSE ---
    if ticker_list is None:
        ticker_list = LIQUID_OPTION_TICKERS

    all_data = get_cached_market_data(ticker_list, period="1y", cache_name="market_scan_us_liquid")
    results = []

    today = datetime.now()
    manage_date = today + timedelta(days=24)

    # OPTIMIZED ITERATION
    if isinstance(all_data.columns, pd.MultiIndex):
        # This iterator yields (ticker, dataframe)
        iterator = [(ticker, all_data[ticker]) for ticker in all_data.columns.unique(level=0)]
    else:
        # Fallback for single ticker result (rare) or flat
        if not all_data.empty and len(ticker_list)==1:
             iterator = [(ticker_list[0], all_data)]
        else:
             iterator = []

    for ticker, df in iterator:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)

            if ticker not in ticker_list: continue

            df = df.dropna(how='all')
            if len(df) < 100: continue

            curr_close = df['Close'].iloc[-1]

            # --- CRITICAL FILTER: DEAD MONEY CHECK ---
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            atr = df['ATR'].iloc[-1]

            atr_pct = (atr / curr_close) * 100

            if atr_pct < 2.0 and current_vix < 20:
                continue

            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]

            trend_status = "Bullish" if curr_close > sma_200 else "Neutral"

            if curr_close < sma_50: continue

            # --- STRIKE CALCULATION ---
            ema_20 = ta.ema(df['Close'], length=20).iloc[-1]

            safe_floor = ema_20 - (safety_k * atr)

            if safe_floor >= curr_close: continue

            if curr_close < 100:
                short_strike = float(int(safe_floor))
                spread_width = 1.0
            elif curr_close < 300:
                short_strike = float(int(safe_floor / 2.5) * 2.5)
                spread_width = 5.0
            else:
                short_strike = float(int(safe_floor / 5) * 5)
                spread_width = 10.0

            long_strike = short_strike - spread_width

            score = atr_pct * 10
            if curr_close > sma_200: score += 15

            breakout_date = _calculate_trend_breakout_date(df)

            # Fortress Stop/Target (Underlying)
            stock_stop_loss = curr_close - (safety_k * atr)
            stock_target = curr_close + (safety_k * atr * 2)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            results.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": round(curr_close, 2),
                "vix_ref": round(current_vix, 2),
                "volatility_pct": f"{atr_pct:.1f}%",
                "safety_mult": f"{safety_k:.1f}x",
                "sell_strike": short_strike,
                "buy_strike": long_strike,
                "stop_loss": round(stock_stop_loss, 2),
                "target": round(stock_target, 2),
                "dist_pct": f"{((curr_close - short_strike)/curr_close)*100:.1f}%",
                "score": round(score, 1),
                "trend": trend_status,
                "breakout_date": breakout_date,
                "atr": round(atr, 2)
            })

        except Exception: continue

    results.sort(key=lambda x: x['score'], reverse=True)
    return results
