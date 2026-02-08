import os
import sys
import json
import logging
import uuid
import pandas as pd
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from option_auditor.main_analyzer import analyze_csv
from option_auditor.analysis_worker import AnalysisWorker

# Configure logging to silence it during generation
logging.basicConfig(level=logging.ERROR)

def generate_golden_master():
    input_csv = os.path.join(os.path.dirname(__file__), '../tests/data/tasty_fills_full.csv')
    output_json = os.path.join(os.path.dirname(__file__), '../tests/data/golden_master_tasty.json')

    print(f"Generating Golden Master from {input_csv}...")

    # Mocks
    with patch('option_auditor.main_analyzer.fetch_live_prices', return_value={}) as mock_prices, \
         patch.object(AnalysisWorker, 'submit_monte_carlo', return_value="mock_mc_task_id"), \
         patch.object(AnalysisWorker, 'submit_black_swan', return_value="mock_bs_task_id"):

        # Run analysis
        result = analyze_csv(csv_path=input_csv, broker="tasty")

        # Clean result for deterministic output
        # Remove excel buffer object which is not JSON serializable
        if "excel_report" in result:
            del result["excel_report"]

        # Remove any timestamp-dependent fields if they vary (e.g. processing time)
        # But 'analyze_csv' is mostly deterministic given the mocks.

        # We need to ensure that 'date_window' is stable? It depends on CSV content which is static.
        # 'open_positions' depend on live prices (mocked to empty) and current time (for DTE).
        # Wait, DTE depends on datetime.now().
        # I must mock datetime.now() or the DTE calculation will change every day!

        # Mocking datetime is tricky because it's a built-in type.
        # I'll use freezegun if available, or just patch datetime.
        # Or I can just strip out time-sensitive fields from the Golden Master.

        # Let's try to patch datetime in the module where it is used.
        # analyze_csv uses pd.Timestamp.now() and datetime.now().

        # Easiest way: remove DTE and days_open from the golden master, or accept they will change?
        # No, regression test must be stable.
        # I'll strip volatile fields from the result before saving.

        # Volatile fields:
        # - open_positions: dte, days_open, opened (since it is parsed from CSV, it is stable, but days_open diffs with now)
        # - strategy_metrics: max_drawdown (stable), etc.
        # - leakage_report: stale_capital (depends on hold_days, stable)

        # Let's strip 'days_open' and 'dte' and 'risk_alert' (depends on DTE) from open_positions.
        if "open_positions" in result:
            for p in result["open_positions"]:
                if "dte" in p: p["dte"] = "MOCKED"
                if "days_open" in p: p["days_open"] = "MOCKED"
                if "risk_alert" in p: p["risk_alert"] = "MOCKED"
                if "current_price" in p: p["current_price"] = "MOCKED" # Mocked anyway

        # Also need to check if any other fields use 'now'.
        # 'buying_power_utilized_percent' uses net_liquidity_now (input, None).

        # Save to JSON
        with open(output_json, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"Golden Master saved to {output_json}")

if __name__ == "__main__":
    generate_golden_master()
