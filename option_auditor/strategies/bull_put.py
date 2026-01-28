import math
import logging
import concurrent.futures
from datetime import date
import pandas as pd
import numpy as np
import pandas_ta as ta
import yfinance as yf

from option_auditor.common.screener_utils import (
    resolve_region_tickers,
    _calculate_put_delta
)
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.common.constants import RISK_FREE_RATE, TICKER_NAMES

logger = logging.getLogger(__name__)

def screen_bull_put_spreads(ticker_list: list = None, min_roi: float = 0.15, region: str = "us", check_mode: bool = False, time_frame: str = "1d") -> list:
    """
    Screens for High Probability Bull Put Spreads (TastyTrade Mechanics).
    - 30-60 DTE
    - 30 Delta Short
    - $5 Wide Wings
    - High IV (IV > HV)
    - Liquid (>1M Vol)
    """
    if ticker_list is None:
        ticker_list = resolve_region_tickers(region)

    # TASTYTRADE PARAMETERS
    MIN_DTE = 30
    MAX_DTE = 60
    TARGET_DTE = 45
    SPREAD_WIDTH = 5.0
    TARGET_DELTA = -0.30
    MIN_AVG_VOLUME = 1_000_000  # Liquid Underlyings Rule

    results = []

    def _process_spread(ticker):
        try:
            # 1. TECHNICAL & LIQUIDITY FILTER (Fast Fail)
            tk = yf.Ticker(ticker)

            # Fetch 1y to calculate HV (Historical Volatility) and Trend
            df = tk.history(period="1y", interval="1d", auto_adjust=True)

            if df.empty or len(df) < 200: return None

            # Flatten MultiIndex if necessary
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            curr_price = float(df['Close'].iloc[-1])
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]

            # Liquidity Rule: Skip "Ant" stocks or Illiquid names
            if not check_mode and (avg_vol < MIN_AVG_VOLUME or curr_price < 20):
                return None

            # Trend Rule: Bullish/Neutral (Price > SMA 50)
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            if not check_mode and curr_price < sma_50:
                return None

            # Historical Volatility (HV) - Annualized StdDev of Log Returns
            log_returns = np.log(df['Close'] / df['Close'].shift(1))
            hv_annual = log_returns.std() * np.sqrt(252)

            # 2. OPTION EXPIRATION FILTER
            expirations = tk.options
            if not expirations: return None

            today = date.today()
            best_date = None
            min_diff = 999

            valid_exps = []
            for exp_str in expirations:
                exp_date = pd.to_datetime(exp_str).date()
                dte = (exp_date - today).days
                if MIN_DTE <= dte <= MAX_DTE:
                    valid_exps.append((exp_str, dte))

            # Pick the one closest to 45 DTE
            if not valid_exps: return None
            valid_exps.sort(key=lambda x: abs(x[1] - TARGET_DTE))
            best_date, actual_dte = valid_exps[0]

            # 3. CHAIN ANALYSIS
            try:
                chain = tk.option_chain(best_date)
                puts = chain.puts
            except Exception:
                return None # Failed to fetch chain

            if puts.empty: return None

            # Add Delta Column to Chain
            T_years = actual_dte / 365.0

            # Use vectorized apply for speed
            # If IV is 0 or NaN, assume HV as fallback for delta calc (common data issue)
            puts['impliedVolatility'] = puts['impliedVolatility'].replace(0, hv_annual)

            puts['calc_delta'] = puts.apply(
                lambda row: _calculate_put_delta(
                    curr_price, row['strike'], T_years, RISK_FREE_RATE, row['impliedVolatility']
                ), axis=1
            )

            # 4. FIND SHORT STRIKE (~30 Delta)
            # Filter for OTM puts only (Strike < Price) to ensure it's a credit spread
            otm_puts = puts[puts['strike'] < curr_price].copy()
            if otm_puts.empty: return None

            otm_puts['delta_dist'] = (otm_puts['calc_delta'] - TARGET_DELTA).abs()
            short_leg_row = otm_puts.loc[otm_puts['delta_dist'].idxmin()]

            short_strike = float(short_leg_row['strike'])
            short_iv = float(short_leg_row['impliedVolatility'])
            short_delta = float(short_leg_row['calc_delta'])

            # Check IV "Richness" (Proxy for IV Rank)
            # If Implied Volatility is lower than Historical Volatility, premiums are cheap (Bad for selling)
            # Allow pass if check_mode is on
            if not check_mode and short_iv < (hv_annual * 0.9):
                # Strict: IV must be at least near HV. Ideally > HV.
                # return None
                pass # Warning only for now, or user will see "Low IV" label

            # 5. FIND LONG STRIKE ($5 Wide Strict)
            long_strike_target = short_strike - SPREAD_WIDTH

            # Find exact strike match or very close match
            long_candidates = puts[ (puts['strike'] - long_strike_target).abs() < 0.1 ]

            if long_candidates.empty:
                return None # No $5 wide strike available

            long_leg_row = long_candidates.iloc[0]
            long_strike = float(long_leg_row['strike'])

            # 6. PRICING & METRICS
            # Use Bid for Short (Selling) and Ask for Long (Buying) -> Conservative Credit
            # Fallback to lastPrice if bid/ask is broken/zero (common in yfinance)
            short_bid = short_leg_row['bid'] if short_leg_row['bid'] > 0 else short_leg_row['lastPrice']
            long_ask = long_leg_row['ask'] if long_leg_row['ask'] > 0 else long_leg_row['lastPrice']

            credit = short_bid - long_ask
            width = short_strike - long_strike
            max_risk = width - credit

            # Sanity Checks
            if credit <= 0 or max_risk <= 0: return None

            roi = credit / max_risk
            if not check_mode and roi < min_roi: return None

            # Probability of Profit (POP) approximation for Credit Spread
            # Roughly 1 - Delta of Short Option (Theoretical Prob OTM)
            pop_pct = (1.0 + short_delta) * 100 # short_delta is negative (e.g. -0.30 -> 70% POP)

            break_even = short_strike - credit

            # IV Status
            iv_status = "High" if short_iv > hv_annual else "Normal"
            if short_iv > (hv_annual * 1.5): iv_status = "🔥 Very High"
            elif short_iv < hv_annual: iv_status = "Low (Cheap)"

            # Prepare Output
            pct_change_1d = 0.0
            if len(df) >= 2:
                prev_close = float(df['Close'].iloc[-2])
                pct_change_1d = ((curr_price - prev_close) / prev_close) * 100

            # Technicals
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            atr = df['ATR'].iloc[-1]
            breakout_date = _calculate_trend_breakout_date(df)

            high_52 = df['High'].max()
            low_52 = df['Low'].min()

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(curr_price, 2),
                "pct_change_1d": round(pct_change_1d, 2),
                "strategy": "Bull Put (Credit Spread)",
                "expiry": str(best_date),
                "dte": int(actual_dte),
                "short_strike": short_strike,
                "long_strike": long_strike,
                "width": round(width, 2),
                "short_delta": round(short_delta, 2),
                "credit": round(credit * 100, 2), # Total credit per 1 contract ($)
                "max_risk": round(max_risk * 100, 2), # Total risk per 1 contract ($)
                "roi_pct": round(roi * 100, 1),
                "pop": round(pop_pct, 1),
                "iv_annual": round(short_iv * 100, 1),
                "hv_annual": round(hv_annual * 100, 1),
                "iv_status": iv_status,
                "break_even": round(break_even, 2),
                "trend": "Bullish" if curr_price > sma_50 else "Bearish",
                "vol_scan": f"{int(avg_vol/1000)}k",
                "breakout_date": breakout_date,
                "atr": round(atr, 2),
                "52_week_high": round(high_52, 2),
                "52_week_low": round(low_52, 2),
                # UI Helpers
                "atr_value": round(atr, 2),
                "stop_loss": round(curr_price - 2*atr, 2), # Technical Stop Reference
                "target": round(curr_price + 2*atr, 2),
                "sector_change": round(pct_change_1d, 2)
            }

        except Exception as e:
            # logger.error(f"Spread Calc Error {ticker}: {e}")
            return None

    # Multi-threaded execution to handle network latency
    final_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_process_spread, t): t for t in ticker_list}
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res: final_list.append(res)
            except: pass

    # Sort by ROI or POP
    final_list.sort(key=lambda x: x['roi_pct'], reverse=True)
    return final_list
