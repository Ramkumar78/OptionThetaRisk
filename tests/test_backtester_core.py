import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.backtest_engine import BacktestEngine
from option_auditor.backtest_reporter import BacktestReporter
from option_auditor.backtesting_strategies import AbstractBacktestStrategy

# --- Mock Strategy for Deterministic Testing ---

class MockStrategy(AbstractBacktestStrategy):
    """
    A strategy that buys/sells based on preset indices or conditions.
    """
    def __init__(self, strategy_type="mock"):
        super().__init__(strategy_type)
        self.buy_indices = set()
        self.sell_indices = set()
        self.forced_stop = None
        self.forced_target = None

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # No indicators needed for mock
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        return i in self.buy_indices

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        if i in self.sell_indices:
            return True, "MOCK SELL"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop = self.forced_stop if self.forced_stop else price * 0.9
        target = self.forced_target if self.forced_target else price * 1.1
        return stop, target

# --- Fixtures ---

@pytest.fixture
def sample_data():
    # We need enough data to satisfy rolling(200) and still have simulation data
    # Structure: 200 days warmup (flat), 100 days uptrend, 50 days downtrend
    end_date = pd.Timestamp.now()
    total_days = 400
    dates = pd.date_range(end=end_date, periods=total_days, freq="D")

    # 0-250: Flat/Warmup (to satisfy rolling 200 and give buffer)
    # 250-350: Uptrend (100 -> 150)
    # 350-400: Downtrend (150 -> 100)

    price_warmup = np.full(250, 100.0)
    price_up = np.linspace(100, 150, 100)
    price_down = np.linspace(150, 100, 50)

    price = np.concatenate([price_warmup, price_up, price_down])

    # Randomize slightly to avoid flat lines if needed, but linear is fine for mock

    data = {
        'Open': price,
        'High': price + 1,
        'Low': price - 1,
        'Close': price,
        'Volume': [100000] * total_days,
        'Spy': price,
        'Vix': [15] * total_days
    }
    df = pd.DataFrame(data, index=dates)
    return df

@pytest.fixture
def engine():
    # We patch get_strategy inside the test or inject the mock strategy manually
    # Since BacktestEngine calls get_strategy in __init__, we need to patch it.
    return BacktestEngine("mock", 10000.0)

# --- Tests ---

def test_pnl_simulation_loop_buy_sell(sample_data):
    """
    Test that a Buy followed by a Sell correctly updates equity.
    With 400pts total and ~200 dropped, sim starts around index 200.
    Uptrend starts at index 250 (sim index 50).
    Buy at sim index 60, Sell at sim index 80.
    """
    with pytest.MonkeyPatch.context() as mp:
        mock_strat = MockStrategy()
        mock_strat.buy_indices = {60}
        mock_strat.sell_indices = {80}

        # Patch get_strategy to return our mock
        mp.setattr("option_auditor.backtest_engine.get_strategy", lambda x: mock_strat)

        engine = BacktestEngine("mock", 10000.0)

        # Run
        result = engine.run(sample_data)

        trade_log = result['trade_log']
        assert len(trade_log) == 2 # Buy and Sell

        buy = trade_log[0]
        sell = trade_log[1]

        assert buy['type'] == 'BUY'
        assert sell['type'] == 'SELL'

        # Check PnL
        final_equity = result['final_equity']
        assert final_equity > 10000.0
        assert sell['equity'] > 10000.0

def test_pnl_stop_loss_trigger(sample_data):
    """
    Test that a Stop Loss triggers a sell.
    Use Downtrend region (starts sim index 150).
    Buy at 160. Price is falling.
    Stop will eventually be hit.
    """
    with pytest.MonkeyPatch.context() as mp:
        mock_strat = MockStrategy()
        mock_strat.buy_indices = {160}
        # Price at 160 is falling from 150.
        # Uptrend ends 150 -> 150. Downtrend 150 -> 100 over 50 steps.
        # Index 160 is 10 steps into downtrend. Price ~ 140.
        # Set stop at 135.
        mock_strat.forced_stop = 135.0

        mp.setattr("option_auditor.backtest_engine.get_strategy", lambda x: mock_strat)

        engine = BacktestEngine("mock", 10000.0)
        result = engine.run(sample_data)

        trade_log = result['trade_log']
        assert len(trade_log) == 2
        assert trade_log[1]['type'] == 'SELL'
        assert "STOP" in trade_log[1]['reason'] or "INITIAL STOP HIT" in trade_log[1]['reason']

def test_drawdown_calculation():
    """
    Test the Max Drawdown calculation logic in Reporter.
    """
    reporter = BacktestReporter()

    # 1. No Drawdown (Straight up)
    equity_up = [100, 105, 110, 115, 120]
    dd_up = reporter._calculate_max_drawdown(equity_up)
    assert dd_up == 0.0

    # 2. Simple Drawdown
    # 100 -> 120 (Peak) -> 100 (Drop 20) -> 110
    # Drawdown = (120 - 100) / 120 = 20 / 120 = 1/6 = 16.67%
    equity_dd = [100, 110, 120, 110, 100, 110]
    dd_val = reporter._calculate_max_drawdown(equity_dd)
    assert dd_val == 16.67

    # 3. Multiple Drawdowns, verify Max is taken
    # 100 -> 110 -> 99 (10%) -> 120 -> 90 (25%) -> 130
    equity_multi = [100, 110, 99, 120, 90, 130]
    # DD1: (110-99)/110 = 10%
    # DD2: (120-90)/120 = 30/120 = 25%
    dd_max = reporter._calculate_max_drawdown(equity_multi)
    assert dd_max == 25.0

def test_multiple_strategy_types_handling(sample_data):
    """
    Verify that the engine can initialize and run with different strategy strings.
    This ensures the factory and dispatch work.
    """
    strategies = ["isa", "turtle", "master"]

    for strat_name in strategies:
        engine = BacktestEngine(strat_name, 10000.0)
        # We don't need to assert logic, just that it runs without error
        result = engine.run(sample_data)
        assert "error" not in result
        assert "equity_curve" in result

def test_recovery_time_metric_calculation():
    """
    Test that BacktestReporter calculates max_drawdown_duration.

    Scenario:
    Day 0: 100 (Peak)
    Day 10: 90
    Day 20: 80 (Max DD point)
    Day 30: 95
    Day 40: 100 (Recovered)
    Duration: Day 0 to Day 40 = 40 days.

    Another DD:
    Day 50: 110 (New Peak)
    Day 60: 105
    Day 70: 110 (Recovered)
    Duration: 20 days.

    Max Duration should be 40.
    """
    reporter = BacktestReporter()

    base_date = datetime(2023, 1, 1)
    curve_data = []

    # Create the curve described above
    # Day 0 to 40
    points = [
        (0, 100.0),
        (10, 90.0),
        (20, 80.0),
        (30, 95.0),
        (40, 100.0), # Recovered
        (50, 110.0), # New Peak
        (60, 105.0),
        (70, 110.0)  # Recovered
    ]

    for day_offset, eq in points:
        d = base_date + timedelta(days=day_offset)
        curve_data.append({
            'date': d.strftime('%Y-%m-%d'),
            'strategy_equity': eq
        })

    engine_result = {
        'sim_data': pd.DataFrame(index=[base_date]),
        'trade_log': [],
        'equity_curve': curve_data,
        'final_equity': 110.0,
        'bnh_final_value': 100.0,
        'initial_price': 100.0,
        'final_price': 110.0,
        'buy_hold_days': 70
    }

    report = reporter.generate_report(engine_result, "TEST", "mock", 100.0)

    assert "max_drawdown_duration" in report
    assert report["max_drawdown_duration"] == 40
