import pytest
import pandas as pd
import numpy as np
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.risk_engine_pro import check_allocation_concentration
from option_auditor.risk_analyzer import calculate_kelly_criterion

# Helper to create mock market data
def create_mock_df(price=100.0, volatility=1.0, length=250):
    """
    Creates a DataFrame with constant price but controllable volatility (High-Low range)
    to influence ATR and thus Stop Loss distance.
    """
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length)
    # Ensure High/Low provide the desired range (volatility)
    # ATR is roughly average of (High - Low) if no gaps.
    half_range = volatility / 2.0

    data = {
        'Open': [price] * length,
        'High': [price + half_range] * length,
        'Low': [price - half_range] * length,
        'Close': [price] * length,
        'Volume': [10_000_000] * length # High enough to pass volume checks
    }
    df = pd.DataFrame(data, index=dates)
    return df

class TestIsaPositionSizing:
    """
    Tests the Position Sizing logic within the ISA Strategy.
    Default Account: £76,000
    Risk per Trade: 1% (£760)
    Max Allocation: 20% (£15,200)
    """

    def test_risk_limited_sizing(self):
        """
        Scenario 1: Risk determines position size.
        Stop Loss is wide enough that position value is < 20% allocation limit.
        """
        account_size = 76000
        risk_pct = 0.01

        # Target: Price 100, Stop Distance ~10 (Risk £10/share).
        # ISA uses 3 * ATR for stop. So we need ATR ~ 3.33.
        # Volatility (Range) should be ~3.33.
        price = 100.0
        volatility = 3.35 # Approx ATR

        df = create_mock_df(price=price, volatility=volatility)

        strategy = IsaStrategy(
            ticker="TEST.L",
            df=df,
            account_size=account_size,
            risk_per_trade_pct=risk_pct
        )

        result = strategy.analyze()

        assert result is not None, "Strategy analysis returned None"

        # Verify inputs
        # Stop Distance = 3 * ATR
        atr = result['atr_20']
        stop_dist = 3 * atr
        risk_per_share = result['risk_per_share']

        # Check math
        # Expected Risk Amount = £760
        # Expected Shares = 760 / risk_per_share
        expected_shares = int(760 / risk_per_share)

        # Check Allocation
        position_value = expected_shares * price
        max_allocation = account_size * 0.20 # 15,200

        # In this scenario, Value (approx 76 * 100 = 7600) < 15200.
        # So it should NOT be capped by allocation.

        assert position_value < max_allocation, "Test setup failed: Position value exceeds allocation limit"
        assert result['shares'] == expected_shares, \
            f"Share count mismatch. Expected {expected_shares}, Got {result['shares']}"
        assert result['risk_amount'] == 760.0

    def test_allocation_limited_sizing(self):
        """
        Scenario 2: Allocation cap determines position size.
        Stop Loss is tight, so Risk-based sizing would exceed 20% portfolio.
        """
        account_size = 76000
        risk_pct = 0.01

        # Target: Price 100.
        # We need Position Value > 15,200.
        # If Risk Based Shares > 152.
        # Risk Amount = 760.
        # Risk Per Share < 760 / 152 = 5.
        # Stop Distance < 5.
        # 3 * ATR < 5 => ATR < 1.66.

        price = 100.0
        volatility = 0.5 # Small range, ATR ~ 0.5. Stop Dist ~ 1.5.

        df = create_mock_df(price=price, volatility=volatility)

        strategy = IsaStrategy(
            ticker="TEST.L",
            df=df,
            account_size=account_size,
            risk_per_trade_pct=risk_pct
        )

        result = strategy.analyze()

        assert result is not None

        # Calculate expected caps
        max_allocation = account_size * 0.20 # 15,200
        max_shares_alloc = int(max_allocation / price) # 152

        # Calculate raw risk shares
        risk_per_share = result['risk_per_share'] # Should be around 1.5
        raw_shares = int(760 / risk_per_share) # Should be around 500

        assert raw_shares > max_shares_alloc, "Test setup failed: Raw shares should exceed allocation limit"

        # Result should be capped at max_shares_alloc
        assert result['shares'] == max_shares_alloc, \
            f"Allocation Cap Failed. Expected {max_shares_alloc}, Got {result['shares']}"

        # Verify 'max_position_size' string logic (optional but good)
        assert f"{max_shares_alloc} shares" in result['max_position_size']

    def test_variable_account_size(self):
        """
        Test with a different account size (e.g. £10,000)
        Risk £100. Allocation £2,000.
        """
        account_size = 10000
        risk_pct = 0.01
        price = 50.0
        volatility = 2.0 # ATR ~ 2. Stop ~ 6.

        df = create_mock_df(price=price, volatility=volatility)

        strategy = IsaStrategy(
            ticker="SMALL.L",
            df=df,
            account_size=account_size,
            risk_per_trade_pct=risk_pct
        )
        result = strategy.analyze()

        risk_amount = account_size * risk_pct # 100
        risk_per_share = result['risk_per_share'] # ~6
        expected_shares = int(risk_amount / risk_per_share) # ~16

        max_alloc = account_size * 0.20 # 2000
        val = expected_shares * price # 16 * 50 = 800

        assert val < max_alloc
        assert result['shares'] == expected_shares

class TestStandaloneRiskModules:
    """
    Tests for standalone risk functions in risk_engine_pro and risk_analyzer.
    """

    def test_kelly_criterion(self):
        # Case 1: Win Rate 50%, Profit Factor 2.0
        # Formula: Kelly = WR * (1 - 1/PF)
        # K = 0.5 * (1 - 0.5) = 0.25
        k1 = calculate_kelly_criterion(0.5, 2.0)
        assert k1 == 0.25, f"Kelly calc wrong. Got {k1}"

        # Case 2: Win Rate 40%, Profit Factor 3.0
        # K = 0.4 * (1 - 1/3) = 0.4 * 0.666... = 0.2666...
        k2 = calculate_kelly_criterion(0.4, 3.0)
        expected_k2 = 0.4 * (1.0 - 1.0/3.0)
        assert abs(k2 - expected_k2) < 1e-9

        # Case 3: Negative Edge (Zero Kelly)
        # Win Rate 30%, Payoff 1:1
        # Kelly = 0.3 - (0.7/1) = -0.4 -> Should be 0
        k3 = calculate_kelly_criterion(0.3, 1.0)
        assert k3 == 0.0

    def test_allocation_concentration(self):
        """
        Verifies the 5% concentration warning logic.
        """
        # Case 1: Safe Portfolio
        positions_safe = [
            {'ticker': 'A', 'value': 4000},
            {'ticker': 'B', 'value': 4000},
            {'ticker': 'C', 'value': 2000}
        ]
        # Total 10,000. Max 40%? Wait, function checks > 5%.
        # Wait, 4000/10000 = 40%. That IS > 5%.
        # The logic in `check_allocation_concentration` flags > 5%.
        # Let's check logic:
        # "Checks if any single ticker exceeds 5% of the total portfolio value."
        # If I want SAFE, I need < 5%.
        # So 21 positions of 4.76% each?

        # Let's just test that it flags correctly.
        violations = check_allocation_concentration(positions_safe)
        # Expect A and B and C to be violations (40%, 40%, 20%).
        tickers = [v['ticker'] for v in violations]
        assert 'A' in tickers
        assert 'B' in tickers
        assert 'C' in tickers # 20% > 5%

        # Case 2: Truly Safe (Very diversified)
        # 100 positions, each 1%.
        positions_diversified = [{'ticker': f"S{i}", 'value': 100} for i in range(100)]
        # Total 10,000. Each 1%.
        violations_safe = check_allocation_concentration(positions_diversified)
        assert len(violations_safe) == 0, "Should satisfy 5% limit"

        # Case 3: Mixed
        # Total 100,000. 5% = 5,000.
        positions_mixed = [
            {'ticker': 'BIG', 'value': 10000}, # 10% -> Violation
            {'ticker': 'SMALL', 'value': 1000} # 1% -> OK
        ]
        # Add buffer to make total correct for assertions if needed,
        # but function calculates total from inputs.
        # Total = 11,000.
        # BIG: 10/11 = 90%.
        # SMALL: 1/11 = 9%.
        # Both violations?
        # Yes.

        v_mixed = check_allocation_concentration(positions_mixed)
        assert len(v_mixed) == 2
