import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterScreener")

# --- CONFIGURATION ---
ISA_ACCOUNT_SIZE = 100000.0  # GBP
OPTIONS_ACCOUNT_SIZE = 9500.0 # USD
RISK_PER_TRADE_PCT = 0.01    # Risk 1%
MARKET_TICKERS = ["SPY", "^VIX"]
LIQUIDITY_MIN_VOL_USD = 1_000_000
LIQUIDITY_MIN_VOL_GBP = 200_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.all_tickers = self.tickers_us + self.tickers_uk
        self.market_regime = "NEUTRAL"
        self.vix_level = 15.0

    def _fetch_market_regime(self):
        """
        Determines market health.
        Fix: Uses '2y' data to guarantee valid 200 SMA calculation.
        """
        try:
            # FETCH 2 YEARS (Crucial fix for 200 SMA)
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)

            # Extract Close prices safely
            if 'Close' in data.columns and isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            # SPY Check
            spy_series = closes['SPY'].dropna()
            spy_curr = spy_series.iloc[-1]
            spy_sma = spy_series.rolling(200).mean().iloc[-1]

            # VIX Check
            vix_series = closes['^VIX'].dropna()
            self.vix_level = vix_series.iloc[-1]

            # FAIL-SAFE: If SMA is NaN, assume Bullish if Price > 50 SMA as backup
            if pd.isna(spy_sma):
                spy_sma = spy_series.rolling(50).mean().iloc[-1]

            # LOGIC
            if spy_curr > spy_sma and self.vix_level < 25:
                self.market_regime = "BULLISH"
                regime_color = "GREEN"
            elif spy_curr < spy_sma and self.vix_level > 25:
                self.market_regime = "BEARISH"
                regime_color = "RED"
            else:
                self.market_regime = "CAUTIOUS"
                regime_color = "YELLOW"

            # Force Bearish only if VIX is properly panic-mode
            if self.vix_level > 28:
                self.market_regime = "BEARISH"
                regime_color = "RED"

            logger.info(f"MARKET REGIME: {regime_color} (SPY: {spy_curr:.2f} vs SMA: {spy_sma:.2f} | VIX: {self.vix_level:.2f})")

        except Exception as e:
            logger.error(f"Failed to fetch market regime: {e}")
            # Fallback to allow scanning if market check fails (don't block the UI)
            self.market_regime = "CAUTIOUS"

    def _process_stock(self, ticker, df):
        try:
            # Data validation
            if df.empty or len(df) < 200: return None

            # Handle MultiIndex column issue from yfinance
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten or select the specific ticker level if needed
                # Assuming 'df' passed here is already the single ticker slice
                if 'Close' in df.columns:
                    close_col = df['Close']
                    high_col = df['High']
                    low_col = df['Low']
                    vol_col = df['Volume']
                else:
                    return None
            else:
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']
                vol_col = df['Volume']

            curr_price = float(close_col.iloc[-1])
            avg_vol_20 = float(vol_col.rolling(20).mean().iloc[-1])

            # Liquidity Filters
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

            # --- LOGIC ---
            isa_signal = False
            options_signal = False
            options_data = {}

            # 1. ISA TREND (Buying Strength)
            # Price must be above 200 SMA
            if curr_price > sma_200:
                dist_to_high = (high_52 - curr_price) / high_52
                # Valid Setup: Uptrend + Near Highs + Not Overbought
                if (curr_price > sma_150) and (dist_to_high < 0.25) and (50 <= rsi <= 75):
                    isa_signal = True

            # 2. OPTIONS SELL (Selling Fear)
            # US Only, Uptrend, Oversold Pullback
            if is_us and (curr_price > sma_200):
                if rsi < 55: # Pullback
                    atr_pct = (atr / curr_price) * 100
                    if atr_pct > 2.0: # High Volatility
                        options_signal = True
                        options_data = {
                            "short": round(curr_price - (2*atr), 1),
                            "long": round((curr_price - (2*atr)) - 5, 1)
                        }

            if not isa_signal and not options_signal:
                return None

            # Sizing Logic
            stop_loss = curr_price - (3 * atr)
            risk_per_share = curr_price - stop_loss
            shares = 0
            if risk_per_share > 0:
                fx = 0.79 if is_us else 1.0
                shares = int((ISA_ACCOUNT_SIZE * 0.01 / fx) / risk_per_share)

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": "ISA_BUY" if isa_signal else "OPT_SELL",
                "Setup": "Trend Leader" if isa_signal else "High Vol Put",
                "Action": f"Buy {shares}" if isa_signal else "Sell Put Spread",
                "Stop Loss": round(stop_loss, 2),
                "Metrics": f"RSI:{rsi:.0f} ATR:{atr:.2f}",
                "Regime": self.market_regime,
                # Extra fields for frontend sorting
                "volatility_pct": round((atr/curr_price)*100, 2)
            }

        except Exception as e:
            return None

    def run(self):
        """
        Executes the screen and RETURNS the list (Does not just print).
        """
        self._fetch_market_regime()

        # If deeply bearish, return a warning row
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
                # auto_adjust=True fixes historical price gaps
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    res = self._process_stock(chunk[0], data)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            # Access ticker level safely
                            df = data[ticker].dropna()
                            res = self._process_stock(ticker, df)
                            if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # Sort: ISA Buys first
        results.sort(key=lambda x: x['Type'] != "ISA_BUY")
        return results
