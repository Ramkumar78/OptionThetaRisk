from .parsers import TastytradeParser, TastytradeFillsParser, ManualInputParser, IBKRParser
from .strategy import build_strategies
from .models import TradeGroup, Leg
from .config import SYMBOL_DESCRIPTIONS, VERDICT_MIN_TRADES
from typing import Optional, Dict, List, Tuple, Any, Union
import pandas as pd
import numpy as np
import os
import io
import yfinance as yf
from datetime import datetime
from collections import defaultdict
import copy
import logging

from option_auditor.common.price_utils import normalize_ticker, fetch_live_prices
from option_auditor.common.data_utils import fetch_batch_data_safe, prepare_data_for_ticker
from option_auditor.risk_analyzer import check_itm_risk, calculate_discipline_score
from option_auditor.risk_intelligence import get_market_regime
from option_auditor.parsers import detect_broker
from option_auditor.monte_carlo_simulator import run_simple_monte_carlo

logger = logging.getLogger(__name__)

def _calculate_drawdown(strategies: List[Any]) -> float:
    """Returns Max Drawdown ($) based on closed equity curve."""
    if not strategies:
        return 0.0

    sorted_strats = sorted(strategies, key=lambda s: s.exit_ts if s.exit_ts else pd.Timestamp.max)

    cumulative = 0.0
    peak = -float('inf') # Start with effectively no peak
    max_dd = 0.0

    # We want to track peak of the cumulative PnL
    # If we start at 0.
    peak = 0.0

    for s in sorted_strats:
        if s.exit_ts:
            cumulative += s.net_pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

    return max_dd

def _calculate_monthly_income(strategies: List[Any]) -> List[Dict]:
    """Aggregates Net PnL by Month-Year of exit."""
    monthly_map = defaultdict(float)

    for s in strategies:
        if s.exit_ts:
            key = s.exit_ts.strftime("%Y-%m")
            monthly_map[key] += s.net_pnl

    sorted_keys = sorted(monthly_map.keys())
    return [{"month": k, "income": round(monthly_map[k], 2)} for k in sorted_keys]

def _calculate_portfolio_curve(strategies: List[Any]) -> List[Dict]:
    """Returns cumulative PnL time series with daily trade details."""
    data_points = []
    cumulative = 0.0

    # Sort by exit date
    sorted_strats = [s for s in strategies if s.exit_ts]
    sorted_strats.sort(key=lambda s: s.exit_ts)

    if not sorted_strats:
        return []

    # Initial point (optional, but good for chart)
    first_ts = sorted_strats[0].exit_ts - pd.Timedelta(days=1)
    data_points.append({"x": first_ts.isoformat(), "y": 0.0, "trades": []})

    # Group trades by date to avoid multiple points per day (which chart.js handles, but nicer to aggregate for tooltip)
    daily_groups = defaultdict(list)
    for s in sorted_strats:
        date_key = s.exit_ts.date() # Group by date
        daily_groups[date_key].append(s)

    sorted_dates = sorted(daily_groups.keys())

    for d in sorted_dates:
        strats_for_day = daily_groups[d]
        daily_pnl = 0.0
        daily_trades = []

        # Identify top contributors (e.g., top 3 biggest moves)
        strats_for_day.sort(key=lambda x: abs(x.net_pnl), reverse=True)

        for s in strats_for_day:
            daily_pnl += s.net_pnl
            if len(daily_trades) < 5: # Limit to top 5 trades per day in tooltip
                symbol = s.symbol
                strat = s.strategy_name
                amt = s.net_pnl
                daily_trades.append(f"{symbol} {strat}: ${amt:.0f}")

        if len(strats_for_day) > 5:
            remaining = len(strats_for_day) - 5
            daily_trades.append(f"...and {remaining} more")

        cumulative += daily_pnl
        data_points.append({
            "x": d.isoformat(),
            "y": float(f"{cumulative:.2f}"),
            "trades": daily_trades
        })

    return data_points

def _group_contracts_with_open(legs_df: pd.DataFrame) -> Tuple[List[TradeGroup], List[TradeGroup]]:
    contract_map: Dict[str, List[TradeGroup]] = {}
    closed_groups: List[TradeGroup] = []
    legs_df = legs_df.sort_values("datetime")
    for _, row in legs_df.iterrows():
        cid = row["contract_id"]
        if cid not in contract_map:
            contract_map[cid] = []
        matched = False
        for g in contract_map[cid]:
            if not g.is_closed:
                if (g.qty_net > 0 and row["qty"] < 0) or (g.qty_net < 0 and row["qty"] > 0):
                    g.add_leg(Leg(ts=row["datetime"], qty=row["qty"], price=0, fees=row["fees"], proceeds=row["proceeds"]))
                    matched = True
                    if g.is_closed:
                        closed_groups.append(g)
                    break
        if not matched:
            ng = TradeGroup(
                contract_id=cid, symbol=row["symbol"], expiry=row["expiry"],
                strike=row["strike"], right=row["right"]
            )
            ng.add_leg(Leg(ts=row["datetime"], qty=row["qty"], price=0, fees=row["fees"], proceeds=row["proceeds"]))
            contract_map[cid].append(ng)
    open_groups: List[TradeGroup] = []
    for lst in contract_map.values():
        for g in lst:
            if not g.is_closed:
                open_groups.append(g)
    return closed_groups, open_groups

def _sym_desc(sym: str) -> str:
    if not isinstance(sym, str):
        return ""
    key = sym.upper()
    human = SYMBOL_DESCRIPTIONS.get(key)
    if human:
        return f"Options on {human}"
    return f"Options on {key}"

def _format_legs(strat) -> str:
    """Extracts a concise string of strikes involved in the strategy."""
    # Collect unique contract descriptions (e.g. "400P", "150C")
    items = set()
    for leg in strat.legs:
        if leg.strike is not None and leg.right:
            # Formatting: 400.0 -> 400 if whole number
            s_val = f"{leg.strike:.0f}" if leg.strike % 1 == 0 else f"{leg.strike}"
            items.add(f"{s_val}{leg.right}")
        elif leg.right is None: # Stock
            items.add("Stock")

    # Sort for consistency (e.g. puts ascending, calls ascending)
    # Simple alpha sort is good enough for V1 "390P, 400P"
    return "/".join(sorted(list(items)))

def _build_risk_map(open_positions: List[Dict]) -> List[Dict]:
    risk_map = []
    for row in open_positions:
        pnl_proxy = 0.0
        try:
            qty = row.get("qty_open", 0)
            cp = row.get("current_price")
            contract = row.get("contract", "")

            if cp and contract and " " in contract:
                 parts = contract.split(" ")
                 right = parts[0]
                 strike = float(parts[1])

                 moneyness = 0.0
                 if right == 'C':
                     moneyness = (cp - strike) / strike
                 elif right == 'P':
                     moneyness = (strike - cp) / strike

                 if qty > 0:
                     pnl_proxy = moneyness * 100
                 else:
                     pnl_proxy = -moneyness * 100
        except:
            pass

        size = 0.0
        if row.get("avg_price") and row.get("qty_open"):
             size = abs(row["qty_open"]) * 100 * row["avg_price"]

        risk_map.append({
             "symbol": row.get("symbol"),
             "dte": row.get("dte", 0),
             "pnl_pct": round(pnl_proxy, 2),
             "size": round(size, 2),
             "risk_alert": row.get("risk_alert")
        })
    return risk_map

def refresh_dashboard_data(saved_data: Dict) -> Dict:
    """
    Refreshes the 'open_positions' in the saved analysis result with live prices.
    Re-calculates PnL (approx), Risk Alerts, and Verdicts based on new data.
    """
    data = copy.deepcopy(saved_data)
    open_positions = data.get("open_positions", [])

    if not open_positions:
        return data

    # 1. Identify Symbols
    symbols = list({p["symbol"] for p in open_positions if p.get("symbol")})

    # 2. Fetch Live Prices
    norm_map = {s: normalize_ticker(s) for s in symbols}
    live_prices = fetch_live_prices(list(norm_map.values()))

    # Map back to raw symbol
    current_prices = {}
    for raw, norm in norm_map.items():
        if norm in live_prices:
            current_prices[raw] = live_prices[norm]

    # 3. Update Positions & Check Risk
    # We need to re-aggregate per symbol for "Net Intrinsic Exposure" check
    net_exposure_map = defaultdict(float)

    # First pass: Calculate Exposure
    for p in open_positions:
        sym = p["symbol"]
        if sym not in current_prices:
            continue

        cp = current_prices[sym]
        qty = p.get("qty_open", 0)
        strike = p.get("strike") # May be None/NaN if stock?
        # Ensure strike is float if present
        try:
             strike = float(strike) if strike else 0.0
        except:
             strike = 0.0

        right = p.get("contract", "").split(" ")[0] if "contract" in p else ""
        # The 'contract' field is like "P 400.0" or "C 150.0" or just "Stock" (if constructed that way)
        # Actually 'contract' in open_rows is "P 400.0" or "C 150.0".
        # But 'right' might not be explicitly stored in open_rows?
        # Wait, 'open_rows' has 'contract' which is built from 'right' and 'strike'.
        # AND check if 'right' is in the dict? No.
        # We need to parse 'contract' string "P 400.0".

        is_put = "P " in p["contract"]
        is_call = "C " in p["contract"]

        intrinsic = 0.0
        if is_call:
            intrinsic = max(0.0, cp - strike) * qty * 100
        elif is_put:
            intrinsic = max(0.0, strike - cp) * qty * 100
        else:
             # Stock
             intrinsic = cp * qty

        net_exposure_map[sym] += intrinsic

    # Second pass: Update Row
    itm_risk_flag = False
    itm_risk_details = []
    total_risk_amt = 0.0

    for sym, net_val in net_exposure_map.items():
        if net_val < -500:
            itm_risk_flag = True
            total_risk_amt += abs(net_val)
            itm_risk_details.append(f"{sym}: Net ITM Exposure -${abs(net_val):,.0f}")

    for p in open_positions:
        sym = p["symbol"]
        p["current_price"] = current_prices.get(sym)

        # Clear old alerts
        if "risk_alert" in p:
            del p["risk_alert"]

        # Re-check DTE
        # p["expiry"] is ISO string "YYYY-MM-DD"
        dte = 0
        if p.get("expiry"):
             try:
                 exp_dt = datetime.fromisoformat(p["expiry"])
                 dte = (exp_dt - datetime.now()).days
                 p["dte"] = dte
             except Exception as e:
                 logger.debug(f"Failed to parse expiry {p.get('expiry')}: {e}")

        if dte <= 0:
            p["risk_alert"] = "Expiring Today"
        elif dte <= 3:
            p["risk_alert"] = "Gamma Risk (<3d)"

        # ITM Risk Alert (Row level)
        if itm_risk_flag and sym in current_prices:
             # Check if this specific leg is the problem
             cp = current_prices[sym]
             qty = p.get("qty_open", 0)
             if qty < 0 and " " in p.get("contract", ""):
                  # Parse strike again
                  parts = p["contract"].split(" ")
                  if len(parts) >= 2:
                       try:
                           strike = float(parts[1])
                           right = parts[0]
                           is_risky = False
                           if right == 'P' and cp < strike and (strike-cp)/strike > 0.01:
                               is_risky = True
                           elif right == 'C' and cp > strike and (cp-strike)/strike > 0.01:
                               is_risky = True

                           if is_risky:
                               p["risk_alert"] = "ITM Risk"
                       except Exception as e:
                           logger.debug(f"Failed to check ITM risk for {p}: {e}")

    # Update Verdict if Risk Changed
    if itm_risk_flag:
        data["verdict"] = "Red Flag: High Open Risk"
        data["verdict_color"] = "red"
        data["verdict_details"] = f"Warning: {len(itm_risk_details)} positions are deep ITM. Total Intrinsic Exposure: -${total_risk_amt:,.2f}."

    # --- NEW: Calculate Discipline Score & Risk Map ---
    # We need strategies for discipline score. They are in saved_data["strategy_groups"] (serialized)
    # But we need strategy objects or at least the dicts to check revenge/hold.
    # saved_data["strategy_groups"] is list of dicts. _calculate_discipline_score expects objects?
    # No, let's adapt _calculate_discipline_score to handle dicts or make a new version.
    # Actually, let's just use the serialized data since we don't have objects in refresh.

    # Check if we can adapt _calculate_discipline_score.
    # It accesses: s.is_revenge, s.net_pnl, s.hold_days().
    # The dict has: "is_revenge", "pnl" (net), "hold_days".
    # So we can wrap them in a simple class or modify the function.

    # I'll modify _calculate_discipline_score to handle dicts duck-typing style.

    class StrategyProxy:
        def __init__(self, d):
            self.is_revenge = d.get("is_revenge", False)
            self.net_pnl = d.get("pnl", 0.0)
            self._hold_days = d.get("hold_days", 0.0)
            self.strategy_name = d.get("strategy", "Unclassified")
            self.exit_ts = pd.to_datetime(d.get("exit_ts")) if d.get("exit_ts") else None
            self.entry_ts = pd.to_datetime(d.get("entry_ts")) if d.get("entry_ts") else None

        def hold_days(self):
            return self._hold_days

    strat_proxies = [StrategyProxy(s) for s in data.get("strategy_groups", [])]

    d_score, d_details = calculate_discipline_score(strat_proxies, open_positions)
    data["discipline_score"] = d_score
    data["discipline_details"] = d_details

    # Risk Map Generation
    data["risk_map"] = _build_risk_map(open_positions)

    # --- NEW: Market Regime ---
    try:
        # Fetch SP500 data (2 years)
        # Using fetch_batch_data_safe to handle retries and safety
        sp500_batch = fetch_batch_data_safe(["^GSPC"], period="2y", interval="1d")

        # Prepare single ticker DF
        sp500_df = prepare_data_for_ticker(
            "^GSPC",
            sp500_batch,
            time_frame="1d",
            period="2y",
            yf_interval="1d",
            resample_rule=None,
            is_intraday=False
        )

        regime = get_market_regime(sp500_df)
        data["market_regime"] = regime
    except Exception as e:
        logger.error(f"Failed to determine market regime: {e}")
        data["market_regime"] = "Unknown (Error)"

    return data

def analyze_csv(csv_path: Optional[str] = None,
                broker: str = "auto",
                account_size_start: Optional[float] = None,
                net_liquidity_now: Optional[float] = None,
                buying_power_available_now: Optional[float] = None,
                out_dir: Optional[str] = None, report_format: str = "all",
                start_date: Optional[str] = None, end_date: Optional[str] = None,
                manual_data: Optional[List[Dict[str, Any]]] = None,
                global_fees: Optional[float] = None,
                style: str = "income",
                max_fee_drag: Optional[float] = None,
                stop_loss_limit: Optional[float] = None) -> Dict:
    
    # 1. Load Data
    df = pd.DataFrame()
    parser = None
    chosen_broker = broker

    if csv_path:
        try:
            df = pd.read_csv(csv_path)
        except pd.errors.EmptyDataError:
            return {"error": "CSV file is empty"}
        except Exception as e:
            return {"error": f"Failed to read CSV: {str(e)}"}

        if broker == "auto" or broker is None:
            chosen_broker = detect_broker(df) or "tasty"
        else:
            # Respect explicit choice if provided
            chosen_broker = broker

        if chosen_broker == "tasty":
            if "Description" in df.columns and "Symbol" in df.columns:
                parser = TastytradeFillsParser()
            else:
                parser = TastytradeParser()
        elif chosen_broker == "ibkr":
            parser = IBKRParser()
        else:
            return {"error": "Unsupported broker"}

    elif manual_data:
        df = pd.DataFrame(manual_data)
        chosen_broker = "manual"
        parser = ManualInputParser()
    else:
        return {"error": "No input data provided"}

    # 2. Parse Data
    try:
        norm_df = parser.parse(df)
    except Exception as e:
        return {"error": str(e)}

    # Apply global_fees logic (Fee per Trade)
    if global_fees is not None:
        try:
            fee_val = float(global_fees)
            if not norm_df.empty:
                if manual_data:
                    norm_df["fees"] = fee_val
                else:
                    norm_df["fees"] = norm_df["fees"].fillna(0.0) + fee_val
            global_fees = None
        except (ValueError, TypeError):
            pass

    if norm_df.empty:
        return {"error": "No options trades found"}

    # 3. Filter by Date Window
    effective_window = None
    if start_date or end_date:
        s = pd.to_datetime(start_date) if start_date else None
        e = pd.to_datetime(end_date) if end_date else None
        dt = pd.to_datetime(norm_df["datetime"], errors="coerce")
        mask = pd.Series([True] * len(norm_df))
        if s:
            mask &= (dt >= pd.Timestamp(s.date()))
        if e:
            mask &= (dt <= (pd.Timestamp(e.date()) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)))
        norm_df = norm_df[mask].copy()
        effective_window = {
            "start": s.date().isoformat() if s is not None else None,
            "end": (e - pd.Timedelta(days=0)).date().isoformat() if e is not None else None,
        }

    # 4. Grouping & Strategy Logic
    contract_groups, open_groups = _group_contracts_with_open(norm_df)
    strategies = build_strategies(norm_df)

    # 4b. Behavioral Analysis: Detect Revenge Trading
    # Sort by entry time to ensure chronological checking
    strategies.sort(key=lambda s: s.entry_ts if s.entry_ts else pd.Timestamp.min)

    # Map to track the last exit time and result for each symbol
    last_trade_map = {}

    for s in strategies:
        s.is_revenge = False  # Initialize flag

        if s.symbol in last_trade_map:
            last_exit, last_pnl = last_trade_map[s.symbol]

            if s.entry_ts and last_exit:
                # Calculate time gap in minutes
                diff_mins = (s.entry_ts - last_exit).total_seconds() / 60.0

                # CRITERIA:
                # 1. Same Symbol (Already checked by map key)
                # 2. Previous trade was a LOSS (last_pnl < 0)
                # 3. Opened within 30 minutes of closing the loser
                if last_pnl < 0 and 0 <= diff_mins <= 30:
                    s.is_revenge = True

        # Update map for the next iteration if this trade is closed
        if s.exit_ts:
            last_trade_map[s.symbol] = (s.exit_ts, s.net_pnl)
    
    # 5. Live Risk Analysis
    live_prices = {}
    itm_risk_flag = False
    itm_risk_details = []
    itm_risk_amount = 0.0
    missing_data_warning = []  # NEW: Track missing symbols
    data_integrity_failure = False

    if open_groups:
        try:
            # 1. Identify symbols needed
            raw_symbols = list({g.symbol for g in open_groups if g.symbol})

            # 2. Create a map of Raw -> Normalized
            sym_map = {raw: normalize_ticker(raw) for raw in raw_symbols}

            # 3. Fetch prices using NORMALIZED symbols
            fetched_prices = fetch_live_prices(list(sym_map.values()))

            # 4. Map back to raw symbols for the risk check logic
            for raw, norm in sym_map.items():
                if norm in fetched_prices:
                    live_prices[raw] = fetched_prices[norm]
                else:
                    missing_data_warning.append(raw) # Track failures

            if raw_symbols and len(missing_data_warning) / len(raw_symbols) > 0.20:
                data_integrity_failure = True

            itm_risk_flag, itm_risk_amount, itm_risk_details = check_itm_risk(open_groups, live_prices)

        except Exception as e:
            # Log error if needed
            logger.warning(f"Live price fetch failed: {e}")
            pass

    # 6. Metrics Calculation
    total_strategy_pnl_gross = sum(s.pnl for s in strategies)
    total_strategy_fees = sum(s.fees for s in strategies)
    total_strategy_pnl_net = total_strategy_pnl_gross - total_strategy_fees

    efficiency_ratio = total_strategy_pnl_net / total_strategy_fees if total_strategy_fees > 0 else 0

    leakage_metrics = {
        "fee_drag": 0.0,
        "fee_drag_verdict": "OK",
        "stale_capital": [],
        "efficiency_ratio": efficiency_ratio
    }

    broker_alert = None
    if total_strategy_pnl_gross > 0:
        fee_drag = (total_strategy_fees / total_strategy_pnl_gross) * 100
        leakage_metrics["fee_drag"] = round(fee_drag, 2)
        if max_fee_drag is not None and fee_drag > max_fee_drag:
            leakage_metrics["fee_drag_verdict"] = "Broker Alert: Fee Drag Exceeds Limit"
            broker_alert = "Fee Drag Exceeds User Limit"
        elif fee_drag > 10.0:
            leakage_metrics["fee_drag_verdict"] = "High Drag! Stop trading 1-wide spreads."
    else:
        leakage_metrics["fee_drag"] = 0.0

    for s in strategies:
        hd = s.hold_days()
        th = s.average_daily_pnl()
        if hd > 10.0 and th < 1.0:
            leakage_metrics["stale_capital"].append({
                "strategy": s.strategy_name,
                "symbol": s.symbol,
                "hold_days": round(hd, 1),
                "average_daily_pnl": round(th, 2),
                "pnl": round(s.net_pnl, 2)
            })

    wins_contracts = [g for g in contract_groups if g.net_pnl > 0]
    win_rate_contracts = len(wins_contracts) / len(contract_groups) if contract_groups else 0.0
    avg_hold_contracts = np.mean([
        (g.exit_ts - g.entry_ts).total_seconds() / 86400.0 if g.entry_ts and g.exit_ts else 0.0
        for g in contract_groups
    ]) if contract_groups else 0.0

    wins = [s for s in strategies if s.net_pnl > 0]
    losses = [s for s in strategies if s.net_pnl <= 0]
    win_rate = len(wins) / len(strategies) if strategies else 0.0
    
    avg_win = float(np.mean([s.net_pnl for s in wins])) if wins else 0.0
    avg_loss = float(np.mean([s.net_pnl for s in losses])) if losses else 0.0

    expectancy = (avg_win * win_rate) + (avg_loss * (1 - win_rate))

    max_drawdown = _calculate_drawdown(strategies)
    monthly_income = _calculate_monthly_income(strategies)
    portfolio_curve = _calculate_portfolio_curve(strategies)

    # --- NEW: Monte Carlo Integration ---
    monte_carlo_results = {}

    # Only run if we have a valid starting account size (from inputs or inference)
    # Default to $10,000 if not provided, just to show the curve relative to 0
    sim_start_equity = net_liquidity_now if net_liquidity_now else (account_size_start if account_size_start else 10000.0)

    if len(strategies) >= 10:
        monte_carlo_results = run_simple_monte_carlo(
            strategies,
            start_equity=sim_start_equity,
            num_sims=1000,
            forecast_trades=50  # Project next 50 trades
        )
    else:
        monte_carlo_results = {"status": "Insufficient data (need 10+ trades)"}

    verdict = "Green Flag"
    verdict_color = "green"

    if style == "speculation":
        if total_strategy_pnl_net < 0:
            verdict = "Red Flag: Negative PnL"
            verdict_color = "red"
        elif win_rate < 0.35:
            verdict = "Amber: Low Win Rate"
            verdict_color = "yellow"
        elif leakage_metrics["fee_drag"] > 15.0:
            verdict = "Amber: High Fee Drag"
            verdict_color = "yellow"
    else:
        if total_strategy_pnl_net < 0:
            verdict = "Red Flag: Negative Income"
            verdict_color = "red"
        elif win_rate < 0.60:
            verdict = "Red Flag: Win Rate < 60%"
            verdict_color = "red"
        elif leakage_metrics["fee_drag"] > 10.0:
            verdict = "Amber: Fee Drag > 10%"
            verdict_color = "yellow"
        elif max_drawdown > (total_strategy_pnl_gross * 0.5) and total_strategy_pnl_gross > 0:
            verdict = "Amber: High Drawdown"
            verdict_color = "yellow"

    if len(strategies) < VERDICT_MIN_TRADES:
        verdict = f"Insufficient Data (Need {VERDICT_MIN_TRADES}+ Trades)"
        verdict_color = "gray"

    # OVERRIDE: ITM Risk Detection
    # If high risk is detected in open positions, it supersedes all other verdicts.
    verdict_details = None

    if data_integrity_failure:
        verdict = "Red Flag: Data Integrity Failure"
        verdict_color = "red"
        verdict_details = "Critical: >20% of symbols failed to fetch live prices."
    elif itm_risk_flag:
        verdict = "Red Flag: High Open Risk"
        verdict_color = "red"
        verdict_details = f"Warning: {len(itm_risk_details)} positions are deep ITM. Total Intrinsic Exposure: -${itm_risk_amount:,.2f}."

    # NEW: Data Integrity Warning
    elif missing_data_warning:
        verdict = "Amber: Data Unavailable"
        verdict_color = "yellow"
        verdict_details = f"Could not fetch live prices for: {', '.join(missing_data_warning[:3])}. Risk not assessed."

    sym_stats = {}
    for s in strategies:
        if s.symbol not in sym_stats:
            sym_stats[s.symbol] = {'pnl': 0.0, 'trades': 0, 'wins': 0}
        sym_stats[s.symbol]['pnl'] += s.net_pnl
        sym_stats[s.symbol]['trades'] += 1
        if s.net_pnl > 0: sym_stats[s.symbol]['wins'] += 1

    symbols_list = sorted([
        {"symbol": k, "pnl": v['pnl'], "win_rate": v['wins'] / v['trades'], "trades": v['trades'], "description": _sym_desc(k)}
        for k, v in sym_stats.items()
    ], key=lambda x: x['pnl'], reverse=True)

    strategy_rows = []
    for s in strategies:
        # Generate the description (NEW)
        legs_desc = _format_legs(s)

        row = {
            "symbol": s.symbol,
            "expiry": s.expiry.date().isoformat() if s.expiry and not pd.isna(s.expiry) else "",
            "strategy": s.strategy_name,
            "entry_ts": s.entry_ts.isoformat() if s.entry_ts else None,
            "exit_ts": s.exit_ts.isoformat() if s.exit_ts else None,
            "legs_desc": legs_desc,
            "pnl": s.net_pnl,
            "gross_pnl": s.pnl,
            "fees": s.fees,
            "hold_days": s.hold_days(),
            "average_daily_pnl": s.average_daily_pnl(),
            "is_revenge": getattr(s, "is_revenge", False),
            "description": _sym_desc(s.symbol),
            "segments": [
                {
                    "strategy_name": seg["strategy_name"],
                    "pnl": seg["pnl"],
                    "entry_ts": seg["entry_ts"].isoformat() if seg["entry_ts"] else "",
                    "exit_ts": seg["exit_ts"].isoformat() if seg["exit_ts"] else ""
                } for seg in s.segments
            ]
        }
        strategy_rows.append(row)

    open_rows = []

    # Aggregation step: Combine open groups by contract_id
    aggregated_open = {}
    for g in open_groups:
        cid = g.contract_id
        if cid not in aggregated_open:
            aggregated_open[cid] = {
                "symbol": g.symbol,
                "expiry": g.expiry,
                "strike": g.strike,
                "right": g.right,
                "qty_net": 0.0,
                "pnl": 0.0,
                "entry_ts": g.entry_ts,
                "contract_id": cid
            }

        agg = aggregated_open[cid]
        agg["qty_net"] += g.qty_net
        agg["pnl"] += g.pnl
        # Keep earliest entry time for "Days Open"
        if g.entry_ts and (agg["entry_ts"] is None or g.entry_ts < agg["entry_ts"]):
            agg["entry_ts"] = g.entry_ts

    sorted_aggs = sorted(aggregated_open.values(), key=lambda x: x["entry_ts"] or pd.Timestamp.min)

    for agg in sorted_aggs:
        qty = agg["qty_net"]
        pnl = agg["pnl"]

        # Calculate Average Entry Price (Cost Basis)
        avg_price = 0.0
        breakeven = 0.0
        if abs(qty) > 0:
            avg_price = abs(pnl) / (abs(qty) * 100.0)

            # Calculate Breakeven
            if agg["strike"]:
                if agg["right"] == 'P': # Put
                    breakeven = agg["strike"] - avg_price
                elif agg["right"] == 'C': # Call
                    breakeven = agg["strike"] + avg_price

        # NEW: Get Current Price for context
        current_mark = live_prices.get(agg["symbol"])

        # Calculate DTE
        dte = None
        if agg["expiry"] and not pd.isna(agg["expiry"]):
            # Calculate difference in days between Expiry and Now
            delta = agg["expiry"] - pd.Timestamp.now()
            dte = delta.days
            # If expired today or in past, set to 0 or negative
            if dte < 0: dte = 0

        row = {
            "symbol": agg["symbol"],
            "current_price": current_mark,
            "expiry": agg["expiry"].date().isoformat() if agg["expiry"] and not pd.isna(agg["expiry"]) else "",
            "contract": f"{agg['right'] or ''} {agg['strike']}",
            "qty_open": qty,
            "avg_price": avg_price,
            "breakeven": breakeven,
            "dte": dte,
            "opened": agg["entry_ts"].isoformat() if agg["entry_ts"] else "",
            "days_open": (pd.Timestamp(datetime.now()) - agg["entry_ts"]).total_seconds() / 86400.0 if agg["entry_ts"] else 0.0,
            "description": _sym_desc(agg["symbol"])
        }

        # Add risk annotation if applicable
        # Extract risky symbols from details
        risky_symbols = set()
        if itm_risk_details:
             risky_symbols = {d.split(":")[0] for d in itm_risk_details}

        if itm_risk_flag and agg["symbol"] in risky_symbols:
            if agg["symbol"] in live_prices and agg["strike"] and qty < 0:
                cp = live_prices[agg["symbol"]]
                is_risky_pos = False
                if agg["right"] == 'P' and cp < agg["strike"]:
                    if (agg["strike"] - cp)/agg["strike"] > 0.01: is_risky_pos = True
                elif agg["right"] == 'C' and cp > agg["strike"]:
                    if (cp - agg["strike"])/agg["strike"] > 0.01: is_risky_pos = True

                if is_risky_pos:
                    row["risk_alert"] = "ITM Risk"

        # Gamma/Expiration Risk Check (If not already flagged as ITM)
        if "risk_alert" not in row and dte is not None:
            if dte <= 0:
                row["risk_alert"] = "Expiring Today"
            elif dte <= 3:
                row["risk_alert"] = "Gamma Risk (<3d)"

        open_rows.append(row)

    buying_power_utilized_percent = None
    if net_liquidity_now is not None and buying_power_available_now is not None and net_liquidity_now > 0:
        buying_power_utilized_percent = (net_liquidity_now - buying_power_available_now) / net_liquidity_now * 100

    position_sizing = []
    if open_groups and net_liquidity_now and net_liquidity_now > 0:
        open_by_symbol = {}
        for g in open_groups:
            if g.symbol not in open_by_symbol:
                open_by_symbol[g.symbol] = []
            open_by_symbol[g.symbol].append(g)

        for sym, groups in open_by_symbol.items():
            total_cost = 0.0
            for g in groups:
                entry_val = sum(l.proceeds for l in g.legs)
                total_cost += abs(entry_val)

            allocation_pct = (total_cost / net_liquidity_now) * 100
            position_sizing.append({
                "symbol": sym,
                "allocation_amt": round(total_cost, 2),
                "allocation_pct": round(allocation_pct, 2),
                "description": _sym_desc(sym)
            })

        position_sizing.sort(key=lambda x: x["allocation_pct"], reverse=True)

    excel_buffer = None
    if report_format == "all" or report_format == "excel":
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            summary_rows = [
                {"Metric": "Strategy Trades", "Value": len(strategies)},
                {"Metric": "Strategy Win Rate", "Value": win_rate},
                {"Metric": "Strategy Total PnL (Net)", "Value": total_strategy_pnl_net},
                {"Metric": "Strategy Total Fees", "Value": total_strategy_fees},
                {"Metric": "Verdict", "Value": verdict},
                {"Metric": "Fee Drag %", "Value": leakage_metrics["fee_drag"]},
            ]
            if account_size_start is not None: summary_rows.append({"Metric": "Account Size (Start)", "Value": account_size_start})
            if net_liquidity_now is not None: summary_rows.append({"Metric": "Net Liquidity (Now)", "Value": net_liquidity_now})
            if buying_power_utilized_percent is not None:
                summary_rows.append({"Metric": "Buying Power Utilized", "Value": f"{buying_power_utilized_percent:.1f}%"})
            
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)
            pd.DataFrame(symbols_list).to_excel(writer, sheet_name="Symbols", index=False)
            pd.DataFrame(strategy_rows).to_excel(writer, sheet_name="Strategies", index=False)
            pd.DataFrame(open_rows).to_excel(writer, sheet_name="Open Positions", index=False)
            pd.DataFrame(leakage_metrics["stale_capital"]).to_excel(writer, sheet_name="Stale Capital", index=False)
        excel_buffer.seek(0)

    # --- NEW: Calculate Discipline Score & Risk Map ---
    d_score, d_details = calculate_discipline_score(strategies, open_rows)
    risk_map = _build_risk_map(open_rows)

    response = {
        "discipline_score": d_score,
        "discipline_details": d_details,
        "risk_map": risk_map,
        "metrics": {
            "num_trades": len(contract_groups), "win_rate": win_rate_contracts,
            "total_pnl": total_strategy_pnl_net,
            "total_fees": total_strategy_fees,
            "avg_hold_days": avg_hold_contracts,
        },
        "strategy_metrics": {
            "num_trades": len(strategies),
            "win_rate": win_rate,
            "total_pnl": total_strategy_pnl_net,
            "total_gross_pnl": total_strategy_pnl_gross,
            "total_fees": total_strategy_fees,
            "max_drawdown": max_drawdown,
            "expectancy": expectancy
        },
        "verdict": verdict,
        "verdict_color": verdict_color,
        "verdict_details": verdict_details,
        "symbols": symbols_list,
        "strategy_groups": strategy_rows,
        "open_positions": open_rows,
        "broker": chosen_broker,
        "date_window": effective_window,
        "account_size_start": account_size_start,
        "net_liquidity_now": net_liquidity_now,
        "buying_power_utilized_percent": buying_power_utilized_percent,
        "position_sizing": position_sizing,
        "leakage_report": leakage_metrics,
        "monthly_income": monthly_income,
        "portfolio_curve": portfolio_curve,
        "monte_carlo": monte_carlo_results,
        "excel_report": excel_buffer
    }

    if broker_alert:
        response["broker_alert"] = broker_alert

    return response
