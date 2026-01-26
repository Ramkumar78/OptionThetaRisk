# Trade Auditor (The Option Auditor)

**The Automated Risk Manager & Strategy Screener for UK & Global Traders**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](https://trade-auditor.onrender.com/)

Trade Auditor is a unified platform for tracking, analyzing, and auditing your trading performance. It combines a powerful **Automated Trade Journal** with **Advanced Risk Analysis** and specialized screeners for **UK ISA** and **Global Options** markets.

![Trade Auditor Banner](webapp/static/img/logo.png)

## 🚀 Key Features

### 🇬🇧 UK ISA Leader Screener
Find high-growth, ISA-eligible stocks using the **ISA Trend Follower** logic.
* **VCP Detection**: Identifies Volatility Contraction Patterns (Minervini style) where sellers are exhausted.
* **Relative Strength**: Filters for stocks outperforming the S&P 500 (RS > 0).
* **Dynamic Position Sizing**: Automatically calculates share counts based on a £1,250 risk limit per trade.

### 📊 Automated Journal & Behavioral Audit
Stop manual logging. Sync your closed trades directly to a high-performance journal.
* **Metric Automation**: Instantly view Win Rate, Profit Factor, and "Tharp" Expectancy.
* **Revenge Trade Detection**: Automatically flags "Revenge Trades" opened within 30 minutes of a losing exit on the same symbol.
* **Leakage Reporting**: Identifies "Fee Drag" and stale capital that is hurting your efficiency.

### 📉 Integrated Strategy Backtester
Verify your edge before risking capital. The built-in **Unified Backtester** allows you to run historical simulations of the core strategies.
* **Strategy Support**: Backtest ISA, Turtle, and Master Convergence strategies.
* **Ticker Analysis**: Run deep historical checks on specific tickers to see how they performed under different regimes.

### 🛡️ Option Risk Manager
* **ITM Risk Alerts**: Real-time monitoring of unhedged In-The-Money (ITM) exposure.
* **Monte Carlo Projections**: Projects future equity curves and "Risk of Ruin" based on your actual PnL distribution.
* **Broker Sync**: Seamlessly analyze CSV exports from **Tastytrade** and **IBKR**.

## 🎛️ Quick Start (Docker)

The easiest way to run Trade Auditor is with Docker Compose:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Ramkumar78/OptionThetaRisk.git
   cd OptionThetaRisk
   ```

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Access the App**:
   * Web Interface: http://localhost:5000

## ⚖️ License
Distributed under the Apache License 2.0. See LICENSE for more information.

Disclaimer: Educational use only. Trading stocks and options involves significant risk of loss. The "Win Rates" and "Probabilities" displayed are historical heuristics, not guarantees of future performance. Use at your own risk.
