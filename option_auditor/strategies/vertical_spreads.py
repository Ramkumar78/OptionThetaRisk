import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from option_auditor.common.data_utils import fetch_batch_data_safe
from option_auditor.common.screener_utils import resolve_region_tickers, _calculate_put_delta
from option_auditor.common.constants import TICKER_NAMES, RISK_FREE_RATE

logger = logging.getLogger(__name__)

def screen_vertical_put_spreads(ticker_list: list = None, region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for High Probability Vertical Put Credit Spreads (Bull Put).
    Logic:
    1. Trend: Price > 200 SMA & 50 SMA.
    2. Volatility: IV (ATM) > HV (20-day).
    3. Earnings: No earnings in next 21 days.
    4. Liquidity: Option Vol > 1000, OI > 500.
    5. Setup: 21-45 DTE, ~0.30 Delta Short, $5 Width.
    """
    if ticker_list is None:
        # Default to US liquid list + Sectors if not provided
        ticker_list = resolve_region_tickers(region)

    # 1. BATCH FETCH DATA (Trend & Stock Liquidity)
    # We fetch 1 year to ensure 200 SMA is valid
    try:
        data = fetch_batch_data_safe(ticker_list, period="1y", interval="1d", raise_on_error=False)
    except Exception as e:
        # If it's a critical yfinance error (401, 429), re-raise to UI
        if "401" in str(e) or "429" in str(e) or "Unauthorized" in str(e):
            raise e
        logger.error(f"Vertical Put Data Fetch Error: {e}")
        return []

    if data.empty:
        logger.warning("Vertical Put: No market data returned.")
        return []

    # Helper to iterate batch data
    iterator = []
    if isinstance(data.columns, pd.MultiIndex):
        iterator = [(t, data[t]) for t in data.columns.levels[0] if t in ticker_list]
    elif len(ticker_list) == 1 and not data.empty:
        iterator = [(ticker_list[0], data)]

    # Pre-filter candidates based on Trend to save API calls for Option Chains
    trend_candidates = []

    for ticker, df in iterator:
        try:
            df = df.dropna(how='all')
            if len(df) < 200: continue

            # Clean columns if multi-index remnants exist
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)

            curr_price = float(df['Close'].iloc[-1])

            # --- FILTER 1: TREND ALIGNMENT ---
            # Source: Price > 200 SMA and Price > 50 SMA
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]

            if curr_price < sma_200 or curr_price < sma_50:
                continue

            # --- FILTER 2: HISTORICAL VOLATILITY ---
            # Calculate HV(20) as baseline
            # Log Returns -> Std Dev -> Annualize
            log_return = np.log(df['Close'] / df['Close'].shift(1))
            hv_20 = log_return.rolling(20).std().iloc[-1] * np.sqrt(252) * 100

            trend_candidates.append({
                "ticker": ticker,
                "price": curr_price,
                "sma_50": sma_50,
                "sma_200": sma_200,
                "hv_20": hv_20,
                "vol_avg": df['Volume'].rolling(20).mean().iloc[-1]
            })
        except Exception:
            continue

    # Limit option chain scanning to avoid timeouts (Top 50 by Volume)
    trend_candidates.sort(key=lambda x: x['vol_avg'], reverse=True)
    trend_candidates = trend_candidates[:50]

    results = []

    # 2. OPTION CHAIN ANALYSIS (Earnings, Liquidity, Greeks)
    # RISK_FREE_RATE imported from constants
    MIN_DTE = 21
    MAX_DTE = 45
    SPREAD_WIDTH = 5.0
    TARGET_DELTA = -0.30

    def process_options(candidate):
        ticker = candidate['ticker']
        curr_price = candidate['price']
        hv_20 = candidate['hv_20']

        try:
            tk = yf.Ticker(ticker)

            # --- FILTER 3: EARNINGS AVOIDANCE ---
            # Exclude if earnings in next 21 days
            try:
                cal = tk.calendar
                earnings_date = None

                # Handle various yfinance calendar formats
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    earnings_date = cal['Earnings Date'][0]
                elif isinstance(cal, pd.DataFrame) and not cal.empty:
                    # Often row 0 is next earnings
                    val = cal.iloc[0, 0]
                    # Check if it's a date object or string
                    if isinstance(val, (date, datetime, pd.Timestamp, str)):
                        earnings_date = val

                if earnings_date:
                    # Fix: Use errors='coerce' to prevent "The string did not match expected pattern" error
                    dt_val = pd.to_datetime(earnings_date, errors='coerce')
                    if not pd.isna(dt_val):
                        earnings_date = dt_val.date()
                        days_to_earnings = (earnings_date - date.today()).days
                        if 0 <= days_to_earnings <= 21:
                            return None # Skip (Earnings Risk)
            except Exception as e:
                logger.debug(f"Earnings check failed: {e}")

            # --- FILTER 4: EXPIRATION SELECTION (21-45 DTE) ---
            expirations = tk.options
            if not expirations: return None

            target_exp = None
            actual_dte = 0

            # Find best expiry closest to 30-45 days
            valid_exps = []
            today = date.today()

            for exp in expirations:
                try:
                    # Fix: Use errors='coerce' to handle malformed expiration strings safely
                    d = pd.to_datetime(exp, errors='coerce')
                    if pd.isna(d): continue

                    d_date = d.date()
                    dte = (d_date - today).days
                    if MIN_DTE <= dte <= MAX_DTE:
                        valid_exps.append((exp, dte))
                except Exception:
                     continue

            if not valid_exps: return None

            # Sort by closeness to 35 days (Midpoint)
            valid_exps.sort(key=lambda x: abs(x[1] - 35))
            target_exp, actual_dte = valid_exps[0]

            # Fetch Chain
            chain = tk.option_chain(target_exp)
            puts = chain.puts

            if puts.empty: return None

            # --- FILTER 5: OPTION LIQUIDITY ---
            # Volume > 1000, OI > 500 (Aggregate)
            total_vol = puts['volume'].sum()
            total_oi = puts['openInterest'].sum()

            if total_vol < 1000 or total_oi < 500:
                return None

            # --- FILTER 6: IMPLIED VOLATILITY CHECK ---
            # Find ATM IV
            atm_row = puts.iloc[(puts['strike'] - curr_price).abs().argsort()[:1]]
            if atm_row.empty: return None

            atm_iv = float(atm_row['impliedVolatility'].iloc[0] * 100)

            # IV > HV Check (Edge)
            if atm_iv < hv_20:
                # Strictly speaking, we want IV > HV.
                # If slightly below, we might skip. Let's enforce strictness.
                return None

            # --- STEP 7: STRIKE SELECTION (Delta ~0.30) ---
            T_years = actual_dte / 365.0

            # Calculate Delta
            puts['calc_delta'] = puts.apply(
                lambda x: _calculate_put_delta(
                    curr_price, x['strike'], T_years, RISK_FREE_RATE,
                    x['impliedVolatility'] if x['impliedVolatility'] > 0 else (hv_20/100)
                ), axis=1
            )

            # Filter OTM Puts
            otm_puts = puts[puts['strike'] < curr_price].copy()
            if otm_puts.empty: return None

            # Find Short (Sell) Strike closest to 30 Delta
            short_leg = otm_puts.iloc[(otm_puts['calc_delta'] - TARGET_DELTA).abs().argsort()[:1]].iloc[0]
            short_strike = float(short_leg['strike'])
            short_delta = float(short_leg['calc_delta'])
            short_bid = float(short_leg['bid'] if short_leg['bid'] > 0 else short_leg['lastPrice'])

            # Find Long (Buy) Strike ($5 Wide)
            target_long = short_strike - SPREAD_WIDTH
            long_leg_candidates = puts.iloc[(puts['strike'] - target_long).abs().argsort()[:1]]
            if long_leg_candidates.empty: return None
            long_leg = long_leg_candidates.iloc[0]
            long_strike = float(long_leg['strike'])
            long_ask = float(long_leg['ask'] if long_leg['ask'] > 0 else long_leg['lastPrice'])

            # Calculate Credit
            credit = short_bid - long_ask
            width = short_strike - long_strike
            max_risk = width - credit

            if credit <= 0.15 or max_risk <= 0: return None

            roc = (credit / max_risk) * 100

            # Minimum ROC Filter (10% min, usually aim for 15%+)
            if roc < 10.0: return None

            # Base Ticker Name
            base = ticker.split('.')[0]
            comp_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base, ticker))

            return {
                "ticker": ticker,
                "company_name": comp_name,
                "price": round(curr_price, 2),
                "verdict": "🟢 HIGH PROB",
                "setup_name": f"Bull Put {int(short_strike)}/{int(long_strike)}",
                "short_put": int(short_strike),
                "long_put": int(long_strike),
                "expiry_date": target_exp,
                "dte": actual_dte,
                "credit": round(credit * 100, 0), # In Dollars
                "risk": round(max_risk * 100, 0),
                "roc": round(roc, 1),
                "earnings_gap": "Safe (>21d)",
                "delta": round(short_delta, 2),
                "iv_atm": round(atm_iv, 1),
                "hv_20": round(hv_20, 1),
                "option_vol": int(total_vol)
            }

        except Exception as e:
            logger.debug(f"Vertical spread calc failed: {e}")
            return None

    # Threaded Execution for Option Chains
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_options, c): c for c in trend_candidates}
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)

    # Sort by ROC
    results.sort(key=lambda x: x['roc'], reverse=True)
    return results
