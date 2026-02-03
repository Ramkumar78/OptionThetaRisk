# Technical Debt Log

## 23. Stale Test Files
- **Issue**: Several test files were identified as stale or temporary artifacts (`test_coverage_improvements.py`, `test_missing_keys.py`, `test_webapp_extra.py`, `test_check_route.py`, `test_storage_gap_fill.py`) and have been removed. Future work should continue to audit for unused tests.
- **Priority**: Low
- **Status**: In Progress.

## 24. Missing Equity Curve Visualization in Monte Carlo UI
- **Issue**: The Monte Carlo Sandbox UI currently displays only summary statistics. The roadmap envisioned "Visual Backtester UI" with "Equity Curves". The backend logic computes `final_equities` but does not expose the distribution or individual curves for plotting.
- **Priority**: Medium
- **Status**: Open.

## 25. Manual Frontend Verification
- **Issue**: Frontend changes are verified using temporary Playwright scripts (`verify_monte_carlo.py`). These scripts should be formalized into permanent integration tests within the repository to ensure continuous regression testing.
- **Priority**: Low
- **Status**: Open.
