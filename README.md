### The Option Auditor — Options Audit Report

This is a lightweight CLI tool that ingests broker CSV exports (Tastytrade or Interactive Brokers),
groups options trades into round-trips (entry → exit), computes key metrics, and produces an
"Options Audit Report" with insights and risk flags.

#### Features
- Auto-detects broker CSV format (Tastytrade or IBKR) or allow `--broker` override.
- Groups trades per option contract and closes a group when position returns to zero.
- Computes per-trade metrics: PnL (incl. fees), hold time, realized-theta approximation (PnL per day held).
- Portfolio metrics: win rate, average hold time, average realized theta.
- Risk flags including an "Over-leveraged" heuristic if `--account-size` is provided.
- Console summary plus optional CSV and Markdown outputs.

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
