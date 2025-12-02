import argparse
import os
from tabulate import tabulate
from .main_analyzer import analyze_csv

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

def _format_pnl(pnl):
    """Formats PnL with color."""
    if pnl >= 0:
        return f"{GREEN}${pnl:,.2f}{RESET}"
    else:
        return f"{RED}${pnl:,.2f}{RESET}"

def main(argv=None):
    parser = argparse.ArgumentParser(description="The Option Auditor")
    parser.add_argument("--csv", required=True, help="Path to CSV")
    parser.add_argument("--output", help="Path to save the report file")
    parser.add_argument("--broker", help="Broker type: auto (default), tasty, ibkr", default="auto")
    args = parser.parse_args(argv)

    res = analyze_csv(csv_path=args.csv, broker=args.broker, report_format="excel" if args.output else "none")

    if "error" in res:
        print(f"Error: {res['error']}")
        return 1

    if args.output and res.get("excel_report"):
        with open(args.output, "wb") as f:
            f.write(res["excel_report"].getvalue())
        print(f"Report saved to {args.output}")

    m = res["metrics"]
    sm = res["strategy_metrics"]
    lr = res["leakage_report"]

    print("\n--- PORTFOLIO AUDIT ---")
    summary = [
        ["Strategies Closed", f"{sm['num_trades']}"],
        ["Win Rate (Real)", f"{sm['win_rate'] * 100:.1f}%"],
        ["Total PnL (Net)", _format_pnl(sm['total_pnl'])],
        ["Total Fees", f"${sm['total_fees']:,.2f}"],
        ["Efficiency Ratio", f"{lr['efficiency_ratio']:.2f}"],
        ["Avg Hold Time", f"{m['avg_hold_days']:.1f} Days"],
        ["Verdict", res["verdict"]]
    ]
    print(tabulate(summary, tablefmt="presto", numalign="right"))

    print("\n--- PERFORMANCE BY TICKER ---")
    sym_table = []
    for s in res["symbols"]:
        sym_table.append([s['symbol'], _format_pnl(s['pnl']), f"{s['win_rate'] * 100:.0f}%"])
    print(tabulate(sym_table, headers=["Ticker", "PnL", "Win Rate"], tablefmt="presto", numalign="right"))

    return 0

def run_main():
    main()

if __name__ == "__main__": # pragma: no cover
    run_main()
