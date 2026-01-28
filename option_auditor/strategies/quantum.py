import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from option_auditor.common.screener_utils import ScreeningRunner
from option_auditor.strategies.math_utils import (
    calculate_hurst,
    shannon_entropy,
    kalman_filter,
    generate_human_verdict
)
from option_auditor.common.data_utils import get_cached_market_data, fetch_batch_data_safe
from option_auditor.common.constants import TICKER_NAMES

logger = logging.getLogger(__name__)

def screen_quantum_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for Quantum Setups using math_utils.
    Logic:
    1. Calculate Hurst Exponent (Memory)
    2. Calculate Entropy (Chaos)
    3. Calculate Kalman Filter Slope (True Trend)
    4. Generate Human Verdict
    """
    if not ticker_list:
        return []

    results = []

    # Fetch data
    try:
        # Retrieve Data
        cache_name = "market_scan_us_liquid"
        if region == "india": cache_name = "market_scan_india"
        elif region == "uk": cache_name = "market_scan_uk"
        elif region == "uk_euro": cache_name = "market_scan_europe"
        elif region == "sp500": cache_name = "market_scan_v1"

        try:
            all_data = get_cached_market_data(ticker_list, period="2y", cache_name=cache_name)
        except Exception:
            all_data = None

        if all_data is None or all_data.empty:
             all_data = fetch_batch_data_safe(ticker_list, period="2y", interval=time_frame)

        # Handle Flat vs MultiIndex
        ticker_data_map = {}
        if isinstance(all_data.columns, pd.MultiIndex):
            for t in ticker_list:
                try:
                    # Select ticker from Level 0
                    if t in all_data.columns.get_level_values(0):
                         df = all_data[t]
                         if not df.empty:
                             ticker_data_map[t] = df
                except KeyError:
                    pass
        else:
            if len(ticker_list) == 1:
                ticker_data_map[ticker_list[0]] = all_data

        for ticker, df in ticker_data_map.items():
            if len(df) < 200: continue

            close = df['Close']
            curr_price = close.iloc[-1]

            # Physics
            hurst = calculate_hurst(close)
            entropy = shannon_entropy(close)
            kalman = kalman_filter(close)

            # Slope of Kalman (last 5 days)
            k_slope = 0.0
            if len(kalman) > 5:
                k_slope = (kalman.iloc[-1] - kalman.iloc[-5]) / kalman.iloc[-5]

            ai_verdict, ai_rationale = generate_human_verdict(hurst, entropy, k_slope, curr_price)

            # Calculate ATR for Risk Management
            # Default length 14
            atr_series = ta.atr(df['High'], df['Low'], close, length=14)
            current_atr = atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 0.0

            # Risk Management Defaults
            stop_loss = curr_price - (2.5 * current_atr) # Default Long Stop
            target = curr_price + (4.0 * current_atr)   # Default Long Target

            if "SHORT" in ai_verdict:
                stop_loss = curr_price + (2.5 * current_atr)
                target = curr_price - (4.0 * current_atr)

            verdict_color = "gray"
            score = 0
            if "BUY" in ai_verdict:
                verdict_color = "green"
                score = 2
            elif "SHORT" in ai_verdict:
                verdict_color = "red"
                score = 1

            results.append({
                "ticker": ticker,
                "company_name": TICKER_NAMES.get(ticker, ticker),
                "price": curr_price,
                "human_verdict": ai_verdict,
                "rationale": ai_rationale,
                "hurst": round(hurst, 2) if hurst is not None else None,
                "entropy": round(entropy, 2) if entropy is not None else None,
                "verdict_color": verdict_color,
                "score": score,
                "ATR": round(current_atr, 2),
                "atr": round(current_atr, 2), # Duplicate for consistency
                "Stop Loss": round(stop_loss, 2),
                "Target": round(target, 2),
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2)
            })

        # Sort by score desc
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    except Exception as e:
        logger.error(f"Quantum Screen Error: {e}")
        return []
