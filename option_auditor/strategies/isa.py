from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import logging
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.common.constants import TICKER_NAMES

logger = logging.getLogger(__name__)

class IsaStrategy(BaseStrategy):
    """
    ISA Trend Strategy:
    - Long Term Trend: Price > 200 SMA
    - Momentum: Price within 15% of 52-week High (implicitly handled by breakout logic)
    - Breakout: Price crosses 50-day High (Donchian Channel)
    - Volatility: ATR logic for stops
    """
    def __init__(self, ticker: str, df: pd.DataFrame, check_mode: bool = False, account_size: float = None, risk_per_trade_pct: float = 0.01, benchmark_df: pd.DataFrame = None):
        self.ticker = ticker
        self.df = df
        self.check_mode = check_mode
        self.account_size = account_size
        self.risk_per_trade_pct = risk_per_trade_pct
        self.benchmark_df = benchmark_df

    def check_vcp(self) -> bool:
        """
        Checks for Volatility Contraction Pattern (VCP).
        Logic: Volatility (measured by Std Dev of price) should decrease over recent periods.
        """
        try:
            if len(self.df) < 50: return False

            # Check last 3 periods of 10 days
            # Period 1: Recent 10 days
            # Period 2: Previous 10-20 days
            # Period 3: Previous 20-30 days

            p1 = self.df['Close'].iloc[-10:].std()
            p2 = self.df['Close'].iloc[-20:-10].std()
            p3 = self.df['Close'].iloc[-30:-20].std()

            # Check for contraction: p3 > p2 > p1
            # We allow small margin or strict inequality
            if pd.isna(p1) or pd.isna(p2) or pd.isna(p3): return False

            return (p1 < p2) and (p2 < p3)
        except Exception:
            return False

    def check_ema_alignment(self) -> bool:
        """
        Checks for Institutional Verdict (EMA Alignment).
        Logic: Price > EMA 50 > EMA 150 > EMA 200.
        """
        if len(self.df) < 200: return False
        try:
            ema_50 = ta.ema(self.df['Close'], length=50)
            ema_150 = ta.ema(self.df['Close'], length=150)
            ema_200 = ta.ema(self.df['Close'], length=200)

            if ema_50 is None or ema_150 is None or ema_200 is None:
                return False

            c = float(self.df['Close'].iloc[-1])
            e50 = float(ema_50.iloc[-1])
            e150 = float(ema_150.iloc[-1])
            e200 = float(ema_200.iloc[-1])

            return (c > e50) and (e50 > e150) and (e150 > e200)
        except Exception:
            return False

    def calculate_relative_strength(self) -> float:
        """
        Calculates Relative Strength vs Benchmark (if provided).
        Returns percentage outperformance over last 252 days.
        """
        if self.benchmark_df is None or self.benchmark_df.empty:
            return 0.0

        try:
            period = 252
            # Use minimal length available if < 252 but > 50
            min_len = min(len(self.df), len(self.benchmark_df))
            if min_len < 50: return 0.0

            if min_len < period:
                period = min_len

            # Use iloc to get start and end prices regardless of index alignment (simplified RS)
            # Ideally we align by date, but for this mock implementation simple return diff is enough

            stock_end = float(self.df['Close'].iloc[-1])
            stock_start = float(self.df['Close'].iloc[-period])
            stock_ret = (stock_end / stock_start) - 1

            bench_end = float(self.benchmark_df['Close'].iloc[-1])
            bench_start = float(self.benchmark_df['Close'].iloc[-period])
            bench_ret = (bench_end / bench_start) - 1

            rs = (stock_ret - bench_ret) * 100
            return rs
        except Exception:
            return 0.0

    def analyze(self) -> dict:
        try:
            # Need to copy df to avoid SettingWithCopy warnings if slice
            df = self.df.copy()
            df = df.dropna(how='all')
            min_length = 50 if self.check_mode else 200
            if len(df) < min_length: return None

            curr_close = float(df['Close'].iloc[-1])

            current_atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1] if len(df) >= 14 else 0.0
            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
            pct_change_1d = ((curr_close - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) >= 2 else 0.0

            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if not self.check_mode and (avg_vol * curr_close) < 5_000_000:
                return None

            sma_200 = df['Close'].rolling(200).mean().iloc[-1]

            df['High_50'] = df['High'].rolling(50).max().shift(1)
            df['Low_20'] = df['Low'].rolling(20).min().shift(1)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)

            # Fix for Data Gaps (e.g. Missing High/Low): Forward Fill indicators
            df['High_50'] = df['High_50'].ffill()
            df['Low_20'] = df['Low_20'].ffill()
            df['ATR'] = df['ATR'].ffill()

            high_50 = df['High_50'].iloc[-1]
            low_20 = df['Low_20'].iloc[-1]
            atr_20 = float(df['ATR'].iloc[-1])

            # Fallback for ATR if completely missing
            if pd.isna(atr_20):
                 atr_20 = curr_close * 0.02

            signal = "WAIT"

            if curr_close > sma_200:
                # Handle NaNs in High_50/Low_20 (if insufficient history)
                if pd.notna(high_50) and curr_close >= high_50:
                    signal = "🚀 ENTER LONG (50d Breakout)"
                elif pd.notna(high_50) and curr_close >= high_50 * 0.98:
                    signal = "👀 WATCH (Near Breakout)"
                elif pd.notna(low_20) and curr_close > low_20:
                    signal = "✅ HOLD (Trend Active)"
                elif pd.notna(low_20) and curr_close <= low_20:
                    signal = "🛑 EXIT (Stop Hit)"
                # Fallback if indicators are missing but Trend is up
                elif signal == "WAIT":
                     signal = "✅ HOLD (Trend Active*)"
            else:
                signal = "❌ SELL/AVOID (Downtrend)"

            stop_price = curr_close - (3 * atr_20)

            risk_per_share = curr_close - stop_price

            effective_stop = stop_price
            if "HOLD" in signal or "EXIT" in signal:
                effective_stop = low_20

            dist_to_stop_pct = 0.0
            if curr_close > 0:
                dist_to_stop_pct = ((curr_close - effective_stop) / curr_close) * 100

            # --- POSITION SIZING LOGIC ---
            position_size_shares = 0
            position_value = 0.0
            risk_amount = 0.0
            account_used_pct = 0.0
            max_position_size_str = ""
            tharp_verdict = ""
            is_tharp_safe = False

            if self.account_size and self.account_size > 0:
                # Explicit sizing based on risk
                risk_amount = self.account_size * self.risk_per_trade_pct

                # Prevent div by zero if stop is at entry or above
                risk_dist_val = max(0.01, curr_close - effective_stop) # Min 1 cent risk per share

                # Calculate shares
                raw_shares = risk_amount / risk_dist_val

                # Cap at 20% of account (Max Allocation Rule)
                max_allocation = self.account_size * 0.20
                max_shares_allocation = max_allocation / curr_close

                final_shares = int(min(raw_shares, max_shares_allocation))

                position_value = final_shares * curr_close
                account_used_pct = (position_value / self.account_size) * 100

                position_size_shares = final_shares
                max_position_size_str = f"{final_shares} shares (£{int(position_value)})"

                # Verdict
                is_tharp_safe = True # Calculated to be safe
                tharp_verdict = f"✅ SAFE (Risk £{int(risk_amount)})"

            else:
                # Legacy Percentage Recommendation
                position_size_pct = 0.04
                risk_dist = max(0.0, dist_to_stop_pct)
                total_equity_risk_pct = position_size_pct * (risk_dist / 100.0)

                is_tharp_safe = bool(total_equity_risk_pct <= 0.01)

                tharp_verdict = "✅ SAFE" if is_tharp_safe else f"⚠️ RISKY (Risks {total_equity_risk_pct*100:.1f}% Equity)"

                suggested_size_val = 0.0
                if risk_dist > 0:
                     suggested_size_val = min(4.0, 1.0 / (risk_dist / 100.0))
                else:
                     suggested_size_val = 4.0

                max_position_size_str = f"{suggested_size_val:.1f}%"

            if dist_to_stop_pct <= 0:
                 tharp_verdict = "🛑 STOPPED OUT"

            volatility_pct = (atr_20 / curr_close) * 100

            breakout_date = _calculate_trend_breakout_date(df)

            base_ticker = self.ticker.split('.')[0]
            company_name = TICKER_NAMES.get(self.ticker, TICKER_NAMES.get(base_ticker, self.ticker))

            # --- NEW METRICS ---
            is_vcp = self.check_vcp()
            ema_alignment = self.check_ema_alignment()
            rs_score = self.calculate_relative_strength()

            return {
                "ticker": self.ticker,
                "company_name": company_name,
                "price": curr_close,
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "trend_200sma": "Bullish",
                "breakout_level": round(high_50, 2),
                "stop_loss_3atr": round(stop_price, 2),
                "stop_loss": round(stop_price, 2), # Alias for unified UI
                "target": round(curr_close + (6 * atr_20), 2), # 6x ATR Target for Trend Following
                "trailing_exit_20d": round(low_20, 2),
                "volatility_pct": round(volatility_pct, 2),
                "atr_20": round(atr_20, 2),
                "atr_value": round(atr_20, 2),
                "risk_per_share": round(risk_per_share, 2),
                "dist_to_stop_pct": round(dist_to_stop_pct, 2),
                "tharp_verdict": tharp_verdict,
                "max_position_size": max_position_size_str,
                "shares": position_size_shares,
                "position_value": round(position_value, 2),
                "risk_amount": round(risk_amount, 2),
                "account_used_pct": round(account_used_pct, 1),
                "breakout_date": breakout_date,
                "safe_to_trade": is_tharp_safe,
                "atr": round(current_atr, 2),
                "52_week_high": round(high_52wk, 2) if high_52wk else None,
                "52_week_low": round(low_52wk, 2) if low_52wk else None,
                "sector_change": pct_change_1d,

                # New Fields
                "vcp": is_vcp,
                "ema_alignment": ema_alignment,
                "rs_rating": round(rs_score, 2)
            }
        except Exception as e:
            # logger.error(f"ISA ticker error: {e}")
            return None
