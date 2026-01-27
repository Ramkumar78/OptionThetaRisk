# Technical Debt Log

## 1. Monolithic Controller
- **Issue**: `webapp/app.py` contains all route definitions in a single `create_app` function.
- **Impact**: Violates Single Responsibility Principle, making maintenance difficult.
- **Priority**: Medium

## 2. Global State Usage
- **Issue**: `screener_cache` is a global variable in `webapp/app.py`.
- **Impact**: Limits testability and scalability (e.g., in a multi-process environment).
- **Priority**: Medium

## 3. Inconsistent Error Handling
- **Issue**: Many routes use generic `try...except Exception` blocks that just return 500 without specific error details or recovery mechanisms.
- **Impact**: Poor user experience and difficult debugging.
- **Priority**: Medium

## 4. Complex Functions
- **Issue**: `screen_vertical_put_spreads` and other screener functions are very long and contain mixed levels of abstraction.
- **Impact**: Reduces readability and maintainability.
- **Priority**: Low

## 5. Dead/Commented Code
- **Issue**: There are commented-out imports and deprecated code blocks.
- **Impact**: Confuses developers and clutters the codebase.
- **Priority**: Low

## 6. Missing Tests
- **Issue**: Comprehensive tests for all screener functions are lacking.
- **Impact**: Increases risk of regression when refactoring.
- **Priority**: Medium

## Resolved Items
- **Code Duplication in Ticker Resolution**: Addressed by centralizing logic in `option_auditor/common/screener_utils.py`.
- **Hardcoded Configuration**: Addressed by loading `DEFAULT_ACCOUNT_SIZE` from environment variables in `option_auditor/common/constants.py`.
