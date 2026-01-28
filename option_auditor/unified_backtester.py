import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from option_auditor.unified_screener import analyze_ticker_hardened, get_market_regime
from option_auditor.backtesting_strategies import get_strategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedBacktester")

class UnifiedBacktester:
    def __init__(self, ticker, strategy_type="grandmaster", initial_capital=10000.0):
        self.ticker = ticker.upper()
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.shares = 0
        self.state = "OUT"
        self.trade_log = []
        self.entry_date = None
        self.strategy = get_strategy(strategy_type)

    def fetch_data(self):
        try:
            # Fetch 10 years to ensure 200 SMA is ready before the 5-year backtest starts
            symbols = [self.ticker, "SPY", "^VIX"]
            data = yf.download(symbols, period="10y", auto_adjust=True, progress=False)

            if isinstance(data.columns, pd.MultiIndex):
                try:
                    close = data['Close']
                    high = data['High']
                    low = data['Low']
                    open_price = data['Open']
                    vol = data['Volume']
                except KeyError:
                    # yfinance 0.2.x structure variations
                     return None
            else:
                return None

            def get_series(df, sym):
                if sym in df.columns: return df[sym]
                # Fallback if single level or other issue
                return pd.Series(dtype=float)

            df = pd.DataFrame({
                'close': get_series(close, self.ticker),
                'high': get_series(high, self.ticker),
                'low': get_series(low, self.ticker),
                'open': get_series(open_price, self.ticker),
                'volume': get_series(vol, self.ticker),
                'spy': get_series(close, 'SPY'),
                'vix': get_series(close, '^VIX')
            }).dropna()

            # Capitalize columns to match unified_screener expectations (Close, High, Low...)
            df.columns = [c.capitalize() for c in df.columns] # Close, High, Low, Open, Volume, Spy, Vix

            return df
        except Exception as e:
            logger.error(f"Data Fetch Error: {e}")
            return None

    def calculate_indicators(self, df):
        # Common indicators needed for context (Regime, etc)
        df['spy_sma200'] = df['Spy'].rolling(200).mean()

        # Volatility & ATR (Universal need for stops usually)
        if len(df) > 14:
            df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        else:
            df['atr'] = 0.0

        # Delegate to strategy
        df = self.strategy.add_indicators(df)

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None: return {"error": "No data found"}
        if df.empty: return {"error": "Not enough history"}

        df = self.calculate_indicators(df)
        if df.empty: return {"error": "Not enough history"}

        # --- EXACT SIMULATION WINDOW ---
        # 5 Years (approx 1825 days)
        target_days = 1825
        start_date = pd.Timestamp.now() - pd.Timedelta(days=target_days)

        # Check if we have enough data, fallback to 3 years or 2 years if not
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

        actual_start_str = sim_data.index[0].strftime('%Y-%m-%d')
        actual_end_str = sim_data.index[-1].strftime('%Y-%m-%d')
        buy_hold_days = (sim_data.index[-1] - sim_data.index[0]).days

        # --- FAIR COMPARISON: BUY & HOLD ---
        initial_price = sim_data['Close'].iloc[0]
        final_price = sim_data['Close'].iloc[-1]

        simple_bnh_return = ((final_price - initial_price) / initial_price) * 100

        bnh_shares = int(self.initial_capital / initial_price)
        bnh_final_value = self.initial_capital - (bnh_shares * initial_price) + (bnh_shares * final_price)

        bnh_return_equity = ((bnh_final_value - self.initial_capital) / self.initial_capital) * 100

        # --- STRATEGY LOOP ---
        stop_loss = 0.0
        target_price = 0.0

        # Context Memory
        recent_swing_highs = []
        recent_swing_lows = []

        context = {
            'recent_swing_highs': recent_swing_highs,
            'recent_swing_lows': recent_swing_lows
        }

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
            current_stop_reason = "STOP"

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
                     # Some strategies might ignore targets (e.g. strict trailing), but base logic usually respects it if set.
                     # In original code, grandmaster/isa/turtle ignored target check here.
                     # We can handle this by checking if strategy provided a target > 0.
                     # But some strategies provided target but ignored it?
                     # Let's trust the target if provided, OR check strategy type (less ideal).
                     # The original code:
                     # if hit_target and self.strategy_type not in ['grandmaster', 'isa', 'turtle']: ...

                     # We can add a property to strategy: respects_target
                     # Or just set target to 0 in get_initial_stop_target for those strategies?
                     # In my implementation, Turtle/ISA return a target! (4*ATR etc).
                     # But the original code IGNORED it for exit.
                     # Refactoring nuance: If I want identical behavior, I should ensure those strategies return 0 target
                     # OR the check here is smarter.

                     # Let's look at my implementation of get_initial_stop_target for Turtle:
                     # target_price = price + (4 * atr)
                     # It returns a target.

                     # Original: if hit_target and self.strategy_type not in ['grandmaster', 'isa', 'turtle']:

                     # So for these, even if target is hit, we DON'T sell. We wait for trailing stop.
                     # I should probably handle this in `should_sell` or make `target_price` 0 for them.
                     # But they use target for R:R calculation in screener?
                     # This is backtester.

                     # I will modify this block to check if target_price > 0 AND strategy allows target exit.
                     # Or simply: if strategy relies on trailing stop, set target to 0 in `get_initial_stop_target`.

                     # Let's assume for now I should respect the explicit exclusion list from original code
                     # but via a property on the strategy class.

                     # Since I can't easily change the classes I just wrote without another write_file,
                     # I will use a list check here for now, or check if target_price is 0.
                     # I'll check the classes... Turtle returns positive target.

                     # I'll rely on `strategy_type` attribute which is available in base class.
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

        # Calculate final equity if still holding
        current_equity_val = self.equity
        if self.state == "IN":
             current_equity_val += (self.shares * final_price)

        strat_return = ((current_equity_val - self.initial_capital) / self.initial_capital) * 100

        sell_trades = [t['days'] for t in self.trade_log if t['type'] == 'SELL' and isinstance(t['days'], int)]
        avg_days_held = round(sum(sell_trades) / len(sell_trades)) if sell_trades else 0
        total_days_held = sum(sell_trades)

        structured_trades = []
        current_trade = {}

        for event in self.trade_log:
            if event['type'] == 'BUY':
                current_trade = {
                    "buy_date": event['date'],
                    "buy_price": event['price'],
                    "stop_loss": event.get('stop'),
                    "target": event.get('target', 'Trailing')
                }
            elif event['type'] == 'SELL':
                if current_trade:
                    current_trade["sell_date"] = event['date']
                    current_trade["sell_price"] = event['price']
                    current_trade["reason"] = event['reason']
                    current_trade["days_held"] = event['days']

                    if current_trade['buy_price'] and current_trade['buy_price'] > 0:
                        pnl = ((current_trade['sell_price'] - current_trade['buy_price']) / current_trade['buy_price']) * 100
                        current_trade["return_pct"] = round(pnl, 2)

                    structured_trades.append(current_trade)
                    current_trade = {}

        return {
            "ticker": self.ticker,
            "strategy": self.strategy_type.upper(),
            "start_date": actual_start_str,
            "end_date": actual_end_str,
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bnh_return_equity, 2),
            "buy_hold_return_pct": round(simple_bnh_return, 2),
            "buy_hold_days": buy_hold_days,
            "avg_days_held": avg_days_held,
            "total_days_held": total_days_held,
            "trades": len(self.trade_log) // 2,
            "win_rate": self._calculate_win_rate(),
            "final_equity": round(current_equity_val, 2),
            "log": self.trade_log,
            "trade_list": structured_trades
        }

    def _calculate_win_rate(self):
        wins = 0; losses = 0; entry = 0
        for t in self.trade_log:
            if t['type'] == 'BUY': entry = t['price']
            if t['type'] == 'SELL':
                if t['price'] > entry: wins += 1
                else: losses += 1
        total = wins + losses
        if total == 0: return "0%"
        return f"{round((wins/total)*100)}%"
