import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import logging
import os
from datetime import datetime, timedelta

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MasterScreener")

# --- CONFIGURATION (HARDENED FOR 100K GBP / 9.5K USD) ---
ISA_ACCOUNT_SIZE = 100000.0  # GBP
OPTIONS_ACCOUNT_SIZE = 9500.0 # USD
RISK_PER_TRADE_PCT = 0.0125  # 1.25% Risk (Kelly/Thorp sizing)

MARKET_TICKERS = ["SPY", "^VIX"]

# LIQUIDITY GATES - THE 100K RULE
LIQUIDITY_MIN_VOL_USD = 10_000_000 # Raised to $10M to ensure easy exit
LIQUIDITY_MIN_VOL_GBP = 500_000    # Raised to £500k to minimize spread cost
LIQUIDITY_MIN_TURNOVER_INR = 150_000_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk, tickers_india=None):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.tickers_india = list(set(tickers_india)) if tickers_india else []
        self.all_tickers = self.tickers_us + self.tickers_uk + self.tickers_india
        self.market_regime = "NEUTRAL"
        self.regime_color = "YELLOW"
        self.vix_level = 15.0

    def _fetch_market_regime(self):
        """
        Hardened Regime Check:
        Verifies Price vs Long Term (200) AND Short Term (20) averages.
        """
        try:
            data = yf.download(MARKET_TICKERS, period="1y", progress=False, auto_adjust=True)

            # Handle MultiIndex vs Flat Index
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            spy_curr = closes['SPY'].dropna().iloc[-1]
            spy_sma200 = closes['SPY'].dropna().rolling(200).mean().iloc[-1]
            spy_sma20 = closes['SPY'].dropna().rolling(20).mean().iloc[-1]
            self.vix_level = closes['^VIX'].dropna().iloc[-1]

            if pd.isna(spy_sma200): spy_sma200 = spy_curr * 0.9

            # Logic:
            # Bullish = Price > 200SMA AND Price > 20SMA AND VIX < 20
            # Caution = Price > 200SMA but VIX high OR Price < 20SMA
            if spy_curr > spy_sma200 and spy_curr > spy_sma20 and self.vix_level < 20:
                self.market_regime = "BULLISH_AGGRESSIVE"
                self.regime_color = "GREEN"
            elif spy_curr > spy_sma200 and self.vix_level < 25:
                self.market_regime = "BULLISH_CAUTIOUS"
                self.regime_color = "YELLOW"
            elif spy_curr < spy_sma200:
                self.market_regime = "BEARISH_DEFENSIVE"
                self.regime_color = "RED"

            if self.vix_level > 28:
                self.market_regime = "VOLATILITY_STORM"
                self.regime_color = "RED"

            logger.info(f"MARKET REGIME: {self.market_regime} (VIX: {self.vix_level:.2f})")

        except Exception as e:
            logger.error(f"Regime fetch failed: {e}")
            self.market_regime = "CAUTIOUS"
            self.regime_color = "YELLOW"

    def _find_fresh_breakout(self, df):
        """
        Refined Logic:
        Finds 'Stage 2' breakouts: High momentum, fresh cross of resistance.
        """
        try:
            # 20-Day High (Donchian Channel)
            df['Pivot'] = df['High'].rolling(20).max().shift(1)
            recent = df.iloc[-10:].copy()

            # Check for Breakout
            above_pivot = recent[recent['Close'] > recent['Pivot']]

            if above_pivot.empty:
                return None, None

            first_breakout_date = above_pivot.index[0]
            days_since = (df.index[-1] - first_breakout_date).days

            # Strict freshness: Must be within last 5 days
            if days_since > 5:
                return None, None

            return first_breakout_date.strftime('%Y-%m-%d'), days_since
        except:
            return None, None

    def _process_stock(self, ticker, df):
        try:
            # 1. DATA INTEGRITY CHECK
            if df.empty or len(df) < 252: return None

            # Check for stale data (Data older than 5 days is dangerous)
            last_date = df.index[-1]
            if (datetime.now() - last_date).days > 5: return None

            # Flatten columns if necessary
            if isinstance(df.columns, pd.MultiIndex):
                # Try to extract Close/High/etc assuming they are top level or second level
                # But usually _process_stock receives a clean DF from run()
                pass

            # Extract Series
            close_col = df['Close']
            high_col = df['High']
            low_col = df['Low']
            vol_col = df['Volume']

            curr_price = float(close_col.iloc[-1])
            if vol_col.iloc[-1] == 0: return None # No volume today

            avg_vol_20 = float(vol_col.rolling(20).mean().iloc[-1])

            # --- REGION IDENTIFICATION ---
            is_uk = ticker in self.tickers_uk or ticker.endswith(".L")
            is_india = ticker in self.tickers_india or ticker.endswith(".NS")
            is_us = not (is_uk or is_india)

            # --- HARDENED LIQUIDITY GATES ---
            # UK: Price often in Pence, convert to Pounds for turnover
            if is_uk:
                turnover = (curr_price / 100) * avg_vol_20
                if turnover < LIQUIDITY_MIN_VOL_GBP: return None
                if curr_price < 50: return None # No penny stocks (<50p)
            elif is_india:
                turnover = curr_price * avg_vol_20
                if turnover < LIQUIDITY_MIN_TURNOVER_INR: return None
            else: # US
                turnover = curr_price * avg_vol_20
                if avg_vol_20 < 500_000 or turnover < LIQUIDITY_MIN_VOL_USD: return None
                if curr_price < 15: return None # No penny stocks (<$15)

            # --- INDICATORS ---
            sma_50 = close_col.rolling(50).mean().iloc[-1]
            sma_150 = close_col.rolling(150).mean().iloc[-1]
            sma_200 = close_col.rolling(200).mean().iloc[-1]
            atr = ta.atr(high_col, low_col, close_col, length=14).iloc[-1]
            rsi = ta.rsi(close_col, length=14).iloc[-1]

            # 52 Week High logic (Minervini)
            high_52w = high_col.rolling(252).max().iloc[-1]
            dist_to_52w = (high_52w - curr_price) / curr_price

            # --- STRATEGY LOGIC ---
            isa_signal = False
            options_signal = False
            setup_name = ""
            action_text = ""
            sort_metric = 0

            # === ISA STRATEGY: POWER TREND ===
            # Minervini Trend Template: Price > 50 > 150 > 200
            trend_aligned = (curr_price > sma_50) and (sma_50 > sma_150) and (sma_150 > sma_200)

            # Must be within 15% of 52 Week Highs (Buying strength, not bottoms)
            near_highs = dist_to_52w < 0.15

            b_date, days_ago = self._find_fresh_breakout(df)

            if trend_aligned and near_highs and b_date:
                # Extension Check: Don't buy if > 20% above 50 SMA (Parabolic risk)
                extension = (curr_price - sma_50) / sma_50
                if extension < 0.20:
                    isa_signal = True
                    setup_name = f"🚀 POWER TREND ({days_ago}d)"
                    sort_metric = 100 - days_ago # Higher score for fresher

            # === OPTIONS STRATEGY: BULL PUT SPREAD (US Only) ===
            # Condition: Bullish Market, Stock > 200 SMA, RSI Oversold (Pullback)
            # Defined Risk: Replaces "Naked Put" with "Vertical Spread"
            atr_pct = (atr / curr_price) * 100

            if is_us and not isa_signal and "BULLISH" in self.market_regime:
                if curr_price > sma_200 and 30 < rsi < 50 and atr_pct > 2.0:
                    options_signal = True
                    setup_name = "🇺🇸 Bull Put Spread"
                    sort_metric = 50

            if not isa_signal and not options_signal:
                return None

            # --- SIZING & EXECUTION ---
            stop_loss = curr_price - (2.5 * atr) # Tightened from 3 ATR
            risk_per_share = curr_price - stop_loss
            shares = 0
            type_label = ""

            if isa_signal:
                if is_uk: type_label = "🇬🇧 ISA BUY"
                elif is_india: type_label = "🇮🇳 BUY"
                else: type_label = "🇺🇸 ISA BUY"

                # Sizing Logic
                risk_amt_gbp = ISA_ACCOUNT_SIZE * RISK_PER_TRADE_PCT
                fx_rate = 1.0
                if is_us: fx_rate = 0.79 # Approx USD/GBP
                if is_india: fx_rate = 0.0093

                if risk_per_share > 0:
                    # Risk based sizing
                    shares = int((risk_amt_gbp / fx_rate) / risk_per_share)
                    # Cap at 20% of Portfolio (Concentration limit)
                    max_cap_shares = int((ISA_ACCOUNT_SIZE / fx_rate * 0.20) / curr_price)
                    shares = min(shares, max_cap_shares)

                action_text = f"Buy {shares} Shares"

            elif options_signal:
                type_label = "🇺🇸 CREDIT SPREAD"
                # SPREAD LOGIC:
                # Sell Put @ 0.5 ATR below support
                short_strike = round(curr_price - (atr * 1.5), 1)
                # Buy Put $5 lower (Defined Risk)
                long_strike = round(short_strike - 5, 1)

                action_text = f"Sell Vert Put {short_strike}/{long_strike}"

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Type": type_label,
                "Setup": setup_name,
                "Action": action_text,
                "Stop Loss": round(stop_loss, 2),
                "RSI": round(rsi, 0),
                "Vol_Rel": round(vol_col.iloc[-1] / avg_vol_20, 1),
                "Regime": self.regime_color,
                "sort_key": sort_metric
            }

        except Exception as e:
            # We log failures now instead of swallowing them
            # logger.warning(f"Error processing {ticker}: {e}")
            return None

    def run(self):
        self._fetch_market_regime()

        if self.market_regime == "VOLATILITY_STORM":
            logger.warning("⛔ MARKET HAZARDOUS (VIX > 28). NO TRADES.")
            return []

        logger.info(f"Scanning {len(self.all_tickers)} tickers...")

        chunk_size = 50
        results = []

        # Iterate in chunks
        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                # Auto_adjust=True gives us Total Return Price (Dividends/Splits handled)
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                if len(chunk) == 1:
                    res = self._process_stock(chunk[0], data)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            # Robust MultiIndex Handling
                            if isinstance(data.columns, pd.MultiIndex):
                                if ticker in data.columns.levels[0]:
                                    df = data[ticker].dropna(how='all')
                                    res = self._process_stock(ticker, df)
                                    if res: results.append(res)
                        except Exception as e:
                            # Log specific ticker failure
                            pass
            except Exception as e:
                logger.error(f"Batch download failed: {e}")

        # Sort: ISA Buys first, then Options
        results.sort(key=lambda x: x['sort_key'], reverse=True)

        # --- CSV EXPORT (Atomic) ---
        if results:
            df_res = pd.DataFrame(results)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"scan_results_{timestamp}.csv"

            # Reorder columns for readability
            cols = ["Ticker", "Action", "Price", "Type", "Setup", "Stop Loss", "RSI", "Vol_Rel", "Regime"]
            df_res = df_res[cols]

            df_res.to_csv(filename, index=False)
            logger.info(f"✅ Results saved to {filename}")

        return results
