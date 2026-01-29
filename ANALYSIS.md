# Project Analysis: Quantitative Systems Trading Platform

## Current Architecture
- **Backend**: Flask-based API (`webapp/`) with a robust strategy engine (`option_auditor/`). Good test coverage and modular design (Blueprints, Strategy Facade).
- **Frontend**: React/Vite application (`frontend/`). Currently in early stages, communicating via proxy.
- **Data**: Relying on `yfinance` with a file-based caching mechanism.

## Feature Analysis: Systems Trading Requirements

The following analysis categorizes features into "Mandatory" (Essentials for a functioning trading business) and "Cool" (Value-add differentiators), prioritized by their impact on PnL and Risk Management.

### 🟥 Mandatory Features (The Core)

#### 1. Real-Time Portfolio Risk & Greeks (Critical)
*   **Description**: A live dashboard showing aggregated Delta, Gamma, Theta, and Vega across the entire portfolio, along with Beta-Weighted Deltas against SPY.
*   **Value**: **Survival**. Allows the trader to instantly see if they are over-leveraged or too directional before a market move hurts them.
*   **Gap**: Currently, the system analyzes singular strategies but lacks a holistic portfolio view.

#### 2. Position Sizing Calculator (High Priority)
*   **Description**: An automated tool that calculates the exact share/contract size based on account equity, risk tolerance (e.g., 1% risk per trade), and stop-loss level (ATR based).
*   **Value**: **Consistency**. Prevents emotional sizing and ensures mathematical expectancy plays out over the long run.
*   **Gap**: `IsaStrategy` has basic logic, but a global, interactive calculator is missing in the UI.

#### 3. Execution Bridge / Broker Integration (High Priority)
*   **Description**: Direct API integration (IBKR/Tastytrade) to execute orders directly from the Screener/Backtester.
*   **Value**: **Efficiency**. Eliminates manual entry errors and slippage. Enables true "Systematic" trading.
*   **Gap**: No execution capability exists; the platform is currently read-only (Audit/Screen).

#### 4. Trade Journal & Performance Metrics (Medium Priority)
*   **Description**: Automated logging of trades with tagging (Strategy, Mistake, Setup). Computation of Expectancy, Sharpe Ratio, Profit Factor, and Win Rate.
*   **Value**: **Improvement**. You cannot improve what you do not measure. Essential for feedback loops.
*   **Gap**: Basic manual entry exists, but lacks automated metrics and visual analytics.

---

### 🟦 Cool Features (The Edge)

#### 1. Monte Carlo Simulation Sandbox (High Value)
*   **Description**: A tool to take a backtest result and simulate 10,000 variations with randomized trade ordering and slippage/noise.
*   **Value**: **Robustness**. Validates if a strategy's edge is real or just lucky. Helps set realistic drawdown expectations.
*   **Gap**: Backtester exists, but simulation capabilities are absent.

#### 2. AI & Sentiment Integration (Medium Value)
*   **Description**: NLP analysis of news headlines and social sentiment (Twitter/StockTwits) to act as a regime filter (e.g., "Don't buy calls if Sentiment < 20").
*   **Value**: **Regime Awareness**. Adds a qualitative data point to quantitative models.
*   **Gap**: Completely missing.

#### 3. Correlation Matrix Heatmap (Medium Value - ✅ Implemented)
*   **Description**: Visual grid showing pairwise correlations of all watchlist/portfolio assets.
*   **Value**: **Diversification**. Ensures you aren't actually betting on the same factor 10 times (e.g., owning AAPL, MSFT, and QQQ).
*   **Gap**: Backend logic implemented; Frontend visualization pending.

#### 4. Automatic Chart Pattern Recognition (Low Priority)
*   **Description**: Computer Vision or Algorithmic detection of Wedges, Flags, and Head & Shoulders.
*   **Value**: **Confluence**. Can be used to confirm statistical signals (e.g., RSI Divergence + Bull Flag).
*   **Gap**: Missing.
