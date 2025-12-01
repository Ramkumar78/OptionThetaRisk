from .parsers import TastytradeParser, TastytradeFillsParser, ManualInputParser
from .strategy import build_strategies
from .models import TradeGroup, Leg
from .config import SYMBOL_DESCRIPTIONS
from typing import Optional, Dict, List, Tuple, Any, Union
import pandas as pd
import numpy as np
import os
import yfinance as yf
from datetime import datetime

def _detect_broker(df: pd.DataFrame) -> Optional[str]:
    cols = {c.strip(): True for c in df.columns}
    if "Underlying Symbol" in cols:
        return "tasty"
    if "Description" in cols and "Symbol" in cols:
        return "tasty"
    return None

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

def analyze_csv(csv_path: Optional[str] = None,
                broker: str = "auto",
                account_size_start: Optional[float] = None,
                net_liquidity_now: Optional[float] = None,
                buying_power_available_now: Optional[float] = None,
                out_dir: Optional[str] = "out", report_format: str = "all",
                start_date: Optional[str] = None, end_date: Optional[str] = None,
                manual_data: Optional[List[Dict[str, Any]]] = None,
                global_fees: Optional[float] = None) -> Dict: # Added global_fees
    
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
            chosen_broker = _detect_broker(df) or "tasty"

        if chosen_broker == "tasty":
            if "Description" in df.columns and "Symbol" in df.columns:
                parser = TastytradeFillsParser()
            else:
                parser = TastytradeParser()
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

    # Apply fee_per_trade logic for manual entries
    # If manual_data is present, global_fees is treated as 'Fee per Trade' and applied to each row.
    if manual_data and global_fees is not None:
        try:
            fee_val = float(global_fees)
            if not norm_df.empty:
                norm_df["fees"] = fee_val
            # Clear global_fees so it's not added again as a lump sum later
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
    
    # 5. Metrics Calculation
    leakage_metrics = {
        "fee_drag": 0.0,
        "fee_drag_verdict": "OK",
        "stale_capital": []
    }

    # Use PnL (Gross) and Fees to calculate everything
    total_strategy_pnl_gross = sum(s.pnl for s in strategies)

    # Fees: Sum strategy fees + global fees
    strategy_sum_fees = sum(s.fees for s in strategies)
    total_strategy_fees = strategy_sum_fees
    if global_fees:
        total_strategy_fees += float(global_fees)

    total_strategy_pnl_net = total_strategy_pnl_gross - total_strategy_fees

    # Fee Drag: Fees / Gross Profit (where Gross Profit = Net + Fees, or just our s.pnl)
    # If Gross PnL is positive
    if total_strategy_pnl_gross > 0:
        fee_drag = (total_strategy_fees / total_strategy_pnl_gross) * 100
        leakage_metrics["fee_drag"] = round(fee_drag, 2)
        if fee_drag > 10.0:
            leakage_metrics["fee_drag_verdict"] = "High Drag! Stop trading 1-wide spreads."
    else:
        leakage_metrics["fee_drag"] = 0.0

    # Stale Capital
    for s in strategies:
        hd = s.hold_days()
        th = s.realized_theta() # This uses net_pnl / days (but s.net_pnl doesn't include global fees)
        # Should we distribute global fees? No, keep it simple.
        if hd > 10.0 and th < 1.0:
            leakage_metrics["stale_capital"].append({
                "strategy": s.strategy_name,
                "symbol": s.symbol,
                "hold_days": round(hd, 1),
                "theta_per_day": round(th, 2),
                "pnl": round(s.net_pnl, 2)
            })

    # Contract Metrics
    # Contract groups also have individual fees.
    # We should add global fees to the aggregate total.
    total_pnl_contracts_gross = float(sum(g.pnl for g in contract_groups))
    # We can't easily attribute global fees to specific contract groups without rules.
    # So contract-level PnL sum might differ from "Total PnL" if we subtract global fees.
    # Let's align "Total PnL" metric with Net PnL.

    wins_contracts = [g for g in contract_groups if g.pnl > 0] # Gross logic for individual? or net?
    # TradeGroup.net_pnl exists.
    wins_contracts = [g for g in contract_groups if g.net_pnl > 0]
    win_rate_contracts = len(wins_contracts) / len(contract_groups) if contract_groups else 0.0
    avg_hold_contracts = np.mean([
        (g.exit_ts - g.entry_ts).total_seconds() / 86400.0 if g.entry_ts and g.exit_ts else 0.0
        for g in contract_groups
    ]) if contract_groups else 0.0

    # Win rate logic remains on strategy level
    wins = [s for s in strategies if s.net_pnl > 0]
    win_rate = len(wins) / len(strategies) if strategies else 0.0
    
    verdict = "Green flag"
    if total_strategy_pnl_net < 0:
        verdict = "Red flag"
    elif win_rate < 0.3:
        verdict = "Red flag"
    elif win_rate < 0.5:
        verdict = "Amber"

    # Symbol Breakdown
    sym_stats = {}
    for s in strategies:
        if s.symbol not in sym_stats:
            sym_stats[s.symbol] = {'pnl': 0.0, 'trades': 0, 'wins': 0}
        sym_stats[s.symbol]['pnl'] += s.net_pnl # Use Net
        sym_stats[s.symbol]['trades'] += 1
        if s.net_pnl > 0: sym_stats[s.symbol]['wins'] += 1

    symbols_list = sorted([
        {"symbol": k, "pnl": v['pnl'], "win_rate": v['wins'] / v['trades'], "trades": v['trades'], "description": _sym_desc(k)}
        for k, v in sym_stats.items()
    ], key=lambda x: x['pnl'], reverse=True)

    strategy_rows = []
    for s in strategies:
        row = {
            "symbol": s.symbol,
            "expiry": s.expiry.date().isoformat() if s.expiry and not pd.isna(s.expiry) else "",
            "strategy": s.strategy_name,
            "pnl": s.net_pnl, # Default to Net for UI clarity
            "gross_pnl": s.pnl,
            "fees": s.fees,
            "hold_days": s.hold_days(),
            "theta_per_day": s.realized_theta(),
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

    open_rows = [{"symbol": g.symbol, "expiry": g.expiry.date().isoformat() if g.expiry and not pd.isna(g.expiry) else "", "contract": f"{g.right or ''} {g.strike}", "qty_open": g.qty_net, "opened": g.entry_ts.isoformat() if g.entry_ts else "", "days_open": (pd.Timestamp(datetime.now()) - g.entry_ts).total_seconds() / 86400.0 if g.entry_ts else 0.0, "description": _sym_desc(g.symbol)} for g in sorted(open_groups, key=lambda x: x.entry_ts or pd.Timestamp.min)]

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

    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
            pd.DataFrame([{
                "symbol": g.symbol, "contract_id": g.contract_id,
                "entry_ts": g.entry_ts.isoformat() if g.entry_ts else "",
                "exit_ts": g.exit_ts.isoformat() if g.exit_ts else "", "pnl": g.pnl,
            } for g in contract_groups]).map(
                lambda x: f"'{x}" if isinstance(x, str) and x.startswith(("=", "+", "-", "@")) else x
            ).to_csv(os.path.join(out_dir, "trades.csv"), index=False)

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

            with pd.ExcelWriter(os.path.join(out_dir, "report.xlsx"), engine="openpyxl") as writer:
                pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)
                pd.DataFrame(symbols_list).to_excel(writer, sheet_name="Symbols", index=False)
                pd.DataFrame(strategy_rows).to_excel(writer, sheet_name="Strategies", index=False)
                pd.DataFrame(open_rows).to_excel(writer, sheet_name="Open Positions", index=False)
                pd.DataFrame(leakage_metrics["stale_capital"]).to_excel(writer, sheet_name="Stale Capital", index=False)
        except Exception:
            pass

    return {
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
            "total_fees": total_strategy_fees
        },
        "verdict": verdict,
        "symbols": symbols_list,
        "strategy_groups": strategy_rows,
        "open_positions": open_rows,
        "broker": chosen_broker,
        "date_window": effective_window,
        "account_size_start": account_size_start,
        "net_liquidity_now": net_liquidity_now,
        "buying_power_utilized_percent": buying_power_utilized_percent,
        "position_sizing": position_sizing,
        "leakage_report": leakage_metrics
    }
