from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import logging
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.screener_utils import (
    DEFAULT_ATR_LENGTH,
    DEFAULT_EMA_FAST,
    DEFAULT_EMA_MED,
    DEFAULT_EMA_SLOW,
)

logger = logging.getLogger(__name__)

class FiveThirteenStrategy(BaseStrategy):
    """
    Screens for 5/13 and 5/21 EMA Crossovers (Momentum Breakouts).
    """
    def __init__(self, ticker: str, df: pd.DataFrame, check_mode: bool = False):
        self.ticker = ticker
        self.df = df
        self.check_mode = check_mode
        self.etf_names = {
            "SPY": "SPDR S&P 500 ETF Trust",
            "QQQ": "Invesco QQQ Trust",
            "IWM": "iShares Russell 2000 ETF",
            "GLD": "SPDR Gold Shares",
            "SLV": "iShares Silver Trust",
            "USO": "United States Oil Fund, LP",
            "TLT": "iShares 20+ Year Treasury Bond ETF",
            "BITO": "ProShares Bitcoin Strategy ETF",
        }

    def analyze(self) -> dict:
        try:
            min_length = 22 if self.check_mode else 22 # Need 21 for EMA 21
            if self.df is None or len(self.df) < min_length: return None

            df = self.df.copy()

            # --- EMA CALCULATIONS ---
            df['EMA_5'] = ta.ema(df['Close'], length=DEFAULT_EMA_FAST)
            df['EMA_13'] = ta.ema(df['Close'], length=DEFAULT_EMA_MED)
            df['EMA_21'] = ta.ema(df['Close'], length=DEFAULT_EMA_SLOW)

            # ATR for standard reporting
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0

            # Current & Previous values
            curr_5 = df['EMA_5'].iloc[-1]
            curr_13 = df['EMA_13'].iloc[-1]
            curr_21 = df['EMA_21'].iloc[-1]

            prev_5 = df['EMA_5'].iloc[-2]
            prev_13 = df['EMA_13'].iloc[-2]
            prev_21 = df['EMA_21'].iloc[-2]

            curr_close = float(df['Close'].iloc[-1])
            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            # Calc ATR, 52wk
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()

            # --- SIGNAL GENERATION ---
            signal = "WAIT"
            status_color = "gray"
            stop_loss = 0.0
            ema_slow = curr_13 # Default to 13

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception as e:
                    logger.debug(f"Pct change calc failed: {e}")

            # Logic Priority:
            # 1. Fresh 5/21 Breakout (Stronger/Rarer)
            # 2. Fresh 5/13 Breakout
            # 3. Trending 5/21 (Trend strength)
            # 4. Trending 5/13

            # 1. Fresh Breakouts
            if curr_5 > curr_21 and prev_5 <= prev_21:
                signal = "🚀 FRESH 5/21 BREAKOUT"
                status_color = "green"
                ema_slow = curr_21
                stop_loss = curr_21 * 0.99

            elif curr_5 > curr_13 and prev_5 <= prev_13:
                signal = "🚀 FRESH 5/13 BREAKOUT"
                status_color = "green"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            # 2. Trending (Held for >1 day)
            elif curr_5 > curr_21:
                 signal = "📈 5/21 TRENDING"
                 status_color = "blue"
                 ema_slow = curr_21
                 stop_loss = curr_21 * 0.99

            elif curr_5 > curr_13:
                # Check how far extended?
                dist = (curr_close - curr_13) / curr_13
                if dist < 0.01: # Price is pulling back to 13 EMA (Buy Support)
                    signal = "✅ 5/13 TREND (Buy Support)"
                    status_color = "blue"
                else:
                    signal = "📈 5/13 TRENDING"
                    status_color = "blue"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            # 3. Bearish Cross (Sell)
            if curr_5 < curr_13 and prev_5 >= prev_13:
                signal = "❌ 5/13 DUMP (Sell Signal)"
                status_color = "red"
                ema_slow = curr_13
                stop_loss = curr_13 * 1.01 # Stop above

            elif curr_5 < curr_21 and prev_5 >= prev_21:
                signal = "❌ 5/21 DUMP (Sell Signal)"
                status_color = "red"
                ema_slow = curr_21
                stop_loss = curr_21 * 1.01

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            # Calculate Target based on 2R relative to EMA stop or 4 ATR
            # If long, target = price + (price - stop) * 2
            target_price = 0.0
            if "DUMP" in signal:
                risk = stop_loss - curr_close
                if risk > 0:
                     target_price = curr_close - (risk * 2)
                else:
                     target_price = curr_close - (4 * current_atr)
            else:
                risk = curr_close - stop_loss
                if risk > 0:
                     target_price = curr_close + (risk * 2)
                else:
                     target_price = curr_close + (4 * current_atr)

            if self.check_mode or signal != "WAIT":
                # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
                base_ticker = self.ticker.split('.')[0]
                company_name = TICKER_NAMES.get(self.ticker, TICKER_NAMES.get(base_ticker, self.etf_names.get(self.ticker, self.ticker)))
                return {
                    "ticker": self.ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
                    "signal": signal,
                    "color": status_color,
                    "ema_5": curr_5,
                    "ema_13": curr_13,
                    "ema_21": curr_21,
                    # Stop Loss usually strictly below the slow EMA line
                    "stop_loss": stop_loss,
                    "target": round(target_price, 2),
                    "atr_value": round(current_atr, 2), # Key was different in 5/13, standardizing or adding both? Keeping original key 'atr_value' but adding 'atr' for unified UI
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d,
                    "volatility_pct": round(volatility_pct, 2),
                    "diff_pct": ((curr_5 - ema_slow)/ema_slow)*100,
                    "breakout_date": breakout_date
                }

        except Exception as e:
            logger.error(f"Error processing 5/13 setup for {self.ticker}: {e}")
            return None
        return None
