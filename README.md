# Trade Auditor (The Option Auditor)

**The Automated Risk Manager & Strategy Screener for Stocks & Options**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](https://trade-auditor.onrender.com/)

Trade Auditor is a unified platform for tracking, analyzing, and auditing trading performance. It combines a powerful **Option/Stock Trade Journal** with **Advanced Risk Analysis** and **Automated Screeners**.

## 🚀 Live Demo
Experience the application here: [https://trade-auditor.onrender.com/](https://trade-auditor.onrender.com/)

## 🛠️ Key Technical Features
* **Monte Carlo Simulations**: Projects future equity curves based on your historical PnL distribution.
* **ITM Risk Detection**: Real-time alerts for unhedged Int-the-Money (ITM) exposure across spreads.
* **Quantum Screener**: Uses Hurst Exponents and Entropy to find non-random market trends.
* **Revenge Trade Detection**: Automatically flags trades opened within 30 minutes of a losing exit on the same symbol.

## 💡 Monetization & Support
If this tool has helped you manage your risk or find better setups, consider supporting the project:
* **GitHub Sponsors**: Support ongoing development.
* **Pro Audits**: (Coming Soon) Detailed PDF performance reports for prop-firm applications.

## 🛠️ Quick Start (Local)
```bash
git clone https://github.com/Ramkumar78/OptionThetaRisk.git
docker-compose up --build
```
Disclaimer: Educational use only. Trading involves significant risk. The "Win Rates" and "Probabilities" displayed are historical heuristics, not guarantees.
