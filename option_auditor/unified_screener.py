import pandas as pd
import pandas_ta as ta
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime, timedelta

# Import Strategy Logic
from option_auditor.strategies.isa import IsaStrategy
# from option_auditor.strategies.bull_put import screen_bull_put_spreads # Use simplified logic for speed if needed
from option_auditor.common.constants import TICKER_NAMES, SECTOR_COMPONENTS
from option_auditor.common.data_utils import _calculate_trend_breakout_date, fetch_batch_data_safe
from option_auditor.common.screener_utils import _get_market_regime

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
ISA_CONFIG = {
    "capital": 100000.0,
    "currency": "GBP",
    "min_vol_gbp": 1000000,
    "min_vol_usd": 20000000
}

def get_market_regime_verdict():
    """
    Returns 'GREEN', 'YELLOW', 'RED' based on SPY/VIX.
    Refactored to use generic VIX fetch.
    """
    try:
        vix_price = _get_market_regime() # Returns float

        # We need SPY for the 200 SMA check
        # Let's fetch SPY efficiently
        spy = yf.download("SPY", period="2y", progress=False, auto_adjust=True)
        if spy.empty:
             return "YELLOW", f"VIX {vix_price:.1f} (SPY Fail)"

        # Handle MultiIndex
        if isinstance(spy.columns, pd.MultiIndex):
             spy_close = spy['Close']['SPY'].iloc[-1]
             spy_sma200 = spy['Close']['SPY'].rolling(200).mean().iloc[-1]
        else:
             spy_close = spy['Close'].iloc[-1]
             spy_sma200 = spy['Close'].rolling(200).mean().iloc[-1]

        if pd.isna(spy_sma200):
             spy_sma200 = spy_close # Fallback

        if spy_close < spy_sma200:
             return "RED", f"Bearish (SPY < 200SMA, VIX {vix_price:.1f})"

        if vix_price > 25:
             return "RED", f"High Volatility (VIX {vix_price:.1f})"

        if vix_price < 20:
             return "GREEN", f"Bullish (VIX {vix_price:.1f})"

        return "YELLOW", f"Volatile Bull (VIX {vix_price:.1f})"

    except Exception as e:
        logger.error(f"Regime Check Failed: {e}")
        return "YELLOW", "Check Failed"

def analyze_ticker_hardened(ticker, df, regime, mode="ISA"):
    """
    The Single Reliable Analysis Pipeline.
    Refactored to use Strategy Classes.
    """
    try:
        # 1. DATA HYGIENE
        if df.empty or len(df) < 200: return None

        # 2. LIQUIDITY GATES (Institutional)
        # Delegate to Strategy or Check here?
        # Original code checked here.
        if isinstance(df.columns, pd.MultiIndex):
             close = df['Close'][ticker]
             volume = df['Volume'][ticker]
             high = df['High'][ticker]
             low = df['Low'][ticker]
        else:
             close = df['Close']
             volume = df['Volume']
             high = df['High']
             low = df['Low']

        curr_price = float(close.iloc[-1])
        avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
        turnover = curr_price * avg_vol_20

        is_uk = ticker.endswith(".L")

        # Specific check from original code
        if is_uk:
             turnover_gbp = (turnover / 100) if curr_price > 500 else turnover
             if turnover_gbp < ISA_CONFIG["min_vol_gbp"]: return None
        else:
             if turnover < ISA_CONFIG["min_vol_usd"]: return None

        # 3. REGIME FILTER
        if regime == "RED": return None

        # 4. STRATEGY EXECUTION
        result = None

        # Helper: Calculate Common Metrics (RSI, Score)
        try:
            rsi_series = ta.rsi(close, length=14)
            rsi = float(rsi_series.iloc[-1]) if rsi_series is not None else 0.0

            atr_series = ta.atr(high, low, close, length=14)
            atr = float(atr_series.iloc[-1]) if atr_series is not None else 1.0

            # Score: Slope of 90d reg / ATR
            if len(close) > 90:
                slope = (curr_price - float(close.iloc[-90])) / 90.0
                quality_score = (slope / atr) * 100 if atr > 0 else 0
            else:
                quality_score = 0
        except Exception:
            rsi = 0.0
            quality_score = 0.0

        if mode == "ISA":
            # Use IsaStrategy
            strategy = IsaStrategy(ticker, df, check_mode=False)
            isa_res = strategy.analyze()

            # IsaStrategy returns a dict if valid, else None.
            # But IsaStrategy returns "WAIT" signals too.
            # Original code only returned if "ISA LEADER BREAKOUT".

            if isa_res and ("ENTER" in isa_res['signal'] or "WATCH" in isa_res['signal']):
                # Map to Unified Format
                result = {
                    "ticker": ticker,
                    "company_name": isa_res['company_name'],
                    "price": isa_res['price'],
                    "master_verdict": f"🚀 ISA {isa_res['signal']}", # Add Rocket
                    "action": f"BUY {isa_res.get('shares', 0)} QTY",
                    "stop_loss": isa_res['stop_loss'],
                    "vol_scan": f"{isa_res['atr_value']} ATR", # Approx
                    "rsi": round(rsi, 0),
                    "quality_score": round(quality_score, 2),
                    "master_color": "green",
                    "breakout_date": isa_res['breakout_date']
                }

        elif mode == "OPTIONS" and not is_uk:
            # Re-implement lightweight Bull Put check or use technicals
            # Original code: Trend > 50SMA, RSI < 55 (Pullback), ATR > 2%
            sma50 = close.rolling(50).mean().iloc[-1]
            atr_pct = (atr / curr_price) * 100

            is_uptrend = curr_price > sma50
            pullback = 40 < rsi < 55

            if is_uptrend and pullback and atr_pct > 2.0:
                 short_strike = round(low.rolling(10).min().iloc[-1], 1)
                 long_strike = round(short_strike - 5, 1)
                 result = {
                    "ticker": ticker,
                    "company_name": TICKER_NAMES.get(ticker, ticker),
                    "price": curr_price,
                    "master_verdict": f"🛡️ BULL PUT ({short_strike}/{long_strike})",
                    "action": "SELL VERTICAL PUT",
                    "stop_loss": short_strike,
                    "vol_scan": f"{atr_pct:.1f}% ATR",
                    "rsi": round(rsi, 0),
                    "quality_score": round(quality_score, 2),
                    "master_color": "blue",
                    "breakout_date": _calculate_trend_breakout_date(df)
                 }

        return result

    except Exception as e:
        # logger.error(f"Error in analyze_ticker_hardened: {e}")
        return None

def screen_universal_dashboard(ticker_list: list = None, time_frame: str = "1d") -> dict:
    """
    The Single Entry Point.
    """
    # 1. DETERMINE REGIME
    regime_status, regime_note = get_market_regime_verdict()

    # 2. DEFINE UNIVERSE
    if ticker_list is None:
        ticker_list = [
            "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX",
            "LLOY.L", "AZN.L", "SHEL.L", "HSBA.L", "BP.L", "RIO.L", "GSK.L", "ULVR.L",
            "SPY", "QQQ", "IWM", "GLD"
        ]
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # 3. FETCH DATA
    data = fetch_batch_data_safe(ticker_list, period="2y", interval="1d")

    if data.empty:
        return {"regime": regime_note, "results": []}

    results = []

    def process(ticker):
        try:
            # Extract DF
            df = pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                # Try both level orders (Price, Ticker) vs (Ticker, Price)
                # fetch_batch_data_safe usually returns (Price, Ticker) or (Ticker, Price) depending on yfinance version/params
                # But we can try to extract ticker column
                try:
                    df = data.xs(ticker, axis=1, level=1).copy()
                except KeyError:
                    try:
                        df = data.xs(ticker, axis=1, level=0).copy()
                    except KeyError:
                         pass
            else:
                df = data.copy() # Only if single ticker?

            df = df.dropna(how='all')

            # Check ISA Fit
            res_isa = analyze_ticker_hardened(ticker, df, regime_status, mode="ISA")
            if res_isa: return res_isa

            # Check Options Fit (If US)
            if not ticker.endswith(".L"):
                res_opt = analyze_ticker_hardened(ticker, df, regime_status, mode="OPTIONS")
                if res_opt: return res_opt

            return None

        except:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process, t): t for t in ticker_list}
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    results.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

    return {"regime": regime_note, "results": results}
