import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
import traceback
from datetime import datetime, timedelta

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FortressScreener")

# --- USER CONFIGURATION ---
ISA_ACCOUNT_GBP = 100000.0
OPTIONS_ACCOUNT_USD = 9500.0
RISK_PER_TRADE_PCT = 0.0125  # 1.25% Risk

# HARDENED GATES
MIN_PRICE_USD = 10.0
MIN_PRICE_GBP = 100.0 # Pence
MIN_PRICE_INR = 100.0 # Rupees

MIN_TURNOVER_USD = 20_000_000
MIN_TURNOVER_GBP = 2_000_000
MIN_TURNOVER_INR = 50_000_000 # 5 Crores INR

class FortressScreener:
    def __init__(self, tickers_us=None, tickers_uk=None, tickers_india=None):
        self.tickers_us = list(set([t for t in (tickers_us or []) if t]))
        self.tickers_uk = list(set([t for t in (tickers_uk or []) if t]))
        self.tickers_india = list(set([t for t in (tickers_india or []) if t]))

        self.all_tickers = self.tickers_us + self.tickers_uk + self.tickers_india
        self.regime = "NEUTRAL"
        self.spy_history = None

    def _fetch_market_regime(self):
        """Checks SPY/VIX to determine if we can buy."""
        logger.info("🚦 Checking Market Regime...")
        try:
            data = yf.download(["SPY", "^VIX"], period="1y", progress=False, auto_adjust=True)
            if data.empty: return

            try:
                spy = data['Close']['SPY'].dropna()
                vix = data['Close']['^VIX'].dropna()
            except KeyError:
                if 'SPY' in data.columns: spy = data['SPY']['Close']
                else: spy = pd.Series()
                if '^VIX' in data.columns: vix = data['^VIX']['Close']
                else: vix = pd.Series()

            if spy.empty: return

            self.spy_history = spy
            curr_spy = float(spy.iloc[-1])
            sma_200 = float(spy.rolling(200).mean().iloc[-1])
            curr_vix = float(vix.iloc[-1]) if not vix.empty else 20.0

            if curr_spy > sma_200 and curr_vix < 20:
                self.regime = "🟢 BULLISH (Aggressive)"
            elif curr_spy > sma_200 and curr_vix >= 20:
                self.regime = "🟡 VOLATILE UPTREND (Caution)"
            else:
                self.regime = "🔴 BEARISH (Cash/Puts Only)"

            logger.info(f"MARKET REGIME: {self.regime}")

        except Exception as e:
            logger.error(f"Regime fetch failed: {e}")
            self.regime = "🟡 NEUTRAL (Data Error)"

    def calculate_atr(self, df, period=14):
        """Calculates the Average True Range (ATR)"""
        try:
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            return float(true_range.rolling(window=period).mean().iloc[-1])
        except:
            return 0.0

    def get_breakout_date(self, df, window=20):
        """Finds the most recent date where price broke a N-day high"""
        try:
            recent = df.iloc[-30:].copy() # Look back 30 days
            roll_max = df['High'].rolling(window=window).max().shift(1)

            # Check where Close > Previous N-Day High
            # Align indices
            roll_max_aligned = roll_max.reindex(recent.index)
            breakouts = recent[recent['Close'] > roll_max_aligned]

            if not breakouts.empty:
                return breakouts.index[-1].strftime('%Y-%m-%d')
            return "Consolidating"
        except:
            return "Unknown"

    def get_council_parameters(self, member_name, price, atr):
        """
        Returns Stop Loss and Target based on the famous trader's style.
        """
        stop = 0.0
        target = 0.0

        # GROUP 1: TREND FOLLOWERS (Turtles, Seykota, Dennis)
        # Style: Wide stops (ATR based), huge targets.
        if any(x in member_name for x in ['Turtle', 'Seykota', 'Dennis', 'Parker', 'Hite', 'Dunn']):
            stop = price - (2.0 * atr)
            target = price + (10.0 * atr) # Let winners run

        # GROUP 2: MOMENTUM / SWING (Minervini, Zanger, O'Neil, Kulmagi)
        # Style: Tight stops (Volatility contraction), quick targets.
        elif any(x in member_name for x in ['Minervini', 'Zanger', 'Kulmagi', 'CanSlim', 'Morales']):
            stop = price * 0.93 # 7-8% Stop strictly
            target = price * 1.25 # 20-25% Target

        # GROUP 3: QUANTS / STAT ARB (Simons, Thorp, Shaw, Griffin)
        # Style: Statistical deviation.
        elif any(x in member_name for x in ['Simons', 'Thorp', 'Shaw', 'Griffin', 'Muller', 'Put']):
            stop = price - (1.5 * atr)
            target = price + (1.5 * atr) # High frequency/mean reversion often tighter

        # GROUP 4: MACRO / VALUE (Soros, Druckenmiller, Buffett)
        # Style: Structural stops.
        elif any(x in member_name for x in ['Soros', 'Druckenmiller', 'Buffett', 'Dalio']):
            stop = price * 0.90 # 10% Structural stop
            target = price * 1.50 # 50% Macro move

        # DEFAULT (The Council Consensus)
        else:
            stop = price - (2 * atr)
            target = price + (4 * atr)

        return round(stop, 2), round(target, 2)

    def _calculate_breakout_date(self, close_series, sma_50_series):
        try:
            above_50 = close_series > sma_50_series
            crossovers = above_50 & (~above_50.shift(1).fillna(False))
            breakout_dates = crossovers[crossovers].index

            if not breakout_dates.empty:
                last_date = breakout_dates[-1]
                days_since = (close_series.index[-1] - last_date).days
                return last_date.strftime("%Y-%m-%d"), days_since
            else:
                return "Long Term Leader", 999
        except:
            return "Unknown", 0

    def _calculate_rs_score(self, df):
        try:
            if self.spy_history is None or self.spy_history.empty: return 0
            stock_cls = df['Close']
            common_idx = stock_cls.index.intersection(self.spy_history.index)
            if len(common_idx) < 63: return 0

            stock_aligned = stock_cls.loc[common_idx]
            spy_aligned = self.spy_history.loc[common_idx]
            rs_ratio = stock_aligned / spy_aligned

            if len(rs_ratio) > 63:
                return ((rs_ratio.iloc[-1] - rs_ratio.iloc[-63]) / rs_ratio.iloc[-63]) * 100
            return 0
        except: return 0

    def _analyze_ticker(self, ticker, df):
        try:
            df = df.dropna(subset=['Close'])
            if len(df) < 200: return None

            close = df['Close']
            low = df['Low']
            volume = df['Volume']
            curr_price = float(close.iloc[-1])

            try: avg_vol = float(volume.rolling(20).mean().iloc[-1])
            except: avg_vol = 0

            # --- REGION IDENTIFICATION ---
            is_uk = ticker.endswith(".L")
            is_india = ticker.endswith(".NS")
            is_us = not (is_uk or is_india)

            # --- LIQUIDITY GATES ---
            if is_uk:
                price_gbp = curr_price / 100.0
                turnover = price_gbp * avg_vol
                if turnover < MIN_TURNOVER_GBP: return None
            elif is_india:
                turnover = curr_price * avg_vol
                if turnover < MIN_TURNOVER_INR: return None # 5 Cr
                if curr_price < MIN_PRICE_INR: return None
            else: # US
                turnover = curr_price * avg_vol
                if turnover < MIN_TURNOVER_USD: return None
                if curr_price < MIN_PRICE_USD: return None

            # Indicators
            sma_50_series = close.rolling(50).mean()
            sma_50 = float(sma_50_series.iloc[-1])
            sma_150 = float(close.rolling(150).mean().iloc[-1])
            sma_200 = float(close.rolling(200).mean().iloc[-1])

            try: rsi = float(ta.rsi(close, length=14).iloc[-1])
            except: rsi = 50.0

            high_52 = float(close.rolling(252).max().iloc[-1])
            low_52 = float(close.rolling(252).min().iloc[-1])

            # Breakout Date
            bk_date_str = self.get_breakout_date(df)
            atr_value = self.calculate_atr(df)

            # Legacy calc for scoring
            legacy_bk_date, days_since = self._calculate_breakout_date(close, sma_50_series)

            setup = "NONE"
            score = 0
            action = "WAIT"
            rs_score = self._calculate_rs_score(df)

            # Trend Template (Minervini)
            stage_2 = (
                curr_price > sma_150 and curr_price > sma_200 and
                sma_150 > sma_200 and sma_50 > sma_150 and
                curr_price > sma_50 and
                curr_price > (low_52 * 1.3) and
                curr_price > (high_52 * 0.75)
            )

            # VCP
            try:
                vol_10 = float(close.rolling(10).std().iloc[-1])
                vol_50 = float(close.rolling(50).std().iloc[-1])
                is_vcp = (vol_10 / vol_50) < 0.60 if vol_50 > 0 else False
            except: is_vcp = False

            # --- STRATEGY LOGIC ---

            # 1. GROWTH (ISA / General Trend) - Applies to ALL regions
            if "BULLISH" in self.regime and stage_2 and rs_score > 0:
                if is_vcp:
                    setup = "🚀 Minervini VCP"
                    score = 90 + rs_score
                elif days_since < 15:
                    setup = "🚀 Turtle Breakout"
                    score = 85 + rs_score
                else:
                    setup = "⚠️ Trend Follower"
                    score = 60

                # Existing sizing logic preserved but ACTION string updated
                stop_loss, target_price = self.get_council_parameters(setup, curr_price, atr_value)

                # Sizing Logic based on Region
                if is_uk:
                    # ISA Account Logic (GBP)
                    risk_per_share = (curr_price/100.0) - (stop_loss/100.0)
                    if risk_per_share > 0:
                        risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE_PCT
                        shares = int(risk_amt / risk_per_share)
                        action = f"BUY ~{shares} (ISA)"
                elif is_india:
                    # Generic Sizing for India (assuming 1L capital for example or just unit based)
                    risk_per_share = curr_price - stop_loss
                    if risk_per_share > 0:
                        action = f"BUY (Stop: {stop_loss:.1f})"
                else:
                    # US Logic (ISA allowed)
                    risk_per_share = curr_price - stop_loss
                    if risk_per_share > 0:
                        risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE_PCT
                        fx_rate = 0.79 # USD/GBP
                        shares = int((risk_amt / fx_rate) / risk_per_share)
                        action = f"BUY ~{shares} (ISA)"

            # 2. OPTIONS INCOME (US Only)
            elif is_us and "BEARISH" not in self.regime:
                if curr_price > sma_200 and rsi < 45 and rsi > 30:
                    setup = "🛡️ OPT: BULL PUT"
                    score = 80 + (50 - rsi)
                    stop_loss, target_price = self.get_council_parameters("Put", curr_price, atr_value)

                    short_strike = round(sma_50 if curr_price > sma_50 else sma_200, 1)
                    if short_strike >= curr_price: short_strike = round(curr_price * 0.95, 1)
                    action = f"SELL 1x {short_strike} PUT"
                else:
                    stop_loss = 0.0
                    target_price = 0.0

            if setup == "NONE" or score < 60: return None

            # Recalculate Stop/Target if not set (for safety)
            if 'stop_loss' not in locals():
                stop_loss, target_price = self.get_council_parameters(setup, curr_price, atr_value)

            return {
                "Ticker": str(ticker),
                "Price": round(curr_price, 2),
                "Change": round(((curr_price - float(df['Close'].iloc[-2]))/float(df['Close'].iloc[-2]))*100, 2),
                "Setup": setup,
                "Strategy": setup, # Alias for Frontend
                "Score": round(score, 1),
                "Action": action,
                "RSI": round(rsi, 0),
                "Regime": self.regime,
                "RS_Rating": round(rs_score, 1),
                "Breakout": bk_date_str, # New Field
                "ATR": round(atr_value, 2), # New Field
                "Stop": stop_loss, # New Field
                "Target": target_price, # New Field
                "days_since_breakout": days_since,
                "VCP": "YES" if is_vcp else "NO"
            }

        except Exception as e:
            return None

    def run_screen(self):
        self._fetch_market_regime()
        results = []
        chunk_size = 50

        logger.info(f"Scanning {len(self.all_tickers)} tickers...")

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)
                for ticker in chunk:
                    try:
                        df = None
                        if len(chunk) == 1: df = data
                        elif isinstance(data.columns, pd.MultiIndex):
                            if ticker in data.columns.levels[0]: df = data[ticker]

                        if df is not None and not df.empty:
                            res = self._analyze_ticker(ticker, df)
                            if res: results.append(res)
                    except: continue
            except: continue

        results.sort(key=lambda x: x['Score'], reverse=True)
        return results

def screen_master_convergence(ticker_list=None, region="us", check_mode=False):
    from option_auditor.common.constants import LIQUID_OPTION_TICKERS, SECTOR_COMPONENTS

    # 1. Ticker Loading Logic
    us = []
    uk = []
    india = []

    if ticker_list:
        # Manual check mode
        for t in ticker_list:
            if ".L" in t: uk.append(t)
            elif ".NS" in t: india.append(t)
            else: us.append(t)
    else:
        # Automatic Region Selection
        if region == "india":
            # Attempt to load India tickers dynamically
            try:
                from option_auditor.india_stock_data import get_indian_tickers
                india = get_indian_tickers()
            except ImportError:
                # Fallback Nifty List if file missing
                india = []
        elif region in ["uk", "uk_euro"]:
            try:
                from option_auditor.uk_stock_data import get_uk_tickers
                uk = get_uk_tickers()
            except: uk = []
        else:
            # Default to US
            us = LIQUID_OPTION_TICKERS + SECTOR_COMPONENTS.get("WATCH", [])

    return FortressScreener(tickers_us=us, tickers_uk=uk, tickers_india=india).run_screen()
