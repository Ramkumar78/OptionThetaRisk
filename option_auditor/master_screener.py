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
LIQUIDITY_MIN_VOL_GBP = 500_000
# 100 Million INR Turnover (~$1.2M USD) - ensuring liquidity
LIQUIDITY_MIN_TURNOVER_INR = 100_000_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk, tickers_india=None):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.tickers_india = list(set(tickers_india)) if tickers_india else []

        self.all_tickers = self.tickers_us + self.tickers_uk + self.tickers_india
        self.market_regime = "NEUTRAL"
        self.vix_level = 15.0

    def _fetch_market_regime(self):
        try:
            data = yf.download(MARKET_TICKERS, period="2y", progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                # Handle MultiIndex by checking for 'Close' or just extracting SPY/VIX directly
                try:
                    closes = data['Close']
                except KeyError:
                    closes = pd.DataFrame()
                    for t in MARKET_TICKERS:
                        if t in data.columns.levels[0]:
                             closes[t] = data[t]['Close']
            else:
                closes = data

            # Ensure we have data
            if 'SPY' not in closes.columns or '^VIX' not in closes.columns:
                self.market_regime = "CAUTIOUS"
                self.regime_color = "YELLOW"
                return

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

    def _find_breakout(self, df, lookback_days=25):
        try:
            df['Pivot'] = df['High'].rolling(20).max().shift(1)
            recent = df.iloc[-lookback_days:].copy()
            breakouts = recent[recent['Close'] > recent['Pivot']]

            if breakouts.empty:
                return None, None

            first_breakout = breakouts.index[0]
            days_since = (df.index[-1] - first_breakout).days
            return first_breakout.strftime('%Y-%m-%d'), days_since
        except:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            if df.empty or len(df) < 252: return None

            # Column Normalization
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

            # --- REGION IDENTIFICATION ---
            is_uk = ticker.endswith(".L")
            is_india = ticker.endswith(".NS") or ticker.endswith(".BO")
            is_us = not (is_uk or is_india)

            # --- LIQUIDITY GATES ---
            if is_us and avg_vol_20 < LIQUIDITY_MIN_VOL_USD: return None
            if is_uk and avg_vol_20 < LIQUIDITY_MIN_VOL_GBP: return None

            if is_india:
                # India Turnover Check (Price * Volume)
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

            # === GLOBAL BREAKOUTS (US, UK, INDIA) ===
            trend_aligned = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            b_date, days_ago = self._find_breakout(df, lookback_days=20)

            if trend_aligned and b_date and days_ago <= 15:
                extension = (curr_price - sma_50) / sma_50
                if extension < 0.25:
                    isa_signal = True
                    days_ago_metric = days_ago
                    if days_ago <= 3:
                        setup_name = f"🔥 FRESH BREAKOUT ({days_ago}d)"
                    else:
                        setup_name = f"Developing Trend ({days_ago}d)"
                    breakout_info = b_date

            # === OPTIONS STRATEGY (US ONLY) ===
            atr_pct = (atr / curr_price) * 100
            if is_us and (curr_price > sma_200):
                if rsi < 45 and atr_pct > 2.5:
                    options_signal = True
                    setup_name = "Vol Pullback"
                    days_ago_metric = 100

            if not isa_signal and not options_signal:
                return None

            # --- POSITION SIZING & LABELING ---
            stop_loss = curr_price - (3 * atr)
            risk_per_share = curr_price - stop_loss
            shares = 0
            type_label = ""

            if risk_per_share > 0 and isa_signal:
                risk_amt_gbp = ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT # £1000 Risk

                if is_india:
                    # INDIA (Non-ISA Logic)
                    # We assume £1000 risk EQUIVALENT, but no ISA FX logic
                    # 1 INR = ~0.0093 GBP.
                    # Risk in INR = £1000 / 0.0093
                    fx_rate = 0.0093
                    risk_amt_inr = risk_amt_gbp / fx_rate
                    shares = int(risk_amt_inr / risk_per_share)
                    type_label = "🇮🇳 BUY (Non-ISA)"

                elif is_us:
                    # US ISA Logic (FX Impact)
                    fx_rate = 0.79
                    shares = int((risk_amt_gbp / fx_rate) / risk_per_share)
                    type_label = "🇺🇸 ISA BUY"

                elif is_uk:
                    # UK ISA Logic (Native)
                    shares = int(risk_amt_gbp / risk_per_share)
                    type_label = "🇬🇧 ISA BUY"

                # Cap max position size (20% of Portfolio Value)
                # Convert Portfolio to Local Currency first
                if is_india:
                    portfolio_val_local = ISA_ACCOUNT_SIZE / 0.0093
                elif is_us:
                    portfolio_val_local = ISA_ACCOUNT_SIZE / 0.79
                else:
                    portfolio_val_local = ISA_ACCOUNT_SIZE

                max_shares = int((portfolio_val_local * 0.20) / curr_price)
                shares = min(shares, max_shares)

            if options_signal:
                type_label = "🇺🇸 OPT SELL"

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": type_label,
                "Setup": setup_name,
                "Action": f"Buy {shares}" if isa_signal else "Sell Put Spread",
                "Stop Loss": round(stop_loss, 2),
                "Metrics": f"BO:{breakout_info}" if isa_signal else f"RSI:{rsi:.0f} ATR:{atr_pct:.1f}%",
                "Regime": self.regime_color,
                "volatility_pct": round(atr_pct, 2),
                "sort_key": days_ago_metric
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

        chunk_size = 50
        results = []

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    t = chunk[0]
                    # yf might return just the DataFrame or nested
                    # If columns are MultiIndex and t is in level 0, extract it.
                    if isinstance(data.columns, pd.MultiIndex) and t in data.columns:
                        df = data[t].dropna()
                    else:
                        df = data.dropna()

                    res = self._process_stock(t, df)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            # If ticker not in columns, data missing
                            if ticker not in data.columns.levels[0]:
                                continue
                            df = data[ticker].dropna()
                            res = self._process_stock(ticker, df)
                            if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # Sort: Fresh Breakouts (ISA/INDIA) -> Older Breakouts -> Options
        results.sort(key=lambda x: (x['Type'] == "🇺🇸 OPT SELL", x['sort_key']))
        return results
