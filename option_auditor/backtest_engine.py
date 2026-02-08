import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from typing import Dict, Any, List, Tuple
from option_auditor.backtesting_strategies import get_strategy, AbstractBacktestStrategy
from option_auditor.config import BACKTEST_DAYS

logger = logging.getLogger("BacktestEngine")

class BacktestEngine:
    def __init__(self, strategy_type: str, initial_capital: float,
                 slippage_type: str = "fixed_pct", slippage_value: float = 0.0,
                 impact_factor: float = 0.0, margin_interest_rate: float = 0.0,
                 leverage_limit: float = 1.0):
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital
        self.strategy: AbstractBacktestStrategy = get_strategy(strategy_type)

        # Execution Simulation Parameters
        self.slippage_type = slippage_type
        self.slippage_value = slippage_value
        self.impact_factor = impact_factor
        self.margin_interest_rate = margin_interest_rate
        self.leverage_limit = leverage_limit

        # State
        self.equity = initial_capital
        self.shares = 0
        self.state = "OUT"
        self.entry_date = None
        self.trade_log = []

    def _calculate_execution_price(self, price: float, quantity: int, side: str, atr: float = 0.0) -> float:
        """
        Calculates the execution price with slippage and market impact.
        side: "BUY" or "SELL"
        """
        # 1. Base Slippage
        slippage_per_share = 0.0
        if self.slippage_type == "fixed_pct":
            # e.g. 0.001 * 100 = 0.10 per share
            slippage_per_share = price * self.slippage_value
        elif self.slippage_type == "atr":
            # e.g. 0.1 * ATR
            slippage_per_share = atr * self.slippage_value

        # 2. Market Impact (Linear Model)
        # Impact penalty per share increases with size
        # e.g. impact_factor 0.0001 * 1000 shares = 0.10 penalty per share
        impact_penalty = self.impact_factor * quantity

        total_penalty = slippage_per_share + impact_penalty

        if side == "BUY":
            return price + total_penalty
        else:
            return price - total_penalty

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

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs the backtest simulation on the provided DataFrame.
        Returns a dictionary with raw results (log, equity curve, etc).
        """
        # 1. Calculate Indicators
        df = self.calculate_indicators(df)
        if df.empty: return {"error": "Not enough history"}

        # 2. Slice Data (Simulation Window)
        target_days = BACKTEST_DAYS
        start_date = pd.Timestamp.now() - pd.Timedelta(days=target_days)

        # Check if we have enough data, fallback logic
        if df.index[0] > start_date:
            start_date_3y = pd.Timestamp.now() - pd.Timedelta(days=1095)
            if df.index[0] > start_date_3y:
                 start_date_2y = pd.Timestamp.now() - pd.Timedelta(days=730)
                 if df.index[0] > start_date_2y:
                     sim_data = df.copy()
                 else:
                     sim_data = df[df.index >= start_date_2y].copy()
            else:
                 sim_data = df[df.index >= start_date_3y].copy()
        else:
             sim_data = df[df.index >= start_date].copy()

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

            atr_val = row['atr'] if 'atr' in row else 0.0

            if self.state == "OUT" and buy_signal:
                # Calculate Max Shares based on Leverage
                # e.g. 10000 * 2.0 / 100 = 200 shares
                max_buying_power = self.equity * self.leverage_limit

                # Estimate shares with raw price first to avoid over-buying due to slippage
                # (Slippage increases cost, so we buy slightly less if full leverage)
                est_shares = int(max_buying_power / price)

                if est_shares > 0:
                    # Calculate Execution Price
                    exec_price = self._calculate_execution_price(price, est_shares, "BUY", atr_val)

                    # Ensure we can afford it (re-check with exec_price)
                    cost = est_shares * exec_price
                    if cost > max_buying_power:
                        est_shares = int(max_buying_power / exec_price)
                        exec_price = self._calculate_execution_price(price, est_shares, "BUY", atr_val) # Recalculate impact for new size
                        cost = est_shares * exec_price

                    if est_shares > 0:
                        self.shares = est_shares
                        self.equity -= cost # Equity drops by full cost (cash balance goes negative if margin)
                        self.state = "IN"
                        self.entry_date = date

                        stop_loss, target_price = self.strategy.get_initial_stop_target(row, atr_val)

                        self.trade_log.append({
                            "date": date.strftime('%Y-%m-%d'), "type": "BUY",
                            "price": round(exec_price, 2), "stop": round(stop_loss, 2),
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
                    # Calculate Execution Price
                    exec_price = self._calculate_execution_price(price, self.shares, "SELL", atr_val)

                    proceeds = self.shares * exec_price
                    self.equity += proceeds
                    self.shares = 0
                    self.state = "OUT"

                    days_held = (date - self.entry_date).days
                    reason = current_stop_reason

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'), "type": "SELL",
                        "price": round(exec_price, 2), "reason": reason,
                        "equity": round(self.equity, 0),
                        "days": days_held
                    })

            # --- MARGIN INTEREST CALCULATION ---
            # If self.equity < 0 (wait, self.equity tracks Net Liquidation Value in simple models usually)
            # But here: self.equity -= cost.
            # If I have 10k, buy 20k stock (cost 20k). self.equity becomes -10k.
            # This represents CASH. Net Liq = Cash + Shares * Price = -10k + 20k = +10k. Correct.
            # So if self.equity (which is effectively Cash Balance here) is negative, we pay interest.

            if self.equity < 0:
                daily_interest = abs(self.equity) * (self.margin_interest_rate / 365.0)
                self.equity -= daily_interest # Interest reduces cash (and thus Net Liq)

            # --- TRACK EQUITY CURVE DAILY ---
            # Net Liquidation Value
            current_total_equity = self.equity
            if self.state == "IN":
                current_total_equity += (self.shares * price) # Mark to Market

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
