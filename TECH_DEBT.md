# Technical Debt Log

## 13. Slow Test Suite
- **Issue**: The full test suite takes a long time to run or times out.
- **Priority**: High
- **Status**: Open.

## 16. Stale Code / Potential Dead Code
- **Issue**: `option_auditor/strategies/grandmaster_screener.py` exists alongside `option_auditor/strategies/master.py`.
- **Priority**: Low
- **Status**: Open.

## Resolved Items
- **Environment Configuration Issues**: Fixed `pytest.ini`.
- **Monolithic Controller**: Refactored `webapp/app.py`.
- **Global State Usage**: Moved `screener_cache`.
- **Code Duplication in Ticker Resolution**: Centralized in `screener_utils.py`.
- **Hardcoded Configuration**: Addressed.
- **Hardcoded Financial Constants**: Addressed.
- **Duplicate Utility Functions**: Addressed.
- **God Object / Complex Logic in screener.py**: Extracted.
- **Missing/Incomplete Unit Tests**: Added unit tests for new strategy modules.
- **Low-Level Math Mixed with Business Logic**: Moved to `math_utils.py`.
- **Inconsistent Error Handling**: Addressed via decorator.
- **God Object in Unified Backtester**: Refactored.
- **Test Suite Fragmentation (Initial Pass)**: Consolidated `test_screener_coverage.py`.
- **Duplicate Ticker Resolution in `screener_routes.py`**: Refactored.
- **Inconsistent/Conditional Imports**: Addressed.
- **God Object in `webapp/blueprints/screener_routes.py`**: Extracted.
- **Hardcoded Market Regime Logic**: Addressed.
- **Screener Boilerplate**: Implemented `run_screening_strategy`.
- **Inconsistent Strategy Invocation**: Standardized.
- **Unused Imports in `screener.py`**: Removed.
- **Broken Tests due to Refactoring (Initial)**: Fixed initial batch.
- **Stale Documentation**: Updated `SCANNERS.md`.
- **God Object in `master_screener.py`**: Deleted.
- **Mixed Logic in Unified Screener**: Refactored.
- **Unused/Stale Code (PortfolioOptimizer)**: Deleted.
- **God Object (QuantPhysicsEngine)**: Dismantled.
- **Test Suite Fragmentation / Bloat**: Consolidate `_extended.py`, `_gap_fill.py`, `_fix.py` files into main test files. Deleted `tests/test_backtest_extended.py`, `tests/test_storage_extended.py`, `tests/test_webapp_gap_fill.py`. Renamed `tests/test_webapp_extended.py` to `tests/test_webapp_routes.py` and `tests/test_india_data_fetch_fix.py` to `tests/test_india_data.py`.
- **Broken Tests (Critical)**: Fixed `tests/test_endpoint_check_stock.py` (API patches), `tests/strategies/test_strategy_fourier.py` (Method patching), and `tests/test_india_data.py` (Mock logic).
- **Redundant Data Modules**: Unified `us_stock_data.py`, `uk_stock_data.py`, and `india_stock_data.py` to use a common `load_tickers_from_csv` utility in `option_auditor/common/file_utils.py`.
- **Failing Tests (API & Integration)**: Fixed 21 failing tests by correcting patch paths (targeting `webapp.blueprints` instead of `webapp.app`) and updating mock logic in `test_api_integration.py`, `test_api_master.py`, `test_region_strategies.py`, `test_cache_logic.py`, and `test_strategy_mms.py`.
