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
RISK_PER_TRADE_PCT = 0.0125  # 1.25% Risk (Institutional Standard)

# HARDENED GATES
MIN_PRICE_USD = 10.0
MIN_PRICE_GBP = 100.0 # Pence
MIN_TURNOVER_USD = 20_000_000 # $20M Daily Dollar Volume
MIN_TURNOVER_GBP = 2_000_000  # £2M Daily Sterling Volume

class FortressScreener:
    def __init__(self, tickers_us=None, tickers_uk=None):
        self.tickers_us = list(set([t for t in (tickers_us or []) if t]))
        self.tickers_uk = list(set([t for t in (tickers_uk or []) if t]))
        self.all_tickers = self.tickers_us + self.tickers_uk

        # Market State
        self.regime = "NEUTRAL"
        self.spy_history = None

    def _fetch_market_regime(self):
        """
        Determines if we are in a 'Green Light' or 'Red Light' market.
        """
        logger.info("🚦 Checking Market Regime...")
        try:
            # Download SPY and VIX
            data = yf.download(["SPY", "^VIX"], period="1y", progress=False, auto_adjust=True)

            if data.empty:
                self.regime = "NEUTRAL"
                return

            # Handle yfinance multi-index columns safely
            try:
                spy = data['Close']['SPY'].dropna()
                vix = data['Close']['^VIX'].dropna()
            except KeyError:
                # Fallback if structure is flat (rare but possible)
                if 'SPY' in data.columns: spy = data['SPY']['Close']
                else: spy = pd.Series()
                if '^VIX' in data.columns: vix = data['^VIX']['Close']
                else: vix = pd.Series()

            if spy.empty:
                self.regime = "NEUTRAL"
                return

            self.spy_history = spy

            curr_spy = float(spy.iloc[-1])
            sma_200 = float(spy.rolling(200).mean().iloc[-1])
            curr_vix = float(vix.iloc[-1]) if not vix.empty else 20.0

            # REGIME LOGIC
            if curr_spy > sma_200 and curr_vix < 20:
                self.regime = "🟢 BULLISH (Aggressive)"
            elif curr_spy > sma_200 and curr_vix >= 20:
                self.regime = "🟡 VOLATILE UPTREND (Caution)"
            else:
                self.regime = "🔴 BEARISH (Cash/Puts Only)"

            logger.info(f"MARKET REGIME: {self.regime} | SPY: ${curr_spy:.2f} | VIX: {curr_vix:.2f}")

        except Exception as e:
            logger.error(f"Regime fetch failed: {e}")
            self.regime = "🟡 NEUTRAL (Data Error)"

    def _calculate_rs_score(self, df):
        """Relative Strength vs SPY (Mansfield)."""
        try:
            if self.spy_history is None or self.spy_history.empty: return 0

            stock_cls = df['Close']
            # Intersect dates
            common_idx = stock_cls.index.intersection(self.spy_history.index)
            if len(common_idx) < 63: return 0

            stock_aligned = stock_cls.loc[common_idx]
            spy_aligned = self.spy_history.loc[common_idx]

            rs_ratio = stock_aligned / spy_aligned
            if len(rs_ratio) > 63:
                # 3-Month Slope
                rs_score = ((rs_ratio.iloc[-1] - rs_ratio.iloc[-63]) / rs_ratio.iloc[-63]) * 100
                return rs_score
            return 0
        except:
            return 0

    def _analyze_ticker(self, ticker, df):
        try:
            # 1. CLEANING & PRE-CHECKS
            df = df.dropna(subset=['Close'])
            if len(df) < 200: return None

            # Extract Series
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']

            curr_price = float(close.iloc[-1])

            # Safe Volume Check
            try:
                avg_vol = float(volume.rolling(20).mean().iloc[-1])
            except:
                avg_vol = 0

            is_uk = ticker.endswith(".L")

            # 2. LIQUIDITY GATES
            if is_uk:
                price_gbp = curr_price / 100.0 # Pence to Pounds
                turnover = price_gbp * avg_vol
                if turnover < MIN_TURNOVER_GBP: return None
            else:
                turnover = curr_price * avg_vol
                if turnover < MIN_TURNOVER_USD: return None

            # 3. INDICATORS
            sma_50 = float(close.rolling(50).mean().iloc[-1])
            sma_150 = float(close.rolling(150).mean().iloc[-1])
            sma_200 = float(close.rolling(200).mean().iloc[-1])

            try:
                atr = float(ta.atr(high, low, close, length=14).iloc[-1])
                rsi = float(ta.rsi(close, length=14).iloc[-1])
            except:
                atr, rsi = 0.0, 50.0

            high_52 = float(close.rolling(252).max().iloc[-1])
            low_52 = float(close.rolling(252).min().iloc[-1])

            # 4. STRATEGY GATES
            setup = "NONE"
            score = 0
            action = "WAIT"
            stop_loss = 0.0

            rs_score = self._calculate_rs_score(df)

            # --- STRATEGY A: ISA GROWTH (Minervini) ---
            stage_2 = (
                curr_price > sma_150 and curr_price > sma_200 and
                sma_150 > sma_200 and sma_50 > sma_150 and
                curr_price > sma_50 and
                curr_price > (low_52 * 1.3) and
                curr_price > (high_52 * 0.75)
            )

            # VCP Calculation
            try:
                vol_10 = float(close.rolling(10).std().iloc[-1])
                vol_50 = float(close.rolling(50).std().iloc[-1])
                is_vcp = (vol_10 / vol_50) < 0.60 if vol_50 > 0 else False
            except: is_vcp = False

            if "BULLISH" in self.regime and stage_2 and is_vcp and rs_score > 0:
                setup = "🚀 ISA: VCP LEADER"
                score = 90 + rs_score
                stop_loss = float(low.rolling(20).min().iloc[-1])

                # Sizing Logic
                risk_per_share = curr_price - stop_loss
                if risk_per_share > 0:
                    risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE_PCT
                    fx_rate = 0.79 if not is_uk else 1.0 # USD/GBP approx
                    shares = int((risk_amt / fx_rate) / risk_per_share)
                    action = f"BUY ~{shares} qty (Stop: {stop_loss:.2f})"
                else:
                    action = "WAIT (Stop undefined)"

            # --- STRATEGY B: OPTIONS INCOME (Bull Put) ---
            # For $9.5k account: Blue chips, trend up, short term oversold
            elif not is_uk and "BEARISH" not in self.regime:
                if curr_price > sma_200 and rsi < 45 and rsi > 30:
                    setup = "🛡️ OPT: BULL PUT"
                    score = 80 + (50 - rsi)

                    short_strike = sma_50 if curr_price > sma_50 else sma_200
                    if short_strike >= curr_price: short_strike = curr_price * 0.95

                    short_strike = round(short_strike, 1)
                    long_strike = round(short_strike - 5, 1)

                    # Risk 5% of $9500 = $475. Max Loss per spread approx $500.
                    # So 1 contract.
                    action = f"SELL 1x {short_strike}/{long_strike} PUT VERTICAL"

            if setup == "NONE": return None

            # STRICT RETURN STRUCTURE (Prevent Frontend Crash)
            return {
                "Ticker": str(ticker),
                "Price": round(curr_price, 2),
                "Change": round(((curr_price - float(df['Close'].iloc[-2]))/float(df['Close'].iloc[-2]))*100, 2),
                "Volume": int(avg_vol),
                "Setup": setup,
                "Score": round(score, 1),
                "Action": action,
                "RSI": round(rsi, 0),
                "ATR": round(atr, 2),
                "Regime": self.regime,
                "RS_Rating": round(rs_score, 1),
                "VCP": "YES" if is_vcp else "NO",
                # Dummy fields to satisfy any other potential frontend checks
                "Sector": "N/A", "Industry": "N/A", "MarketCap": "N/A"
            }

        except Exception as e:
            # logger.error(f"Err {ticker}: {e}")
            return None

    def run_screen(self):
        self._fetch_market_regime()
        results = []
        chunk_size = 50

        logger.info(f"Scanning {len(self.all_tickers)} tickers...")

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                # Fast batch download
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

# Compatibility Adapter for CLI/Webapp
def screen_master_convergence(ticker_list=None, region="us", check_mode=False):
    # Dynamic imports to avoid circular deps
    from option_auditor.common.constants import LIQUID_OPTION_TICKERS, SECTOR_COMPONENTS
    try:
        from option_auditor.uk_stock_data import get_uk_tickers
    except:
        def get_uk_tickers(): return []

    us_tickers = []
    uk_tickers = []

    # If list provided (e.g. from Check Stock box)
    if ticker_list:
        for t in ticker_list:
            if ".L" in t: uk_tickers.append(t)
            else: us_tickers.append(t)
    else:
        # Default Lists
        if region in ["uk", "uk_euro"]:
            uk_tickers = get_uk_tickers()
        else:
            us_tickers = LIQUID_OPTION_TICKERS + SECTOR_COMPONENTS.get("WATCH", [])

    screener = FortressScreener(us_tickers, uk_tickers)
    results = screener.run_screen()
    return results # Returns list of dicts directly
