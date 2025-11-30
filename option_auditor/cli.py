import argparse
from tabulate import tabulate
from .auditor import analyze_csv


def main(argv=None):
    parser = argparse.ArgumentParser(description="The Option Auditor")
    parser.add_argument("--csv", required=True, help="Path to CSV")
    args = parser.parse_args(argv)

    res = analyze_csv(csv_path=args.csv)

    if "error" in res:
        print(f"Error: {res['error']}")
        return 1

    m = res["metrics"]

    print("\n--- PORTFOLIO AUDIT ---")
    summary = [
        ["Strategies Closed", m["num_trades"]],
        ["Win Rate (Real)", f"{m['win_rate'] * 100:.1f}%"],
        ["Total PnL", f"${m['total_pnl']:.2f}"],
        ["Avg Hold Time", f"{m['avg_hold_days']:.1f} Days"],
        ["Verdict", res["verdict"]]
    ]
    print(tabulate(summary, tablefmt="simple"))

    print("\n--- PERFORMANCE BY TICKER ---")
    sym_table = []
    for s in res["symbols"]:
        sym_table.append([s['symbol'], f"${s['pnl']:.2f}", f"{s['win_rate'] * 100:.0f}%"])
    print(tabulate(sym_table, headers=["Ticker", "PnL", "Win Rate"], tablefmt="simple"))

    return 0


if __name__ == "__main__":
    main()