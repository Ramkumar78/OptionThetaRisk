from .base import BaseStrategy
import pandas_ta as ta
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.screener_utils import DEFAULT_RSI_LENGTH, DEFAULT_ATR_LENGTH
from option_auditor.common.data_utils import _calculate_trend_breakout_date

class RsiDivergenceStrategy(BaseStrategy):
    def __init__(self, ticker: str, df: pd.DataFrame, check_mode: bool = False):
        self.ticker = ticker
        self.df = df
        self.check_mode = check_mode

    def _find_divergence(self, price, rsi, lookback=30, order=3):
        # Find peaks (Highs)
        # argrelextrema returns indices of local maxima/minima
        # order=3 means it must be the max of 3 neighbors on each side

        if len(price) < lookback: return None, None

        high_idx = argrelextrema(price.values, np.greater, order=order)[0]
        low_idx = argrelextrema(price.values, np.less, order=order)[0]

        current_idx = len(price) - 1
        relevant_highs = [i for i in high_idx if (current_idx - i) < lookback]
        relevant_lows = [i for i in low_idx if (current_idx - i) < lookback]

        signal = None
        div_type = None

        # BEARISH DIVERGENCE CHECK (Higher Highs in Price, Lower Highs in RSI)
        if len(relevant_highs) >= 2:
            p2_idx = relevant_highs[-1] # Most recent peak
            p1_idx = relevant_highs[-2] # Previous peak

            # Check if recent peak is very recent (within last 5 bars)
            if (current_idx - p2_idx) <= 5:
                price_p2 = price.iloc[p2_idx]
                price_p1 = price.iloc[p1_idx]

                rsi_p2 = rsi.iloc[p2_idx]
                rsi_p1 = rsi.iloc[p1_idx]

                # Price made Higher High, RSI made Lower High
                if price_p2 > price_p1 and rsi_p2 < rsi_p1:
                    signal = "🐻 BEARISH DIVERGENCE"
                    div_type = "Bearish"

        # BULLISH DIVERGENCE CHECK (Lower Lows in Price, Higher Lows in RSI)
        if len(relevant_lows) >= 2:
            p2_idx = relevant_lows[-1]
            p1_idx = relevant_lows[-2]

            # Check if recent valley is very recent
            if (current_idx - p2_idx) <= 5:
                price_p2 = price.iloc[p2_idx]
                price_p1 = price.iloc[p1_idx]

                rsi_p2 = rsi.iloc[p2_idx]
                rsi_p1 = rsi.iloc[p1_idx]

                # Price made Lower Low, RSI made Higher Low
                if price_p2 < price_p1 and rsi_p2 > rsi_p1:
                    signal = "🐂 BULLISH DIVERGENCE"
                    div_type = "Bullish"

        return signal, div_type

    def analyze(self) -> dict:
        try:
            df = self.df
            ticker = self.ticker

            if len(df) < 50: return None
            if 'Close' not in df.columns: return None

            # Calc RSI
            rsi = ta.rsi(df['Close'], length=DEFAULT_RSI_LENGTH)
            if rsi is None: return None
            df['RSI'] = rsi

            # Find Div
            signal, div_type = self._find_divergence(df['Close'], df['RSI'])

            if signal:
                curr_price = df['Close'].iloc[-1]
                curr_rsi = df['RSI'].iloc[-1]

                # ATR for stop/target
                if 'ATR' not in df.columns:
                    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)

                atr = 0.0
                if 'ATR' in df.columns and not df['ATR'].empty:
                     atr = df['ATR'].iloc[-1]
                else:
                     atr = curr_price * 0.01

                stop_loss = curr_price - (3*atr) if div_type == "Bullish" else curr_price + (3*atr)
                target = curr_price + (5*atr) if div_type == "Bullish" else curr_price - (5*atr)

                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

                pct_change_1d = 0.0
                if len(df) >= 2:
                    pct_change_1d = ((curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100

                return {
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": round(curr_price, 2),
                    "pct_change_1d": round(pct_change_1d, 2),
                    "signal": signal,
                    "verdict": signal,
                    "rsi": round(curr_rsi, 2),
                    "atr": round(atr, 2),
                    "atr_value": round(atr, 2),
                    "stop_loss": round(stop_loss, 2),
                    "target": round(target, 2),
                    "breakout_date": _calculate_trend_breakout_date(df),
                    "score": 90
                }
        except Exception as e:
            return None
        return None
