from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.screener_utils import DEFAULT_ATR_LENGTH

logger = logging.getLogger(__name__)

class DarvasBoxStrategy(BaseStrategy):
    """
    Screens for Darvas Box Breakouts.
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
        }

    def analyze(self) -> dict:
        try:
            min_length = 50 if self.check_mode else 50 # Darvas needs enough history for pivots
            if self.df is None or len(self.df) < min_length: return None

            df = self.df.copy()
            curr_close = float(df['Close'].iloc[-1])
            curr_volume = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0

            # 1. 52-Week High Check (Momentum Filter)
            period_high = df['High'].max()
            if curr_close < period_high * 0.90 and not self.check_mode:
                pass # Just a filter, but we proceed to check boxes

            # 2. Identify Box (Ceiling & Floor)
            # We iterate back to find the most recent valid Box.
            ceiling = None
            floor = None

            # Convert to numpy for speed
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            volumes = df['Volume'].values if 'Volume' in df.columns else np.zeros(len(df))

            lookback = min(len(df), 60)
            found_top_idx = -1

            for i in range(len(df) - 4, len(df) - lookback, -1):
                if i < 3: break
                if i + 3 >= len(df): continue

                curr_h = highs[i]
                if (curr_h >= highs[i-1] and curr_h >= highs[i-2] and curr_h >= highs[i-3] and
                    curr_h >= highs[i+1] and curr_h >= highs[i+2] and curr_h >= highs[i+3]):

                    found_top_idx = i
                    ceiling = curr_h
                    break

            if found_top_idx == -1: return None

            found_bot_idx = -1

            for j in range(found_top_idx + 1, len(df) - 3):
                if j < 3: continue
                if j + 3 >= len(df): continue

                curr_l = lows[j]
                if curr_l >= ceiling: continue # Bottom must be below top

                if (curr_l <= lows[j-1] and curr_l <= lows[j-2] and curr_l <= lows[j-3] and
                    curr_l <= lows[j+1] and curr_l <= lows[j+2] and curr_l <= lows[j+3]):

                    found_bot_idx = j
                    floor = curr_l
                    break

            # Calc ATR, 52wk
            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH).iloc[-1] if len(df) >= DEFAULT_ATR_LENGTH else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            pct_change_1d = ((curr_close - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) >= 2 else 0.0

            # --- SIGNAL GENERATION ---
            signal = "WAIT"

            # 3. Check for Breakout
            if ceiling and floor:
                if closes[-1] > ceiling and closes[-2] <= ceiling:
                     signal = "📦 DARVAS BREAKOUT"

                elif closes[-1] < floor and closes[-2] >= floor:
                     signal = "📉 BOX BREAKDOWN"

                elif closes[-1] > ceiling:
                     if (closes[-1] - ceiling) / ceiling < 0.05:
                         signal = "🚀 MOMENTUM (Post-Breakout)"

            elif ceiling and not floor:
                pass

            if signal == "WAIT" and not self.check_mode:
                return None

            # 4. Volume Filter (for Breakouts)
            is_valid_volume = True
            vol_ma_ratio = 1.0
            if "BREAKOUT" in signal and not self.check_mode:
                vol_ma = np.mean(volumes[-21:-1]) if len(volumes) > 21 else np.mean(volumes)
                if vol_ma > 0:
                    vol_ma_ratio = curr_volume / vol_ma
                    if curr_volume < vol_ma * 1.2:
                        is_valid_volume = False

            if not is_valid_volume and not self.check_mode:
                return None

            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            stop_loss = floor if floor else (ceiling - 2*current_atr if ceiling else curr_close * 0.95)
            box_height = (ceiling - floor) if (ceiling and floor) else (4 * current_atr)
            target = ceiling + box_height if ceiling else curr_close * 1.2

            base_ticker = self.ticker.split('.')[0]
            company_name = TICKER_NAMES.get(self.ticker, TICKER_NAMES.get(base_ticker, self.etf_names.get(self.ticker, self.ticker)))
            breakout_date = _calculate_trend_breakout_date(df)

            return {
                "ticker": self.ticker,
                "company_name": company_name,
                "price": curr_close,
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "breakout_level": ceiling,
                "floor_level": floor,
                "stop_loss": stop_loss,
                "target_price": target,
                "target": target,
                "high_52w": period_high,
                "atr_value": round(current_atr, 2),
                "volatility_pct": round(volatility_pct, 2),
                "volume_ratio": round(vol_ma_ratio, 2),
                "breakout_date": breakout_date,
                "atr": round(current_atr, 2),
                "52_week_high": round(high_52wk, 2) if high_52wk else None,
                "52_week_low": round(low_52wk, 2) if low_52wk else None,
                "sector_change": pct_change_1d
            }

        except Exception as e:
            logger.error(f"Error processing Darvas for {self.ticker}: {e}")
            return None
