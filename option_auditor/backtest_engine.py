import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from typing import Dict, Any, List, Tuple
from option_auditor.backtesting_strategies import get_strategy, AbstractBacktestStrategy
from option_auditor.config import BACKTEST_DAYS

logger = logging.getLogger("BacktestEngine")

class BacktestEngine:
    def __init__(self, strategy_type: str, initial_capital: float):
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital
        self.strategy: AbstractBacktestStrategy = get_strategy(strategy_type)

        # State
        self.equity = initial_capital
        self.shares = 0
        self.state = "OUT"
        self.entry_date = None
        self.trade_log = []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Common indicators needed for context (Regime, etc)
        if 'Spy' in df.columns:
            df['spy_sma200'] = df['Spy'].rolling(200).mean()
        else:
            df['spy_sma200'] = 0.0

        # Volatility & ATR (Universal need for stops usually)
        if len(df) > 14:
            df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        else:
            df['atr'] = 0.0

        # Delegate to strategy
        df = self.strategy.add_indicators(df)

        return df.dropna()

    def run(self, df: pd.DataFrame, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Runs the backtest simulation on the provided DataFrame.
        Returns a dictionary with raw results (log, equity curve, etc).
        """
        # 1. Calculate Indicators
        df = self.calculate_indicators(df)
        if df.empty: return {"error": "Not enough history"}

        # 2. Slice Data (Simulation Window)
        sim_data = pd.DataFrame()

        if start_date:
            s_date = pd.Timestamp(start_date)
            # Ensure start_date matches dataframe timezone awareness
            if df.index.tz is not None and s_date.tz is None:
                s_date = s_date.tz_localize(df.index.tz)
            elif df.index.tz is None and s_date.tz is not None:
                s_date = s_date.tz_localize(None)

            sim_data = df[df.index >= s_date].copy()

            if end_date:
                e_date = pd.Timestamp(end_date)
                if df.index.tz is not None and e_date.tz is None:
                    e_date = e_date.tz_localize(df.index.tz)
                elif df.index.tz is None and e_date.tz is not None:
                    e_date = e_date.tz_localize(None)
                sim_data = sim_data[sim_data.index <= e_date]
        else:
            target_days = BACKTEST_DAYS
            s_date = pd.Timestamp.now() - pd.Timedelta(days=target_days)
            if df.index.tz is not None:
                s_date = s_date.tz_localize(df.index.tz)

            # Check if we have enough data, fallback logic
            if df.index[0] > s_date:
                start_date_3y = pd.Timestamp.now() - pd.Timedelta(days=1095)
                if df.index.tz is not None:
                    start_date_3y = start_date_3y.tz_localize(df.index.tz)

                if df.index[0] > start_date_3y:
                    start_date_2y = pd.Timestamp.now() - pd.Timedelta(days=730)
                    if df.index.tz is not None:
                        start_date_2y = start_date_2y.tz_localize(df.index.tz)

                    if df.index[0] > start_date_2y:
                        sim_data = df.copy()
                    else:
                        sim_data = df[df.index >= start_date_2y].copy()
                else:
                    sim_data = df[df.index >= start_date_3y].copy()
            else:
                sim_data = df[df.index >= s_date].copy()

        if sim_data.empty: return {"error": "Not enough history"}

        # 3. Setup Loop
        initial_price = sim_data['Close'].iloc[0]
        final_price = sim_data['Close'].iloc[-1]

        # B&H Tracking
        bnh_shares = int(self.initial_capital / initial_price)
        bnh_cash_residue = self.initial_capital - (bnh_shares * initial_price)

        # Reset State for run
        self.equity = self.initial_capital
        self.shares = 0
        self.state = "OUT"
        self.entry_date = None
        self.trade_log = []

        equity_curve = []

        # Context Memory
        recent_swing_highs = []
        recent_swing_lows = []
        context = {
            'recent_swing_highs': recent_swing_highs,
            'recent_swing_lows': recent_swing_lows
        }

        stop_loss = 0.0
        target_price = 0.0
        current_stop_reason = "STOP"

        # 4. Loop
        for i in range(len(sim_data)):
            if i < 20: continue # Warmup

            date = sim_data.index[i]
            row = sim_data.iloc[i]

            # --- FRACTAL IDENTIFICATION (Shared Logic) ---
            if i >= 2:
                row_minus_1 = sim_data.iloc[i-1]
                row_minus_2 = sim_data.iloc[i-2]

                # Swing High
                if row_minus_1['High'] > row_minus_2['High'] and row_minus_1['High'] > row['High']:
                    recent_swing_highs.append({
                        'price': row_minus_1['High'],
                        'rsi': row_minus_1['rsi'] if 'rsi' in row_minus_1 else 50,
                        'idx': i-1
                    })
                    if len(recent_swing_highs) > 10: recent_swing_highs.pop(0)

                # Swing Low
                if row_minus_1['Low'] < row_minus_2['Low'] and row_minus_1['Low'] < row['Low']:
                    recent_swing_lows.append({
                        'price': row_minus_1['Low'],
                        'rsi': row_minus_1['rsi'] if 'rsi' in row_minus_1 else 50,
                        'idx': i-1
                    })
                    if len(recent_swing_lows) > 10: recent_swing_lows.pop(0)

            price = row['Close']
            buy_signal = False
            sell_signal = False

            # --- DELEGATE TO STRATEGY ---
            if self.state == "OUT":
                if self.strategy.should_buy(i, sim_data, context):
                    buy_signal = True
            else:
                should_sell, reason = self.strategy.should_sell(i, sim_data, context)
                if should_sell:
                    sell_signal = True
                    current_stop_reason = reason

            # ==============================
            # EXECUTION
            # ==============================

            if self.state == "OUT" and buy_signal:
                self.shares = int(self.equity / price)
                self.equity -= (self.shares * price)
                self.state = "IN"
                self.entry_date = date

                atr = row['atr']
                stop_loss, target_price = self.strategy.get_initial_stop_target(row, atr)

                self.trade_log.append({
                    "date": date.strftime('%Y-%m-%d'), "type": "BUY",
                    "price": round(price, 2), "stop": round(stop_loss, 2),
                    "target": round(target_price, 2) if target_price > 0 else "Trailing",
                    "days": "-"
                })

            elif self.state == "IN":
                # Check Hard Stop / Target
                hit_stop = price < stop_loss
                hit_target = (target_price > 0) and (price > target_price)

                if hit_stop:
                     sell_signal = True
                     current_stop_reason = "INITIAL STOP HIT"
                elif hit_target:
                     # Exception for trend strategies that don't use fixed targets
                     # This list logic is preserved from original UnifiedBacktester
                     if self.strategy_type not in ['grandmaster', 'isa', 'turtle', 'council', 'master', 'master_convergence']:
                        sell_signal = True
                        current_stop_reason = "TARGET HIT"

                if sell_signal:
                    proceeds = self.shares * price
                    self.equity += proceeds
                    self.shares = 0
                    self.state = "OUT"

                    days_held = (date - self.entry_date).days
                    reason = current_stop_reason

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'), "type": "SELL",
                        "price": round(price, 2), "reason": reason,
                        "equity": round(self.equity, 0),
                        "days": days_held
                    })

            # --- TRACK EQUITY CURVE DAILY ---
            current_total_equity = self.equity
            if self.state == "IN":
                current_total_equity += (self.shares * price)

            bnh_value = bnh_cash_residue + (bnh_shares * price)

            equity_curve.append({
                "date": date.strftime('%Y-%m-%d'),
                "strategy_equity": round(current_total_equity, 2),
                "buy_hold_equity": round(bnh_value, 2)
            })

        # Calculate final equity if still holding
        current_equity_val = self.equity
        if self.state == "IN":
             current_equity_val += (self.shares * final_price)

        # Recalculate B&H final value based on logic
        bnh_final_value = self.initial_capital - (bnh_shares * initial_price) + (bnh_shares * final_price)

        return {
            "sim_data": sim_data,
            "trade_log": self.trade_log,
            "equity_curve": equity_curve,
            "final_equity": current_equity_val,
            "bnh_final_value": bnh_final_value,
            "initial_price": initial_price,
            "final_price": final_price,
            "buy_hold_days": (sim_data.index[-1] - sim_data.index[0]).days
        }
