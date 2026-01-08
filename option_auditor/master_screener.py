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
MIN_TURNOVER_USD = 20_000_000
MIN_TURNOVER_GBP = 2_000_000

class FortressScreener:
    def __init__(self, tickers_us=None, tickers_uk=None):
        self.tickers_us = list(set([t for t in (tickers_us or []) if t]))
        self.tickers_uk = list(set([t for t in (tickers_uk or []) if t]))
        self.all_tickers = self.tickers_us + self.tickers_uk
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

    def _calculate_breakout_date(self, close_series, sma_50_series):
        """
        Identifies the last date price crossed ABOVE the SMA 50.
        Returns: (date_string, days_since)
        """
        try:
            # Boolean series: True where Price > SMA50
            above_50 = close_series > sma_50_series

            # Find crossover: Current is True, Previous was False
            # shift(1) moves data down, so we compare Today vs Yesterday
            crossovers = above_50 & (~above_50.shift(1).fillna(False))

            # Get the dates where this happened
            breakout_dates = crossovers[crossovers].index

            if not breakout_dates.empty:
                last_date = breakout_dates[-1]
                # Calculate days since
                days_since = (close_series.index[-1] - last_date).days
                return last_date.strftime("%Y-%m-%d"), days_since
            else:
                # If it's been above for the whole loaded history (2y)
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

            # Liquidity Check
            try: avg_vol = float(volume.rolling(20).mean().iloc[-1])
            except: avg_vol = 0

            is_uk = ticker.endswith(".L")
            if is_uk:
                if (curr_price/100 * avg_vol) < MIN_TURNOVER_GBP: return None
            else:
                if (curr_price * avg_vol) < MIN_TURNOVER_USD: return None

            # Indicators
            sma_50_series = close.rolling(50).mean()
            sma_50 = float(sma_50_series.iloc[-1])
            sma_150 = float(close.rolling(150).mean().iloc[-1])
            sma_200 = float(close.rolling(200).mean().iloc[-1])

            try: rsi = float(ta.rsi(close, length=14).iloc[-1])
            except: rsi = 50.0

            high_52 = float(close.rolling(252).max().iloc[-1])
            low_52 = float(close.rolling(252).min().iloc[-1])

            # --- BREAKOUT DATE CALCULATION ---
            bk_date, days_since = self._calculate_breakout_date(close, sma_50_series)

            # Setup Detection
            setup = "NONE"
            score = 0
            action = "WAIT"
            stop_loss = 0.0
            rs_score = self._calculate_rs_score(df)

            # Trend Template (Minervini)
            stage_2 = (
                curr_price > sma_150 and curr_price > sma_200 and
                sma_150 > sma_200 and sma_50 > sma_150 and
                curr_price > sma_50 and
                curr_price > (low_52 * 1.3) and
                curr_price > (high_52 * 0.75)
            )

            # VCP (Volatility Contraction)
            try:
                vol_10 = float(close.rolling(10).std().iloc[-1])
                vol_50 = float(close.rolling(50).std().iloc[-1])
                is_vcp = (vol_10 / vol_50) < 0.60 if vol_50 > 0 else False
            except: is_vcp = False

            # --- LOGIC ---
            # 1. ISA GROWTH (Trend + VCP)
            if "BULLISH" in self.regime and stage_2 and rs_score > 0:
                if is_vcp:
                    setup = "🚀 ISA: VCP LEADER"
                    score = 90 + rs_score
                elif days_since < 15:
                    setup = "🚀 ISA: FRESH BREAKOUT"
                    score = 85 + rs_score
                else:
                    setup = "⚠️ ISA: EXTENDED" # Valid trend but maybe too late
                    score = 60

                stop_loss = float(low.rolling(20).min().iloc[-1])

                # Sizing
                risk_per_share = curr_price - stop_loss
                if risk_per_share > 0:
                    risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE_PCT
                    fx_rate = 0.79 if not is_uk else 1.0
                    shares = int((risk_amt / fx_rate) / risk_per_share)
                    action = f"BUY ~{shares} (Stop: {stop_loss:.2f})"
                else:
                    action = "WAIT"

            # 2. OPTIONS INCOME (Bull Put)
            elif not is_uk and "BEARISH" not in self.regime:
                if curr_price > sma_200 and rsi < 45 and rsi > 30:
                    setup = "🛡️ OPT: BULL PUT"
                    score = 80 + (50 - rsi)
                    short_strike = round(sma_50 if curr_price > sma_50 else sma_200, 1)
                    if short_strike >= curr_price: short_strike = round(curr_price * 0.95, 1)
                    action = f"SELL 1x {short_strike} PUT"

            if setup == "NONE" or score < 60: return None

            return {
                "Ticker": str(ticker),
                "Price": round(curr_price, 2),
                "Change": round(((curr_price - float(df['Close'].iloc[-2]))/float(df['Close'].iloc[-2]))*100, 2),
                "Setup": setup,
                "Score": round(score, 1),
                "Action": action,
                "RSI": round(rsi, 0),
                "Regime": self.regime,
                "RS_Rating": round(rs_score, 1),
                "breakout_date": bk_date, # <--- NEW FIELD
                "days_since_breakout": days_since, # <--- NEW FIELD
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
    try: from option_auditor.uk_stock_data import get_uk_tickers
    except: get_uk_tickers = lambda: []

    us = []
    uk = []
    if ticker_list:
        for t in ticker_list:
            if ".L" in t: uk.append(t)
            else: us.append(t)
    else:
        if region in ["uk", "uk_euro"]: uk = get_uk_tickers()
        else: us = LIQUID_OPTION_TICKERS + SECTOR_COMPONENTS.get("WATCH", [])

    return FortressScreener(us, uk).run_screen()
