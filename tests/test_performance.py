import pytest
import time
import pandas as pd
from option_auditor.strategy import build_strategies
from datetime import datetime, timedelta

def test_strategy_grouping_performance():
    n_strats = 1500
    rows = []
    base_time = datetime(2025, 1, 1, 9, 30)

    for i in range(n_strats):
        t_open = base_time + timedelta(hours=i*4)
        rows.append({
            "contract_id": f"SYM:2025-02-20:P:{100+i}",
            "symbol": "SPY",
            "datetime": t_open,
            "qty": 1,
            "price": 1.0,
            "fees": 0.5,
            "proceeds": -100.0,
            "expiry": pd.Timestamp("2025-02-20"),
            "strike": 100+i,
            "right": "P"
        })
        t_close = t_open + timedelta(days=5)
        rows.append({
            "contract_id": f"SYM:2025-02-20:P:{100+i}",
            "symbol": "SPY",
            "datetime": t_close,
            "qty": -1,
            "price": 0.5,
            "fees": 0.5,
            "proceeds": 50.0,
            "expiry": pd.Timestamp("2025-02-20"),
            "strike": 100+i,
            "right": "P"
        })

    df = pd.DataFrame(rows)

    start_time = time.time()
    strategies = build_strategies(df)
    duration = time.time() - start_time

    print(f"Processed {len(rows)} rows in {duration:.4f} seconds")

    # With the new logic, we expect 30 chains (Campaigns)
    assert len(strategies) == 30

    total_segments = sum(len(s.segments) for s in strategies)
    assert total_segments == n_strats

    assert duration < 15.0
