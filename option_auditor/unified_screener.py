import pandas as pd
import pandas_ta as ta
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime, timedelta

# Import Strategy Logic (Keep specific calc logic, but we govern execution here)
from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.common.constants import TICKER_NAMES, SECTOR_COMPONENTS

logger = logging.getLogger(__name__)

# --- CONFIGURATION FOR 100K GBP ISA & 9.5K USD OPTIONS ---
ISA_CONFIG = {
    "capital": 100000.0,
    "currency": "GBP",
    "risk_per_trade": 0.01, # 1% Risk
    "max_pos_size": 0.20,   # Max 20% in one stock
    "min_price": 10.0,
    "min_vol_gbp": 1000000, # £1M daily turnover
    "min_vol_usd": 20000000 # $20M daily turnover
}

OPTIONS_CONFIG = {
    "capital": 9500.0,
    "currency": "USD",
    "risk_per_trade": 0.02, # 2% Risk (More aggressive on small acc)
    "min_iv_rank": 20,
    "min_vol_usd": 30000000
}

def get_market_regime():
    """
    DALIO / SOROS CHECK:
    Returns 'GREEN', 'YELLOW', 'RED'.
    If SPY < 200SMA or VIX > 25, we do NOT buy stocks.
    """
    try:
        tickers = ["SPY", "^VIX"]
        data = yf.download(tickers, period="1y", progress=False, auto_adjust=True)

        # Handle multi-index columns from yfinance
        if isinstance(data.columns, pd.MultiIndex):
            # yfinance returns (Price, Ticker) MultiIndex
            try:
                spy = data['Close']['SPY']
                vix = data['Close']['^VIX']
            except KeyError:
                 # Try reverse (Ticker, Price) just in case
                spy = data['SPY']['Close']
                vix = data['^VIX']['Close']
        else:
            # Fallback if download structure changes
            return "YELLOW", "Data Error"

        spy_price = spy.iloc[-1]
        spy_sma200 = spy.rolling(200).mean().iloc[-1]
        vix_price = vix.iloc[-1]

        if spy_price > spy_sma200 and vix_price < 20:
            return "GREEN", f"Bullish (VIX {vix_price:.1f})"
        elif spy_price > spy_sma200 and vix_price < 28:
            return "YELLOW", f"Volatile Bull (VIX {vix_price:.1f})"
        else:
            return "RED", f"Bearish/Crash (VIX {vix_price:.1f})"
    except Exception as e:
        logger.error(f"Regime Check Failed: {e}")
        return "YELLOW", "Check Failed"

def analyze_ticker_hardened(ticker, df, regime, mode="ISA"):
    """
    The Single Reliable Analysis Pipeline.
    """
    try:
        # 1. DATA HYGIENE
        if df.empty or len(df) < 252: return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        curr_price = float(close.iloc[-1])

        # 2. LIQUIDITY GATES (Institutional)
        avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
        turnover = curr_price * avg_vol_20

        is_uk = ticker.endswith(".L")

        if is_uk:
            # Normalize Pence to Pounds for turnover calc if needed, usually Yahoo sends pence
            # Assuming Yahoo sends pence for LSE stocks < 20gbp typically
            turnover_gbp = (turnover / 100) if curr_price > 500 else turnover
            if turnover_gbp < ISA_CONFIG["min_vol_gbp"]: return None
        else:
            if turnover < ISA_CONFIG["min_vol_usd"]: return None

        # 3. REGIME FILTER (The Kill Switch)
        # If Regime is RED, we only look for Short setups or Deep Value (not covered here).
        # We return None to enforce discipline.
        if regime == "RED":
            return None

        # 4. TECHNICAL METRICS
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        atr = ta.atr(high, low, close, length=14).iloc[-1]
        rsi = ta.rsi(close, length=14).iloc[-1]

        # Relative Volume
        rvol = volume.iloc[-1] / avg_vol_20

        # 5. STRATEGY SELECTION BASED ON MODE

        setup_type = None
        action = None
        stop_loss = 0.0

        # --- MODE: ISA (Long Only Equity) ---
        if mode == "ISA":
            # TREND TEMPLATE (Minervini)
            # 1. Price > 200 SMA
            # 2. Price > 50 SMA
            # 3. 50 SMA > 200 SMA
            # 4. Price at least 25% above 52-week low (Momentum)
            # 5. Price within 25% of 52-week high (Near leaders)

            low_52w = low.rolling(252).min().iloc[-1]
            high_52w = high.rolling(252).max().iloc[-1]

            is_trend = (curr_price > sma200) and (curr_price > sma50) and (sma50 > sma200)
            is_leader = (curr_price > 1.25 * low_52w) and (curr_price > 0.75 * high_52w)

            # TRIGGER: VCP Breakout or Pocket Pivot
            # Simple Trigger: Consolidation breakout (Close > 20 Day High) + Volume
            high_20d = high.rolling(20).max().shift(1).iloc[-1]
            breakout = (curr_price > high_20d) and (rvol > 1.2)

            if is_trend and is_leader and breakout:
                setup_type = "🚀 ISA LEADER BREAKOUT"
                stop_loss = curr_price - (2.5 * atr) # Wide swing stop

                # POSITION SIZING (Kelly/Fixed Ratio)
                risk_amt = ISA_CONFIG["capital"] * ISA_CONFIG["risk_per_trade"]
                risk_per_share = curr_price - stop_loss
                if risk_per_share <= 0: risk_per_share = curr_price * 0.10

                # FX Conversion for US stocks in ISA
                fx_rate = 1.0 if is_uk else 0.79 # USD to GBP approx

                shares = int((risk_amt) / (risk_per_share * fx_rate))

                # Cap at max allocation
                max_shares = int((ISA_CONFIG["capital"] * ISA_CONFIG["max_pos_size"]) / (curr_price * fx_rate))
                shares = min(shares, max_shares)

                action = f"BUY {shares} QTY"

        # --- MODE: OPTIONS (US Income) ---
        elif mode == "OPTIONS" and not is_uk:
            # BULL PUT SPREAD (Thorp/Income)
            # 1. Trend is Up (Price > 50SMA)
            # 2. Not Overbought (RSI < 70)
            # 3. High IV Rank (Implied here by ATR ratio > 2.5% of price)

            atr_pct = (atr / curr_price) * 100
            is_uptrend = curr_price > sma50
            pullback = rsi < 55 and rsi > 40 # Slight dip in uptrend

            if is_uptrend and pullback and atr_pct > 2.0:
                setup_type = "🛡️ BULL PUT SPREAD"
                short_strike = round(low.rolling(10).min().iloc[-1], 1) # Support level
                long_strike = round(short_strike - 5, 1)
                credit_est = (curr_price - short_strike) * 0.15 # Rough est

                setup_type += f" ({short_strike}/{long_strike})"
                action = "SELL VERTICAL PUT"

        if not setup_type:
            return None

        # SCORE: Risk Adjusted Momentum
        # (Slope of 90d reg / ATR) - measures smoothness of trend
        slope = (curr_price - close.iloc[-90]) / 90
        quality_score = (slope / atr) * 100

        return {
            "ticker": ticker,
            "company_name": TICKER_NAMES.get(ticker, ticker),
            "price": curr_price,
            "master_verdict": setup_type,
            "action": action,
            "stop_loss": round(stop_loss, 2),
            "vol_scan": f"{rvol:.1f}x Vol",
            "rsi": round(rsi, 0),
            "quality_score": round(quality_score, 2),
            "master_color": "green" if "ISA" in mode else "blue"
        }

    except Exception as e:
        return None

def screen_universal_dashboard(ticker_list: list = None, time_frame: str = "1d") -> dict:
    """
    The Single Entry Point.
    1. Checks Regime.
    2. Scans UK/US Universes.
    3. Returns enriched list in dictionary format:
       {
          "regime": "GREEN/YELLOW/RED ...",
          "results": [...]
       }
    """
    # 1. DETERMINE REGIME
    regime_status, regime_note = get_market_regime()

    # 2. DEFINE UNIVERSE
    # Expand the default list to be useful.
    if ticker_list is None:
        # Default mix of US Tech + UK Blue Chips
        ticker_list = [
            "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX", # US Leaders
            "LLOY.L", "AZN.L", "SHEL.L", "HSBA.L", "BP.L", "RIO.L", "GSK.L", "ULVR.L", # UK Leaders
            "SPY", "QQQ", "IWM", "GLD" # ETFs
        ]
        # Add Sector Watch
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # 3. FETCH DATA
    from option_auditor.common.data_utils import fetch_batch_data_safe
    data = fetch_batch_data_safe(ticker_list, period="2y", interval="1d")

    # If NO DATA at all, return empty results but still return the regime
    if data.empty:
        return {"regime": regime_note, "results": []}

    results = []

    def process(ticker):
        try:
            # Extract DF
            df = pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                # Try both level orders (Price, Ticker) vs (Ticker, Price)
                try:
                    df = data.xs(ticker, axis=1, level=1).copy()
                except KeyError:
                    try:
                        df = data.xs(ticker, axis=1, level=0).copy()
                    except KeyError:
                         # Ticker not found in columns
                         pass
            else:
                df = data.copy()

            df = df.dropna(how='all')

            # DETECT MODE
            mode = "ISA" # Default
            if ticker not in ["LLOY.L", "AZN.L"] and not ticker.endswith(".L"):
                # If it's a US stock, we might want Options or ISA
                # For this One Screener, we calculate BOTH and return the best
                pass

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
                # We no longer inject regime here
                results.append(res)

    # Sort by Quality Score (Smooth Momentum)
    results.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

    return {"regime": regime_note, "results": results}
