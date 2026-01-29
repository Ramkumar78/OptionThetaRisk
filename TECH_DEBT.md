# Technical Debt Log

## 13. Slow Test Suite
- **Issue**: The full test suite takes a long time to run (approx 5-6 mins) due to integration tests fetching data or heavy mocking.
- **Priority**: High
- **Status**: Open.

## 17. Deprecation Warnings
- **Issue**: `datetime.utcnow()` is deprecated (used in `openpyxl`). `yfinance` FutureWarnings regarding `auto_adjust` default change.
- **Priority**: Medium
- **Status**: Open.

## 18. Code Quality - Silent Failures
- **Issue**: Remaining `try-except-continue` blocks in data processing loops. While necessary for resilience, they can mask underlying logic errors. (Critical silent failures in logic were addressed).
- **Priority**: Low
- **Status**: Resolved (Silent blocks replaced with logging).

## 19. Inconsistent Logging
- **Issue**: Some modules (e.g. `main_analyzer.py` previously) used `print` instead of `logging`. Potential remaining `print` statements in legacy code.
- **Priority**: Low
- **Status**: Open.

## 20. Unresolved Security Vulnerability
- **Issue**: `protobuf` version 6.33.4 has CVE-2026-0994. No fix version is currently available.
- **Priority**: High
- **Status**: Open (Waiting for vendor fix).

## 21. Pandas FutureWarnings
- **Issue**: `pd.concat` sorting defaults are deprecated. Copy-on-Write mode is becoming default.
- **Priority**: Low
- **Status**: In Progress (Fixing test suite usage).
