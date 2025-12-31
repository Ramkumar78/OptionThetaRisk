import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
from datetime import datetime, timedelta

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterScreener")

# --- CONFIGURATION (THE COUNCIL'S STANDARDS) ---
ISA_ACCOUNT_SIZE = 100000.0  # GBP
OPTIONS_ACCOUNT_SIZE = 9500.0 # USD
RISK_PER_TRADE_PCT = 0.01    # Risk 1% of account
MARKET_TICKERS = ["SPY", "^VIX"]

# LIQUIDITY GATES (Hardened)
LIQUIDITY_MIN_VOL_USD = 1_500_000 # Minimum $1.5M daily volume
LIQUIDITY_MIN_VOL_GBP = 500_000   # Minimum £500k daily volume

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
        The Soros Gate: Market Health Check.
        """
        try:
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)

            # Handle MultiIndex
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            # SPY Check (Trend)
            spy = closes['SPY'].dropna()
            spy_curr = spy.iloc[-1]
            spy_sma = spy.rolling(200).mean().iloc[-1]

            # VIX Check (Fear)
            vix = closes['^VIX'].dropna()
            self.vix_level = vix.iloc[-1] if not vix.empty else 20.0

            if pd.isna(spy_sma): spy_sma = spy_curr * 0.9 # Fallback

            # STRICT REGIME LOGIC
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

        except Exception as e:
            logger.error(f"Regime check failed: {e}")
            self.market_regime = "CAUTIOUS"

    def _find_fresh_breakout(self, df):
        """
        Minervini Logic: Did price cross a 20-day High recently?
        Returns: (date_str, days_since, breakout_price)
        """
        try:
            # 1. Define Pivot: High of the *previous* 20 days
            # shift(1) ensures we don't compare today to today
            df['Pivot'] = df['High'].rolling(20).max().shift(1)

            # 2. Look closely at last 12 days only
            # We don't care if it broke out 2 months ago.
            recent = df.iloc[-12:].copy()

            # 3. Find the specific day it crossed
            # Condition: Close > Pivot
            breakout_mask = recent['Close'] > recent['Pivot']

            if not breakout_mask.any():
                return None, None, None

            # Get the first date in this window
            breakout_dates = recent[breakout_mask].index
            first_bo_date = breakout_dates[0]

            # 4. Volume Confirmation on that specific day
            # Was volume > 120% of average?
            bo_vol = recent.loc[first_bo_date, 'Volume']
            avg_vol = df.loc[:first_bo_date, 'Volume'].tail(20).mean()

            # STRICT FILTER: If volume wasn't high, it's a fakeout.
            if bo_vol < (avg_vol * 1.2):
                return None, None, None

            days_since = (df.index[-1] - first_bo_date).days
            bo_price = recent.loc[first_bo_date, 'Close']

            return first_bo_date.strftime('%Y-%m-%d'), days_since, bo_price

        except Exception:
            return None, None, None

    def _process_stock(self, ticker, df):
        try:
            # 1. Data Hygiene
            if df.empty or len(df) < 252: return None

            # Flatten YFinance MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                if 'Close' in df.columns:
                    c = df['Close']
                    h = df['High']
                    l = df['Low']
                    v = df['Volume']
                else: return None
            else:
                c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']

            # 2. Liquidity Gate (Griffin Rule)
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

            # --- DECISION LOGIC ---
            isa_signal = False
            options_signal = False
            setup_name = ""
            metrics_display = ""

            # === ISA STRATEGY: FRESH BREAKOUTS (Momentum) ===
            # Trend Check
            trend_ok = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            if trend_ok:
                # Event Check: Did it breakout in the last 12 days?
                bo_date, days_ago, bo_level = self._find_fresh_breakout(df)

                if bo_date:
                    # Extension Check: Don't buy if > 15% above 50 SMA
                    extension = (curr_price - sma_50) / sma_50
                    if extension < 0.15:
                        isa_signal = True
                        setup_name = f"Fresh Breakout ({days_ago}d)"
                        metrics_display = f"BO Date: {bo_date}"

            # === OPTIONS STRATEGY: MEAN REVERSION (Contrarian) ===
            # Uptrending US stock that is oversold with high volatility
            atr_pct = (atr / curr_price) * 100

            if is_us and (curr_price > sma_200):
                # Strict: RSI < 45 (Real Pullback)
                # Strict: ATR% > 2.5 (High Premium)
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback (Put Sell)"
                    metrics_display = f"ATR:{atr_pct:.1f}% RSI:{rsi:.0f}"

            if not isa_signal and not options_signal:
                return None

            # 4. Risk Management (The Kelly/Thorp Logic)
            stop_loss = curr_price - (3 * atr) # Volatility-based stop

            # Refine Stop for Breakouts: Use the Low of the breakout pivot
            if isa_signal:
                stop_loss = curr_price - (2.5 * atr)

            risk_per_share = curr_price - stop_loss
            shares = 0

            if isa_signal and risk_per_share > 0:
                fx = 0.79 if is_us else 1.0 # FX buffer
                # Account Sizing: Fixed Risk Amount
                risk_amt = ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT # £1,000 Risk
                shares = int((risk_amt / fx) / risk_per_share)

                # Portfolio Constraint: Max 20% position
                max_pos_shares = int((ISA_ACCOUNT_SIZE * 0.20) / (curr_price * fx))
                shares = min(shares, max_pos_shares)

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": "ISA_BUY" if isa_signal else "OPT_SELL",
                "Setup": setup_name,
                "Action": f"Buy {shares}" if isa_signal else "Sell Put Spread",
                "Stop Loss": round(stop_loss, 2),
                "Metrics": metrics_display,
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2)
            }

        except Exception:
            return None

    def run(self):
        """
        Execute scan.
        """
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
                # auto_adjust=True is VITAL for correct breakout levels
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    res = self._process_stock(chunk[0], data)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            # Safe slice for MultiIndex
                            df = data[ticker].dropna(how='all')
                            res = self._process_stock(ticker, df)
                            if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # Sort Priority: ISA Buys first, then by Volatility
        results.sort(key=lambda x: (x['Type'] != "ISA_BUY", -x.get('volatility_pct', 0)))

        return results
