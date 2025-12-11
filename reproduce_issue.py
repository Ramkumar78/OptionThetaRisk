import pandas as pd
from option_auditor.strategy import build_strategies
from option_auditor.models import TradeGroup

def reproduction():
    t1 = pd.Timestamp("2023-01-01 10:00")
    t2 = pd.Timestamp("2023-01-15 16:00")

    legs = []
    # Short Put: Open
    legs.append({"datetime": t1, "contract_id": "P1", "symbol": "XYZ", "qty": -1, "proceeds": 100, "fees": 1, "strike": 100, "right": "P", "expiry": t2})
    # Short Put: Close
    legs.append({"datetime": t2, "contract_id": "P1", "symbol": "XYZ", "qty": 1, "proceeds": 0, "fees": 0, "strike": 100, "right": "P", "expiry": t2})

    # Stock Acquisition
    t3 = t2 + pd.Timedelta(hours=1)
    legs.append({"datetime": t3, "contract_id": "STOCK", "symbol": "XYZ", "qty": 100, "proceeds": -10000, "fees": 5, "strike": None, "right": None, "expiry": None})

    df = pd.DataFrame(legs)
    print("DataFrame:")
    print(df)

    strategies = build_strategies(df)
    print(f"\nStrategies found: {len(strategies)}")
    for s in strategies:
        print(f"Strategy: {s.strategy_name}, ID: {s.id}, Symbol: {s.symbol}")
        print(f"  Entry: {s.entry_ts}, Exit: {s.exit_ts}")
        print(f"  PnL: {s.pnl}, Fees: {s.fees}")
        for leg in s.legs:
            print(f"    Leg Group: {leg.contract_id}, Right: {leg.right}, Closed: {leg.is_closed}")
            for l in leg.legs:
                print(f"      L: {l.ts} Qty: {l.qty}")

if __name__ == "__main__":
    reproduction()
