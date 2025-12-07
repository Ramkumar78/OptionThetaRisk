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

#### Web UI (upload and view results)
A lightweight Flask app is included so you can upload a CSV from a webpage and view results directly.

How to run the web app (development):
```
pip install -r requirements.txt
python -m webapp.app
```
Then open http://127.0.0.1:5000 in your browser.

#### Running with Docker (SaaS Architecture)
The application is designed to run as a set of containers mirroring a production SaaS architecture. This setup includes:
- **Web**: The Flask web application.
- **Worker**: A Celery worker for processing large CSV uploads in the background.
- **Postgres**: A persistent database for user data, portfolios, and journal entries.
- **Redis**: A message broker for the task queue and result backend.

**Prerequisites:**
- Docker and Docker Compose installed on your machine.

**Steps:**
1.  Start all services:
    ```bash
    docker-compose up --build
    ```
2.  The application will be available at http://127.0.0.1:5000.
3.  To stop the services:
    ```bash
    docker-compose down
    ```

**Persistence:**
- Database data is persisted in a Docker volume `postgres_data`.
- Redis data is persisted in a Docker volume `redis_data`.
- Report metadata and logs are stored in the mounted `./instance` directory.

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
