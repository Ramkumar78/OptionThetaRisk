# Technical Debt Log

## 13. Slow Test Suite
- **Issue**: The full test suite takes a long time to run (approx 5-6 mins) due to integration tests fetching data or heavy mocking.
- **Priority**: High
- **Status**: Open.

## 17. Deprecation Warnings
- **Issue**: `datetime.utcnow()` is deprecated (used in `openpyxl`). `yfinance` FutureWarnings regarding `auto_adjust` default change.
- **Priority**: Medium
- **Status**: Open.

## 19. Inconsistent Logging
- **Issue**: Some modules (e.g. `main_analyzer.py` previously) used `print` instead of `logging`. Potential remaining `print` statements in legacy code.
- **Priority**: Low
- **Status**: Open.

## 20. Unresolved Security Vulnerability
- **Issue**: `protobuf` version 6.33.4 has CVE-2026-0994. No fix version is currently available.
- **Priority**: High
- **Status**: Open (Waiting for vendor fix).

## 22. Test Suite Fragmentation
- **Issue**: The test suite contains many small, specific test files (e.g. `test_screener_*.py`) that should be consolidated into broader domain tests to reduce file clutter and improve maintainability.
- **Priority**: Medium
- **Status**: Open.

## 23. Stale Test Files
- **Issue**: Several test files were identified as stale or temporary artifacts (`test_coverage_improvements.py`, `test_missing_keys.py`) and have been removed. Future work should continue to audit for unused tests.
- **Priority**: Low
- **Status**: In Progress.
