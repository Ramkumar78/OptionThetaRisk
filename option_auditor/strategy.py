from .models import StrategyGroup, TradeGroup, Leg
from typing import List
import pandas as pd

def _classify_strategy(strat: StrategyGroup) -> str:
    openings = []
    total_open_proceeds = 0.0
    for g in strat.legs:
        if not g.legs:
            continue
        first = g.legs[0]
        openings.append({
            "right": (g.right or "").upper() if g.right else "",
            "strike": float(g.strike) if g.strike is not None else None,
            "qty": float(first.qty),
            "proceeds": float(first.proceeds),
        })
        total_open_proceeds += float(first.proceeds)

    openings = [o for o in openings if o["right"] in {"P", "C"} and o["strike"] is not None]
    if not openings:
        return "Unclassified"

    if len(openings) == 1:
        o = openings[0]
        if o["right"] == "P":
            return "Short Put" if o["qty"] < 0 else "Long Put"
        else:
            return "Short Call" if o["qty"] < 0 else "Long Call"

    if len(openings) == 2:
        rset = {o["right"] for o in openings}
        if len(rset) == 1:
            right = openings[0]["right"]
            if len([o for o in openings if o["qty"] < 0]) == 1 and len([o for o in openings if o["qty"] > 0]) == 1:
                is_credit = total_open_proceeds > 0
                side = "Credit" if is_credit else "Debit"
                if right == "P":
                    return f"Put Vertical ({side})"
                else:
                    return f"Call Vertical ({side})"
        return "Multi‑leg"

    if len(openings) == 4:
        rights = [o["right"] for o in openings]
        if rights.count("P") == 2 and rights.count("C") == 2:
            is_credit = total_open_proceeds > 0
            side = "Credit" if is_credit else "Debit"
            return f"Iron Condor ({side})"

    return "Multi‑leg"

def build_strategies(legs_df: pd.DataFrame) -> List[StrategyGroup]:
    if legs_df.empty:
        return []

    contract_map = {}
    closed_groups = []
    all_groups = []
    legs_df = legs_df.sort_values("datetime")

    for _, row in legs_df.iterrows():
        cid = row['contract_id']
        if cid not in contract_map:
            contract_map[cid] = []
        found_match = False
        for group in contract_map[cid]:
            if not group.is_closed:
                if (group.qty_net > 0 and row['qty'] < 0) or (group.qty_net < 0 and row['qty'] > 0):
                    group.add_leg(Leg(ts=row['datetime'], qty=row['qty'], price=0, fees=row['fees'], proceeds=row['proceeds']))
                    found_match = True
                    if group.is_closed:
                        closed_groups.append(group)
                    break
        if not found_match:
            new_group = TradeGroup(
                contract_id=cid, symbol=row['symbol'], expiry=row['expiry'],
                strike=row['strike'], right=row['right']
            )
            new_group.add_leg(Leg(ts=row['datetime'], qty=row['qty'], price=0, fees=row['fees'], proceeds=row['proceeds']))
            contract_map[cid].append(new_group)
            all_groups.append(new_group)

    strategies = []
    base_groups = closed_groups if closed_groups else all_groups
    base_groups.sort(key=lambda x: x.entry_ts)
    processed_ids = set()

    for i, group in enumerate(base_groups):
        if id(group) in processed_ids:
            continue
        strat = StrategyGroup(
            id=f"STRAT-{i}", symbol=group.symbol, expiry=group.expiry
        )
        strat.add_leg_group(group)
        processed_ids.add(id(group))
        for j in range(i + 1, len(base_groups)):
            candidate = base_groups[j]
            if id(candidate) in processed_ids:
                continue
            time_diff = (candidate.entry_ts - group.entry_ts).total_seconds() / 3600
            if (candidate.symbol == group.symbol and
                    candidate.expiry == group.expiry and
                    time_diff < 2.0):
                strat.add_leg_group(candidate)
                processed_ids.add(id(candidate))
        strat.strategy_name = _classify_strategy(strat)
        strategies.append(strat)

    strategies.sort(key=lambda s: s.exit_ts if s.exit_ts is not None else pd.Timestamp.min)
    merged_strategies = []
    processed_strat_ids = set()

    for i, strat in enumerate(strategies):
        if strat.id in processed_strat_ids:
            continue
        for j in range(i + 1, len(strategies)):
            next_strat = strategies[j]
            if next_strat.id in processed_strat_ids:
                continue
            if strat.symbol == next_strat.symbol and strat.exit_ts and next_strat.entry_ts:
                time_diff_minutes = (next_strat.entry_ts - strat.exit_ts).total_seconds() / 60
                if 0 <= time_diff_minutes <= 5:
                    strat.pnl += next_strat.pnl
                    strat.exit_ts = next_strat.exit_ts
                    strat.strategy_name = f"Rolled {strat.strategy_name}"
                    processed_strat_ids.add(next_strat.id)
        merged_strategies.append(strat)

    return merged_strategies
