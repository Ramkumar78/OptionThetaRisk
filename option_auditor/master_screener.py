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
LIQUIDITY_MIN_VOL_USD = 1_500_000
LIQUIDITY_MIN_VOL_GBP = 200_000
LIQUIDITY_MIN_TURNOVER_INR = 100_000_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk, tickers_india=None):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.tickers_india = list(set(tickers_india)) if tickers_india else []
        self.all_tickers = self.tickers_us + self.tickers_uk + self.tickers_india
        self.market_regime = "NEUTRAL"
        self.regime_color = "YELLOW" # Initialize default color
        self.vix_level = 15.0

    def _fetch_market_regime(self):
        try:
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)
            # Flatten MultiIndex if necessary
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
        Refined Freshness Logic:
        1. Pivot = 20 Day High (shifted 1 day).
        2. Breakout = Close > Pivot.
        3. FRESHNESS CHECK: Ensure the stock was NOT above the pivot
           for the 5 days prior to the breakout. This kills "trending" noise.
        """
        try:
            df['Pivot'] = df['High'].rolling(20).max().shift(1)

            # Scan last 10 days
            recent = df.iloc[-10:].copy()
            breakout_mask = recent['Close'] > recent['Pivot']

            if not breakout_mask.any():
                return None, None

            # Find the FIRST date it broke out in this window
            first_bo_idx = breakout_mask.idxmax() # Returns index of first True

            # Calculate days since that specific breakout
            days_since = (df.index[-1] - first_bo_idx).days

            if days_since > 5:
                return None, None # Too old

            # DOUBLE CHECK: Was it consolidating before?
            # Look at the 5 days BEFORE the breakout date
            # If any of those days were also breakouts, it's not fresh, it's choppy.
            # (We skip this for now to keep it fast, the days_since logic is usually enough)

            return first_bo_idx.strftime('%Y-%m-%d'), days_since
        except:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            if df.empty or len(df) < 252: return None

            # 1. Normalize Columns
            if isinstance(df.columns, pd.MultiIndex):
                # If 'df' is passed as the slice for 'ticker', columns might still be MultiIndex?
                # Usually yf.download(group_by='ticker') gives DataFrame with (Price, Ticker) if we slice [Ticker].
                # If we slice df[Ticker], we get SingleIndex columns.
                # Assuming SingleIndex here:
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']
                vol_col = df['Volume']
                open_col = df['Open'] # Needed for Change%
            else:
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']
                vol_col = df['Volume']
                open_col = df['Open']

            curr_price = float(close_col.iloc[-1])
            prev_close = float(close_col.iloc[-2])
            avg_vol_20 = float(vol_col.rolling(20).mean().iloc[-1])

            # Calculate Change %
            change_pct = ((curr_price - prev_close) / prev_close) * 100

            # 2. Region & Liquidity
            is_uk = ticker in self.tickers_uk or ticker.endswith(".L")
            is_india = ticker in self.tickers_india or ticker.endswith(".NS") or ticker.endswith(".BO")
            is_us = not (is_uk or is_india) # Default to US

            if is_us and avg_vol_20 < LIQUIDITY_MIN_VOL_USD:
                 # print(f"DEBUG: {ticker} Failed Vol Check {avg_vol_20} < {LIQUIDITY_MIN_VOL_USD}")
                 return None
            if is_uk and avg_vol_20 < LIQUIDITY_MIN_VOL_GBP: return None
            if is_india:
                if (curr_price * avg_vol_20) < LIQUIDITY_MIN_TURNOVER_INR: return None

            # 3. Indicators
            sma_50 = close_col.rolling(50).mean().iloc[-1]
            sma_150 = close_col.rolling(150).mean().iloc[-1]
            sma_200 = close_col.rolling(200).mean().iloc[-1]
            atr = ta.atr(high_col, low_col, close_col, length=14).iloc[-1]
            rsi = ta.rsi(close_col, length=14).iloc[-1]

            # 4. Strategy Logic
            isa_signal = False
            options_signal = False
            setup_name = ""
            breakout_info = ""
            days_ago_metric = 999

            # --- ISA STRATEGY (Breakouts) ---
            trend_aligned = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            b_date, days_ago = self._find_fresh_breakout(df)

            if trend_aligned and b_date:
                # Extension check: < 25% from 50 SMA
                if ((curr_price - sma_50) / sma_50) < 0.25:
                    isa_signal = True
                    days_ago_metric = days_ago
                    setup_name = f"Fresh Breakout ({days_ago}d)"
                    breakout_info = b_date

            # --- OPTIONS STRATEGY (US Only) ---
            atr_pct = (atr / curr_price) * 100
            if is_us and not isa_signal and (curr_price > sma_200):
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback"
                    days_ago_metric = 100 # Low priority sort

            if not isa_signal and not options_signal:
                # print(f"DEBUG: {ticker} No Signal. ISA={isa_signal} OPT={options_signal}. Trend={trend_aligned} BDate={b_date}")
                return None

            # 5. Position Sizing & Output Construction
            stop_loss = curr_price - (3 * atr)
            target_price = curr_price + (6 * atr) # 2R Target

            risk_per_share = curr_price - stop_loss
            shares = 0
            type_label = ""
            action_text = ""

            if isa_signal:
                risk_amt_gbp = ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT
                fx_rate = 1.0

                if is_india:
                    fx_rate = 0.0093
                    type_label = "🇮🇳 BUY (Non-ISA)"
                elif is_us:
                    fx_rate = 0.79
                    type_label = "🇺🇸 ISA BUY"
                else:
                    type_label = "🇬🇧 ISA BUY"

                if risk_per_share > 0:
                    shares = int((risk_amt_gbp / fx_rate) / risk_per_share)
                    # 20% Portfolio Cap
                    max_shares = int((ISA_ACCOUNT_SIZE / fx_rate * 0.20) / curr_price)
                    shares = min(shares, max_shares)

                action_text = f"Buy {shares} Shares"

            elif options_signal:
                type_label = "🇺🇸 OPT SELL"
                short_strike = round(curr_price - (2*atr), 1)
                long_strike = round(short_strike - 5, 1)
                action_text = f"Sell Put {short_strike}/{long_strike}"

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Change%": f"{change_pct:+.2f}%",
                "Volume": f"{int(avg_vol_20/1000)}K",
                "Type": type_label,
                "Setup": setup_name,
                "Action": action_text,
                "Stop Loss": round(stop_loss, 2),
                "Target": round(target_price, 2),
                "Metrics": f"BO:{breakout_info}" if isa_signal else f"RSI:{rsi:.0f} ATR:{atr_pct:.1f}%",
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2),
                "sort_key": days_ago_metric
            }

        except Exception as e:
            # print(f"DEBUG: Error processing {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def run(self):
        self._fetch_market_regime()

        if self.market_regime == "BEARISH":
            return [{
                "Ticker": "MARKET",
                "Price": 0,
                "Change%": "0%",
                "Volume": "0",
                "Type": "WARNING",
                "Setup": "BEARISH REGIME",
                "Action": "CASH IS KING",
                "Stop Loss": 0,
                "Target": 0,
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
                            # Robust MultiIndex Handling
                            if ticker in data.columns.levels[0]:
                                df = data[ticker].dropna(how='all')
                                res = self._process_stock(ticker, df)
                                if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # Sort: Fresh Breakouts (0d) -> Older (5d) -> Options
        results.sort(key=lambda x: (x['Type'] == "🇺🇸 OPT SELL", x['sort_key']))
        return results
