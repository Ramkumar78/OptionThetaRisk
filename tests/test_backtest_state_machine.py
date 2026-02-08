import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.backtest_engine import BacktestEngine
from option_auditor.backtesting_strategies import AbstractBacktestStrategy

class MockBreakoutStrategy(AbstractBacktestStrategy):
    def __init__(self, strategy_type: str = "mock"):
        super().__init__(strategy_type)
        self.buy_signal_indices = []
        self.sell_signal_indices = []
        self.stop_loss_pct = 0.05
        self.target_pct = 0.10
        self.sell_reason = "MOCK SELL"

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Minimal indicators to satisfy potential dependencies
        df['sma50'] = df['Close'].rolling(50).mean()
        df['sma200'] = df['Close'].rolling(200).mean()
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        return i in self.buy_signal_indices

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        if i in self.sell_signal_indices:
            return True, self.sell_reason
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price * (1 - self.stop_loss_pct)
        target_price = price * (1 + self.target_pct)
        return stop_loss, target_price

class TestBacktestStateMachine(unittest.TestCase):
    def setUp(self):
        # Create recent synthetic data (last 250 days)
        # To avoid being filtered out by BacktestEngine and satisfy sma200
        dates = pd.date_range(end=pd.Timestamp.now(), periods=250, freq='D')
        prices = [100.0] * 250
        data = {
            'Open': prices,
            'High': [p + 1.0 for p in prices],
            'Low': [p - 1.0 for p in prices],
            'Close': prices,
            'Volume': [1000] * 250,
            'Spy': [400.0] * 250
        }
        self.df = pd.DataFrame(data, index=dates)

    @patch('option_auditor.backtest_engine.get_strategy')
    def test_state_machine_target_hit(self, mock_get_strategy):
        # Setup strategy
        strategy = MockBreakoutStrategy()
        mock_get_strategy.return_value = strategy

        # Modify price to hit target
        # Index 200: Buy (Breakout)
        # Index 210: Target Hit (Price > 110)

        # We need to set buy signal index.
        # Note: BacktestEngine iterates with 'i' from 0 to len(sim_data)
        # But it skips first 20 (warmup).
        # Also, calculate_indicators drops NaNs. rolling(200) will create 199 NaNs.
        # So sim_data will start from index 200 (approx).

        # Let's adjust data to be clean.
        # If we fillna(0) inside strategy or use smaller window, it's easier.
        # But MockBreakoutStrategy calculates sma200.
        # Let's use backfill for simplicity in strategy or just ensure enough data.

        # To make indices predictable, let's look at how BacktestEngine handles data.
        # 1. calculate_indicators -> drops NaNs.
        # 2. sim_data = df.dropna()
        # 3. loop i in range(len(sim_data))

        # If I have 250 rows, and sma200 consumes 199, I have ~51 rows left.
        # i=0 corresponds to original index 199.

        # Let's configure the price action on the TAIL of the dataframe.
        # Let's say entry at -10 (10 days from end), exit at -5.

        # Set buy signal
        # We need the integer index relative to sim_data.
        # Let's assume sim_data has N rows.
        # We'll invoke buy at index N-10.

        # Price manipulation:
        # At N-10: Close = 100. Buy triggered. Target = 110 (+10%).
        # At N-5: Close = 115. Target Hit.

        # Since we don't know N exactly easily without running logic,
        # let's just use specific dates or boolean column logic in strategy.
        # But MockBreakoutStrategy uses integer index 'i'.

        # Better approach:
        # Mock strategy logic: Buy if Close == 101.0
        # Sell if Close == 999 (unused here as we test target hit)

        # 1. Trigger Buy
        # self.df.iloc[-10, self.df.columns.get_loc('Close')] = 101.0
        # Wait, if I modify df, I need to re-assign it.

        # Let's rely on `should_buy` using index is tricky if we don't know the exact index.
        # Let's change MockStrategy to use Date or Price pattern.

        # Let's use Price pattern.
        # Buy when Price == 101.0

        # Setup Data
        # Default 100.
        idx_buy = 230 # absolute index
        self.df.iloc[idx_buy, self.df.columns.get_loc('Close')] = 101.0

        # Target Hit
        # Target is +10% => 111.1
        idx_target = 235
        self.df.iloc[idx_target, self.df.columns.get_loc('Close')] = 115.0
        self.df.iloc[idx_target, self.df.columns.get_loc('High')] = 116.0 # Ensure high covers it too

        # Update Strategy to buy at 101.0
        # We need to subclass or modify behavior dynamically.
        # Let's override should_buy in the test or make strategy smarter.

        strategy.should_buy = MagicMock(side_effect=lambda i, df, ctx: df.iloc[i]['Close'] == 101.0)

        engine = BacktestEngine("mock", 10000.0)
        results = engine.run(self.df)

        trade_log = results['trade_log']

        # Verification
        # 1. Buy happened
        self.assertTrue(len(trade_log) >= 1)
        buy_trade = next((t for t in trade_log if t['type'] == 'BUY'), None)
        self.assertIsNotNone(buy_trade)
        self.assertEqual(buy_trade['price'], 101.0)

        # 2. Sell happened (Target Hit)
        sell_trade = next((t for t in trade_log if t['type'] == 'SELL'), None)
        self.assertIsNotNone(sell_trade)
        self.assertEqual(sell_trade['reason'], 'TARGET HIT')
        self.assertTrue(sell_trade['price'] >= 115.0) # It closes at Close price of the day

        # 3. Equity increased
        # Initial: 10000. Buy ~99 shares at 101 (~9999 cost).
        # Sell 99 shares at 115 (~11385 proceeds).
        # Profit ~1386.
        self.assertGreater(results['final_equity'], 10000.0)

        # 4. Equity Curve
        self.assertTrue(len(results['equity_curve']) > 0)

    @patch('option_auditor.backtest_engine.get_strategy')
    def test_state_machine_stop_hit(self, mock_get_strategy):
        strategy = MockBreakoutStrategy()
        mock_get_strategy.return_value = strategy

        # Setup Data
        # Buy at 101.0
        idx_buy = 230
        self.df.iloc[idx_buy, self.df.columns.get_loc('Close')] = 101.0

        # Stop Hit
        # Stop is -5% => ~95.95
        idx_stop = 235
        self.df.iloc[idx_stop, self.df.columns.get_loc('Close')] = 90.0 # Way below stop

        strategy.should_buy = MagicMock(side_effect=lambda i, df, ctx: df.iloc[i]['Close'] == 101.0)

        engine = BacktestEngine("mock", 10000.0)
        results = engine.run(self.df)

        trade_log = results['trade_log']

        # Verification
        sell_trade = next((t for t in trade_log if t['type'] == 'SELL'), None)
        self.assertIsNotNone(sell_trade)
        self.assertEqual(sell_trade['reason'], 'INITIAL STOP HIT')
        self.assertEqual(sell_trade['price'], 90.0)

        self.assertLess(results['final_equity'], 10000.0)

    @patch('option_auditor.backtest_engine.get_strategy')
    def test_state_machine_strategy_exit(self, mock_get_strategy):
        strategy = MockBreakoutStrategy()
        mock_get_strategy.return_value = strategy

        # Setup Data
        idx_buy = 230
        self.df.iloc[idx_buy, self.df.columns.get_loc('Close')] = 101.0

        idx_exit = 235
        # Price moves up slightly but strategy signals exit
        self.df.iloc[idx_exit, self.df.columns.get_loc('Close')] = 102.0

        strategy.should_buy = MagicMock(side_effect=lambda i, df, ctx: df.iloc[i]['Close'] == 101.0)

        # Configure should_sell to return True at idx_exit
        # We need to know 'i' corresponding to idx_exit.
        # Since exact 'i' is hard to guess, let's use date or price check in side_effect.

        def mock_should_sell(i, df, ctx):
            if df.iloc[i]['Close'] == 102.0:
                return True, "STRATEGY EXIT"
            return False, ""

        strategy.should_sell = MagicMock(side_effect=mock_should_sell)

        engine = BacktestEngine("mock", 10000.0)
        results = engine.run(self.df)

        trade_log = results['trade_log']

        sell_trade = next((t for t in trade_log if t['type'] == 'SELL'), None)
        self.assertIsNotNone(sell_trade)
        self.assertEqual(sell_trade['reason'], 'STRATEGY EXIT')
        self.assertEqual(sell_trade['price'], 102.0)

if __name__ == '__main__':
    unittest.main()
