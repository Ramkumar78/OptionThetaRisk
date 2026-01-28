# Technical Debt Log

## 1. God Object / Complex Logic in `option_auditor/screener.py`
- **Issue**: The file is approx 1700 lines long and contains all screening logic, mixed levels of abstraction, and repetitive patterns.
- **Specifics**: The following functions are still monolithic and need extraction:
    - `screen_market`
    - `screen_hybrid_strategy`
    - `screen_master_convergence`
    - `screen_quantum_setups`
    - `screen_alpha_101`
    - `screen_options_only_strategy`
    - `screen_mms_ote_setups`
    - `screen_my_strategy`
- **Impact**: Extremely difficult to maintain, test, and extend. High risk of breaking existing functionality.
- **Priority**: High
- **Status**: Partially Addressed.
    - `screen_turtle_setups`, `screen_trend_followers_isa`, `screen_vertical_put_spreads`, `screen_bull_put_spreads`, `screen_bollinger_squeeze`, `screen_rsi_divergence`, `screen_fourier_cycles`, `screen_liquidity_grabs`, and `screen_dynamic_volatility_fortress` have been refactored to `option_auditor/strategies/`.
    - **[NEW]** `screen_5_13_setups` refactored to `option_auditor/strategies/five_thirteen.py`.
    - **[NEW]** `screen_darvas_box` refactored to `option_auditor/strategies/darvas.py`.

## 2. Missing/Incomplete Unit Tests
- **Issue**: Comprehensive tests for all screener functions are lacking. Many strategies rely on "happy path" tests or implicit integration tests via `screener.py`.
- **Impact**: Increases risk of regression when refactoring. Hard to verify individual strategy logic.
- **Priority**: High
- **Status**: In Progress. Added direct unit tests for `FiveThirteenStrategy` and `DarvasBoxStrategy`.

## 3. Low-Level Math Mixed with Business Logic
- **Issue**: Mathematical functions like `_calculate_hilbert_phase`, `_calculate_dominant_cycle` are defined directly inside `screener.py`.
- **Impact**: Reduces readability and reusability. Harder to test math in isolation.
- **Priority**: Medium
- **Status**: Partially Addressed. `_identify_swings` and `_detect_fvgs` have been moved to `option_auditor/strategies/liquidity.py`. `_calculate_hilbert_phase` moved to `option_auditor/strategies/fourier.py`.

## 4. Inconsistent Error Handling
- **Issue**: Many routes in `webapp/blueprints/screener_routes.py` used generic `try...except Exception` blocks.
- **Impact**: Poor user experience and difficult debugging.
- **Priority**: Medium
- **Status**: Addressed via `handle_screener_errors` decorator in `webapp/blueprints/screener_routes.py`.

## 5. Complex Functions (Specifics)
- **Issue**: `screen_options_only_strategy` is very long and contains nested logic.
- **Impact**: Reduces readability and maintainability.
- **Priority**: Low

## 6. Dead/Commented Code
- **Issue**: There are commented-out imports and deprecated code blocks in `screener.py`.
- **Impact**: Confuses developers and clutters the codebase.
- **Priority**: Low

## Resolved Items
- **Monolithic Controller**: Refactored `webapp/app.py` to use Blueprints (`webapp/blueprints/`).
- **Global State Usage**: Moved `screener_cache` to `webapp/cache.py`.
- **Code Duplication in Ticker Resolution**: Addressed by centralizing logic in `option_auditor/common/screener_utils.py`.
- **Hardcoded Configuration**: Addressed by loading `DEFAULT_ACCOUNT_SIZE` from environment variables in `option_auditor/common/constants.py`.
- **Hardcoded Financial Constants**: Addressed by replacing hardcoded values in `screener.py` with imports from `common/constants.py`.
