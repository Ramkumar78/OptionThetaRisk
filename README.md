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

#### Tastytrade Integration (Real-Time Data)
The application supports a **Hybrid Data Fetching Mode** that integrates with the Tastytrade API to pull real-time bid/ask prices from DXFeed for US markets, while falling back to Yahoo Finance for historical data and other regions.

**How to Use:**
1.  Navigate to the **Screener** tab in the web interface.
2.  Select the **Market Screener** (US Options Only) sub-tab.
3.  Toggle the **"Tasty Data"** switch to ON.
4.  Click the **Settings (Gear)** icon next to the toggle.
5.  Enter your Tastytrade credentials (Username/Password) in the modal and click Save.
6.  Run the screener. The application will use your session to fetch live execution prices for the "Close" column, ensuring you see the most accurate spread prices.

*Note: This feature is only active for the Market Screener tab. All other screeners (Turtle, EMA, etc.) and regions (UK/Euro, India) continue to utilize Yahoo Finance data exclusively.*

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
