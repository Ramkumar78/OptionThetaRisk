import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from collections import defaultdict
from .models import TradeGroup

logger = logging.getLogger(__name__)

def check_itm_risk(open_groups: List[TradeGroup], prices: Dict[str, float]) -> Tuple[bool, float, List[str]]:
    """
    Checks Net Intrinsic Risk per symbol to handle Spreads and Covered Calls correctly.
    Returns (is_risky_flag, total_itm_amount, list_of_risk_descriptions).
    """
    risky = False
    total_net_exposure = 0.0
    details = []

    # 1. Group positions by Symbol
    by_symbol = defaultdict(list)
    for g in open_groups:
        if g.symbol in prices:
            by_symbol[g.symbol].append(g)

    # 2. Analyze Net Risk per Symbol
    for symbol, groups in by_symbol.items():
        current_price = prices[symbol]
        net_intrinsic_val = 0.0

        # Calculate the Net Liquidation Value of options if expired NOW
        for g in groups:
            qty = g.qty_net

            # Stock (Treat as asset/liability at full market value)
            if not g.strike or g.right not in ['C', 'P']:
                net_intrinsic_val += current_price * qty
                continue

            if g.strike and g.right:
                intrinsic = 0.0
                if g.right == 'C': # Call
                    # Value = Max(0, Price - Strike)
                    val = max(0.0, current_price - g.strike)
                    intrinsic = val * qty * 100
                elif g.right == 'P': # Put
                    # Value = Max(0, Strike - Price)
                    val = max(0.0, g.strike - current_price)
                    intrinsic = val * qty * 100

                # Add to net total (Longs add value, Shorts subtract value)
                net_intrinsic_val += intrinsic

        # 3. Verdict on this Symbol
        # If the Net Intrinsic Value is significantly negative (e.g. < -$500),
        # it means the Short legs are ITM and NOT fully covered by Long legs.
        if net_intrinsic_val < -500:
            risky = True
            total_net_exposure += abs(net_intrinsic_val)
            details.append(f"{symbol}: Net ITM Exposure -${abs(net_intrinsic_val):,.0f} (Unhedged)")

    return risky, total_net_exposure, details

def calculate_discipline_score(strategies: List[Any], open_positions: List[Dict]) -> Tuple[int, List[str]]:
    """
    Calculates a 'Trader Discipline Score' (0-100) based on behavioral metrics.
    """
    score = 100
    details = []

    # 1. Strategy Analysis (History)
    # Penalize Revenge Trading
    revenge_count = sum(1 for s in strategies if getattr(s, "is_revenge", False))
    if revenge_count > 0:
        penalty = revenge_count * 10
        score -= penalty
        details.append(f"Revenge Trading: -{penalty} pts ({revenge_count} instances)")

    # Reward Early Loss Cutting
    # Definition: Loss trade closed faster than average win/loss hold time?
    # Simple proxy: Loss < average hold time * 0.5
    avg_hold = 0.0
    if strategies:
        avg_hold = np.mean([s.hold_days() for s in strategies])

    early_cuts = 0
    for s in strategies:
        if s.net_pnl < 0 and s.hold_days() < (avg_hold * 0.5):
            early_cuts += 1

    if early_cuts > 0:
        bonus = min(20, early_cuts * 2) # Cap bonus
        score += bonus
        details.append(f"Cutting Losses Early: +{bonus} pts")

    # 2. Open Position Analysis (Risk Management)
    # Penalize Gamma Risk (holding < 3 DTE)
    gamma_risks = 0
    for p in open_positions:
        dte = p.get("dte")
        # Ensure DTE is valid number
        if dte is not None and isinstance(dte, (int, float)) and dte <= 3:
            gamma_risks += 1

    if gamma_risks > 0:
        penalty = gamma_risks * 5
        score -= penalty
        details.append(f"Gamma Risk (Held < 3 DTE): -{penalty} pts")

    # Clamp Score
    score = max(0, min(100, score))

    return score, details
