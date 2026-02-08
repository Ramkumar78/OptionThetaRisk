import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.backtest_engine import BacktestEngine
from option_auditor.backtesting_strategies import AbstractBacktestStrategy

# --- Mock Strategy ---
class MockStrategy(AbstractBacktestStrategy):
    def __init__(self, strategy_type: str = "mock_strategy"):
        super().__init__(strategy_type)
        self.mock_indicators_df = None
        self.should_buy_result = False
        self.should_sell_result = (False, "")
        self.stop_loss = 90.0
        self.target_price = 110.0

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.mock_indicators_df is not None:
             return self.mock_indicators_df
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        return self.should_buy_result

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return self.should_sell_result

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        return self.stop_loss, self.target_price

# --- Fixtures ---
@pytest.fixture
def mock_strategy():
    """Patches get_strategy to return a MockStrategy instance."""
    with patch('option_auditor.backtest_engine.get_strategy') as mock_get:
        strategy_instance = MockStrategy()
        mock_get.return_value = strategy_instance
        yield strategy_instance

@pytest.fixture
def sample_df():
    """Creates a basic DataFrame for testing."""
    dates = pd.date_range(start="2023-01-01", periods=20, freq="D")
    df = pd.DataFrame({
        "Open": np.linspace(100, 110, 20),
        "High": np.linspace(105, 115, 20),
        "Low": np.linspace(95, 105, 20),
        "Close": np.linspace(102, 112, 20),
        "Volume": 1000
    }, index=dates)
    return df

# --- Tests ---

def test_calculate_indicators_logic(mock_strategy, sample_df):
    """
    Test indicator calculation logic:
    1. Spy column presence/absence.
    2. Data length checks for ATR.
    3. Strategy delegation.
    """
    engine = BacktestEngine("mock", 10000.0)

    # Case 1: Spy present, long enough data
    df_with_spy = sample_df.copy()
    df_with_spy['Spy'] = np.linspace(400, 410, 20)

    # Ensure add_indicators is called
    mock_strategy.add_indicators = MagicMock(side_effect=lambda x: x)

    # We need > 14 rows for ATR, sample_df has 20.
    result_df = engine.calculate_indicators(df_with_spy)

    assert 'spy_sma200' in result_df.columns
    # Verify ATR calculated
    assert 'atr' in result_df.columns
    mock_strategy.add_indicators.assert_called_once()

    # Case 2: Spy missing
    df_no_spy = sample_df.copy()
    result_df_no_spy = engine.calculate_indicators(df_no_spy)
    assert result_df_no_spy['spy_sma200'].iloc[0] == 0.0

    # Case 3: Short data (< 14)
    df_short = sample_df.iloc[:10].copy()
    result_df_short = engine.calculate_indicators(df_short)
    assert result_df_short['atr'].iloc[0] == 0.0

def test_run_date_slicing_logic(mock_strategy):
    """
    Test date slicing logic with mocked 'now'.
    Scenarios:
    1. Full 5Y (BACKTEST_DAYS=1825). Input > 5Y. Result ~5Y.
    2. Fallback to 3Y (1095 days). Input 3.5Y. Result ~3Y.
    3. Fallback to 2Y (730 days). Input 2.5Y. Result ~2Y.
    4. Fallback to Available. Input 1.5Y. Result 1.5Y.
    """
    # Fix "now" to a specific date for deterministic testing
    fixed_now = pd.Timestamp("2023-12-31")

    with patch('pandas.Timestamp.now', return_value=fixed_now):
        # Patch calculate_indicators to avoid data drop (which affects slicing logic checks)
        with patch.object(BacktestEngine, 'calculate_indicators', side_effect=lambda df: df):
            # Create engine
            engine = BacktestEngine("mock", 10000.0)

            # Helper to create DF of specific length
            def create_data(days_back):
                start = fixed_now - pd.Timedelta(days=days_back)
                # Ensure start date is handled correctly (inclusive/exclusive)
                # pd.date_range includes start.
                dates = pd.date_range(start=start, end=fixed_now, freq='D')
                df = pd.DataFrame({
                    "Open": 100, "High": 105, "Low": 95, "Close": 100, "Volume": 1000,
                    "Spy": 400  # Ensure indicators don't fail
                }, index=dates)
                return df

            # Scenario 1: Input 6Y (2190 days). Expect slicing to last 5Y (1825 days).
            # Note: BacktestEngine uses BACKTEST_DAYS from config, default 1825.
            df_6y = create_data(2190)
            res_1 = engine.run(df_6y)
            # Verify start date of sim_data is close to now - 1825
            expected_start_1 = fixed_now - pd.Timedelta(days=1825)
            # The slicing is df[df.index >= start_date]
            # So the first index should be >= expected_start_1
            assert res_1['sim_data'].index[0] >= expected_start_1
            # And it should not include older data (e.g. from 6y ago)
            # Check total duration roughly
            duration_days = (res_1['sim_data'].index[-1] - res_1['sim_data'].index[0]).days
            assert 1820 <= duration_days <= 1830 # Allow small buffer for exact day matching

            # Scenario 2: Input 3.5Y (1277 days). Expect slicing to last 3Y (1095 days).
            df_3_5y = create_data(1277)
            res_2 = engine.run(df_3_5y)
            expected_start_2 = fixed_now - pd.Timedelta(days=1095)
            assert res_2['sim_data'].index[0] >= expected_start_2
            duration_days_2 = (res_2['sim_data'].index[-1] - res_2['sim_data'].index[0]).days
            assert 1090 <= duration_days_2 <= 1100

            # Scenario 3: Input 2.5Y (912 days). Expect slicing to last 2Y (730 days).
            df_2_5y = create_data(912)
            res_3 = engine.run(df_2_5y)
            expected_start_3 = fixed_now - pd.Timedelta(days=730)
            assert res_3['sim_data'].index[0] >= expected_start_3
            duration_days_3 = (res_3['sim_data'].index[-1] - res_3['sim_data'].index[0]).days
            assert 725 <= duration_days_3 <= 735

            # Scenario 4: Input 1.5Y (547 days). Expect full usage (no slicing of start).
            df_1_5y = create_data(547)
            res_4 = engine.run(df_1_5y)
            # Should start from beginning of input
            assert res_4['sim_data'].index[0] == df_1_5y.index[0]
            duration_days_4 = (res_4['sim_data'].index[-1] - res_4['sim_data'].index[0]).days
            assert duration_days_4 == 547

def test_run_execution_loop(mock_strategy):
    """
    Test execution loop:
    1. Warmup skipping (first 20).
    2. Buy execution (OUT -> IN).
    3. Sell execution (IN -> OUT via signal).
    4. Stop Loss execution.
    """
    # Setup data
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "Open": 100.0, "High": 105.0, "Low": 95.0, "Close": 100.0, "Volume": 1000,
        "Spy": 400.0, "atr": 2.0
    }, index=dates)

    # Create engine
    engine = BacktestEngine("mock", 10000.0)

    # Scenario 1: Buy then Sell on Signal
    # We use side_effect to control signals based on index 'i'
    # Warmup is < 20. Loop starts at 0. Logic skips if i < 20.

    def buy_side_effect(i, df, context):
        if i == 30: return True
        return False

    def sell_side_effect(i, df, context):
        if i == 35: return True, "SIGNAL"
        return False, ""

    mock_strategy.should_buy = MagicMock(side_effect=buy_side_effect)
    mock_strategy.should_sell = MagicMock(side_effect=sell_side_effect)

    # Set stops/targets wide so they aren't hit
    mock_strategy.get_initial_stop_target = MagicMock(return_value=(50.0, 150.0))

    # Patch calculate_indicators to pass through
    with patch.object(BacktestEngine, 'calculate_indicators', side_effect=lambda df: df):
        # We patch Timestamp.now to be just after data end so date slicing logic (5y/3y/2y)
        # sees our data (starts 2023) as "recent" but doesn't slice it because it's < 2y old.
        # Data end ~ April 2023. Now = April 2023.
        # Start (Jan 2023) is > Now-2y (April 2021). So it uses all data.
        fixed_now_exec = pd.Timestamp("2023-04-15")
        with patch('pandas.Timestamp.now', return_value=fixed_now_exec):
            # Run
            res = engine.run(df.copy())

            log = res['trade_log']
            assert len(log) == 2 # Buy and Sell
            assert log[0]['type'] == 'BUY'
            assert log[0]['date'] == dates[30].strftime('%Y-%m-%d')
            assert log[1]['type'] == 'SELL'
            assert log[1]['date'] == dates[35].strftime('%Y-%m-%d')
            assert log[1]['reason'] == 'SIGNAL'

            # Verify warmup: Ensure no calls before i=20?
            # The loop: "if i < 20: continue".
            # So strategy methods shouldn't be called for i < 20.
            # Check call args of should_buy
            args_list = mock_strategy.should_buy.call_args_list
            indices_called = [args[0][0] for args in args_list]
            assert min(indices_called) >= 20

    # Scenario 2: Stop Loss Hit
    # Buy at 30. Stop at 90.
    # Price drops to 80 at day 40.

    # Need to reset mock
    mock_strategy.should_buy.reset_mock()
    mock_strategy.should_sell.reset_mock()
    mock_strategy.get_initial_stop_target.reset_mock()

    mock_strategy.should_buy.side_effect = lambda i, d, c: True if i == 30 else False
    mock_strategy.should_sell.side_effect = None
    mock_strategy.should_sell.return_value = (False, "")
    # Set stop at 90
    mock_strategy.get_initial_stop_target.return_value = (90.0, 150.0)

    df_stop = df.copy()
    # At i=40, price drops below 90
    df_stop.iloc[40, df_stop.columns.get_loc('Close')] = 80.0

    with patch.object(BacktestEngine, 'calculate_indicators', side_effect=lambda df: df):
        fixed_now_exec = pd.Timestamp("2023-04-15")
        with patch('pandas.Timestamp.now', return_value=fixed_now_exec):
            res_stop = engine.run(df_stop)
            log = res_stop['trade_log']
            assert len(log) == 2
            assert log[1]['type'] == 'SELL'
            assert log[1]['date'] == dates[40].strftime('%Y-%m-%d')
            assert log[1]['reason'] == 'INITIAL STOP HIT'

def test_run_equity_vs_buy_hold(mock_strategy):
    """
    Test Equity vs Buy & Hold calculations.
    Scenario: Price doubles from 100 to 200.
    1. Strategy Buys at start and Holds: Should match B&H.
    2. Strategy Never Buys: Equity = Initial, B&H = Double.
    """
    dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "Open": np.linspace(100, 200, 50),
        "High": np.linspace(105, 205, 50),
        "Low": np.linspace(95, 195, 50),
        "Close": np.linspace(100, 200, 50),
        "Volume": 1000,
        "Spy": 400.0, "atr": 2.0
    }, index=dates)

    engine = BacktestEngine("mock", 10000.0)

    # Case 1: Strategy Buys at index 20 (after warmup) and holds till end
    # Entry Price ~140 (at index 20, 100 + (20/49)*100 approx)
    # Actually linspace(100, 200, 50).
    # Index 0 = 100. Index 49 = 200. Step ~ 2.04 per day.
    # Index 20 price = 100 + 20 * (100/49) = 140.8.

    mock_strategy.should_buy = MagicMock(side_effect=lambda i, d, c: True if i == 20 else False)
    mock_strategy.should_sell = MagicMock(return_value=(False, ""))
    mock_strategy.get_initial_stop_target = MagicMock(return_value=(0.0, 99999.0)) # No stop/target

    with patch.object(BacktestEngine, 'calculate_indicators', side_effect=lambda df: df):
        fixed_now = pd.Timestamp("2023-04-01")
        with patch('pandas.Timestamp.now', return_value=fixed_now):
            res = engine.run(df.copy())

            # B&H: Starts at 100, Ends at 200. Should double.
            # Initial Capital 10000.
            # Shares = 10000 / 100 = 100.
            # Final Value = 100 * 200 = 20000.
            assert res['bnh_final_value'] == 20000.0

            # Strategy:
            # Enters at i=20 (Price ~140.8).
            # Equity before trade = 10000.
            # Shares = 10000 / 140.81 = 71.
            # Residue = 10000 - (71 * 140.81) = 1.84.
            # Final Price = 200.
            # Final Equity = 1.84 + (71 * 200) = 14201.84.

            # Verify Strategy made profit
            assert res['final_equity'] > 10000.0
            # Verify Logic: final_equity should match calculation
            # Use exact price from data, not rounded price from log
            entry_price = res['sim_data'].iloc[20]['Close']
            shares = int(10000.0 / entry_price)
            residue = 10000.0 - (shares * entry_price)
            expected_equity = residue + (shares * 200.0)
            assert res['final_equity'] == pytest.approx(expected_equity, abs=0.01)

    # Case 2: Strategy Never Buys
    mock_strategy.should_buy = MagicMock(return_value=False)

    with patch.object(BacktestEngine, 'calculate_indicators', side_effect=lambda df: df):
        with patch('pandas.Timestamp.now', return_value=fixed_now):
            res_2 = engine.run(df.copy())

            # B&H still doubles
            assert res_2['bnh_final_value'] == 20000.0

            # Strategy never entered -> Equity stays initial
            assert res_2['final_equity'] == 10000.0
            assert len(res_2['trade_log']) == 0
