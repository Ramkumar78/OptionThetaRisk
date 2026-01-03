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

# --- CONFIGURATION ---
ISA_ACCOUNT_SIZE = 100000.0 # GBP
OPTIONS_ACCOUNT_SIZE = 9500.0 # USD
RISK_PER_TRADE_PCT = 0.0125 # 1.25% Risk (Kelly/Thorp sizing)

MARKET_TICKERS = ["SPY", "^VIX"]

# HARDENED LIQUIDITY GATES (Institutional Grade)
LIQUIDITY_MIN_VOL_USD = 20_000_000 # Raised to $20M to ensure institutional participation
LIQUIDITY_MIN_VOL_GBP = 1_000_000  # Raised to £1M
LIQUIDITY_MIN_TURNOVER_INR = 200_000_000

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk, tickers_india=None):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.tickers_india = list(set(tickers_india)) if tickers_india else []
        self.all_tickers = self.tickers_us + self.tickers_uk + self.tickers_india
        self.market_regime = "NEUTRAL"
        self.regime_color = "YELLOW"
        self.vix_level = 15.0
        self.spy_history = None # Store SPY data for Relative Strength calc

    def _fetch_market_regime(self):
        """
        Fetches Market Regime and stores SPY history for Relative Strength (RS) calculations.
        """
        try:
            data = yf.download(MARKET_TICKERS, period="1y", progress=False, auto_adjust=True)

            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close']
            else:
                closes = data

            # Store SPY series for RS Calc later (last 6 months needed)
            if 'SPY' in closes:
                self.spy_history = closes['SPY'].dropna()
            else:
                self.spy_history = pd.Series()

            spy_curr = self.spy_history.iloc[-1] if not self.spy_history.empty else 0
            spy_sma200 = self.spy_history.rolling(200).mean().iloc[-1] if not self.spy_history.empty else 0
            spy_sma20 = self.spy_history.rolling(20).mean().iloc[-1] if not self.spy_history.empty else 0

            # VIX Check
            if '^VIX' in closes:
                vix_series = closes['^VIX'].dropna()
                self.vix_level = vix_series.iloc[-1] if not vix_series.empty else 15.0
            else:
                self.vix_level = 15.0

            if pd.isna(spy_sma200) or spy_sma200 == 0: spy_sma200 = spy_curr * 0.9

            # Regime Definitions
            if spy_curr > spy_sma200 and spy_curr > spy_sma20 and self.vix_level < 22:
                self.market_regime = "BULLISH_AGGRESSIVE"
                self.regime_color = "GREEN"
            elif spy_curr > spy_sma200 and self.vix_level < 30:
                self.market_regime = "BULLISH_CAUTIOUS"
                self.regime_color = "YELLOW"
            else:
                self.market_regime = "BEARISH_DEFENSIVE"
                self.regime_color = "RED"

            logger.info(f"MARKET REGIME: {self.market_regime} (VIX: {self.vix_level:.2f})")

        except Exception as e:
            logger.error(f"Regime fetch failed: {e}")
            self.market_regime = "CAUTIOUS"
            self.regime_color = "YELLOW"
            self.spy_history = pd.Series()

    def _calculate_relative_strength(self, stock_closes):
        """
        Calculates 'Mansfield Relative Strength' proxy:
        Ratio of Stock/SPY normalized to 60 days ago.
        Returns: RS Slope (Positive = Outperforming, Negative = Lagging)
        """
        if self.spy_history is None or self.spy_history.empty:
            return 0.0

        try:
            # Align Dates
            common_idx = stock_closes.index.intersection(self.spy_history.index)
            if len(common_idx) < 60: return 0.0

            stock_series = stock_closes.loc[common_idx]
            spy_series = self.spy_history.loc[common_idx]

            # Calculate RS Line
            rs_line = stock_series / spy_series

            # Calculate 60-day momentum of the RS Line (Slope)
            # If RS Line today is higher than 60 days ago, stock is outperforming.
            rs_mom = (rs_line.iloc[-1] / rs_line.iloc[-60]) - 1.0
            return rs_mom
        except:
            return 0.0

    def _check_vcp(self, df):
        """
        Volatility Contraction Pattern (VCP) Logic:
        Checks if volatility is drying up (Standard Deviation compressing).
        """
        try:
            close = df['Close']
            # Volatility of last 10 days vs last 50 days
            vol_10 = close.rolling(10).std().iloc[-1]
            vol_50 = close.rolling(50).std().iloc[-1]

            # Contraction Ratio
            if vol_50 == 0: return False, 1.0
            ratio = vol_10 / vol_50

            # Squeeze is valid if short-term vol is < 60% of long-term vol
            is_squeeze = ratio < 0.60
            return is_squeeze, ratio
        except:
            return False, 1.0

    def _process_stock(self, ticker, df):
        try:
            # 1. DATA INTEGRITY
            if df.empty or len(df) < 252: return None
            if (datetime.now() - df.index[-1]).days > 5: return None

            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']

            curr_price = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            # Filter Penny Stocks
            if curr_price < 5.0: return None

            # 2. LIQUIDITY GATES (Hardened)
            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            if avg_vol_20 == 0: return None

            is_uk = ticker.endswith(".L") or ticker in self.tickers_uk
            is_india = ticker.endswith(".NS") or ticker in self.tickers_india
            is_us = not (is_uk or is_india)

            turnover = curr_price * avg_vol_20
            if is_uk: turnover = (curr_price / 100) * avg_vol_20 # Pence to GBP

            # STRICT GATES
            if is_us and turnover < LIQUIDITY_MIN_VOL_USD: return None
            if is_uk and turnover < LIQUIDITY_MIN_VOL_GBP: return None
            if is_india and turnover < LIQUIDITY_MIN_TURNOVER_INR: return None

            # 3. TECHNICAL METRICS
            sma50 = close.rolling(50).mean().iloc[-1]
            sma200 = close.rolling(200).mean().iloc[-1]
            atr = ta.atr(high, low, close, length=14).iloc[-1]
            rsi = ta.rsi(close, length=14).iloc[-1]

            # 4. THE EDGE CALCULATIONS

            # A. Relative Strength (Must be > 0, i.e., Outperforming Market)
            rs_score = self._calculate_relative_strength(close)

            # B. Volatility Contraction (VCP)
            is_squeeze, squeeze_ratio = self._check_vcp(df)

            # C. Volume Anomaly (Demand)
            # Breakout Volume > 1.5x Average OR Pocket Pivot (Vol > max down vol of 10d)
            curr_vol = volume.iloc[-1]
            vol_ratio = curr_vol / avg_vol_20

            # Pocket Pivot Logic
            # Find largest down-volume in last 10 days
            recent_prc = close.iloc[-11:-1] # Prior 10 days
            recent_vol = volume.iloc[-11:-1]
            down_days = recent_prc.diff() < 0
            max_down_vol = recent_vol[down_days].max() if any(down_days) else 0
            is_pocket_pivot = (curr_vol > max_down_vol) and (curr_price > prev_close)

            # D. Trend Integrity
            strong_trend = (curr_price > sma50 > sma200)

            # --- SETUP CLASSIFICATION ---

            signal_type = "NONE"
            setup_name = ""
            action_text = ""
            sort_score = 0
            stop_loss = 0.0

            # SETUP 1: "VCP EXPLOSION" (High Conviction)
            # Logic: Strong Trend + RS Outperformance + VCP Squeeze + Volume Spike
            if strong_trend and rs_score > 0.05 and is_squeeze and (vol_ratio > 1.5 or is_pocket_pivot):
                # Don't buy extended (>15% over 50SMA)
                extension = (curr_price - sma50) / sma50
                if extension < 0.15:
                    signal_type = "BUY"
                    setup_name = "💥 VCP EXPLOSION"
                    # Score based on RS (Leaders first) + Volume
                    sort_score = 100 + (rs_score * 100) + vol_ratio
                    # Tight Stop below the squeeze low (Low of last 5 days)
                    stop_loss = low.iloc[-5:].min() - (0.5 * atr)

            # SETUP 2: "POWER TREND PULLBACK" (Swing)
            # Logic: Trend is massive (Price > 200SMA), but RSI oversold (Dip buy in leader)
            elif strong_trend and rs_score > 0.10 and rsi < 45 and rsi > 30:
                signal_type = "BUY"
                setup_name = "⚓ POWER DIP"
                sort_score = 80 + (rs_score * 100)
                # Stop loss wider (1 ATR below recent low)
                stop_loss = low.iloc[-1] - (1.5 * atr)

            # SETUP 3: "FORTRESS PUT SPREAD" (Income)
            # Logic: US Only, High Volatility (ATR high), Support hold
            elif is_us and "BULLISH" in self.market_regime and strong_trend and not signal_type == "BUY":
                atr_pct = (atr / curr_price) * 100
                if atr_pct > 2.5 and rsi < 55: # High Vol + Not Overbought
                     signal_type = "CREDIT"
                     setup_name = "🛡️ FORTRESS SPREAD"
                     sort_score = 50 + atr_pct

                     short_strike = round(curr_price - (2 * atr), 1)
                     long_strike = round(short_strike - 5, 1)
                     action_text = f"Sell Put Vertical {short_strike}/{long_strike}"

            # --- FINAL FILTER ---
            if signal_type == "NONE": return None

            # Formatting
            if signal_type == "BUY":
                # Position Sizing (Risk 1.25% of Equity)
                risk_per_share = curr_price - stop_loss
                if risk_per_share <= 0: risk_per_share = curr_price * 0.05 # Fallback

                # Currency Adjust
                acc_size = ISA_ACCOUNT_SIZE
                fx = 1.0
                if is_us: fx = 0.79
                if is_india: fx = 0.0093

                risk_amt = acc_size * RISK_PER_TRADE_PCT
                shares = int((risk_amt / fx) / risk_per_share)

                # Cap max allocation (20%)
                max_shares = int((acc_size * 0.20 / fx) / curr_price)
                shares = min(shares, max_shares)

                action_text = f"Buy {shares} Shares"
                type_label = "✅ LONG EQUITY"
            elif signal_type == "CREDIT":
                type_label = "🇺🇸 OPTIONS"

            change_pct = ((curr_price - prev_close) / prev_close) * 100

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Change%": f"{change_pct:.2f}%",
                "Type": type_label,
                "Setup": setup_name,
                "Action": action_text,
                "Stop Loss": round(stop_loss, 2),
                "Target": round(curr_price + (2 * (curr_price - stop_loss)), 2),
                "Metrics": f"RS:{rs_score:.2f} Vol:{vol_ratio:.1f}x",
                "Regime": self.regime_color,
                "sort_key": sort_score,
                # Fields for UI
                "atr_value": round(atr, 2),
                "breakout_date": datetime.now().strftime('%Y-%m-%d') if "EXPLOSION" in setup_name else "-",
                "pct_change_1d": change_pct
            }

        except Exception as e:
            # logger.error(f"Error processing {ticker}: {e}")
            return None

    def run(self):
        self._fetch_market_regime()

        if self.market_regime == "BEARISH_DEFENSIVE":
            logger.warning("⚠️ MARKET DEFENSIVE. STRICT CRITERIA ONLY.")
            # We continue, but logic requires strict setups

        logger.info(f"Scanning {len(self.all_tickers)} tickers for CONFLUENCE...")

        chunk_size = 50
        results = []

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                # Group_by ticker is crucial for multi-ticker download
                data = yf.download(chunk, period="1y", group_by='ticker', progress=False, threads=True, auto_adjust=True)

                for ticker in chunk:
                    try:
                        df = None
                        if len(chunk) == 1:
                            df = data # Single ticker returns simple DF
                        elif isinstance(data.columns, pd.MultiIndex):
                             if ticker in data.columns.levels[0]:
                                 df = data[ticker].dropna(how='all')

                        if df is not None:
                            res = self._process_stock(ticker, df)
                            if res: results.append(res)
                    except:
                        continue
            except Exception as e:
                logger.error(f"Batch failed: {e}")

        # Sort by Score (High Conviction first)
        results.sort(key=lambda x: x['sort_key'], reverse=True)

        return results
