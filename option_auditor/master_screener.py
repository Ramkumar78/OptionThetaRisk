import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
from datetime import datetime

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterScreener")

# --- CONFIGURATION (STRICT MODE) ---
ISA_ACCOUNT_SIZE = 100000.0  # GBP
OPTIONS_ACCOUNT_SIZE = 9500.0 # USD
RISK_PER_TRADE_PCT = 0.01    # Risk 1%
MARKET_TICKERS = ["SPY", "^VIX"]

# LIQUIDITY GATES
LIQUIDITY_MIN_VOL_USD = 2_000_000
LIQUIDITY_MIN_VOL_GBP = 500_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.all_tickers = self.tickers_us + self.tickers_uk
        self.market_regime = "NEUTRAL"
        self.vix_level = 15.0
        self.regime_color = "YELLOW" # Added default

    def _fetch_market_regime(self):
        try:
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            spy_curr = closes['SPY'].dropna().iloc[-1]
            spy_sma = closes['SPY'].dropna().rolling(200).mean().iloc[-1]

            # VIX check
            try:
                self.vix_level = closes['^VIX'].dropna().iloc[-1]
            except:
                self.vix_level = 20.0 # Fallback

            if pd.isna(spy_sma): spy_sma = spy_curr * 0.9

            if spy_curr > spy_sma and self.vix_level < 20:
                self.market_regime = "BULLISH"
                self.regime_color = "GREEN"
            elif spy_curr < spy_sma and self.vix_level > 25:
                self.market_regime = "BEARISH"
                self.regime_color = "RED"
            else:
                self.market_regime = "CAUTIOUS"
                self.regime_color = "YELLOW"

            if self.vix_level > 28:
                self.market_regime = "BEARISH"
                self.regime_color = "RED"

        except Exception:
            self.market_regime = "CAUTIOUS"
            self.regime_color = "YELLOW"

    def _find_breakout(self, df, lookback_days=25):
        """
        Identifies the specific date a stock broke out.
        """
        try:
            # Pivot = Highest High of previous 20 days
            df['Pivot'] = df['High'].rolling(20).max().shift(1)

            # Check last N days for the FIRST break
            recent = df.iloc[-lookback_days:].copy()
            breakouts = recent[recent['Close'] > recent['Pivot']]

            if breakouts.empty:
                return None, None

            # The specific breakout date is the FIRST day in this window it crossed
            first_breakout = breakouts.index[0]
            days_since = (df.index[-1] - first_breakout).days

            return first_breakout.strftime('%Y-%m-%d'), days_since
        except:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            if df.empty or len(df) < 252: return None

            # Handle Columns
            if isinstance(df.columns, pd.MultiIndex):
                if 'Close' in df.columns:
                    close_col = df['Close']
                    high_col = df['High']
                    low_col = df['Low']
                    vol_col = df['Volume']
                else: return None
            else:
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']
                vol_col = df['Volume']

            curr_price = float(close_col.iloc[-1])
            avg_vol_20 = float(vol_col.rolling(20).mean().iloc[-1])

            # Liquidity
            is_uk = ticker.endswith(".L")
            is_us = not is_uk
            if is_us and avg_vol_20 < LIQUIDITY_MIN_VOL_USD: return None
            if is_uk and avg_vol_20 < LIQUIDITY_MIN_VOL_GBP: return None

            # Indicators
            sma_50 = close_col.rolling(50).mean().iloc[-1]
            sma_150 = close_col.rolling(150).mean().iloc[-1]
            sma_200 = close_col.rolling(200).mean().iloc[-1]
            atr = ta.atr(high_col, low_col, close_col, length=14).iloc[-1]
            rsi = ta.rsi(close_col, length=14).iloc[-1]

            high_52 = high_col.rolling(252).max().iloc[-1]
            dist_to_high = (high_52 - curr_price) / high_52

            # --- STRATEGY LOGIC ---
            isa_signal = False
            options_signal = False
            setup_name = ""
            breakout_info = ""
            days_ago_metric = 999 # Default high for sorting

            # === ISA STRATEGY: BREAKOUTS (Fresh & Recent) ===
            trend_aligned = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            # Check Breakout (Window 15 days)
            b_date, days_ago = self._find_breakout(df, lookback_days=20)

            if trend_aligned and b_date and days_ago <= 15:
                # FILTER: Extension check.
                # If breakout was 10 days ago, is price still chaseable? (<20% from 50SMA)
                extension = (curr_price - sma_50) / sma_50

                if extension < 0.25:
                    isa_signal = True
                    days_ago_metric = days_ago

                    if days_ago <= 3:
                        setup_name = f"🔥 FRESH BREAKOUT ({days_ago}d)"
                    else:
                        setup_name = f"Developing Trend ({days_ago}d)"

                    breakout_info = b_date

            # === OPTIONS STRATEGY: MEAN REVERSION ===
            atr_pct = (atr / curr_price) * 100
            if is_us and (curr_price > sma_200):
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback"
                    days_ago_metric = 100 # Push to bottom

            if not isa_signal and not options_signal:
                return None

            # Sizing
            stop_loss = curr_price - (3 * atr)
            risk_per_share = curr_price - stop_loss
            shares = 0
            if risk_per_share > 0 and isa_signal:
                fx = 0.79 if is_us else 1.0
                shares = int((ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT / fx) / risk_per_share)
                max_shares = int((ISA_ACCOUNT_SIZE * 0.20) / (curr_price * fx))
                shares = min(shares, max_shares)

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": "ISA_BUY" if isa_signal else "OPT_SELL",
                "Setup": setup_name,
                "Action": f"Buy {shares}" if isa_signal else "Sell Put Spread",
                "Stop Loss": round(stop_loss, 2),
                "Metrics": f"BO:{breakout_info}" if isa_signal else f"RSI:{rsi:.0f} ATR:{atr_pct:.1f}%",
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2),
                "sort_key": days_ago_metric # Hidden key for sorting
            }

        except Exception as e:
            return None

    def run(self):
        self._fetch_market_regime()

        if self.market_regime == "BEARISH":
            return [{
                "Ticker": "MARKET",
                "Price": 0,
                "Type": "WARNING",
                "Setup": "BEARISH REGIME",
                "Action": "CASH IS KING",
                "Stop Loss": 0,
                "Metrics": f"VIX: {self.vix_level:.2f}",
                "Regime": "RED",
                "sort_key": 0
            }]

        logger.info(f"Scanning {len(self.all_tickers)} tickers...")

        # Batch Fetch (Chunk size 50 is safer for large lists like S&P500)
        chunk_size = 50
        results = []

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    ticker = chunk[0]
                    df = data
                    # Handle MultiIndex if YF returns it even for single ticker
                    if isinstance(data.columns, pd.MultiIndex) and ticker in data.columns:
                         df = data[ticker]

                    res = self._process_stock(ticker, df)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            # Safe slice for MultiIndex
                            # .dropna(how='all') might remove needed rows if not careful,
                            # but usually valid trade days have data.
                            if ticker in data.columns:
                                df = data[ticker].dropna(how='all')
                                res = self._process_stock(ticker, df)
                                if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # SORTING MAGIC:
        # 1. ISA Buys first
        # 2. Inside ISA Buys: Sort by 'sort_key' (Days Since Breakout) ASCENDING
        results.sort(key=lambda x: (x['Type'] != "ISA_BUY", x['sort_key']))

        return results
