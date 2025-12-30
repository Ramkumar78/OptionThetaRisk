import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
from datetime import timedelta

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
        self.regime_color = "YELLOW"
        self.vix_level = 15.0

    def _fetch_market_regime(self):
        try:
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            spy_curr = closes['SPY'].dropna().iloc[-1]
            spy_sma = closes['SPY'].dropna().rolling(200).mean().iloc[-1]
            self.vix_level = closes['^VIX'].dropna().iloc[-1]

            if pd.isna(spy_sma): spy_sma = spy_curr * 0.9 # Fallback

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

    def _find_breakout(self, df, lookback_days=15):
        """
        Identifies the specific date a stock broke out of a base.
        Definition: Price closes above the highest high of the previous 20 days.
        Returns: (date_str, days_since) or (None, None)
        """
        try:
            # Create a "Pivot" line (Highest High of previous 20 days)
            # shift(1) is crucial so we don't compare today's high to today's high
            df['Pivot'] = df['High'].rolling(20).max().shift(1)

            # Check last N days
            recent = df.iloc[-lookback_days:].copy()

            # Find crossover: Close > Pivot AND Previous Close < Previous Pivot
            # Or simply Close > Pivot
            breakouts = recent[recent['Close'] > recent['Pivot']]

            if breakouts.empty:
                return None, None

            # Get the FIRST date in the window where it broke out
            first_breakout = breakouts.index[0]
            days_since = (df.index[-1] - first_breakout).days

            return first_breakout.strftime('%Y-%m-%d'), days_since
        except:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            if df.empty or len(df) < 252: return None

            # Columns Handling
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

            # 52 Week Stats
            high_52 = high_col.rolling(252).max().iloc[-1]
            low_52 = low_col.rolling(252).min().iloc[-1]
            dist_to_high = (high_52 - curr_price) / high_52

            # --- STRATEGY LOGIC ---
            isa_signal = False
            options_signal = False
            setup_name = ""
            breakout_info = ""

            # === ISA STRATEGY: FRESH BREAKOUTS ONLY ===
            # 1. Trend Alignment
            trend_aligned = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            # 2. Breakout Detection
            b_date, days_ago = self._find_breakout(df, lookback_days=10) # Only look back 10 days

            # 3. Volume Confirmation (Demand)
            # Check if volume on breakout date was high?
            # For simplicity/speed, we check if current volume or avg volume is healthy relative to recent history
            vol_spike = vol_col.iloc[-1] > (avg_vol_20 * 1.0) # At least average volume

            if trend_aligned and b_date and days_ago <= 12 and vol_spike:
                # FILTER: Don't chase extensions.
                # If price is > 15% above the 50 SMA, it's extended.
                extension = (curr_price - sma_50) / sma_50

                if extension < 0.20: # Allow up to 20% extension for strong momentum
                    isa_signal = True
                    setup_name = f"Breakout ({days_ago}d ago)"
                    breakout_info = b_date

            # === OPTIONS STRATEGY: MEAN REVERSION ===
            atr_pct = (atr / curr_price) * 100
            if is_us and (curr_price > sma_200):
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback"

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
                # We pack the Date into Metrics to show it on UI without code changes
                "Metrics": f"BO:{breakout_info} RSI:{rsi:.0f}" if isa_signal else f"RSI:{rsi:.0f} ATR:{atr_pct:.1f}%",
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2)
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
                "Regime": "RED"
            }]

        logger.info(f"Scanning {len(self.all_tickers)} tickers...")

        chunk_size = 50
        results = []

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    res = self._process_stock(chunk[0], data)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            df = data[ticker].dropna()
                            res = self._process_stock(ticker, df)
                            if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        results.sort(key=lambda x: x['Type'] != "ISA_BUY")
        return results
