import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
from datetime import datetime, timedelta

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterScreener")

# --- CONFIGURATION (STRICT MODE) ---
ISA_ACCOUNT_SIZE = 100000.0  # GBP
OPTIONS_ACCOUNT_SIZE = 9500.0 # USD
RISK_PER_TRADE_PCT = 0.01    # Risk 1%
MARKET_TICKERS = ["SPY", "^VIX"]

# LIQUIDITY GATES
LIQUIDITY_MIN_VOL_USD = 1_500_000 # Strict: $1.5M Volume
LIQUIDITY_MIN_VOL_GBP = 300_000   # Strict: £300k Volume

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.all_tickers = self.tickers_us + self.tickers_uk
        self.market_regime = "NEUTRAL"
        self.vix_level = 15.0
        self.regime_color = "YELLOW"

    def _fetch_market_regime(self):
        """
        Determines if the market is safe to trade.
        """
        try:
            # Download 2 years to ensure valid 200 SMA
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)

            # Handle MultiIndex safely
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            # SPY Analysis
            spy_series = closes['SPY'].dropna()
            if spy_series.empty:
                raise ValueError("No SPY data")

            spy_curr = spy_series.iloc[-1]
            spy_sma = spy_series.rolling(200).mean().iloc[-1]

            # VIX Analysis
            vix_series = closes['^VIX'].dropna()
            self.vix_level = vix_series.iloc[-1] if not vix_series.empty else 20.0

            # Fallback if SMA is NaN (data starved)
            if pd.isna(spy_sma): spy_sma = spy_curr * 0.9

            # LOGIC
            if spy_curr > spy_sma and self.vix_level < 20:
                self.market_regime = "BULLISH"
                self.regime_color = "GREEN"
            elif spy_curr < spy_sma and self.vix_level > 25:
                self.market_regime = "BEARISH"
                self.regime_color = "RED"
            else:
                self.market_regime = "CAUTIOUS"
                self.regime_color = "YELLOW"

            # Panic Check
            if self.vix_level > 28:
                self.market_regime = "BEARISH"
                self.regime_color = "RED"

        except Exception as e:
            logger.error(f"Regime Check Failed: {e}")
            self.market_regime = "CAUTIOUS"
            self.regime_color = "YELLOW"

    def _find_breakout_date(self, df, lookback=20):
        """
        Detects the exact date price crossed the N-day high.
        Returns: (date_str, days_since_breakout) or (None, None)
        """
        try:
            # 1. Define 'Pivot': The highest High of the PREVIOUS 20 days
            # We shift(1) because today's high doesn't count as the 'previous' range
            df['Pivot'] = df['High'].rolling(window=20).max().shift(1)

            # 2. Identify Cross: Close > Pivot
            # Only look at the last 'lookback' days to find recent moves
            recent = df.iloc[-lookback:].copy()
            breakout_mask = recent['Close'] > recent['Pivot']

            if not breakout_mask.any():
                return None, None

            # 3. Get the FIRST date in this window where breakout occurred
            # This handles stocks that broke out 3 days ago and are still running
            breakout_dates = recent[breakout_mask].index
            first_bo_date = breakout_dates[0]

            days_since = (df.index[-1] - first_bo_date).days
            return first_bo_date.strftime('%Y-%m-%d'), days_since

        except Exception:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            # 1. Data Hygiene
            if df.empty or len(df) < 252: return None

            # Flatten MultiIndex if necessary (YFinance quirks)
            if isinstance(df.columns, pd.MultiIndex):
                if 'Close' in df.columns:
                    c = df['Close']
                    h = df['High']
                    l = df['Low']
                    v = df['Volume']
                else: return None
            else:
                c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']

            # 2. Liquidity Gate
            curr_price = float(c.iloc[-1])
            avg_vol = float(v.rolling(20).mean().iloc[-1])

            is_uk = ticker.endswith(".L")
            is_us = not is_uk

            if is_us and avg_vol < LIQUIDITY_MIN_VOL_USD: return None
            if is_uk and avg_vol < LIQUIDITY_MIN_VOL_GBP: return None

            # 3. Indicators
            sma_50 = c.rolling(50).mean().iloc[-1]
            sma_150 = c.rolling(150).mean().iloc[-1]
            sma_200 = c.rolling(200).mean().iloc[-1]
            atr = ta.atr(h, l, c, length=14).iloc[-1]
            rsi = ta.rsi(c, length=14).iloc[-1]

            # --- STRATEGY LOGIC ---
            isa_signal = False
            options_signal = False
            setup_name = ""
            breakout_date_str = ""

            # === STRATEGY A: ISA FRESH BREAKOUT (Minervini Style) ===
            # Rule 1: Trend Alignment (Price > 50 > 150 > 200)
            trend_ok = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            if trend_ok:
                # Rule 2: Fresh Breakout Detection
                # We check if it broke out in the last 15 days
                bo_date, days_since = self._find_breakout_date(df, lookback=15)

                if bo_date and days_since <= 12:
                    # Rule 3: Extension Check
                    # Don't buy if it's already > 20% above the 50 SMA (too extended)
                    extension = (curr_price - sma_50) / sma_50
                    if extension < 0.20:
                        isa_signal = True
                        breakout_date_str = bo_date
                        setup_name = f"Breakout ({days_since}d ago)"

            # === STRATEGY B: OPTIONS BULL PUT (Thorp/Mean Reversion) ===
            # Rule: Uptrending US Stock + Oversold RSI + High Volatility
            atr_pct = (atr / curr_price) * 100
            if is_us and (curr_price > sma_200):
                # Strict: RSI must be < 45 (Real Pullback)
                # Strict: ATR% > 2.5 (Good Premium)
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback (Put Sell)"

            if not isa_signal and not options_signal:
                return None

            # 4. Sizing
            stop_loss = curr_price - (3 * atr)
            risk_per_share = curr_price - stop_loss
            shares = 0

            if isa_signal and risk_per_share > 0:
                fx = 0.79 if is_us else 1.0
                shares = int((ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT / fx) / risk_per_share)
                # Cap at 20% of Portfolio
                max_shares = int((ISA_ACCOUNT_SIZE * 0.20) / (curr_price * fx))
                shares = min(shares, max_shares)

            # 5. Formatting for Frontend
            metrics_str = ""
            if isa_signal:
                metrics_str = f"BO:{breakout_date_str} RSI:{rsi:.0f}"
            else:
                metrics_str = f"RSI:{rsi:.0f} ATR:{atr_pct:.1f}%"

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": "ISA_BUY" if isa_signal else "OPT_SELL",
                "Setup": setup_name,
                "Action": f"Buy {shares}" if isa_signal else "Sell Put Spread",
                "Stop Loss": round(stop_loss, 2),
                "Metrics": metrics_str,
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2)
            }

        except Exception:
            return None

    def run(self):
        """
        Main execution method.
        """
        self._fetch_market_regime()

        # Hard Stop if Market is Crashing
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

        # Batch Processing
        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                # auto_adjust=True is critical for correct breakout levels
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    res = self._process_stock(chunk[0], data)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            # Safe slice
                            df = data[ticker].dropna(how='all')
                            res = self._process_stock(ticker, df)
                            if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # Sort: ISA Buys first, then by Volatility
        results.sort(key=lambda x: (x['Type'] != "ISA_BUY", -x.get('volatility_pct', 0)))

        return results
