### The Option Auditor — Options Audit Report

This is a lightweight CLI tool that ingests broker CSV exports (Tastytrade or Interactive Brokers),
groups options trades into round-trips (entry → exit), computes key metrics, and produces an
"Options Audit Report" with insights and risk flags.

#### Features
- **Multi-Broker Ingestion Engine:** Seamlessly processes CSV exports from major brokerage platforms, including Tastytrade and Interactive Brokers, with an intelligent auto-detection engine and manual override capabilities.
- **Heuristic-based Trade Reconstruction Engine:** Automatically clusters disparate execution legs into complex Option Strategies (Iron Condors, Verticals) using temporal locality algorithms.
- **Advanced Performance Analytics:** Delivers a comprehensive suite of per-trade and portfolio-level metrics, including PnL with fee attribution, duration analysis, and a proprietary Realized-Theta model (PnL per day held).
- **Risk Management & Compliance Module:** Employs a sophisticated "Over-leveraged" heuristic, benchmarked against a configurable account size, to flag high-risk trading behavior.
- **Multi-Format Reporting Suite:** Generates a variety of outputs, including an executive summary for the console, a detailed CSV for further analysis, and a presentation-ready Markdown report.

## 📊 Strategy & Screener Compendium

A curated collection of quantitative scanners designed to assist traders in identifying high-probability setups across various market conditions. This educational tool aims to highlight potential opportunities—from income generation to trend following—while emphasizing the importance of risk management.

### 🌟 The "Holy Grail" & Trend Strategies

| Strategy | Goal | Key Rules | Risk Management (Stop/Target) |
| :--- | :--- | :--- | :--- |
| **Hybrid (Trend + Cycle)**<br>_(The "Holy Grail")_ | **High Confidence**<br>Dip in Uptrend | **Trend:** Bullish (>200 SMA)<br>**Cycle:** Bottom Phase (Fourier)<br>**Signal:** "🚀 PERFECT BUY" | **Stop:** 3x ATR<br>**Target:** 2x ATR<br>_High R/R Setup_ |
| **ISA Trend Follower**<br>_(The "Legend")_ | **Long Term Wealth**<br>Set & Forget | **Trend:** Price > 200 SMA<br>**Entry:** Break 50-Day High<br>**Hold:** Above 20-Day Low | **Initial Stop:** 3x ATR<br>**Trailing Stop:** 20-Day Low<br>**Size:** Max 1% Equity Risk |
| **Turtle Trading** | **Trend Capture**<br>Big Moves | **Buy:** Break 20-Day High<br>**Short:** Break 20-Day Low | **Stop:** 2x ATR<br>**Target:** 4x ATR<br>**Trail:** 10-Day Low |

### ⚡ Momentum & Swing Strategies

| Strategy | Goal | Key Rules | Risk Management (Stop/Target) |
| :--- | :--- | :--- | :--- |
| **5/13 & 5/21 EMA** | **Momentum**<br>Crypto/Growth | **Breakout:** 5 EMA crosses 13/21 EMA<br>**Trend:** 5 > 13 > 21 | **Stop:** Close below Slow EMA (13 or 21)<br>**Signal:** "🚀 FRESH BREAKOUT" |
| **Darvas Box** | **Explosive Growth**<br>ATH Breakouts | **Setup:** Consolidating near 52w High<br>**Trigger:** Break "Box Ceiling" w/ Vol | **Stop:** Box Floor<br>**Target:** Breakout + Box Height |
| **Harmonic Cycles**<br>_(Fourier Analysis)_ | **Mean Reversion**<br>Swing Trading | **Math:** FFT Cycle Detection<br>**Buy:** Cycle Bottom (-1.0)<br>**Sell:** Cycle Top (+1.0) | **Timing Tool**<br>Use with Price Action |

### 🧠 Smart Money & Income Strategies

| Strategy | Goal | Key Rules | Risk Management (Stop/Target) |
| :--- | :--- | :--- | :--- |
| **MMS / OTE**<br>_(ICT Concepts)_ | **Precision Entry**<br>Day Trading | **Setup:** Liquidity Raid + Displacement<br>**Trigger:** Retrace to 62-79% Fib (OTE) | **Stop:** Recent Swing High/Low<br>**Target:** Opposing Liquidity |
| **Bull Put Spreads** | **Income**<br>Monthly Cashflow | **Trend:** Bullish (>50 SMA)<br>**Setup:** Sell 30 Delta Put (45 DTE)<br>**Hedge:** Buy Put $5 Lower | **Risk:** Width - Credit<br>**Exit:** 50% Profit or 21 DTE |
| **Market Screener**<br>_(Traffic Light)_ | **Market Overview**<br>Sector Rotation | **Bull:** RSI 30-50 in Uptrend ("🟢 GREEN")<br>**Bear:** RSI > 70 or Downtrend | **Exit:** RSI Overbought or Trend Break |

---

## 🚀 How to Use: The Workflow

This tool is designed to serve as an **Automated Risk Manager** and analysis companion. Below is a suggested workflow to utilize the screeners effectively, keeping in mind that markets are probabilistic.

1.  **Assess the Landscape (Market Screener):**
    *   Start here to gauge general market health.
    *   Look for **Sector Rotation**: Are Financials (XLF) green while Tech (XLK) is red?
    *   _Objective:_ Identify which way the wind is blowing.

2.  **Seek High-Quality Setups (The "Holy Grail"):**
    *   Navigate to the **Hybrid Screener**.
    *   Scan for **"🚀 PERFECT BUY"** signals. These rare setups occur when a long-term uptrend (ISA) aligns with a short-term cycle low (Fourier).
    *   _Discipline:_ If no signals appear, it may be prudent to wait.

3.  **Refine & Execute:**
    *   For precision, cross-reference with **MMS / OTE** to find an optimal entry point on a lower timeframe.
    *   Alternatively, use **Bull Put Spreads** to generate income on the bullish tickers identified.
    *   **Always** respect the mechanical stops and targets provided by the screener.

4.  **Audit & Review:**
    *   After trading, upload your logs to the **Audit** tab.
    *   Review your **PnL**, **Win Rate**, and check for behavioral risks like "Revenge Trading".

> **Disclaimer:** This software is for educational purposes only. Past performance does not guarantee future results.

#### Installation
Requires Python 3.9+.

```
pip install -r requirements.txt
```

#### CLI Usage
```
python -m option_auditor.cli --csv path/to/export.csv --broker auto --account-size 25000 --out-dir reports --report-format all
```

Key arguments:
- `--csv` (required): Path to broker CSV export.
- `--broker`: `auto` (default), `tasty`, or `ibkr`.
- `--account-size`: Optional numeric value in account currency. Enables leverage checks.
- `--out-dir`: Directory to write outputs. Default: `./out`.
- `--report-format`: `md`, `csv`, or `all` (default is `all`).

#### Notes / Assumptions
- This MVP focuses on options trades. Non-option rows are ignored.
- Realized Theta is approximated as `PnL / max(hold_days, 1/24)` (PnL per day, safeguarding very short holds).
- Grouping logic: per unique option contract (underlying + expiry + strike + right) aggregated by signed quantity; a trade closes when net position returns to zero.
- IBKR and Tastytrade exports vary by user settings; if auto-detection fails, use `--broker` to force a parser.

#### Example
```
python -m option_auditor.cli --csv sample_data/tasty_sample.csv --broker tasty --account-size 10000
```

Outputs:
- Console table with summary metrics and verdict.
- `out/trades.csv`: detailed grouped trades with metrics.
- `out/report.md`: markdown summary of the audit.

#### Web UI (Single Command Startup)
The application features a modern React frontend backed by a Flask API. To build and run everything in one go:

**Prerequisites:** Node.js (v18+), Python (3.9+)

```bash
./run.sh
```
This script will:
1. Install frontend dependencies and build the React app.
2. Install backend dependencies.
3. Start the Flask server.

Then open http://127.0.0.1:5000 in your browser.

#### Running with Docker
You can also run the web application using Docker, which automatically handles the frontend build and backend setup.

**Prerequisites:**
- Docker installed on your machine.
- (Optional) Docker Compose.

**Using Docker Compose (Recommended):**
1.  Run the application:
    ```bash
    docker-compose up --build
    ```
2.  Open http://127.0.0.1:5000 in your browser.

**Using Docker manually:**
1.  Build the image:
    ```bash
    docker build -t option-auditor .
    ```
2.  Run the container:
    ```bash
    docker run -p 5000:5000 option-auditor
    ```

**Persistence:**
The application uses a SQLite database in the `instance/` directory to store report metadata. To persist this data across container restarts, mount a volume to `/app/instance`. The `docker-compose.yml` file is pre-configured to do this.

#### Building an Executable
You can build a standalone executable for your operating system (Windows or macOS).

1.  Install the package with development dependencies (specifically `pyinstaller`):
    ```bash
    pip install -r requirements.txt
    pip install pyinstaller
    ```

2.  Run the build script:
    ```bash
    python build_executable.py
    ```

3.  The executable will be located in the `dist/` directory.
    -   **Windows**: `dist/OptionAuditor.exe`
    -   **macOS**: `dist/OptionAuditor`

*Note: You must build the executable on the target operating system (e.g., build on Windows to get a Windows .exe).*

What you can do:
- Upload your broker CSV (.csv only; default 5 MB limit).
- Choose broker (Auto/Tastytrade/IBKR) and optional account size.
- View portfolio metrics and verdict on the results page.
- Download generated `trades.csv` and `report.md` directly from the UI.

Security notes for web UI:
- Uploads are stored in a temporary directory and deleted right after processing.
- Only `.csv` files are allowed; a max upload size is enforced (configurable via `MAX_CONTENT_LENGTH`).
- A restrictive Content-Security-Policy is applied in templates.
- The core analyzer reads CSVs safely and output CSV is sanitized against spreadsheet formula injection.

#### Continuous Integration (CI)
This repo includes a GitHub Actions workflow at `.github/workflows/ci.yml` that runs tests on pushes and PRs
against Python 3.9–3.12. It installs dependencies from `requirements.txt` and executes `pytest -q`.

#### Security notes
- CSV uploads are read safely with Pandas and never executed as code.
- Exported `trades.csv` is sanitized to help prevent CSV/Excel formula injection: any cell beginning with `=`, `+`, `-`, or `@` is prefixed with a quote so that spreadsheet apps do not evaluate it as a formula.

#### Contact
shriram2222@gmail.com

#### Disclaimer
The Option Auditor is an educational tool designed to analyze past trading performance. It is not a financial advisor and does not provide investment recommendations.

**No Warranty:** The software is provided "as is." Calculations (including PnL, Theta, and Risk) are estimates based on heuristics and third-party data sources (yfinance) which may be inaccurate or delayed.

**Risk Warning:** Options trading involves high risk and you can lose more than your initial investment. Always consult a qualified financial professional before trading.
