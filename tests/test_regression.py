import os
import json
import pytest
from unittest.mock import patch, MagicMock
from option_auditor.main_analyzer import analyze_csv
from option_auditor.analysis_worker import AnalysisWorker

def test_regression_tasty_fills_pnl():
    """
    Regression test using Golden Master approach.
    Ensures that PnL calculations for a known set of trades (tasty_fills_full.csv)
    match the historically recorded output (golden_master_tasty.json).
    """
    input_csv = os.path.join(os.path.dirname(__file__), 'data/tasty_fills_full.csv')
    golden_master_json = os.path.join(os.path.dirname(__file__), 'data/golden_master_tasty.json')

    # Load Golden Master
    with open(golden_master_json, 'r') as f:
        expected_result = json.load(f)

    # Run Analysis with Mocks (same as generator script)
    with patch('option_auditor.main_analyzer.fetch_live_prices', return_value={}) as mock_prices, \
         patch.object(AnalysisWorker, 'submit_monte_carlo', return_value="mock_mc_task_id"), \
         patch.object(AnalysisWorker, 'submit_black_swan', return_value="mock_bs_task_id"):

        actual_result = analyze_csv(csv_path=input_csv, broker="tasty")

    # Clean actual result to match Golden Master format (strip volatile/binary fields)
    if "excel_report" in actual_result:
        del actual_result["excel_report"]

    # Strip volatile fields from open_positions in actual_result
    if "open_positions" in actual_result:
        for p in actual_result["open_positions"]:
            if "dte" in p: p["dte"] = "MOCKED"
            if "days_open" in p: p["days_open"] = "MOCKED"
            if "risk_alert" in p: p["risk_alert"] = "MOCKED"
            if "current_price" in p: p["current_price"] = "MOCKED"

    # Strip volatile fields from risk_map in actual_result
    if "risk_map" in actual_result:
        for r in actual_result["risk_map"]:
            if "dte" in r: r["dte"] = "MOCKED"
            if "risk_alert" in r: r["risk_alert"] = "MOCKED"
            # pnl_pct and size depend on price/qty which are consistent given mocks or input,
            # but if price is mocked to {}, pnl_pct might be 0.
            # In Golden Master, pnl_pct is 0.0.
            # So we don't strictly need to mask them if they are deterministic.
            # But let's verify if they are present in Golden Master.

    # Also mask risk_map in expected_result because we didn't mask it during generation!
    # The Golden Master has real values (0, "Expiring Today").
    # We must mask expected_result's risk_map too to match "MOCKED".
    if "risk_map" in expected_result:
        for r in expected_result["risk_map"]:
            if "dte" in r: r["dte"] = "MOCKED"
            if "risk_alert" in r: r["risk_alert"] = "MOCKED"

    # Compare Metrics
    # We compare specific keys to give better error messages
    keys_to_compare = [
        "metrics",
        "strategy_metrics",
        "leakage_report",
        "discipline_score",
        "discipline_details",
        "verdict",
        "verdict_details",
        "symbols",
        "strategy_groups",
        "risk_map", # Added
        # "open_positions", # Compared separately due to list order potential (though usually stable)
    ]

    for key in keys_to_compare:
        assert actual_result.get(key) == expected_result.get(key), f"Mismatch in {key}"

    # Compare Open Positions (carefully)
    # They should be in same order if sorting is deterministic.
    # We can check list length and then check each item.
    assert len(actual_result["open_positions"]) == len(expected_result["open_positions"])
    for i, (act, exp) in enumerate(zip(actual_result["open_positions"], expected_result["open_positions"])):
        # We already mocked the volatile fields in 'act'
        assert act == exp, f"Mismatch in open_positions index {i}"

    # Compare Monte Carlo status (should be deterministic given mocks)
    assert actual_result["monte_carlo"] == expected_result["monte_carlo"]
