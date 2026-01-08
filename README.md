# Trade Auditor (The Option Auditor)

**The Automated Risk Manager for Stocks & Options**

Trade Auditor (formerly The Option Auditor) is a unified platform for tracking, analyzing, and auditing your trading performance. It combines a powerful **Option/Stock Trade Journal** with **Advanced Risk Analysis** and **Automated Screeners** (Trend, Reversion, Momentum, Income).

![Trade Auditor Banner](webapp/static/img/logo.png)

---

## 🚀 Key Features

*   **Portfolio Risk Analysis**: Analyze CSV exports from brokers (Tastytrade, IBKR) or manual inputs.
    *   **Risk Heatmap**: Visualize concentration risk by sector and symbol.
    *   **Monte Carlo Simulation**: Project future equity curves and risk of ruin.
    *   **"Tharp" Expectancy**: Calculate your mathematical edge.
*   **Unified Screener (The Fortress)**:
    *   **ISA Trend Follower**: Finds high-growth stocks in strong uptrends (Minervini/O'Neil style).
    *   **Turtle Trading**: Classic Donchian Channel breakouts.
    *   **Darvas Box**: Momentum breakouts from consolidated boxes.
    *   **Income Screeners**: Bull Put Spreads, Iron Condors (Market Screener).
    *   **Smart Money Concepts (MMS/OTE)**: Intraday setups for day traders.
*   **Journal & Review**:
    *   **Import Trades**: Sync closed trades from analysis directly to your journal.
    *   **Automated Metrics**: Win rate, Avg Win/Loss, Profit Factor.
    *   **Mistake Tracking**: Tag trades with psychological or execution errors.

---

## 🎛️ TRADING DASHBOARD LEGEND

### REGIME (The First Filter)

*   **🟢 BULLISH**: Aggressive buying in ISA allowed.
*   **🔴 BEARISH**: NO ISA BUYS. Cash position or Put Spreads only.

### SETUP TYPES

*   **🚀 ISA: VCP LEADER**: High Growth stock. Outperforming S&P 500 (RS > 0). Volatility has dried up (VCP), indicating sellers are exhausted. Buy signal.
*   **🛡️ OPT: BULL PUT**: For the $9.5k USD Account. Blue-chip stock in uptrend, but oversold (RSI < 40). Sell Puts below support. Income signal.

### METRICS

*   **RS Rating**: Relative Strength vs SPY. >0 means it is stronger than the market.
*   **Action**: Explicitly tells you how many shares/contracts to trade based on your risk limits (£1,250 risk per ISA trade).
*   **Vol Squeeze**: "YES" means the price action is tight (Minervini VCP). A breakout here is explosive.

---

## 🛠️ Quick Start (Docker)

The easiest way to run Trade Auditor is with Docker Compose.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Ramkumar78/OptionThetaRisk.git
    cd OptionThetaRisk
    ```

2.  **Run with Docker**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the App**:
    *   Web Interface: `http://localhost:5000`
    *   PgAdmin (Database): `http://localhost:5050`

---

## 💻 Local Development

If you want to contribute or run without Docker:

1.  **Backend (Flask)**:
    ```bash
    # Create venv
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows

    # Install deps
    pip install -r requirements.txt

    # Run App
    python -m webapp.app
    ```

2.  **Frontend (React)**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

3.  **Tests**:
    ```bash
    pytest
    ```

---

## ⚠️ Disclaimer

**Educational Use Only.** This software is for analysis and educational purposes. It is not financial advice. Trading options and stocks involves significant risk of loss. The "Win Rates" and "Probabilities" displayed are historical heuristics, not guarantees of future performance. Use at your own risk.
