import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.backtest_engine import BacktestEngine
from option_auditor.unified_backtester import UnifiedBacktester

# Helper to create synthetic market data
def create_synthetic_data(days=100, start_price=100.0, trend=0.1):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='B')
    df = pd.DataFrame(index=dates)

    # Create a simple trend with some noise
    np.random.seed(42)
    prices = [start_price]
    # Use actual length of dates to avoid mismatch
    for _ in range(len(dates) - 1):
        change = np.random.normal(0, 1.0) + trend
        prices.append(prices[-1] + change)

    df['Close'] = prices
    df['High'] = df['Close'] + 1.0
    df['Low'] = df['Close'] - 1.0
    df['Open'] = df['Close']
    df['Volume'] = 1000000

    # Required columns for some strategies/indicators
    df['Spy'] = df['Close'] # Mock SPY

    return df

@pytest.fixture
def synthetic_df():
    # Need enough data for rolling(200) to have valid values
    return create_synthetic_data(days=400, start_price=100, trend=0.2)

def test_slippage_impact(synthetic_df):
    """Verify that slippage reduces profitability."""
    # Baseline: No slippage
    engine_base = BacktestEngine("grandmaster", 10000)
    # Mock strategy to simply buy and hold or trade frequently
    # Grandmaster logic is complex, let's use a simpler one if available,
    # or just trust that grandmaster will trade on this trend.
    # Actually, let's just use the engine and see.
    # If Grandmaster doesn't trade, we won't see slippage.
    # We can use 'trend' strategy if it exists, or just force a trade by mocking strategy.

    # Let's mock the strategy to BUY on day 20 and SELL on day 30
    mock_strategy = MagicMock()
    mock_strategy.add_indicators.return_value = synthetic_df
    mock_strategy.should_buy.side_effect = lambda i, df, ctx: i == 30
    mock_strategy.should_sell.side_effect = lambda i, df, ctx: (True, "Test") if i == 40 else (False, None)
    mock_strategy.get_initial_stop_target.return_value = (0, 0) # No stop/target

    # Inject mock strategy
    with patch('option_auditor.backtest_engine.get_strategy', return_value=mock_strategy):
        # 1. Base Run (No Slippage)
        engine_base = BacktestEngine("mock", 10000)
        # We need to manually inject the mock strategy because get_strategy is called in __init__
        engine_base.strategy = mock_strategy
        res_base = engine_base.run(synthetic_df)

        # 2. Slippage Run (Fixed % 1%)
        engine_slip = BacktestEngine("mock", 10000, slippage_type="fixed_pct", slippage_value=0.01)
        engine_slip.strategy = mock_strategy
        res_slip = engine_slip.run(synthetic_df)

        # Verify
        trades_base = res_base['trade_log']
        trades_slip = res_slip['trade_log']

        assert len(trades_base) > 0, "Strategy should have traded"
        assert len(trades_slip) == len(trades_base)

        buy_base = trades_base[0]['price']
        buy_slip = trades_slip[0]['price']

        # Buy Price with slippage should be higher
        assert buy_slip > buy_base
        # Should be exactly 1% higher
        assert abs(buy_slip - (buy_base * 1.01)) < 0.01

        sell_base = trades_base[1]['price']
        sell_slip = trades_slip[1]['price']

        # Sell Price with slippage should be lower
        assert sell_slip < sell_base

        # Final Equity should be lower
        assert res_slip['final_equity'] < res_base['final_equity']

def test_market_impact(synthetic_df):
    """Verify larger positions get worse fills."""
    mock_strategy = MagicMock()
    mock_strategy.add_indicators.return_value = synthetic_df
    mock_strategy.should_buy.side_effect = lambda i, df, ctx: i == 30
    mock_strategy.should_sell.side_effect = lambda i, df, ctx: (True, "Test") if i == 40 else (False, None)
    mock_strategy.get_initial_stop_target.return_value = (0, 0)

    with patch('option_auditor.backtest_engine.get_strategy', return_value=mock_strategy):
        # Small Account (10k)
        # Impact factor 0.01 per share
        engine_small = BacktestEngine("mock", 10000, impact_factor=0.01)
        engine_small.strategy = mock_strategy
        res_small = engine_small.run(synthetic_df)

        # Large Account (1M) -> 100x shares -> 100x impact penalty per share
        engine_large = BacktestEngine("mock", 1000000, impact_factor=0.01)
        engine_large.strategy = mock_strategy
        res_large = engine_large.run(synthetic_df)

        buy_price_small = res_small['trade_log'][0]['price']
        buy_price_large = res_large['trade_log'][0]['price']

        # Large account should pay significantly more per share
        assert buy_price_large > buy_price_small

def test_margin_interest(synthetic_df):
    """Verify margin interest is deducted when leveraged."""
    mock_strategy = MagicMock()
    mock_strategy.add_indicators.return_value = synthetic_df
    # Buy at 30, Hold until 40 (10 days)
    mock_strategy.should_buy.side_effect = lambda i, df, ctx: i == 30
    mock_strategy.should_sell.side_effect = lambda i, df, ctx: (True, "Test") if i == 40 else (False, None)
    mock_strategy.get_initial_stop_target.return_value = (0, 0)

    with patch('option_auditor.backtest_engine.get_strategy', return_value=mock_strategy):
        # 1. No Leverage (Cash)
        engine_cash = BacktestEngine("mock", 10000, leverage_limit=1.0, margin_interest_rate=0.10)
        engine_cash.strategy = mock_strategy
        res_cash = engine_cash.run(synthetic_df)

        # 2. Leverage (2x)
        engine_lev = BacktestEngine("mock", 10000, leverage_limit=2.0, margin_interest_rate=0.10)
        engine_lev.strategy = mock_strategy
        res_lev = engine_lev.run(synthetic_df)

        # Cash account equity curve during holding period should be flat (ignoring price changes for a moment,
        # but actually equity changes with price).
        # However, the interest is deducted from equity explicitly.

        # Check equity drop due to interest
        # In the cash account, we buy 10k worth. Cash = 0. Interest = 0.
        # In the leveraged account, we buy 20k worth. Cash = -10k. Interest on 10k.

        # We can compare the *relative* performance or check if interest was deducted.
        # Let's check the logic: if equity < 0, interest deducted.
        # Wait, if I start with 10k and buy 20k stock, my Equity is still 10k (20k stock - 10k loan).
        # My logic in `run` was:
        # `if self.equity < 0: ... self.equity -= interest`
        # But `self.equity` variable in `BacktestEngine` tracks "Net Liquidation Value" (Cash + Positions) OR just "Cash"?

        # Let's review `BacktestEngine` code:
        # self.shares = ...
        # self.equity -= (self.shares * price)
        # This `self.equity` variable seems to represent CASH BALANCE in the loop logic!
        # Because when we sell: `self.equity += proceeds`.
        # So yes, `self.equity` is CASH.
        # Net Liquidation Value is calculated as `current_total_equity = self.equity + (self.shares * price)`.

        # So my logic `if self.equity < 0` (Cash < 0) checks if we are borrowing. Correct.

        # In Leverage case:
        # Cash starts 10k. Buy 20k. Cash becomes -10k.
        # Daily interest = 10k * (0.10 / 365) approx 2.73
        # Holding 10 days = approx 27.3

        # Compare final equity (assuming price didn't change much or changed same way)
        # Actually, price changes will amplify PnL in leverage case.
        # If price stays flat, leverage loses money due to interest.

        # Let's make price flat during holding period to isolate interest
        flat_prices = synthetic_df.copy()
        # Flatten prices in the simulation window (after dropna/warmup)
        # Assuming dropna removes first ~200 rows
        start_flat = 200
        flat_prices.iloc[start_flat:, flat_prices.columns.get_loc('Close')] = 100.0
        flat_prices.iloc[start_flat:, flat_prices.columns.get_loc('High')] = 101.0
        flat_prices.iloc[start_flat:, flat_prices.columns.get_loc('Low')] = 99.0

        engine_lev.strategy = mock_strategy # Re-inject
        res_lev_flat = engine_lev.run(flat_prices)

        engine_cash.strategy = mock_strategy
        res_cash_flat = engine_cash.run(flat_prices)

        # Debugging: Print trade logs to understand execution prices
        print("Cash Trades:", res_cash_flat['trade_log'])
        print("Lev Trades:", res_lev_flat['trade_log'])

        # Check if we paid interest
        # We can look at the equity curve during the holding period
        # Find index where we are holding (between buy and sell dates)

        # Get buy date and sell date from trade log
        if not res_lev_flat['trade_log']:
             pytest.fail("Leveraged strategy did not trade!")

        buy_date = res_lev_flat['trade_log'][0]['date']
        sell_date = res_lev_flat['trade_log'][1]['date']

        # Filter equity curve for this period
        curve = res_lev_flat['equity_curve']
        holding_period_equity = [
            e['strategy_equity'] for e in curve
            if e['date'] > buy_date and e['date'] < sell_date
        ]

        # In a flat market, leveraged equity should DECREASE daily due to interest
        # We need to ensure market was actually flat or account for it.
        # But even if not perfectly flat, we can compare with Cash account curve.

        curve_cash = res_cash_flat['equity_curve']
        holding_cash = [
            e['strategy_equity'] for e in curve_cash
            if e['date'] > buy_date and e['date'] < sell_date
        ]

        # Check delta difference
        # Delta_Lev = 2 * Delta_Price - Interest
        # Delta_Cash = Delta_Price
        # => Interest = 2 * Delta_Cash - Delta_Lev
        # Interest should be > 0

        assert len(holding_period_equity) > 0, "Holding period too short to test interest"

        for i in range(1, len(holding_period_equity)):
            delta_lev = holding_period_equity[i] - holding_period_equity[i-1]
            delta_cash = holding_cash[i] - holding_cash[i-1]

            # Since leverage is 2.0
            interest_paid = (2 * delta_cash) - delta_lev

            # Allow for some floating point noise, but should be positive
            # Interest on 10k loan is ~2.7 per day.
            assert interest_paid > 0.1, f"Interest not deducted correctly on day {i}. Int: {interest_paid}"

def test_monte_carlo_wrapper(synthetic_df):
    """Verify UnifiedBacktester runs Monte Carlo when requested."""

    # Mock engine run to return a trade log
    mock_result = {
        "trade_log": [
            {"type": "BUY", "price": 100, "date": "2023-01-01"},
            {"type": "SELL", "price": 110, "date": "2023-01-05", "days": 5, "reason": "Test"}, # 10% gain
            {"type": "BUY", "price": 110, "date": "2023-01-06"},
            {"type": "SELL", "price": 100, "date": "2023-01-10", "days": 4, "reason": "Test"}  # 9% loss
        ] * 10, # Need enough trades for MC
        "sim_data": synthetic_df,
        "equity_curve": [],
        "final_equity": 10000,
        "bnh_final_value": 10000,
        "initial_price": 100,
        "final_price": 100,
        "buy_hold_days": 100
    }

    with patch('option_auditor.unified_backtester.BacktestEngine') as MockEngine:
        instance = MockEngine.return_value
        instance.run.return_value = mock_result

        ub = UnifiedBacktester("TEST")
        # Mock fetch_data
        ub.fetch_data = MagicMock(return_value=synthetic_df)

        report = ub.run(monte_carlo=True)

        assert "monte_carlo" in report
        mc = report["monte_carlo"]
        assert "median_final_equity" in mc
        assert mc["simulations"] == 10000
