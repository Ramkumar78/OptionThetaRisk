# 📈 Trade Auditor: The Quest for Alpha

**Automated Risk Auditing, ISA Screening, and Strategy Backtesting.**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)![License](https://img.shields.io/badge/License-MIT-purple)
[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](https://trade-auditor.onrender.com/)
![CI/CD](https://img.shields.io/github/actions/workflow/status/Ramkumar78/OptionThetaRisk/ci.yml?label=CI%2FCD)
![Language](https://img.shields.io/badge/Language-Python%203.10%2B%20%7C%20TypeScript-blue)
![Coverage](https://img.shields.io/badge/Coverage-95%25-green)
![Code Style](https://img.shields.io/badge/Code%20Style-Black%20%7C%20ESLint-black)

Trade Auditor is built for traders and investors who aren't satisfied with market-average returns. It provides the technical "edge" required to audit performance, identify high-probability setups, and manage catastrophic risk.

## 🚀 "Beat The inflation" Toolkit

### 🇬🇧 UK ISA Trend Screener (`isa.py`)
Specifically tuned for the UK market, this screener identifies stocks transitioning from "Value" to "High-Growth" phases.
* **VCP Detection**: Uses Volatility Contraction Pattern logic to find institutional accumulation.
* **Relative Strength (RS)**: Automatically ranks stocks against the S&P 500 to ensure you are holding leaders, not laggards.
* **Institutional Verdicts**: Provides clear 'Buy', 'Watch', or 'Avoid' signals based on 50/150/200 EMA alignment.
* **Dynamic Position Sizing**: Automatically calculates optimal share count based on a £76k account (configurable) using 1% risk per trade and a 20% max allocation limit.

### 🧪 Integrated Strategy Backtester (`unified_backtester.py`)
Verify your edge before risking capital. Most traders fail because they don't know their historical expectancy.
* **Multi-Strategy Support**: Run backtests on **ISA Trend Following**, **Turtle Trading**, and **Master Convergence**.
* **PnL Simulation**: View drawdowns, recovery times, and win rates over years of historical data.

### 🛡️ The Behavioral Auditor (`journal_analyzer.py`)
The difference between a 5% return and a 15% return is often "Leakage."
* **Revenge Trade Detection**: Automatically flags trades opened within 30 minutes of a losing exit—the #1 killer of retail accounts.
* **Monte Carlo Projections**: Simulates 1,000+ versions of your future equity curve to calculate your **Probability of Ruin**.
* **Fee Audit**: Highlighting how much your broker is eating into your Alpha.

### 🔮 Advanced Screeners (SMC & Divergence)
Detects high-probability reversal setups using Institutional Logic.
*   **Liquidity Grab (SMC)**: Identifies Bullish/Bearish Sweeps where price breaches a swing point to "grab liquidity" before rejecting.
*   **RSI Divergence**: Finds trend exhaustion points where momentum (RSI) disagrees with price action.
*   **Bollinger Squeeze**: Identifies volatility compression (TTM Squeeze) for potential explosive breakouts.
*   **Backtesting Support**: Verify these strategies historically using the Unified Backtester.

👉 **[See SCANNERS.md for detailed documentation](SCANNERS.md)**

## 🛠️ Quick Start (Professional Setup)

The system is fully containerized. To run your own private instance:

```bash
git clone https://github.com/Ramkumar78/OptionThetaRisk.git
cd OptionThetaRisk
docker-compose up --build
```
Access the dashboard at http://localhost:5000.

## 📈 Roadmap & Contributions
We are currently working on integrating real-time LSE data for deeper UK market penetration.

Found a bug? Open an issue.

Have a strategy? See CONTRIBUTING.md to add your logic to the strategies/ directory.

If this tool helps you manage risk or find better setups, please ⭐ Star the repo to support development!

Disclaimer: For educational purposes only. Trading involves significant risk. Performance auditing is a tool for better decision-making, not a guarantee of future returns.
