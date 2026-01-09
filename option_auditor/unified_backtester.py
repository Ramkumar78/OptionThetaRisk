import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from option_auditor.unified_screener import analyze_ticker_hardened, get_market_regime

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

    def fetch_data(self):
        try:
            # Fetch 5 years to ensure 200 SMA is ready before the 3-year backtest starts
            symbols = [self.ticker, "SPY", "^VIX"]
            data = yf.download(symbols, period="5y", auto_adjust=True, progress=False)

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
        # Additional indicators for Turtle/Legacy strategies if needed
        # Unified Screener calculates its own, but we can pre-calc helpers

        # --- Trend Moving Averages ---
        df['sma200'] = df['Close'].rolling(200).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        df['sma150'] = df['Close'].rolling(150).mean()
        df['sma20'] = df['Close'].rolling(20).mean()

        # --- Volatility & ATR ---
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        # --- Donchian Channels (Legacy) ---
        df['high_20'] = df['High'].rolling(20).max().shift(1)
        df['high_10'] = df['High'].rolling(10).max().shift(1)
        df['low_20'] = df['Low'].rolling(20).min().shift(1)
        df['low_10'] = df['Low'].rolling(10).min().shift(1)
        df['high_50'] = df['High'].rolling(50).max().shift(1)

        # Regime Indicators
        df['spy_sma200'] = df['Spy'].rolling(200).mean()

        # --- Strategy Specific Indicators ---

        # EMA Strategy
        df['ema5'] = ta.ema(df['Close'], length=5)
        df['ema13'] = ta.ema(df['Close'], length=13)
        df['ema21'] = ta.ema(df['Close'], length=21)

        # RSI
        df['rsi'] = ta.rsi(df['Close'], length=14)

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None: return {"error": "No data found"}
        if df.empty: return {"error": "Not enough history"}

        df = self.calculate_indicators(df)
        if df.empty: return {"error": "Not enough history"}

        # --- EXACT SIMULATION WINDOW ---
        # 3 Years (approx 1095 days)
        target_days = 1095
        start_date = pd.Timestamp.now() - pd.Timedelta(days=target_days)

        # Check if we have enough data, fallback to 2 years if not
        if df.index[0] > start_date:
            # Not enough history for 3 years
            start_date_2y = pd.Timestamp.now() - pd.Timedelta(days=730)
            if df.index[0] > start_date_2y:
                 # Even 2y is tight, just use what we have
                 sim_data = df.copy()
            else:
                 sim_data = df[df.index >= start_date_2y].copy()
        else:
             sim_data = df[df.index >= start_date].copy()

        if sim_data.empty: return {"error": "Not enough history"}

        actual_start_str = sim_data.index[0].strftime('%Y-%m-%d')
        actual_end_str = sim_data.index[-1].strftime('%Y-%m-%d')
        buy_hold_days = (sim_data.index[-1] - sim_data.index[0]).days

        # --- FAIR COMPARISON: BUY & HOLD ---
        initial_price = sim_data['Close'].iloc[0]
        final_price = sim_data['Close'].iloc[-1]

        # Simple Buy and Hold Return %
        simple_bnh_return = ((final_price - initial_price) / initial_price) * 100

        # Portfolio Buy and Hold (Investing initial capital)
        bnh_shares = int(self.initial_capital / initial_price)
        bnh_final_value = self.initial_capital - (bnh_shares * initial_price) + (bnh_shares * final_price)

        bnh_return_equity = ((bnh_final_value - self.initial_capital) / self.initial_capital) * 100

        # --- STRATEGY LOOP ---
        stop_loss = 0.0
        target_price = 0.0

        for i in range(len(sim_data)):
            if i < 20: continue # Warmup

            date = sim_data.index[i]
            row = sim_data.iloc[i]
            prev_row = sim_data.iloc[i-1]

            price = row['Close']
            buy_signal = False
            sell_signal = False
            current_stop_reason = "STOP"

            # Dynamic Regime Check
            regime = "RED"
            spy_price = row['Spy']
            spy_sma = row['spy_sma200']
            vix_price = row['Vix']

            if spy_price > spy_sma and vix_price < 20:
                regime = "GREEN"
            elif spy_price > spy_sma and vix_price < 28:
                regime = "YELLOW"

            # --- STRATEGY LOGIC ---

            if self.strategy_type in ['grandmaster', 'council', 'master', 'master_convergence']:
                # ISA Trend + Momentum logic
                # 1. Regime Filter
                if regime == "RED":
                    if self.state == "IN":
                        sell_signal = True
                        current_stop_reason = "REGIME CHANGE (RED)"
                    buy_signal = False

                else:
                    sma50 = row['sma50']
                    sma200 = row['sma200']

                    # Trend Template
                    is_trend = (price > sma200) and (price > sma50) and (sma50 > sma200)

                    # Trigger: VCP Breakout (High of last 20 days)
                    high_20d = row['high_20']
                    breakout = (price > high_20d)

                    if is_trend and breakout:
                        buy_signal = True

                    if self.state == "IN":
                        # Trailing Stop: 20 Day Low
                        trail_stop = row['low_20']
                        if price < trail_stop:
                            sell_signal = True
                            current_stop_reason = "TRAILING STOP (20d Low)"

            elif self.strategy_type == 'turtle':
                if price > row['high_20']: buy_signal = True
                if self.state == "IN" and price < row['low_10']:
                    sell_signal = True
                    current_stop_reason = "10d LOW EXIT"

            elif self.strategy_type == 'isa': # Legacy ISA
                is_breakout_50 = row['Close'] > row['high_50']
                is_isa_reentry = (price > row['sma50']) and (price > row['sma200'])
                if (price > row['sma200']) and (is_breakout_50 or is_isa_reentry): buy_signal = True
                if self.state == "IN" and price < row['low_20']:
                    sell_signal = True
                    current_stop_reason = "20d LOW EXIT"

            elif self.strategy_type == 'market':
                # Market Screener: Price > SMA50, Buy Dip (RSI 30-50)
                is_uptrend = price > row['sma50']
                rsi = row['rsi']

                if is_uptrend and 30 <= rsi <= 50:
                    buy_signal = True

                # Exit: Trend Change
                if not is_uptrend and self.state == "IN":
                     sell_signal = True
                     current_stop_reason = "TREND CHANGE (<SMA50)"

            elif self.strategy_type == 'ema_5_13' or self.strategy_type == 'ema':
                ema5 = row['ema5']
                ema13 = row['ema13']
                prev_ema5 = prev_row['ema5']
                prev_ema13 = prev_row['ema13']

                # Buy: 5 crosses above 13
                if ema5 > ema13 and prev_ema5 <= prev_ema13:
                    buy_signal = True

                # Sell: 5 crosses below 13
                if self.state == "IN" and ema5 < ema13:
                    sell_signal = True
                    current_stop_reason = "CROSS UNDER (5<13)"

            elif self.strategy_type == 'darvas':
                # Darvas Box Breakout
                high_20d = row['high_20']
                if price > high_20d:
                    buy_signal = True

                # Exit
                if self.state == "IN" and price < row['low_20']:
                    sell_signal = True
                    current_stop_reason = "BOX LOW BREAK"

            elif self.strategy_type == 'mms_ote' or self.strategy_type == 'mms':
                # RSI < 40 (Oversold/Retracement)
                if price > row['sma50'] and row['rsi'] < 40:
                    buy_signal = True

            elif self.strategy_type == 'bull_put':
                if price > row['sma50'] and row['rsi'] < 55 and row['rsi'] > 40:
                    buy_signal = True

            elif self.strategy_type == 'fourier' or self.strategy_type == 'hybrid':
                # Hybrid: Trend (SMA200) + Cycle Low (Proxy RSI < 30)
                is_trend = price > row['sma200']
                is_cycle_low = row['rsi'] < 30 # Proxy

                if self.strategy_type == 'hybrid':
                     if is_trend and is_cycle_low: buy_signal = True
                else:
                     if is_cycle_low: buy_signal = True

                # Exit: Cycle High (RSI > 70)
                if self.state == "IN" and row['rsi'] > 70:
                     sell_signal = True
                     current_stop_reason = "CYCLE HIGH"

            elif self.strategy_type == 'fortress':
                if price > row['sma200'] and regime != "RED":
                     if row['rsi'] < 40: buy_signal = True

            elif self.strategy_type == 'quantum':
                if price > row['sma50'] and row['rsi'] > 50: buy_signal = True


            # ==============================
            # EXECUTION
            # ==============================

            if self.state == "OUT" and buy_signal:
                self.shares = int(self.equity / price)
                self.equity -= (self.shares * price)
                self.state = "IN"
                self.entry_date = date

                # Set Initial Stop based on Strategy
                atr = row['atr']
                if self.strategy_type in ['grandmaster', 'council', 'master', 'isa', 'hybrid', 'master_convergence']:
                    stop_loss = price - (2.5 * atr)
                    target_price = price + (6 * atr) # ISA Target
                elif self.strategy_type == 'market':
                    stop_loss = price - (2 * atr)
                    target_price = price + (4 * atr)
                elif self.strategy_type == 'ema_5_13':
                    stop_loss = row['ema21'] * 0.99
                    target_price = price * 1.2 # Open
                elif self.strategy_type == 'darvas':
                    stop_loss = row['low_20']
                    target_price = price * 1.25
                elif self.strategy_type == 'fourier':
                    stop_loss = price - (2 * atr)
                    target_price = price + (2 * atr)
                else:
                    stop_loss = price - (2 * atr)
                    target_price = price + (4 * atr)

                self.trade_log.append({
                    "date": date.strftime('%Y-%m-%d'), "type": "BUY",
                    "price": round(price, 2), "stop": round(stop_loss, 2),
                    "days": "-"
                })

            elif self.state == "IN":
                # Check Hard Stop / Target
                hit_stop = price < stop_loss
                hit_target = (target_price > 0) and (price > target_price)

                if hit_stop:
                     sell_signal = True
                     current_stop_reason = "INITIAL STOP HIT"
                elif hit_target and self.strategy_type not in ['grandmaster', 'isa', 'turtle']:
                     # Trend followers (ISA/Turtle/Grandmaster) don't use fixed targets usually, they trail.
                     if self.strategy_type in ['market', 'fourier']:
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

        return {
            "ticker": self.ticker,
            "strategy": self.strategy_type.upper(),
            "start_date": actual_start_str,
            "end_date": actual_end_str,
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bnh_return_equity, 2), # Portfolio based comparison
            "buy_hold_return_pct": round(simple_bnh_return, 2), # Raw stock return
            "buy_hold_days": buy_hold_days,
            "avg_days_held": avg_days_held,
            "total_days_held": total_days_held,
            "trades": len(self.trade_log) // 2,
            "win_rate": self._calculate_win_rate(),
            "final_equity": round(current_equity_val, 2),
            "log": self.trade_log
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
