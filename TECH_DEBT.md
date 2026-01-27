# Technical Debt Log

## 1. Code Duplication in Ticker Resolution
- **Issue**: The logic to resolve tickers based on region (`us`, `uk`, `india`, etc.) is repeated in almost every screener function in `option_auditor/screener.py` and partially in `webapp/app.py`.
- **Impact**: Makes it difficult to add new regions or update logic consistently.
- **Priority**: High

## 2. Hardcoded Configuration
- **Issue**: `account_size` (76000.0) is hardcoded in `webapp/app.py`.
- **Impact**: Limits flexibility for different account sizes without code changes.
- **Priority**: High

## 3. Monolithic Controller
- **Issue**: `webapp/app.py` contains all route definitions in a single `create_app` function.
- **Impact**: Violates Single Responsibility Principle, making maintenance difficult.
- **Priority**: Medium

## 4. Global State Usage
- **Issue**: `screener_cache` is a global variable in `webapp/app.py`.
- **Impact**: Limits testability and scalability (e.g., in a multi-process environment).
- **Priority**: Medium

## 5. Inconsistent Error Handling
- **Issue**: Many routes use generic `try...except Exception` blocks that just return 500 without specific error details or recovery mechanisms.
- **Impact**: Poor user experience and difficult debugging.
- **Priority**: Medium

## 6. Complex Functions
- **Issue**: `screen_vertical_put_spreads` and other screener functions are very long and contain mixed levels of abstraction.
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
