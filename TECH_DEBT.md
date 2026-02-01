# Technical Debt Log

## 17. Deprecation Warnings
- **Issue**: `datetime.utcnow()` is deprecated (used in `openpyxl`). `yfinance` FutureWarnings regarding `auto_adjust` default change.
- **Priority**: Medium
- **Status**: Open.

## 23. Stale Test Files
- **Issue**: Several test files were identified as stale or temporary artifacts (`test_coverage_improvements.py`, `test_missing_keys.py`) and have been removed. Future work should continue to audit for unused tests.
- **Priority**: Low
- **Status**: In Progress.
