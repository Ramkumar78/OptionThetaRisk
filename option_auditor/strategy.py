from .models import StrategyGroup, TradeGroup, Leg
from typing import List, Optional, Dict
import pandas as pd
import numpy as np

def _classify_strategy(strat: StrategyGroup) -> str:
    """
    Classify a StrategyGroup by inspecting the opening legs.
    """
    # 1. Normalize Legs
    # We aggregate legs from the TradeGroups.
    # We care about the "Net" position of the strategy to determine what it IS.
    # Usually "opening" legs define it.

    legs_data = []
    total_open_proceeds = 0.0

    for g in strat.legs:
        if not g.legs:
            continue
        # Use the first leg of the group as representative of the "Contract" details
        # But we need the NET quantity of the group to know if we are Long or Short this contract.
        # Actually, StrategyGroup.legs contains TradeGroups.
        # Each TradeGroup represents a Contract.
        # TradeGroup.qty_net tells us the current position?
        # No, audit logic usually looks at the "Opening" transaction.
        # But here we are classifying the *Trade history* or the *Position*?
        # The existing code looked at `first = g.legs[0]` and used `first.qty`.
        # This implies we classify based on the INITIAL trade that opened the group.

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

    # Sort legs by Strike (asc), then Expiry (asc), then Right (C first?)
    # Helping consistency in pattern matching
    legs_data.sort(key=lambda x: (x["strike"], x["expiry"] if x["expiry"] else pd.Timestamp.min, x["right"] or ""))

    # Helper counts
    stock_legs = [l for l in legs_data if l["type"] == "STOCK"]
    opt_legs = [l for l in legs_data if l["type"] == "OPT"]

    num_stock = len(stock_legs)
    num_opt = len(opt_legs)

    # --- Stock-Based Strategies ---
    if num_stock > 0:
        # Covered Call: Long Stock + Short Call
        if num_stock == 1 and num_opt == 1:
            s = stock_legs[0]
            o = opt_legs[0]
            if s["qty"] > 0 and o["right"] == "C" and o["qty"] < 0:
                return "Covered Call"
            # Protective Put: Long Stock + Long Put
            if s["qty"] > 0 and o["right"] == "P" and o["qty"] > 0:
                return "Protective Put"

        # Collar: Long Stock + Long Put + Short Call
        if num_stock == 1 and num_opt == 2:
            s = stock_legs[0]
            # Expect 1 Long Put, 1 Short Call
            puts = [l for l in opt_legs if l["right"] == "P"]
            calls = [l for l in opt_legs if l["right"] == "C"]
            if len(puts) == 1 and len(calls) == 1:
                if s["qty"] > 0 and puts[0]["qty"] > 0 and calls[0]["qty"] < 0:
                    return "Collar"

    # --- Option-Only Strategies ---
    if num_stock == 0 and num_opt > 0:

        # 1 Leg
        if num_opt == 1:
            o = opt_legs[0]
            side = "Long" if o["qty"] > 0 else "Short"
            desc = "Call" if o["right"] == "C" else "Put"
            return f"{side} {desc}"

        # 2 Legs
        if num_opt == 2:
            l1, l2 = opt_legs[0], opt_legs[1]

            # Check for Time Spreads (Same Strike, Diff Expiry)
            # usually strict same strike, same right, opposite signs
            if (l1["strike"] == l2["strike"] and
                l1["right"] == l2["right"] and
                (l1["qty"] * l2["qty"] < 0) and
                l1["expiry"] != l2["expiry"]):
                return "Calendar Spread"

            # Check for Diagonal (Diff Strike, Diff Expiry)
            if (l1["strike"] != l2["strike"] and
                l1["right"] == l2["right"] and
                (l1["qty"] * l2["qty"] < 0) and
                l1["expiry"] != l2["expiry"]):
                return "Diagonal Spread"

            # Same Expiry Analysis
            if l1["expiry"] == l2["expiry"]:

                # Different Rights (1 Call, 1 Put)
                if l1["right"] != l2["right"]:
                    # Straddle: Same Strike, Same Sign (Both Long or Both Short)
                    if l1["strike"] == l2["strike"]:
                        if l1["qty"] > 0 and l2["qty"] > 0: return "Long Straddle"
                        if l1["qty"] < 0 and l2["qty"] < 0: return "Short Straddle"
                        # Opposite signs? Synthetic Stock
                        # Long Call + Short Put = Synthetic Long Stock
                        call_leg = l1 if l1["right"] == "C" else l2
                        put_leg = l1 if l1["right"] == "P" else l2
                        if call_leg["qty"] > 0 and put_leg["qty"] < 0:
                            return "Synthetic Long Stock"

                    # Strangle: Diff Strike, Same Sign
                    if l1["strike"] != l2["strike"]:
                        if l1["qty"] > 0 and l2["qty"] > 0: return "Long Strangle"
                        if l1["qty"] < 0 and l2["qty"] < 0: return "Short Strangle"

                # Same Right (2 Calls or 2 Puts)
                if l1["right"] == l2["right"]:
                    # Ratio Spread: Opposite Signs, Quantity Ratio != 1
                    # e.g. Buy 1, Sell 2
                    if (l1["qty"] * l2["qty"] < 0) and (abs(l1["qty"]) != abs(l2["qty"])):
                        return "Ratio Spread"

                    # Vertical Spread: Opposite Signs, Qty Match (approx)
                    if (l1["qty"] * l2["qty"] < 0):
                        is_credit = total_open_proceeds > 0
                        # Naming convention: "Bull Call Spread", "Bear Put Spread"
                        # Bull Call: Long Lower (l1), Short Higher (l2). Debit.
                        # Bear Call: Short Lower (l1), Long Higher (l2). Credit.
                        # Bull Put: Long Lower (l1), Short Higher (l2). Credit.
                        # Bear Put: Short Lower (l1), Long Higher (l2). Debit.

                        right = l1["right"]
                        if right == "C":
                            # l1 is lower strike. If l1 is Long (>0), it's Bull.
                            if l1["qty"] > 0: return "Bull Call Spread"
                            else: return "Bear Call Spread"
                        else: # Put
                            # l1 is lower strike.
                            # Bull Put: Long Lower (l1), Short Higher (l2). Credit.
                            # Bear Put: Short Lower (l1), Long Higher (l2). Debit.
                            if l1["qty"] > 0: return "Bull Put Spread"
                            else: return "Bear Put Spread"

        # 3 Legs
        if num_opt == 3:
            # Butterfly: 3 legs, same expiry, same right usually.
            # Ratios 1 : -2 : 1
            # Sorted by strike: Low, Mid, High
            l1, l2, l3 = opt_legs
            if (l1["expiry"] == l2["expiry"] == l3["expiry"]) and (l1["right"] == l2["right"] == l3["right"]):
                # Check Qty structure
                # Long Fly: Buy 1 Low, Sell 2 Mid, Buy 1 High. (+1, -2, +1)
                # Short Fly: Sell 1 Low, Buy 2 Mid, Sell 1 High. (-1, +2, -1)
                if l1["qty"] == l3["qty"] and l2["qty"] == -2 * l1["qty"]:
                    side = "Long" if l1["qty"] > 0 else "Short"
                    return f"{side} Butterfly Spread"

        # 4 Legs
        if num_opt == 4:
            # Iron Condor / Iron Butterfly / Box
            # Usually 2 Puts, 2 Calls
            puts = [l for l in opt_legs if l["right"] == "P"]
            calls = [l for l in opt_legs if l["right"] == "C"]

            if len(puts) == 2 and len(calls) == 2:
                # Check if same expiry
                exps = {l["expiry"] for l in opt_legs}
                if len(exps) == 1:
                    # Sort Puts and Calls by strike
                    puts.sort(key=lambda x: x["strike"])
                    calls.sort(key=lambda x: x["strike"])

                    # Iron Condor/Butterfly usually:
                    # Bull Put Spread (Long P Low, Short P High)
                    # Bear Call Spread (Short C Low, Long C High)
                    # Strikes: P_Long < P_Short <= C_Short < C_Long

                    p_long_low = puts[0]
                    p_short_high = puts[1]
                    c_short_low = calls[0]
                    c_long_high = calls[1]

                    # Check Quantities (Standard 1 lot)
                    # Bull Put: +1 P_low, -1 P_high
                    # Bear Call: -1 C_low, +1 C_high

                    is_condor_structure = (
                        p_long_low["qty"] > 0 and p_short_high["qty"] < 0 and
                        c_short_low["qty"] < 0 and c_long_high["qty"] > 0
                    )

                    if is_condor_structure:
                        # Check Strikes for Butterfly vs Condor
                        # Iron Butterfly: P_Short Strike == C_Short Strike
                        if abs(p_short_high["strike"] - c_short_low["strike"]) < 0.01:
                            return "Iron Butterfly"
                        else:
                            return "Iron Condor"

                    # Box Spread
                    # Bull Call Spread (Long C Low, Short C High)
                    # Bear Put Spread (Long P High, Short P Low) -> Wait, Bear Put is Short Low, Long High.
                    # Standard Box: Long Call Low + Short Call High + Long Put High + Short Put Low
                    # Strikes: Low (LC + SP), High (SC + LP)
                    # C_Low > 0, C_High < 0. P_Low < 0, P_High > 0.

                    is_box_structure = (
                        c_short_low["qty"] > 0 and c_long_high["qty"] < 0 and # C_Low Long, C_High Short?
                        # Wait, calls sorted by strike. c_short_low is index 0 (Lower strike).
                        # Bull Call: Buy Low Call (c_short_low should be > 0), Sell High Call (c_long_high < 0).

                        p_long_low["qty"] < 0 and p_short_high["qty"] > 0
                        # Bear Put: Sell Low Put (p_long_low < 0), Buy High Put (p_short_high > 0).
                    )

                    # My variable names above `c_short_low` assumed Condor structure (short inner).
                    # Let's just use indices.
                    c1, c2 = calls[0], calls[1] # c1 Low, c2 High
                    p1, p2 = puts[0], puts[1]   # p1 Low, p2 High

                    if (c1["qty"] > 0 and c2["qty"] < 0 and p1["qty"] < 0 and p2["qty"] > 0):
                        # Verify strikes match pairs
                        if abs(c1["strike"] - p1["strike"]) < 0.01 and abs(c2["strike"] - p2["strike"]) < 0.01:
                            return "Box Spread"


    # Fallback to old vertical naming if generic
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
            if candidate.symbol == group.symbol:
                # Group if Expiry matches (within 2 hours) OR Right matches (within 1 min) for Calendars
                same_expiry = (candidate.expiry == group.expiry and time_diff < 2.0)

                # Check for roll: Small time diff (< 5 min) allows different expiry
                is_roll = (time_diff < (5.0 / 60.0))

                # Calendar Spread: Same Right, Different Expiry, executed together (< 1 min)
                # (Often covered by is_roll now, but keeping for clarity if needed)
                calendar = (candidate.right == group.right and time_diff < (1.0 / 60.0))

                if same_expiry or is_roll or calendar:
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
