import pytest
from option_auditor import risk_engine_pro

class TestSafetyLogic:
    def test_allocation_concentration_empty(self):
        assert risk_engine_pro.check_allocation_concentration([]) == []
        assert risk_engine_pro.check_allocation_concentration([{'ticker': 'A', 'value': 0}]) == []

    def test_allocation_concentration_violation(self):
        # Total = 1000. 5% = 50.
        positions = [
            {'ticker': 'SAFE', 'value': 40}, # 4%
            {'ticker': 'RISKY', 'value': 60}, # 6% - VIOLATION
            {'ticker': 'OTHER', 'value': 900}
        ]
        violations = risk_engine_pro.check_allocation_concentration(positions)
        assert len(violations) >= 1
        v = next((x for x in violations if x['ticker'] == 'RISKY'), None)
        assert v is not None
        assert v['percentage'] == 6.0

    def test_allocation_concentration_aggregation(self):
        # Split position: 3% + 3% = 6% -> Violation
        positions = [
            {'ticker': 'SPLIT', 'value': 30},
            {'ticker': 'SPLIT', 'value': 30},
            {'ticker': 'OTHER', 'value': 940}
        ]
        violations = risk_engine_pro.check_allocation_concentration(positions)
        # Both SPLIT (6%) and OTHER (94%) are violations (> 5%)
        assert len(violations) == 2

        split_violation = next((v for v in violations if v['ticker'] == 'SPLIT'), None)
        assert split_violation is not None
        assert split_violation['percentage'] == 6.0

    def test_retail_safety_score_perfect(self, mocker):
        # Mock portfolio_risk to return no warnings
        mocker.patch('option_auditor.portfolio_risk.analyze_portfolio_risk', return_value={})

        # 20 tickers with value 1 each = 5% each. (5.0 is not > 5.0).
        positions = [{'ticker': f'T{i}', 'value': 1} for i in range(20)]

        score = risk_engine_pro.calculate_retail_safety_score(positions)
        assert score['score'] == 100
        assert len(score['breakdown']) == 0

    def test_retail_safety_score_penalties(self, mocker):
        # Mock portfolio_risk
        mocker.patch('option_auditor.portfolio_risk.analyze_portfolio_risk', return_value={
            "sector_warnings": ["Too much Tech"],
            "high_correlation_pairs": [{"pair": "A+B", "verdict": "🔥 DUPLICATE RISK"}]
        })

        # 1 ticker = 100% concentration -> -5 points
        positions = [{'ticker': 'A', 'value': 100}]

        result = risk_engine_pro.calculate_retail_safety_score(positions)

        # Expected score:
        # Start: 100
        # Concentration: -5 (A is 100%)
        # Sector: -10
        # Correlation: -10
        # Total: 75
        assert result['score'] == 75
        assert any("Concentration penalty" in s for s in result['breakdown'])
        assert any("Sector penalty" in s for s in result['breakdown'])
        assert any("Correlation penalty" in s for s in result['breakdown'])

    def test_what_if_scenario_equity(self):
        positions = [{'ticker': 'A', 'value': 100}, {'ticker': 'B', 'value': 200}]
        # Total 300. Drop 10% -> 270. PnL -30.
        result = risk_engine_pro.calculate_what_if_scenario(positions, "market_drop_10")
        assert result['current_value'] == 300
        assert result['new_value'] == 270
        assert result['pnl'] == -30
        assert result['pnl_pct'] == -10.0

    def test_what_if_scenario_options(self, mocker):
        # Mock analyze_scenario
        mock_res = {"pnl": -500, "details": []}
        mocker.patch('option_auditor.portfolio_risk.analyze_scenario', return_value=mock_res)

        positions = [{'ticker': 'A', 'strike': 100, 'expiry': '2025-01-01', 'qty': 1, 'type': 'call'}]
        result = risk_engine_pro.calculate_what_if_scenario(positions)
        assert result == mock_res
