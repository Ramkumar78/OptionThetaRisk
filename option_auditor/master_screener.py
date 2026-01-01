import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
from datetime import datetime

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterScreener")

# --- CONFIGURATION ---
ISA_ACCOUNT_SIZE = 100000.0  # GBP
RISK_PER_TRADE_PCT = 0.01    # Risk 1%
MARKET_TICKERS = ["SPY", "^VIX"]

# LIQUIDITY GATES
LIQUIDITY_MIN_VOL_USD = 2_000_000
LIQUIDITY_MIN_VOL_GBP = 250_000   # Lowered slightly for UK Midcaps
LIQUIDITY_MIN_TURNOVER_INR = 100_000_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk, tickers_india=None):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.tickers_india = list(set(tickers_india)) if tickers_india else []
        self.all_tickers = self.tickers_us + self.tickers_uk + self.tickers_india
        self.market_regime = "NEUTRAL"
        self.regime_color = "YELLOW" # Default initialization
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

    def _find_fresh_breakout(self, df):
        """
        Refined Logic:
        1. Calculate 20-Day High (Resistance).
        2. Identify the FIRST day in the last 10 days where Price > Resistance.
        3. Ensure that BEFORE that day, price was BELOW Resistance.
        This filters out stocks that have been trending above the high for weeks.
        """
        try:
            # Shift 1 to get yesterday's 20-day high (the resistance line)
            df['Pivot'] = df['High'].rolling(20).max().shift(1)

            # Look at last 10 days only
            recent = df.iloc[-10:].copy()

            # Find days where we are ABOVE the pivot
            above_pivot = recent[recent['Close'] > recent['Pivot']]

            if above_pivot.empty:
                return None, None # No breakout

            # Get the date of the FIRST breakout in this window
            first_breakout_date = above_pivot.index[0]

            # Check if this is truly fresh:
            # We check the 3 days PRIOR to the first breakout.
            # If price was above pivot then, it's not a fresh base breakout, it's a choppy mess.
            # (Simplified: Just ensure first_breakout_date is within last 5 days)
            days_since = (df.index[-1] - first_breakout_date).days

            if days_since > 5:
                return None, None # Stale trend, not a fresh breakout

            return first_breakout_date.strftime('%Y-%m-%d'), days_since
        except:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            if df.empty or len(df) < 252: return None

            if isinstance(df.columns, pd.MultiIndex):
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']
                vol_col = df['Volume']
            else:
                # Handle flattened structure with Ticker as column prefix or just columns
                # However, yf.download group_by='ticker' usually results in MultiIndex or single DataFrame per ticker
                # If we get here, it assumes simple columns
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']
                vol_col = df['Volume']

            curr_price = float(close_col.iloc[-1])
            avg_vol_20 = float(vol_col.rolling(20).mean().iloc[-1])

            # --- REGION IDENTIFICATION ---
            # Explicit check against lists passed in init for safety
            is_uk = ticker in self.tickers_uk or ticker.endswith(".L")
            is_india = ticker in self.tickers_india or ticker.endswith(".NS")
            is_us = not (is_uk or is_india) # Default to US if not others

            # --- LIQUIDITY GATES ---
            if is_us and avg_vol_20 < LIQUIDITY_MIN_VOL_USD: return None
            if is_uk and avg_vol_20 < LIQUIDITY_MIN_VOL_GBP: return None
            if is_india:
                turnover = curr_price * avg_vol_20
                if turnover < LIQUIDITY_MIN_TURNOVER_INR: return None

            # --- INDICATORS ---
            sma_50 = close_col.rolling(50).mean().iloc[-1]
            sma_150 = close_col.rolling(150).mean().iloc[-1]
            sma_200 = close_col.rolling(200).mean().iloc[-1]
            atr = ta.atr(high_col, low_col, close_col, length=14).iloc[-1]
            rsi = ta.rsi(close_col, length=14).iloc[-1]

            # --- STRATEGY LOGIC ---
            isa_signal = False
            options_signal = False
            setup_name = ""
            breakout_info = ""
            days_ago_metric = 999

            # === ISA STRATEGY (Global Breakouts) ===
            trend_aligned = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            # Use NEW Fresh Breakout Logic
            b_date, days_ago = self._find_fresh_breakout(df)

            if trend_aligned and b_date:
                # Extension Check: Don't buy if > 25% above 50 SMA (Parabolic)
                extension = (curr_price - sma_50) / sma_50
                if extension < 0.25:
                    isa_signal = True
                    days_ago_metric = days_ago
                    setup_name = f"🔥 FRESH BREAKOUT ({days_ago}d)"
                    breakout_info = b_date

            # === OPTIONS STRATEGY (US Only) ===
            atr_pct = (atr / curr_price) * 100
            # Only consider options if NOT an ISA buy (Prioritise Stock Ownership)
            if is_us and not isa_signal and (curr_price > sma_200):
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback"
                    days_ago_metric = 100

            if not isa_signal and not options_signal:
                return None

            # --- POSITION SIZING & VERDICT ---
            stop_loss = curr_price - (3 * atr)
            risk_per_share = curr_price - stop_loss
            shares = 0
            type_label = ""
            action_text = ""

            # FIX: Priority Logic - ISA BUY takes precedence
            if isa_signal:
                if is_uk: type_label = "🇬🇧 ISA BUY"
                elif is_india: type_label = "🇮🇳 BUY (Non-ISA)"
                else: type_label = "🇺🇸 ISA BUY"

                # Sizing
                risk_amt_gbp = ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT
                fx_rate = 1.0
                if is_us: fx_rate = 0.79
                if is_india: fx_rate = 0.0093

                if risk_per_share > 0:
                    shares = int((risk_amt_gbp / fx_rate) / risk_per_share)
                    max_shares = int((ISA_ACCOUNT_SIZE / fx_rate * 0.20) / curr_price)
                    shares = min(shares, max_shares)

                action_text = f"Buy {shares} Shares"

            elif options_signal:
                type_label = "🇺🇸 OPT SELL"
                # Options specific data
                short_strike = round(curr_price - (2*atr), 1)
                long_strike = round(short_strike - 5, 1)
                action_text = f"Sell Put {short_strike}/{long_strike}"

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": type_label,
                "Setup": setup_name,
                "Action": action_text, # Unified Action Column
                "Stop Loss": round(stop_loss, 2),
                "Metrics": f"BO:{breakout_info}" if isa_signal else f"RSI:{rsi:.0f} ATR:{atr_pct:.1f}%",
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2),
                "sort_key": days_ago_metric
            }

        except Exception as e:
            # print(f"Error processing {ticker}: {e}", flush=True)
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
                            # Handle YF MultiIndex mess
                            # If columns are MultiIndex, the first level is Ticker
                            if isinstance(data.columns, pd.MultiIndex):
                                if ticker in data.columns.levels[0]:
                                    df = data[ticker].dropna(how='all')
                                    # Ensure we have required columns. yfinance might return 'Adj Close' instead of 'Close' if auto_adjust=False,
                                    # but we used auto_adjust=True so we get 'Close', 'High', 'Low', 'Volume'.
                                    res = self._process_stock(ticker, df)
                                    if res: results.append(res)
                            else:
                                # Sometimes single ticker download with group_by='ticker' might still return flat if yfinance version varies?
                                # But usually it returns MultiIndex if group_by='ticker' is set even for one?
                                # Wait, the code above handles len(chunk) == 1 separately.
                                # For len(chunk) > 1, it should be MultiIndex.
                                pass
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # Sort: Fresh Breakouts (0d) -> Older (5d) -> Options
        results.sort(key=lambda x: (x['Type'] == "🇺🇸 OPT SELL", x['sort_key']))
        return results
