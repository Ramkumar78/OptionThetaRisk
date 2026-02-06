import logging
from typing import List, Dict, Any
from option_auditor import portfolio_risk

logger = logging.getLogger(__name__)

def check_allocation_concentration(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Checks if any single ticker exceeds 5% of the total portfolio value.
    Input: List of dicts with 'ticker' and 'value'.
    Output: List of violations, e.g., [{'ticker': 'AAPL', 'percentage': 12.5}]
    """
    if not positions:
        return []

    total_value = sum(float(p.get('value', 0)) for p in positions)
    if total_value == 0:
        return []

    violations = []

    # Aggregate value by ticker first to handle multiple entries for same ticker
    ticker_values = {}
    for p in positions:
        t = p.get('ticker', 'UNKNOWN').upper()
        v = float(p.get('value', 0))
        ticker_values[t] = ticker_values.get(t, 0) + v

    for ticker, value in ticker_values.items():
        pct = (value / total_value) * 100
        if pct > 5.0:
            violations.append({
                "ticker": ticker,
                "percentage": round(pct, 2),
                "message": f"Allocation {pct:.1f}% exceeds 5% limit."
            })

    return violations

def calculate_retail_safety_score(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates a 'Retail Safety Score' (0-100).
    Penalties:
    - Concentration: -5 points for each ticker > 5%.
    - Sector Risk: -10 points for each sector warning (from portfolio_risk).
    - Correlation: -10 points for high correlation warnings (from portfolio_risk).
    """
    score = 100
    breakdown = []

    # 1. Concentration Check
    concentration_violations = check_allocation_concentration(positions)
    for violation in concentration_violations:
        penalty = 5
        score -= penalty
        breakdown.append(f"Concentration penalty: -{penalty} for {violation['ticker']} ({violation['percentage']}%)")

    # 2. Use existing portfolio risk analysis for Sector and Correlation
    # portfolio_risk.analyze_portfolio_risk handles sector and correlation logic
    try:
        risk_report = portfolio_risk.analyze_portfolio_risk(positions)
    except Exception as e:
        logger.error(f"Error calling analyze_portfolio_risk: {e}")
        risk_report = {}

    # Sector Warnings
    sector_warnings = risk_report.get("sector_warnings", [])
    for warning in sector_warnings:
        penalty = 10
        score -= penalty
        breakdown.append(f"Sector penalty: -{penalty} ({warning})")

    # Correlation / Diversification
    # analyze_portfolio_risk returns 'high_correlation_pairs'
    high_corr = risk_report.get("high_correlation_pairs", [])
    duplicate_risks = [p for p in high_corr if p.get('verdict') == "🔥 DUPLICATE RISK"]

    if duplicate_risks:
        penalty = 10 * len(duplicate_risks)
        score -= penalty
        breakdown.append(f"Correlation penalty: -{penalty} ({len(duplicate_risks)} high correlation pairs)")

    # Ensure score is 0-100
    score = max(0, min(100, score))

    return {
        "score": score,
        "breakdown": breakdown,
        "details": risk_report
    }

def calculate_what_if_scenario(positions: List[Dict[str, Any]], scenario_type: str = "market_drop_10") -> Dict[str, Any]:
    """
    Calculates impact of a market scenario.
    Default: FTSE 100 or S&P 500 drops 10% overnight.
    We simulate this by dropping all asset prices by 10%.
    """
    if scenario_type == "market_drop_10":
        scenario = {"price_change_pct": -10.0, "vol_change_pct": 0.0}
    else:
        # Default or handle other scenarios
        scenario = {"price_change_pct": -10.0, "vol_change_pct": 0.0}

    # Check if the input has option details (strike, type, expiry)
    # analyze_scenario requires these to price options.
    has_option_details = any('strike' in p and 'expiry' in p for p in positions)

    if has_option_details:
        return portfolio_risk.analyze_scenario(positions, scenario)
    else:
        # Simple equity simulation using 'value'
        total_val = sum(float(p.get('value', 0)) for p in positions)
        if total_val == 0:
            return {"current_value": 0, "new_value": 0, "pnl": 0, "pnl_pct": 0, "details": []}

        drop_pct = scenario["price_change_pct"] / 100.0
        new_val = total_val * (1 + drop_pct)
        pnl = new_val - total_val

        return {
            "current_value": total_val,
            "new_value": new_val,
            "pnl": pnl,
            "pnl_pct": scenario["price_change_pct"],
            "details": [{"ticker": "ALL", "pnl": pnl, "note": "Simplified equity shock applied to total value"}]
        }
