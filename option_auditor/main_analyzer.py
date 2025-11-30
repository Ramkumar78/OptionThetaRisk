from .parsers import TastytradeParser, TastytradeFillsParser
from .strategy import build_strategies
from .models import TradeGroup, Leg
from .config import SYMBOL_DESCRIPTIONS
from typing import Optional, Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

def _detect_broker(df: pd.DataFrame) -> Optional[str]:
    cols = {c.strip(): True for c in df.columns}
    if "Underlying Symbol" in cols:
        return "tasty"
    if "Description" in cols and "Symbol" in cols:
        return "tasty_fills"
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

def analyze_csv(csv_path: str, broker: str = "auto",
                account_size_start: Optional[float] = None,
                net_liquidity_now: Optional[float] = None,
                buying_power_available_now: Optional[float] = None,
                out_dir: Optional[str] = "out", report_format: str = "all",
                start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    df = pd.read_csv(csv_path)
    chosen_broker = broker
    if broker == "auto" or broker is None:
        chosen_broker = _detect_broker(df) or "tasty"
    
    parser = None
    if chosen_broker == "tasty":
        parser = TastytradeParser()
    elif chosen_broker == "tasty_fills":
        parser = TastytradeFillsParser()
    else:
        return {"error": "Unsupported broker"}

    norm_df = parser.parse(df)
    if norm_df.empty:
        return {"error": "No options trades found"}

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

    contract_groups, open_groups = _group_contracts_with_open(norm_df)
    strategies = build_strategies(norm_df)
    
    total_pnl = sum(s.pnl for s in strategies)
    win_rate = len([s for s in strategies if s.pnl > 0]) / len(strategies) if strategies else 0.0
    
    verdict = "Green flag"
    if total_pnl < 0 or win_rate < 0.3:
        verdict = "Red flag"
    elif win_rate < 0.5:
        verdict = "Amber"

    buying_power_utilized_percent = None
    if net_liquidity_now is not None and buying_power_available_now is not None and net_liquidity_now > 0:
        buying_power_utilized_percent = (net_liquidity_now - buying_power_available_now) / net_liquidity_now * 100

    return {
        "verdict": verdict,
        "symbols": sorted([{"symbol": k, "pnl": v['pnl'], "win_rate": v['wins'] / v['trades'], "trades": v['trades'], "description": _sym_desc(k)} for k, v in pd.DataFrame([s.__dict__ for s in strategies]).groupby("symbol").apply(lambda x: {"pnl": x.pnl.sum(), "wins": (x.pnl > 0).sum(), "trades": len(x)}).to_dict().items()], key=lambda x: x['pnl'], reverse=True),
        "strategy_groups": [{"symbol": s.symbol, "expiry": s.expiry.date().isoformat() if s.expiry and not pd.isna(s.expiry) else "", "strategy": s.strategy_name, "pnl": s.pnl, "hold_days": s.hold_days(), "theta_per_day": s.realized_theta(), "description": _sym_desc(s.symbol)} for s in strategies],
        "open_positions": [{"symbol": g.symbol, "expiry": g.expiry.date().isoformat() if g.expiry and not pd.isna(g.expiry) else "", "contract": f"{g.right or ''} {g.strike}", "qty_open": g.qty_net, "opened": g.entry_ts.isoformat() if g.entry_ts else "", "days_open": (pd.Timestamp(datetime.now()) - g.entry_ts).total_seconds() / 86400.0 if g.entry_ts else 0.0, "description": _sym_desc(g.symbol)} for g in sorted(open_groups, key=lambda x: x.entry_ts or pd.Timestamp.min)],
        "account_size_start": account_size_start,
        "net_liquidity_now": net_liquidity_now,
        "buying_power_utilized_percent": buying_power_utilized_percent,
    }
