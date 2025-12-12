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

## Strategy Reference Guide

This application includes a suite of quantitative screeners designed to identify trading setups across different timeframes and styles.

### 1. Market Screener (The "Traffic Light")
*Best for: General Market Overview, Swing Trading*

- **Description:** A sector-based scanner that categorizes stocks by trend and momentum. It acts as a "Traffic Light" system for your watchlist.
- **Time Frames:** Daily (1D), Intraday (49m/98m), Weekly (1W).
- **Entry Strategy:**
  - **Trend:** Bullish if Price > SMA 50.
  - **Signal:** "🟢 GREEN LIGHT" (Buy Dip) triggers when a Bullish stock pulls back to an RSI between 30 and 50 (or user defined).
- **Exit Strategy:** Sell when RSI becomes Overbought (>70) or Price closes below SMA 50 (Trend Reversal).

### 2. Turtle Trading
*Best for: Trend Following, Catching big moves*

- **Description:** Based on the classic Richard Dennis "Turtle" rules.
- **Time Frames:** Daily (1D).
- **Entry Strategy:** Buy on a **20-Day Breakout** (Price > 20-Day High).
- **Exit Strategy:**
  - **Stop Loss:** 2 * ATR below entry price.
  - **Profit Target:** 4 * ATR above entry (2:1 Risk/Reward).
  - **Trailing Stop:** Exit if Price falls below the 10-Day Low.

### 3. EMA Momentum (5/13 & 5/21)
*Best for: Active Swing Trading, Crypto, High Momentum Stocks*

- **Description:** A fast-moving crossover strategy using Exponential Moving Averages (EMA).
- **Time Frames:** 1H, 4H, Daily.
- **Entry Strategy:**
  - **Fresh Breakout:** 5 EMA crosses above 13 EMA or 21 EMA.
  - **Trend:** 5 EMA > 21 EMA indicates a strong ongoing trend.
- **Exit Strategy:**
  - **Stop Loss:** Close below the "Slow" EMA (13 or 21).
  - **Signal:** "❌ DUMP" when 5 EMA crosses below the Slow EMA.

### 4. Darvas Box
*Best for: Explosive Growth Stocks*

- **Description:** Identifies stocks consolidating near 52-week highs that break out of a defined "Box" with volume.
- **Time Frames:** Daily (1D).
- **Entry Strategy:** Buy when Price breaks above the "Box Ceiling" (a confirmed resistance level) with above-average volume.
- **Exit Strategy:**
  - **Stop Loss:** "Box Floor" (Support level) or Ceiling - 2*ATR.
  - **Target:** Price Projection = Breakout Level + Box Height.

### 5. MMS / OTE (Smart Money Concepts)
*Best for: Day Trading, Precision Entries*

- **Description:** Implements ICT (Inner Circle Trader) concepts to find "Market Maker Models" and "Optimal Trade Entries" (OTE).
- **Time Frames:** Intraday (15m, 1H).
- **Entry Strategy:**
  - **Bullish:** Price raids a Liquidity Low -> Reverses with Displacement (FVG) -> Retraces to 62-79% Fibonacci Level.
  - **Bearish:** Price raids a Liquidity High -> Reverses with Displacement -> Retraces to 62-79% Fibonacci Level.
- **Exit Strategy:** Stop Loss at the recent Swing High/Low. Target the opposing liquidity pool.

### 6. Bull Put Spreads (Income)
*Best for: Generating Monthly Income (The Wheel / Spreads)*

- **Description:** Scans the Option Chain for high-probability credit spreads.
- **Time Frames:** N/A (Uses Option Chain).
- **Entry Strategy:**
  - **Trend:** Price > SMA 50 (Bullish).
  - **Setup:** Sell ~30 Delta Put, Buy Put $5 Lower.
  - **Expiration:** ~45 Days (DTE).
- **Exit Strategy:** Manage at 50% Profit or 21 DTE.

### 7. ISA Trend Follower
*Best for: Long-Term Investing (ISA/SIPP/401k)*

- **Description:** A "Set and Forget" style trend follower designed to keep you in major moves and out of bear markets.
- **Time Frames:** Weekly / Daily.
- **Entry Strategy:** Price > 200 SMA (Long Term Trend) AND Price breaks 50-Day High.
- **Exit Strategy:**
  - **Initial Stop:** 3 * ATR.
  - **Trailing Stop:** Exit if Price closes below the **20-Day Low**.

---

## How to use the US Option Screeners

The **Market Screener** is the primary tool for US Options traders.

1.  **Select Region:** Choose "US Options" (default) or "S&P 500".
2.  **Tastytrade Integration (Optional):**
    -   Toggle "Tasty Data" to **ON**.
    -   Enter your Tastytrade Refresh Token and Account ID (if prompted).
    -   *Benefit:* This bypasses Yahoo Finance delay and fetches **Real-Time Price** and **IV Rank** directly from the exchange.
3.  **Analyze Sectors:**
    -   Results are grouped by Sector (Technology, Financials, etc.).
    -   Look for "Green Light" signals in sectors that are performing well.
4.  **Workflow:**
    -   Identify a Bullish Stock (Green Light).
    -   Check IV Rank. If IV Rank > 50, consider selling Premium (Short Puts/Verticals). If IV Rank < 20, consider buying Spreads/Calls.

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
