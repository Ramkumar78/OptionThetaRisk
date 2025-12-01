import pytest
import time
import pandas as pd
from option_auditor.strategy import build_strategies, _classify_strategy
from option_auditor.models import StrategyGroup, TradeGroup, Leg
from datetime import datetime, timedelta

def test_strategy_grouping_performance():
    # Generate 1500 strategies (3000 rows)
    n_strats = 1500
    rows = []
    base_time = datetime(2025, 1, 1, 9, 30)

    for i in range(n_strats):
        # Open
        t_open = base_time + timedelta(hours=i*4) # Spread out by 4 hours
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
        # Close
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

    # Due to Roll Detection logic, strategies that exit exactly when another enters (or close to it)
    # will be merged. With 4h spacing and 5d duration, Trade X exits at T+120h.
    # Trade (X+30) enters at (X+30)*4h = X*4h + 120h.
    # So Trade X exits exactly when Trade X+30 enters. They merge.
    # This results in 30 chains (Campaigns).

    assert len(strategies) == 30

    # Verify we didn't lose any trades
    total_segments = sum(len(s.segments) for s in strategies)
    # The first strategy in a chain counts as 1 segment (implied) + additional segments?
    # No, `segments` list in StrategyGroup usually stores ALL segments including the first one if we structured it that way.
    # Let's check `strategy.py`:
    # "if not current_strat.segments: current_strat.segments.append({...})" -> Adds first one.
    # So `len(s.segments)` is total strategies in the campaign.
    assert total_segments == n_strats

    # Performance assertion
    # 3000 rows should process reasonably fast.
    assert duration < 10.0
