import pandas as pd
import numpy as np
import yfinance as yf
import os
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Local Imports
from option_auditor.common.screener_utils import _calculate_put_delta
from option_auditor.common.constants import RISK_FREE_RATE

logger = logging.getLogger(__name__)

def screen_options_only_strategy(region: str = "us", limit: int = 75) -> list:
    """
    THALAIVA'S OPTIONS ONLY PROTOCOL (Optimized for Speed)
    ------------------------------------------------------
    Fixes:
    - Reduced history fetch to 5 days (faster liquidity check).
    - Added strict limit to prevent Worker Timeouts.
    - Aggressive error handling for yfinance 404s.
    """

    # --- 1. LOAD TICKERS ---
    # We are in option_auditor/strategies/options_only.py
    # Data is in option_auditor/data/us_sectors.csv
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, '../data/us_sectors.csv')

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
            except Exception:
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
            except Exception as e:
                logger.debug(f"Earnings check failed: {e}")
                earnings_date = None

            # --- PHASE 3: EXPIRATIONS ---
            try:
                expirations = tk.options
            except Exception:
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
                except Exception:
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
            except Exception:
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

        except Exception as e:
            logger.debug(f"Options only failed for {ticker}: {e}")
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
            except Exception as e:
                logger.debug(f"Future failed: {e}")

    results.sort(key=lambda x: (1 if "GREEN" in x['verdict'] else 0, x['roc']), reverse=True)
    return results
