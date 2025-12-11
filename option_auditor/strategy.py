from .models import StrategyGroup, TradeGroup, Leg
from typing import List, Optional, Dict, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict

def _classify_strategy(strat: StrategyGroup) -> str:
    """
    Classify a StrategyGroup by inspecting the opening legs.
    """
    legs_data = []
    total_open_proceeds = 0.0

    for g in strat.legs:
        if not g.legs:
            continue
        first = g.legs[0]
        qty = float(first.qty)
        proceeds = float(first.proceeds)
        total_open_proceeds += proceeds

        # Determine asset type
        is_option = (g.right in ["C", "P"] and g.strike is not None)

        legs_data.append({
            "type": "OPT" if is_option else "STOCK",
            "right": (g.right or "").upper() if is_option else None,
            "strike": float(g.strike) if is_option and g.strike is not None else 0.0,
            "expiry": g.expiry,
            "qty": qty,
            "proceeds": proceeds
        })

    if not legs_data:
        return "Unclassified"

    legs_data.sort(key=lambda x: (x["strike"], x["expiry"] if x["expiry"] else pd.Timestamp.min, x["right"] or ""))

    stock_legs = [l for l in legs_data if l["type"] == "STOCK"]
    opt_legs = [l for l in legs_data if l["type"] == "OPT"]

    num_stock = len(stock_legs)
    num_opt = len(opt_legs)

    if num_stock > 0:
        if num_stock == 1 and num_opt == 1:
            s = stock_legs[0]
            o = opt_legs[0]
            if s["qty"] > 0 and o["right"] == "C" and o["qty"] < 0:
                return "Covered Call"
            if s["qty"] > 0 and o["right"] == "P" and o["qty"] > 0:
                return "Protective Put"
            if s["qty"] > 0 and o["right"] == "P" and o["qty"] < 0:
                if abs(o["qty"] * 100) == s["qty"]:
                    return "Wheel"

        if num_stock == 1 and num_opt == 2:
            s = stock_legs[0]
            puts = [l for l in opt_legs if l["right"] == "P"]
            calls = [l for l in opt_legs if l["right"] == "C"]
            if len(puts) == 1 and len(calls) == 1:
                if s["qty"] > 0 and puts[0]["qty"] > 0 and calls[0]["qty"] < 0:
                    return "Collar"

    if num_stock == 0 and num_opt > 0:
        if num_opt == 1:
            o = opt_legs[0]
            side = "Long" if o["qty"] > 0 else "Short"
            desc = "Call" if o["right"] == "C" else "Put"
            return f"{side} {desc}"

        if num_opt == 2:
            l1, l2 = opt_legs[0], opt_legs[1]
            if (l1["strike"] == l2["strike"] and
                l1["right"] == l2["right"] and
                (l1["qty"] * l2["qty"] < 0) and
                l1["expiry"] != l2["expiry"]):
                return "Calendar Spread"

            if (l1["strike"] != l2["strike"] and
                l1["right"] == l2["right"] and
                (l1["qty"] * l2["qty"] < 0) and
                l1["expiry"] != l2["expiry"]):
                return "Diagonal Spread"

            if l1["expiry"] == l2["expiry"]:
                if l1["right"] != l2["right"]:
                    if l1["strike"] == l2["strike"]:
                        if l1["qty"] > 0 and l2["qty"] > 0: return "Long Straddle"
                        if l1["qty"] < 0 and l2["qty"] < 0: return "Short Straddle"
                        call_leg = l1 if l1["right"] == "C" else l2
                        put_leg = l1 if l1["right"] == "P" else l2
                        if call_leg["qty"] > 0 and put_leg["qty"] < 0:
                            return "Synthetic Long Stock"

                    if l1["strike"] != l2["strike"]:
                        if l1["qty"] > 0 and l2["qty"] > 0: return "Long Strangle"
                        if l1["qty"] < 0 and l2["qty"] < 0: return "Short Strangle"

                if l1["right"] == l2["right"]:
                    if (l1["qty"] * l2["qty"] < 0) and (abs(l1["qty"]) != abs(l2["qty"])):
                        return "Ratio Spread"

                    if (l1["qty"] * l2["qty"] < 0):
                        right = l1["right"]
                        if right == "C":
                            if l1["qty"] > 0: return "Bull Call Spread"
                            else: return "Bear Call Spread"
                        else:
                            if l1["qty"] > 0: return "Bull Put Spread"
                            else: return "Bear Put Spread"

        if num_opt == 3:
            l1, l2, l3 = opt_legs
            if (l1["expiry"] == l2["expiry"] == l3["expiry"]) and (l1["right"] == l2["right"] == l3["right"]):
                if l1["qty"] == l3["qty"] and l2["qty"] == -2 * l1["qty"]:
                    side = "Long" if l1["qty"] > 0 else "Short"
                    return f"{side} Butterfly Spread"

        if num_opt == 4:
            puts = [l for l in opt_legs if l["right"] == "P"]
            calls = [l for l in opt_legs if l["right"] == "C"]
            if len(puts) == 2 and len(calls) == 2:
                exps = {l["expiry"] for l in opt_legs}
                if len(exps) == 1:
                    puts.sort(key=lambda x: x["strike"])
                    calls.sort(key=lambda x: x["strike"])
                    p_long_low = puts[0]
                    p_short_high = puts[1]
                    c_short_low = calls[0]
                    c_long_high = calls[1]
                    is_condor_structure = (
                        p_long_low["qty"] > 0 and p_short_high["qty"] < 0 and
                        c_short_low["qty"] < 0 and c_long_high["qty"] > 0
                    )
                    if is_condor_structure:
                        if abs(p_short_high["strike"] - c_short_low["strike"]) < 0.01:
                            return "Iron Butterfly"
                        else:
                            return "Iron Condor"
                    c1, c2 = calls[0], calls[1]
                    p1, p2 = puts[0], puts[1]
                    if (c1["qty"] > 0 and c2["qty"] < 0 and p1["qty"] < 0 and p2["qty"] > 0):
                        if abs(c1["strike"] - p1["strike"]) < 0.01 and abs(c2["strike"] - p2["strike"]) < 0.01:
                            return "Box Spread"

    if num_opt == 2:
        l1, l2 = opt_legs[0], opt_legs[1]
        if l1["right"] == l2["right"] and l1["qty"] * l2["qty"] < 0:
             is_credit = total_open_proceeds > 0
             side = "Credit" if is_credit else "Debit"
             if l1["right"] == "P":
                 return f"Put Vertical ({side})"
             else:
                 return f"Call Vertical ({side})"

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

    # --- Start of new Wheel Strategy detection logic ---
    wheel_strategies = []
    processed_groups = set()

    # Find closed short puts and open long stocks
    short_puts = [g for g in all_groups if g.right == "P" and g.is_closed and any(l.qty < 0 for l in g.legs)]
    long_stocks = [g for g in all_groups if g.right is None and not g.is_closed and any(l.qty > 0 for l in g.legs)]

    short_puts.sort(key=lambda g: g.exit_ts)
    long_stocks.sort(key=lambda g: g.entry_ts)

    for put_group in short_puts:
        if id(put_group) in processed_groups:
            continue

        for stock_group in long_stocks:
            if id(stock_group) in processed_groups:
                continue

            if put_group.symbol == stock_group.symbol:
                if put_group.exit_ts and stock_group.entry_ts:
                    time_diff_hours = (stock_group.entry_ts - put_group.exit_ts).total_seconds() / 3600
                    if 0 <= time_diff_hours < 48:  # 2-day window for assignment
                        # Assuming 1 contract = 100 shares.
                        put_qty = sum(l.qty for l in put_group.legs if l.qty < 0)
                        stock_qty = sum(l.qty for l in stock_group.legs if l.qty > 0)

                        if abs(put_qty * 100) == stock_qty:
                            strat = StrategyGroup(
                                id=f"STRAT-WHEEL-{len(wheel_strategies)}",
                                symbol=put_group.symbol,
                                expiry=None,
                                strategy_name="Wheel"
                            )
                            strat.add_leg_group(put_group)
                            strat.add_leg_group(stock_group)

                            # Adjust cost basis. The PNL of the put is the premium received.
                            # We effectively reduce the cost of the stock.
                            # The stock_group.pnl is negative (a cost).
                            stock_group.pnl += put_group.pnl
                            strat.pnl = stock_group.pnl
                            strat.fees = stock_group.fees + put_group.fees
                            
                            # Mark the original put group as "absorbed" into the wheel
                            put_group.pnl = 0 
                            put_group.fees = 0

                            wheel_strategies.append(strat)
                            processed_groups.add(id(put_group))
                            processed_groups.add(id(stock_group))
                            break

    # Filter out groups that are now part of a wheel
    remaining_groups = [g for g in all_groups if id(g) not in processed_groups]
    # --- End of new Wheel Strategy detection logic ---

    base_groups = [g for g in remaining_groups if g.is_closed] if closed_groups else remaining_groups
    base_groups.sort(key=lambda x: x.entry_ts)

    # Optimization: Bucket groups by symbol AND expiry to strictly reduce N^2 complexity
    groups_by_bucket = defaultdict(list)
    for g in base_groups:
        groups_by_bucket[(g.symbol, g.expiry)].append(g)

    strategies = []
    processed_ids = set()

    # Iterate by bucket
    for (symbol, expiry), groups in groups_by_bucket.items():
        # groups are already sorted by time (because base_groups was sorted)
        for i, group in enumerate(groups):
            if id(group) in processed_ids:
                continue

            strat = StrategyGroup(
                id=f"STRAT-{len(strategies)}", symbol=group.symbol, expiry=group.expiry
            )
            strat.add_leg_group(group)
            processed_ids.add(id(group))

            # Look ahead in the SAME symbol list
            for j in range(i + 1, len(groups)):
                candidate = groups[j]
                if id(candidate) in processed_ids:
                    continue

                time_diff = (candidate.entry_ts - group.entry_ts).total_seconds() / 3600.0

                # Heuristic: If > 3 hours, unlikely to be part of the same strategy opening structure.
                if time_diff > 3.0:
                    break

                # 1. Match Expiry (within 2h window to account for data quirks)
                same_expiry = (candidate.expiry == group.expiry and time_diff < 2.0)

                # 2. Roll (very short timeframe < 5min, can have different expiry)
                is_roll_execution = (time_diff < (5.0 / 60.0))

                # 3. Calendar Spread (Same Right, Diff Expiry, < 1 min execution)
                calendar = (candidate.right == group.right and time_diff < (1.0 / 60.0))

                # CHECK: If the current strategy is already fully closed BEFORE this candidate starts,
                # do NOT merge them. They are likely sequential trades (e.g. Day Trading).
                # We want to detect "Revenge Trading" which implies separate trades.
                # Calculate if strat is closed relative to candidate.entry_ts
                is_closed_before_next = False
                if strat.exit_ts and candidate.entry_ts:
                    if strat.exit_ts < candidate.entry_ts:
                         # Ensure the net quantity is zero (closed)
                         current_net_qty = sum(l.qty_net for l in strat.legs)
                         if abs(current_net_qty) < 1e-9:
                             is_closed_before_next = True

                if (same_expiry or is_roll_execution or calendar) and not is_closed_before_next:
                    strat.add_leg_group(candidate)
                    processed_ids.add(id(candidate))

            strat.strategy_name = _classify_strategy(strat)
            strategies.append(strat)

    strategies.extend(wheel_strategies)
    strategies.sort(key=lambda s: s.exit_ts if s.exit_ts is not None else pd.Timestamp.min)

    # Second Pass: Detect Rolls (Campaigns)
    merged_strategies = []
    processed_strat_ids = set()

    # Re-bucket strategies by symbol for efficient roll detection
    strategies_by_symbol = defaultdict(list)
    for s in strategies:
        strategies_by_symbol[s.symbol].append(s)

    for strat in strategies:
        if strat.id in processed_strat_ids:
            continue

        # Start a campaign with this strategy
        campaign_head = strat
        search_pointer = strat
        processed_strat_ids.add(campaign_head.id)

        # Initialize first segment
        if not campaign_head.segments:
            campaign_head.segments.append({
                "strategy_name": campaign_head.strategy_name,
                "pnl": campaign_head.pnl,
                "fees": campaign_head.fees,
                "entry_ts": campaign_head.entry_ts,
                "exit_ts": campaign_head.exit_ts
            })

        while True:
            candidates = strategies_by_symbol[search_pointer.symbol]
            found_next = None

            if search_pointer.exit_ts:
                exit_time = search_pointer.exit_ts
                best_candidate = None
                min_gap = float('inf')

                for cand in candidates:
                    if cand.id in processed_strat_ids or cand.id == search_pointer.id:
                        continue

                    if cand.entry_ts:
                        diff_sec = (cand.entry_ts - exit_time).total_seconds()
                        diff_min = diff_sec / 60.0

                        # Roll window: -2 min to +15 mins
                        # DYNAMIC WINDOW: If previous trade was a LOSS, tighten window to 1 min.
                        # This prevents "Revenge Trades" (re-entry after loss) from being merged into rolls.
                        roll_window_max = 15.0
                        if search_pointer.net_pnl < 0:
                            roll_window_max = 1.0

                        if -2 <= diff_min <= roll_window_max:
                            if diff_min < min_gap:
                                min_gap = diff_min
                                best_candidate = cand

                if best_candidate:
                    found_next = best_candidate

            if found_next:
                next_strat = found_next
                segment_info = {
                    "strategy_name": next_strat.strategy_name,
                    "pnl": next_strat.pnl,
                    "fees": next_strat.fees,
                    "entry_ts": next_strat.entry_ts,
                    "exit_ts": next_strat.exit_ts
                }
                campaign_head.segments.append(segment_info)

                campaign_head.pnl += next_strat.pnl
                campaign_head.fees += next_strat.fees
                campaign_head.exit_ts = next_strat.exit_ts
                campaign_head.strategy_name = f"Rolled {campaign_head.strategy_name}"
                campaign_head.legs.extend(next_strat.legs)

                processed_strat_ids.add(next_strat.id)
                search_pointer = next_strat
            else:
                break

        merged_strategies.append(strat)

    return merged_strategies
