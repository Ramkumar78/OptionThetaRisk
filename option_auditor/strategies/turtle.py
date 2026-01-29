from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import logging
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.screener_utils import DEFAULT_DONCHIAN_WINDOW, DEFAULT_ATR_LENGTH

logger = logging.getLogger(__name__)

class TurtleStrategy(BaseStrategy):
    """
    Turtle Trading Strategy:
    - 20-Day Breakouts (Donchian Channel)
    - Volatility (ATR)
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
            min_length = 21 if self.check_mode else 21 # Turtle needs 20 bars for Donchian
            if self.df is None or len(self.df) < min_length: return None

            df = self.df.copy()

            # --- TURTLE & DARVAS CALCULATIONS ---
            # 1. Donchian Channels (20-day High/Low)
            df['20_High'] = df['High'].rolling(window=DEFAULT_DONCHIAN_WINDOW).max().shift(1)
            df['20_Low'] = df['Low'].rolling(window=DEFAULT_DONCHIAN_WINDOW).min().shift(1)

            # Darvas / 10-day Box for faster breakouts
            df['10_High'] = df['High'].rolling(window=10).max().shift(1)
            df['10_Low'] = df['Low'].rolling(window=10).min().shift(1)

            # 2. ATR (Volatility 'N') - Using Donchian Window for N as per Turtle
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_DONCHIAN_WINDOW)

            curr_close = float(df['Close'].iloc[-1])

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception as e:
                    logger.debug(f"Pct change calc failed: {e}")

            if pd.isna(df['20_High'].iloc[-1]) or pd.isna(df['ATR'].iloc[-1]):
                return None

            prev_high = float(df['20_High'].iloc[-1])
            prev_low = float(df['20_Low'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])

            # 10-day values
            prev_high_10 = float(df['10_High'].iloc[-1]) if not pd.isna(df['10_High'].iloc[-1]) else prev_high
            prev_low_10 = float(df['10_Low'].iloc[-1]) if not pd.isna(df['10_Low'].iloc[-1]) else prev_low

            signal = "WAIT"
            buy_price = 0.0
            stop_loss = 0.0
            target = 0.0

            dist_to_breakout_high = (curr_close - prev_high) / prev_high

            # Buy Breakout (Turtle 20-Day)
            if curr_close > prev_high:
                signal = "🚀 BREAKOUT (BUY)"
                buy_price = curr_close
                stop_loss = buy_price - (2 * atr)
                target = buy_price + (4 * atr)

            # Sell Breakout (Short)
            elif curr_close < prev_low:
                signal = "📉 BREAKDOWN (SELL)"
                buy_price = curr_close
                stop_loss = buy_price + (2 * atr) # Stop above entry for short
                target = buy_price - (4 * atr)    # Target below entry

            # Near High (Turtle 20-Day only for now)
            elif -0.02 <= dist_to_breakout_high <= 0:
                signal = "👀 WATCH (Near High)"
                buy_price = prev_high
                stop_loss = prev_high - (2 * atr)
                target = prev_high + (4 * atr)

            # Calculate Trend Breakout Date
            breakout_date = _calculate_trend_breakout_date(df)

            # Additional Calcs for Consistency
            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH).iloc[-1] if len(df) >= DEFAULT_ATR_LENGTH else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()

            # Risk/Reward calculation
            invalidation_level = stop_loss
            target_level = target
            potential_risk = curr_close - invalidation_level
            potential_reward = target_level - curr_close
            rr_ratio = potential_reward / potential_risk if potential_risk > 0 else 0.0

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
                    "breakout_level": prev_high,
                    "stop_loss": invalidation_level,
                    "target": target_level,
                    "risk_reward": f"1:{rr_ratio:.2f}",
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d,
                    "trailing_exit_10d": round(prev_low_10, 2),
                    "breakout_date": breakout_date,
                    "atr_value": round(current_atr, 2)
                }
        except Exception as e:
            logger.error(f"Error processing turtle setup for {self.ticker}: {e}")
            return None
        return None
