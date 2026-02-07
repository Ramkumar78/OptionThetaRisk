import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from collections import defaultdict
from .models import TradeGroup, StressTestResult
from option_auditor.strategies.math_utils import calculate_option_price

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

def calculate_black_swan_impact(open_groups: List[TradeGroup], prices: Dict[str, float]) -> List[StressTestResult]:
    """
    Calculates portfolio PnL impact under Black Swan scenarios (+/- 5%, 10%, 20%).
    Uses Theoretical Black-Scholes pricing with constant volatility assumption.
    """
    results = []
    scenarios = [
        ("Market -20%", -0.20),
        ("Market -10%", -0.10),
        ("Market -5%", -0.05),
        ("Market +5%", 0.05),
        ("Market +10%", 0.10),
        ("Market +20%", 0.20)
    ]

    now = pd.Timestamp.now()
    # Default Assumptions if data missing
    risk_free_rate = 0.045
    default_vol = 0.40

    for name, move_pct in scenarios:
        total_current_val = 0.0
        total_new_val = 0.0

        # We need to calculate portfolio value at current prices vs new prices
        # Iterate all groups
        for g in open_groups:
            # Handle both object and dict (if serialized)
            if isinstance(g, dict):
                symbol = g.get("symbol")
                qty = g.get("qty_net", g.get("qty_open", 0.0))
                strike = g.get("strike")
                otype = g.get("right")
                # contract string fallback? 'P 400.0'
                if not otype and g.get("contract") and " " in g.get("contract", ""):
                    parts = g["contract"].split(" ")
                    otype = parts[0]
                    if not strike:
                        try:
                            strike = float(parts[1])
                        except: pass

                expiry = g.get("expiry")
            else:
                symbol = g.symbol
                qty = g.qty_net
                strike = g.strike
                otype = g.right
                expiry = g.expiry

            if symbol not in prices:
                continue

            S_curr = prices[symbol]
            S_new = S_curr * (1 + move_pct)

            # Check if Option or Stock
            is_option = strike is not None and otype in ['C', 'P']

            if not is_option:
                # Stock Logic
                val_curr = qty * S_curr
                val_new = qty * S_new
                total_current_val += val_curr
                total_new_val += val_new
            else:
                # Option Logic
                K = strike
                # otype is already extracted

                # Calculate T (Time to Expiry)
                T = 0.0
                if expiry:
                    try:
                        # ensure expiry is timestamp
                        exp_ts = pd.to_datetime(expiry)
                        # Time to expiry in years
                        # If expired, T=0
                        diff = (exp_ts - now).total_seconds()
                        if diff > 0:
                            T = diff / (365.0 * 24 * 3600)
                    except Exception:
                        T = 0.0

                # Map 'C' -> 'call', 'P' -> 'put'
                otype_param = 'call' if otype == 'C' else 'put' if otype == 'P' else 'call'

                # Calculate Option Prices
                price_curr = calculate_option_price(S_curr, K, T, risk_free_rate, default_vol, otype_param)
                price_new = calculate_option_price(S_new, K, T, risk_free_rate, default_vol, otype_param) # Constant Vol assumption

                val_curr = price_curr * 100 * qty
                val_new = price_new * 100 * qty

                total_current_val += val_curr
                total_new_val += val_new

        pnl = total_new_val - total_current_val
        pnl_pct = (pnl / abs(total_current_val)) * 100 if total_current_val != 0 else 0.0

        results.append(StressTestResult(
            scenario_name=name,
            market_move_pct=move_pct * 100,
            portfolio_value_change=pnl,
            portfolio_value_change_pct=pnl_pct,
            details=[]
        ))

    return results

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

    # Penalize Tilt (Rapid losses)
    losses = [s for s in strategies if s.net_pnl < 0 and getattr(s, 'exit_ts', None)]
    losses.sort(key=lambda x: x.exit_ts)

    tilt_events = 0
    for i in range(len(losses)):
        current = losses[i]
        window_start = current.exit_ts - pd.Timedelta(hours=24)

        count = 0
        for j in range(i, -1, -1):
            if losses[j].exit_ts < window_start:
                break
            count += 1

        if count > 3:
            tilt_events += 1

    if tilt_events > 0:
        p = tilt_events * 5
        score -= p
        details.append(f"Tilt Detected (>3 losses in 24h): -{p} pts")

    # Reward Patience (Holding Winners)
    strategy_hold_avgs = defaultdict(list)
    for s in strategies:
        name = getattr(s, 'strategy_name', "Unclassified")
        strategy_hold_avgs[name].append(s.hold_days())

    avg_map = {k: np.mean(v) for k, v in strategy_hold_avgs.items()}

    patience_count = 0
    for s in strategies:
        name = getattr(s, 'strategy_name', "Unclassified")
        if s.net_pnl > 0:
            avg = avg_map.get(name, 0)
            if avg > 0 and s.hold_days() > avg:
                patience_count += 1

    if patience_count > 0:
        b = min(20, patience_count * 2)
        score += b
        details.append(f"Patience Bonus (Holding Winners): +{b} pts")

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

def calculate_kelly_criterion(win_rate: float, profit_factor: float) -> float:
    """
    Calculates the Kelly Criterion percentage for position sizing.

    Formula derived from standard Kelly f = p - q/b, where:
    p = win_rate
    b = AvgWin/AvgLoss
    Profit Factor (PF) = (p * AvgWin) / ((1-p) * AvgLoss) => b = PF * (1-p)/p

    Resulting simplified formula: Kelly % = Win Rate * (1 - 1 / Profit Factor)

    Args:
        win_rate: The probability of winning (0.0 to 1.0).
        profit_factor: The ratio of Gross Profit / Gross Loss.

    Returns:
        The optimal fraction of the bankroll to wager (0.0 to 1.0).
        Returns 0.0 if the Profit Factor is <= 1 or calculation fails.
    """
    if profit_factor <= 1.0 or win_rate <= 0.0 or win_rate > 1.0:
        return 0.0

    kelly_pct = win_rate * (1.0 - 1.0 / profit_factor)

    return max(0.0, kelly_pct)
