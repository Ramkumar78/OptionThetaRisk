import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Local Imports
from option_auditor.quant_engine import QuantPhysicsEngine
from option_auditor.common.screener_utils import (
    resolve_region_tickers,
    resolve_ticker,
    sanitize
)
from option_auditor.common.data_utils import (
    get_cached_market_data,
    fetch_batch_data_safe,
    _calculate_trend_breakout_date
)
from option_auditor.common.constants import (
    TICKER_NAMES,
    LIQUID_OPTION_TICKERS
)

logger = logging.getLogger(__name__)

def screen_quantum_setups(ticker_list: list = None, region: str = "us", time_frame: str = "1d") -> list:
    """
    Screens for Quantum Setups using QuantPhysicsEngine.
    """
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
