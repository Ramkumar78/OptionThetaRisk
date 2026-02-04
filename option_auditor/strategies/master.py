import logging
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
from typing import List, Optional, Dict, Any

from option_auditor.common.screener_utils import (
    ScreeningRunner,
    run_screening_strategy,
    resolve_region_tickers,
    _get_market_regime as _get_simple_vix
)
from option_auditor.strategies.grandmaster_screener import GrandmasterScreener
from option_auditor.common.constants import (
    ISA_ACCOUNT_GBP, RISK_PER_TRADE_PCT, MIN_PRICE_USD, MIN_PRICE_GBP, MIN_PRICE_INR,
    MIN_TURNOVER_USD, MIN_TURNOVER_GBP, MIN_TURNOVER_INR
)

logger = logging.getLogger(__name__)

def get_detailed_market_regime() -> dict:
    """
    Checks SPY/VIX to determine if we can buy.
    Returns a dict with 'regime', 'spy_history', 'vix'.
    """
    logger.info("🚦 Checking Market Regime...")
    regime = "NEUTRAL"
    spy_history = None
    curr_vix = 20.0

    try:
        data = yf.download(["SPY", "^VIX"], period="1y", progress=False, auto_adjust=True)
        if data.empty:
            return {"regime": "🟡 NEUTRAL (Data Empty)", "spy_history": None, "vix": 20.0}

        try:
            spy = data['Close']['SPY'].dropna()
            vix = data['Close']['^VIX'].dropna()
        except KeyError:
            # Handle potential flat structure if only one symbol returned (unlikely with list)
            if 'SPY' in data.columns: spy = data['SPY']['Close'] if 'Close' in data['SPY'] else data['SPY']
            else: spy = pd.Series()
            if '^VIX' in data.columns: vix = data['^VIX']['Close'] if 'Close' in data['^VIX'] else data['^VIX']
            else: vix = pd.Series()

        if spy.empty:
            return {"regime": "🟡 NEUTRAL (No SPY Data)", "spy_history": None, "vix": 20.0}

        spy_history = spy
        curr_spy = float(spy.iloc[-1])
        sma_200 = float(spy.rolling(200).mean().iloc[-1])
        curr_vix = float(vix.iloc[-1]) if not vix.empty else 20.0

        if curr_spy > sma_200 and curr_vix < 20:
            regime = "🟢 BULLISH (Aggressive)"
        elif curr_spy > sma_200 and curr_vix >= 20:
            regime = "🟡 VOLATILE UPTREND (Caution)"
        else:
            regime = "🔴 BEARISH (Cash/Puts Only)"

        logger.info(f"MARKET REGIME: {regime}")

    except Exception as e:
        logger.error(f"Regime fetch failed: {e}")
        regime = "🟡 NEUTRAL (Data Error)"

    return {
        "regime": regime,
        "spy_history": spy_history,
        "vix": curr_vix
    }

class FortressMasterScreener:
    """
    Orchestrates the Grandmaster (Growth) and Lite Bull Put (Options) strategies
    based on Market Regime.
    """
    def __init__(self, regime_data: dict, check_mode: bool = False):
        self.regime = regime_data.get("regime", "NEUTRAL")
        self.spy_history = regime_data.get("spy_history")
        self.vix = regime_data.get("vix", 20.0)
        self.check_mode = check_mode
        self.grandmaster = GrandmasterScreener()

    def _calculate_rs_score(self, df):
        try:
            if self.spy_history is None or self.spy_history.empty: return 0
            stock_cls = df['Close']

            # Align indices
            common_idx = stock_cls.index.intersection(self.spy_history.index)
            if len(common_idx) < 63: return 0

            stock_aligned = stock_cls.loc[common_idx]
            spy_aligned = self.spy_history.loc[common_idx]
            rs_ratio = stock_aligned / spy_aligned

            if len(rs_ratio) > 63:
                return ((rs_ratio.iloc[-1] - rs_ratio.iloc[-63]) / rs_ratio.iloc[-63]) * 100
            return 0
        except: return 0

    def analyze(self, ticker: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        try:
            if df is None or df.empty or len(df) < 200: return None

            curr_price = float(df['Close'].iloc[-1])
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            try: avg_vol = float(volume.rolling(20).mean().iloc[-1])
            except: avg_vol = 0

            # --- REGION IDENTIFICATION ---
            is_uk = ticker.endswith(".L")
            is_india = ticker.endswith(".NS")
            is_us = not (is_uk or is_india)

            # --- LIQUIDITY GATES ---
            if not self.check_mode:
                if is_uk:
                    price_gbp = curr_price / 100.0
                    turnover = price_gbp * avg_vol
                    if turnover < MIN_TURNOVER_GBP: return None
                elif is_india:
                    turnover = curr_price * avg_vol
                    if turnover < MIN_TURNOVER_INR: return None
                    if curr_price < MIN_PRICE_INR: return None
                else: # US
                    turnover = curr_price * avg_vol
                    if turnover < MIN_TURNOVER_USD: return None
                    if curr_price < MIN_PRICE_USD: return None

            # --- RUN GRANDMASTER (GROWTH) ---
            gm_result = self.grandmaster.analyze(df)

            setup = "NONE"
            score = 0
            action = "WAIT"
            rs_score = self._calculate_rs_score(df)

            # Extract metrics from GM result
            atr = gm_result.get('volatility_atr', 0.0)
            breakout_level = gm_result.get('breakout_level', 0.0)
            stop_loss = gm_result.get('stop_loss_atr', 0.0)

            # --- STRATEGY LOGIC ---

            # 1. GROWTH (ISA / General Trend)
            # Logic: If Regime is Bullish OR stock is exceptionally strong (RS Score > 10)
            if ("BULLISH" in self.regime) or (rs_score > 10):

                gm_signal = gm_result.get('signal', 'WAIT')

                # Grandmaster uses "BUY BREAKOUT", "WATCHLIST"
                if "BUY" in gm_signal:
                    setup = "🚀 Turtle Breakout" if is_us else "🚀 Leader Breakout"
                    score = 85 + rs_score
                    if score > 99: score = 99

                    # Sizing Logic
                    if is_uk:
                        risk_per_share = (curr_price/100.0) - (stop_loss/100.0)
                        if risk_per_share > 0:
                            risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE_PCT
                            shares = int(risk_amt / risk_per_share)
                            action = f"BUY ~{shares} (ISA)"
                    elif is_india:
                         action = f"BUY (Stop: {stop_loss:.1f})"
                    else:
                        risk_per_share = curr_price - stop_loss
                        if risk_per_share > 0:
                            risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE_PCT
                            fx_rate = 0.79 # USD/GBP approx
                            shares = int((risk_amt / fx_rate) / risk_per_share)
                            action = f"BUY ~{shares} (ISA)"

                elif "WATCHLIST" in gm_signal:
                    setup = "⚠️ Trend Follower"
                    score = 60 + (rs_score / 2)
                    action = "WATCH"

            # 2. OPTIONS INCOME (US Only) - LITE CHECK
            # Logic: If NOT Bearish (so Bullish or Neutral/Volatile ok) and US
            if is_us and "BEARISH" not in self.regime and setup == "NONE":
                sma_50 = df['Close'].rolling(50).mean().iloc[-1]
                sma_200 = df['Close'].rolling(200).mean().iloc[-1]

                try: rsi = float(ta.rsi(df['Close'], length=14).iloc[-1])
                except: rsi = 50.0

                if curr_price > sma_200 and rsi < 45 and rsi > 30:
                    setup = "🛡️ OPT: BULL PUT"
                    score = 80 + (50 - rsi)

                    # Simple council parameters for Put
                    stop_loss = curr_price - (2.0 * atr)
                    target = curr_price + (4.0 * atr)

                    short_strike = round(sma_50 if curr_price > sma_50 else sma_200, 1)
                    if short_strike >= curr_price: short_strike = round(curr_price * 0.95, 1)
                    action = f"SELL 1x {short_strike} PUT"

            if setup == "NONE" or score < 60: return None

            # Legacy fields for Frontend compatibility
            # It expects: Ticker, Price, Change, Setup, Strategy, Score, Action, RSI, Regime, RS_Rating, Breakout, ATR, Stop, Target, VCP

            pct_change = 0.0
            if len(df) >= 2:
                pct_change = ((curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100

            try: rsi = float(ta.rsi(df['Close'], length=14).iloc[-1])
            except: rsi = 50.0

            # VCP Check (re-implemented lite version or just pass NO)
            is_vcp = False # Can be improved later by pulling from GM if it had it

            # Breakout Date
            bk_date_str = "Consolidating" # Placeholder or calc

            return {
                "Ticker": str(ticker),
                "Price": round(curr_price, 2),
                "Change": round(pct_change, 2),
                "Setup": setup,
                "Strategy": setup, # Alias
                "Score": round(score, 1),
                "Action": action,
                "RSI": round(rsi, 0),
                "Regime": self.regime,
                "RS_Rating": round(rs_score, 1),
                "Breakout": bk_date_str,
                "ATR": round(atr, 2),
                "Stop": round(stop_loss, 2),
                "Target": round(gm_result.get('target', curr_price + 3*atr), 2), # Default target if not set
                "days_since_breakout": 0, # Placeholder
                "breakout_date": bk_date_str, # Placeholder
                "VCP": "YES" if is_vcp else "NO"
            }

        except Exception as e:
            # logger.error(f"Error analyzing {ticker}: {e}")
            return None

def screen_master_convergence(ticker_list: list = None, region: str = "us", check_mode: bool = False, time_frame: str = "1d") -> list:
    """
    Runs the Master Fortress Screener.
    Orchestrates Grandmaster (Growth) and Bull Put (Options) strategies.
    """
    if ticker_list is None:
        ticker_list = resolve_region_tickers(region)

    # Fetch Regime once
    regime_data = get_detailed_market_regime()

    # Initialize Strategy Wrapper
    screener_instance = FortressMasterScreener(regime_data, check_mode=check_mode)

    # Use generic runner
    # We pass the method `screener_instance.analyze`
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

    results = runner.run(screener_instance.analyze)

    # Sort by Score
    results.sort(key=lambda x: x['Score'], reverse=True)
    return results
