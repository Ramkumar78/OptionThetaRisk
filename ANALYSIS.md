# Project Analysis: Quantitative Systems Trading Platform

## Current Architecture
- **Backend**: Flask-based API (`webapp/`) with a robust strategy engine (`option_auditor/`). Good test coverage and modular design (Blueprints, Strategy Facade).
- **Frontend**: React/Vite application (`frontend/`). Currently in early stages, communicating via proxy.
- **Data**: Relying on `yfinance` with a file-based caching mechanism.

## Gap Analysis: Missing "Cool & Mandatory" Features
To evolve this into a professional Systems Trading Platform, the following features are critical. They are ranked by Value/Priority.

### 1. Broker Integration & Execution (Mandatory / High Priority)
- **Why**: A screener is only as good as the execution. Manual entry causes slippage and missed opportunities.
- **Value**: Enables "One-Click" or fully automated trading, completing the loop from Signal to PnL.
- **Implementation**: Integration with IBKR (ib_insync) or Alpaca APIs.

### 2. Portfolio Risk Heatmap (Mandatory / High Priority)
- **Why**: Systems trading often involves holding multiple correlated positions. Managing aggregate risk (Delta, Theta, Beta-weighted exposure) is essential to survival.
- **Value**: Prevents "blowing up" due to unrecognized concentration risk.
- **Implementation**: A real-time dashboard aggregating all positions and calculating Portfolio VaR (Value at Risk) and Greeks.

### 3. Walk-Forward Optimization (Mandatory / High Priority)
- **Why**: Standard backtesting suffers from overfitting (look-ahead bias).
- **Value**: Ensures strategies are robust and adaptable to changing market regimes.
- **Implementation**: Extend `UnifiedBacktester` to support rolling training/testing windows.

### 4. Strategy Builder UI (Cool / Medium Priority)
- **Why**: Coding strategies in Python is powerful but creates friction for rapid idea testing.
- **Value**: "Drag-and-Drop" signal composition allows for faster experimentation and democratizes strategy creation.
- **Implementation**: A React Flow interface generating JSON strategy definitions executed by the backend.

### 5. Market Regime Classification Dashboard (Cool / Medium Priority)
- **Why**: Strategies that work in a Bull Market fail in a Choppy/Bear Market.
- **Value**: Provides context for signals, allowing the system to auto-disable incompatible strategies.
- **Implementation**: Visual gauge of the current regime (e.g., "Volatile Bear") based on VIX, ADX, and Sector Rotation.
