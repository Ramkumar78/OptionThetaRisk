import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.strategies.fourier import FourierStrategy
from option_auditor.common.constants import TICKER_NAMES, SECTOR_COMPONENTS
from option_auditor.optimization import PortfolioOptimizer
from option_auditor.quant_engine import QuantPhysicsEngine
# Use centralized verdict logic from QuantPhysicsEngine to avoid circular import with screener.py
generate_human_verdict = QuantPhysicsEngine.generate_human_verdict

logger = logging.getLogger(__name__)

def run_quantum_audit(ticker, df, tech_result):
    try:
        prices = df['Close'].values
        close_series = df['Close']

        # Calculate physical stats
        h = QuantPhysicsEngine.calculate_hurst(close_series)
        s = QuantPhysicsEngine.shannon_entropy(close_series)
        decay_days = QuantPhysicsEngine.calculate_momentum_decay(prices)

        # Calculate Kalman Slope for consistency with main screener
        kalman = QuantPhysicsEngine.kalman_filter(close_series)
        k_slope = (kalman.iloc[-1] - kalman.iloc[-3]) / 2.0

        # USE CENTRALIZED LOGIC
        # We replace the hardcoded "EXHAUSTED" logic with the shared "human verdict"
        verdict, rationale = generate_human_verdict(h, s, k_slope, float(close_series.iloc[-1]))

        # Map back to Dashboard format
        final_verdict = tech_result.get('master_verdict', 'WAIT')
        if "BUY" in verdict:
             final_verdict = f"🚀 QUANTUM {final_verdict}"
        elif "SHORT" in verdict:
             final_verdict = f"📉 QUANTUM SHORT"

        return {
            **tech_result,
            "master_verdict": final_verdict,
            "hurst": h,
            "entropy": s,
            "quantum_note": rationale # Add the rationale to the dashboard
        }
    except Exception as e:
        logger.error(f"Quantum audit failed for {ticker}: {e}")
        return tech_result

def screen_universal_dashboard(ticker_list: list = None, time_frame: str = "1d") -> list:
    """
    Runs ALL strategies on the provided ticker list using a single data fetch.
    Returns a unified "Master Signal" matrix.
    """
    if ticker_list is None:
        # Default to a mix if not provided
        ticker_list = ["SPY", "QQQ", "IWM", "AAPL", "NVDA", "MSFT", "TSLA", "AMD", "AMZN", "GOOGL"]
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # 1. Download Data ONCE
    # Use 2 years to satisfy ISA (200 SMA) and Fourier
    period = "2y"
    yf_interval = "1d"

    # Adjust for timeframe if needed (though universal dashboard implies daily macro view usually)
    if time_frame != "1d":
        # Logic for intraday?
        # For now, let's assume this is a Daily Dashboard tool as described in "Morning Meeting".
        pass

    # 1. Download Data in Chunks using robust fetcher
    from option_auditor.common.data_utils import fetch_batch_data_safe

    try:
        data = fetch_batch_data_safe(ticker_list, period=period, interval=yf_interval, chunk_size=50)
    except Exception as e:
        logger.error(f"Universal dashboard data fetch failed: {e}")
        return []

    if data.empty:
        return []

    results = []

    # Initialize Strategies
    turtle_strat = TurtleStrategy()
    isa_strat = IsaStrategy()
    fourier_strat = FourierStrategy()

    def process_ticker(ticker):
        try:
            # Prepare DF
            df = pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data.columns.levels[0]:
                    df = data[ticker].copy()
            else:
                df = data.copy()

            df = df.dropna(how='all')
            if len(df) < 50: return None

            # Run Strategies
            turtle_res = turtle_strat.analyze(df)
            isa_res = isa_strat.analyze(df)
            fourier_res = fourier_strat.analyze(df)

            # Collate Verdict (Confluence)
            confluence_score = 0
            buy_signals = 0
            sell_signals = 0

            # Weighted Scoring?
            # Turtle Buy + ISA Buy = Strong Trend
            # Fourier Buy = Cycle Low

            # Count positive signals (BUY or strong HOLD/WATCH)
            if turtle_res['signal'] in ["BUY", "WATCH"]: buy_signals += 1
            if isa_res['signal'] in ["BUY", "WATCH", "HOLD"]: buy_signals += 1
            if fourier_res['signal'] == "BUY": buy_signals += 1

            if turtle_res['signal'] == "SELL": sell_signals += 1
            # ISA doesn't short usually, but if AVOID/EXIT?
            if isa_res['signal'] == "EXIT": sell_signals += 0.5
            if fourier_res['signal'] == "SELL": sell_signals += 1

            master_verdict = "WAIT"
            master_color = "gray"

            if buy_signals == 3:
                master_verdict = "🚀 STRONG BUY (3/3)"
                master_color = "green"
            elif buy_signals == 2:
                master_verdict = "✅ BUY (2/3 Confluence)"
                master_color = "green"
            elif buy_signals == 1:
                # Which one?
                if fourier_res['signal'] == "BUY":
                    master_verdict = "🌊 DIP BUY (Cycle Only)"
                    master_color = "blue"
                else:
                    master_verdict = "👀 WATCH (Trend Start)"
                    master_color = "yellow"

            if sell_signals >= 2:
                master_verdict = "🛑 STRONG SELL / AVOID"
                master_color = "red"

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            tech_result = {
                "ticker": ticker,
                "company_name": company_name,
                "price": float(df['Close'].iloc[-1]),
                "master_verdict": master_verdict,
                "master_color": master_color,
                "confluence_score": f"{buy_signals}/3",
                "strategies": {
                    "turtle": turtle_res,
                    "isa": isa_res,
                    "fourier": fourier_res
                }
            }

            # --- QUANTUM AUDIT ---
            quantum_result = run_quantum_audit(ticker, df, tech_result)
            return quantum_result

        except Exception as e:
            # logger.error(f"Error processing universal {ticker}: {e}")
            return None

    # Threaded Execution
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {executor.submit(process_ticker, sym): sym for sym in ticker_list}
        for future in as_completed(future_to_symbol):
            try:
                res = future.result()
                if res: results.append(res)
            except: pass

    # Sort by Buy Confluence (and maybe Quantum Score/Hurst if we had it numerically easier)
    # Just sort by text score for now
    results.sort(key=lambda x: x['confluence_score'], reverse=True)

    # --- NEW: Enrich only the output ---
    from option_auditor.screener import enrich_with_fundamentals

    # Only enrich the top 30 results to keep UI snappy
    top_results = results[:30]
    remaining = results[30:]

    enriched_top = enrich_with_fundamentals(top_results)

    results = enriched_top + remaining

    # --- OPTIMIZATION STEP ---
    # 1. Identify "BUY" candidates for optimization
    buy_candidates = []
    expected_returns = {}

    for r in results:
        # Extract signal counts
        buy_count = int(r['confluence_score'].split('/')[0])

        # Check Quantum status
        is_quantum = "QUANTUM" in r.get('master_verdict', '')
        is_valid = "RANDOM" not in r.get('verdict', '') and "HEAT DEATH" not in r.get('verdict', '') and "EXHAUSTED" not in r.get('verdict', '')

        # Simple Logic: Only optimize allocation for Strong Buys (2/3 or 3/3) AND Valid Physics
        if buy_count >= 2 and is_valid:
            ticker = r['ticker']
            buy_candidates.append(ticker)

            # Map Confluence to Expected Return (Heuristic)
            # 3/3 = 40% Annualized Exp Return
            # 2/3 = 20% Annualized Exp Return
            # Bonus for Quantum
            base_return = 0.40 if buy_count == 3 else 0.20
            if is_quantum:
                base_return += 0.10

            expected_returns[ticker] = base_return

    # 2. Run Optimizer if we have candidates
    if len(buy_candidates) >= 2:
        try:
            optimizer = PortfolioOptimizer(buy_candidates)
            # Reuse existing data to avoid double download
            optimizer.set_data(data)

            # Maximize Sharpe Ratio
            allocations = optimizer.optimize_weights(expected_returns_map=expected_returns)

            # 3. Enrich Results with Allocation
            for r in results:
                t = r['ticker']
                if t in allocations:
                    weight = allocations[t]
                    r['optimized_weight'] = f"{weight*100:.1f}%"
                    r['allocation_note'] = "Optimal MVO"
                elif t in buy_candidates:
                    r['optimized_weight'] = "0.0%" # Optimized out
        except Exception as e:
            logger.error(f"Portfolio Optimization failed in Dashboard: {e}")

    return results
