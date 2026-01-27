# Technical Debt Log

## 1. God Object / Complex Logic in `option_auditor/screener.py`
- **Issue**: The file is approx 1700 lines long and contains all screening logic, mixed levels of abstraction, and repetitive patterns.
- **Impact**: Extremely difficult to maintain, test, and extend. High risk of breaking existing functionality.
- **Priority**: High

## 2. Hardcoded Financial Constants
- **Issue**: Constants like `RISK_FREE_RATE = 0.045` are hardcoded inside multiple functions in `screener.py`.
- **Impact**: Changing these values requires modifying multiple code paths; inconsistency risk.
- **Priority**: Medium

## 5. Inconsistent Error Handling
- **Issue**: Many routes use generic `try...except Exception` blocks that just return 500 without specific error details or recovery mechanisms.
- **Impact**: Poor user experience and difficult debugging.
- **Priority**: Medium

## 6. Complex Functions (Specifics)
- **Issue**: `screen_vertical_put_spreads` and other individual screener functions are very long.
- **Impact**: Reduces readability and maintainability.
- **Priority**: Low

## 7. Dead/Commented Code
- **Issue**: There are commented-out imports and deprecated code blocks.
- **Impact**: Confuses developers and clutters the codebase.
- **Priority**: Low

## 8. Missing Tests
- **Issue**: Comprehensive tests for all screener functions are lacking.
- **Impact**: Increases risk of regression when refactoring.
- **Priority**: Medium

## Resolved Items
- **Monolithic Controller**: Refactored `webapp/app.py` to use Blueprints (`webapp/blueprints/`).
- **Global State Usage**: Moved `screener_cache` to `webapp/cache.py`.
- **Code Duplication in Ticker Resolution**: Addressed by centralizing logic in `option_auditor/common/screener_utils.py`.
- **Hardcoded Configuration**: Addressed by loading `DEFAULT_ACCOUNT_SIZE` from environment variables in `option_auditor/common/constants.py`.
