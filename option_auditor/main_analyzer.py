from .parsers import TastytradeParser, TastytradeFillsParser
from .strategy import build_strategies
from .models import TradeGroup, Leg
from .config import SYMBOL_DESCRIPTIONS
from typing import Optional, Dict, List, Tuple
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
        # Auto-select parser based on columns even if broker is forced to "tasty"
        if "Description" in df.columns and "Symbol" in df.columns:
            parser = TastytradeFillsParser()
        else:
            parser = TastytradeParser()
    else:
        return {"error": "Unsupported broker"}

    try:
        norm_df = parser.parse(df)
    except Exception as e:
        return {"error": str(e)}

    if norm_df.empty:
        return {"error": "No options trades found"}

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

    contract_groups, open_groups = _group_contracts_with_open(norm_df)
    strategies = build_strategies(norm_df)
    
    # --- Portfolio Correlation ---
    correlation_matrix_df = None
    correlation_json = None

    # Identify unique symbols traded
    unique_symbols = sorted(list(set(g.symbol for g in contract_groups if g.symbol)))

    # We need a start and end date for correlation data fetch
    if unique_symbols:
        min_date = norm_df['datetime'].min()
        max_date = norm_df['datetime'].max()

        # Buffer dates
        start_fetch = (min_date - pd.Timedelta(days=30)).date()
        end_fetch = (max_date + pd.Timedelta(days=1)).date()

        # Only fetch if we have valid symbols and data range
        if unique_symbols:
            try:
                # Fetch data for all symbols at once
                # yfinance expects space-separated string
                tickers_str = " ".join(unique_symbols)

                # Download close data
                # auto_adjust=True accounts for splits/dividends
                history = yf.download(tickers_str, start=start_fetch, end=end_fetch, progress=False, auto_adjust=True)['Close']

                if not history.empty:
                    # If single symbol, history is Series. Convert to DataFrame
                    if isinstance(history, pd.Series):
                        history = history.to_frame(name=unique_symbols[0])

                    # Calculate daily percent change
                    daily_returns = history.pct_change()

                    # Calculate correlation matrix
                    correlation_matrix_df = daily_returns.corr()

                    # Convert to JSON format (list of dicts for heatmap)
                    # We want a format: [{'index': 'SPY', 'SPY': 1.0, 'QQQ': 0.8}, ...]
                    correlation_json = correlation_matrix_df.round(4).reset_index().to_dict(orient='records')
            except Exception:
                # Fallback or ignore if yfinance fails (no internet, bad tickers, etc)
                pass

    # Calc Metrics
    total_pnl_contracts = float(sum(g.pnl for g in contract_groups))
    wins_contracts = [g for g in contract_groups if g.pnl > 0]
    win_rate_contracts = len(wins_contracts) / len(contract_groups) if contract_groups else 0.0
    avg_hold_contracts = np.mean([
        (g.exit_ts - g.entry_ts).total_seconds() / 86400.0 if g.entry_ts and g.exit_ts else 0.0
        for g in contract_groups
    ]) if contract_groups else 0.0

    total_pnl = sum(s.pnl for s in strategies)
    wins = [s for s in strategies if s.pnl > 0]
    win_rate = len(wins) / len(strategies) if strategies else 0.0
    
    verdict = "Green flag"
    if total_pnl < 0:
        verdict = "Red flag"
    elif win_rate < 0.3:
        verdict = "Red flag"
    elif win_rate < 0.5:
        verdict = "Amber"

    # Symbol Breakdown
    sym_stats = {}
    for s in strategies:
        if s.symbol not in sym_stats:
            sym_stats[s.symbol] = {'pnl': 0, 'trades': 0, 'wins': 0}
        sym_stats[s.symbol]['pnl'] += s.pnl
        sym_stats[s.symbol]['trades'] += 1
        if s.pnl > 0: sym_stats[s.symbol]['wins'] += 1

    symbols_list = sorted([
        {"symbol": k, "pnl": v['pnl'], "win_rate": v['wins'] / v['trades'], "trades": v['trades'], "description": _sym_desc(k)}
        for k, v in sym_stats.items()
    ], key=lambda x: x['pnl'], reverse=True)

    strategy_rows = [{"symbol": s.symbol, "expiry": s.expiry.date().isoformat() if s.expiry and not pd.isna(s.expiry) else "", "strategy": s.strategy_name, "pnl": s.pnl, "hold_days": s.hold_days(), "theta_per_day": s.realized_theta(), "description": _sym_desc(s.symbol)} for s in strategies]

    open_rows = [{"symbol": g.symbol, "expiry": g.expiry.date().isoformat() if g.expiry and not pd.isna(g.expiry) else "", "contract": f"{g.right or ''} {g.strike}", "qty_open": g.qty_net, "opened": g.entry_ts.isoformat() if g.entry_ts else "", "days_open": (pd.Timestamp(datetime.now()) - g.entry_ts).total_seconds() / 86400.0 if g.entry_ts else 0.0, "description": _sym_desc(g.symbol)} for g in sorted(open_groups, key=lambda x: x.entry_ts or pd.Timestamp.min)]

    buying_power_utilized_percent = None
    if net_liquidity_now is not None and buying_power_available_now is not None and net_liquidity_now > 0:
        buying_power_utilized_percent = (net_liquidity_now - buying_power_available_now) / net_liquidity_now * 100

    # --- Position Sizing Analysis (Capital Allocation) ---
    # Calculated using pandas
    position_sizing = []
    if open_groups and net_liquidity_now and net_liquidity_now > 0:
        # Group by symbol
        open_by_symbol = {}
        for g in open_groups:
            if g.symbol not in open_by_symbol:
                open_by_symbol[g.symbol] = []
            open_by_symbol[g.symbol].append(g)

        for sym, groups in open_by_symbol.items():
            # Estimate allocation based on entry cost (proceeds < 0 for debits)
            # For credits, proceeds > 0, risk is undefined or margin-based.
            # We use absolute net proceeds as a proxy for "capital involved" to show activity level,
            # but for true sizing, we focus on Debit paid or Credit received as 'exposure'.
            total_cost = 0.0
            for g in groups:
                # Sum of legs proceeds. Negative = Debit paid. Positive = Credit received.
                # Usually sizing is about how much you paid (debit) or margin req (credit).
                # Lacking margin data, we use Entry Cost for Longs, and Credit Received for Shorts as proxy.
                entry_val = sum(l.proceeds for l in g.legs)
                # If negative (Debit), it costs money. If positive (Credit), it adds cash but uses margin.
                # We will just take the absolute value to represent "magnitude" of the position for visualization.
                total_cost += abs(entry_val)

            allocation_pct = (total_cost / net_liquidity_now) * 100
            position_sizing.append({
                "symbol": sym,
                "allocation_amt": round(total_cost, 2),
                "allocation_pct": round(allocation_pct, 2),
                "description": _sym_desc(sym)
            })

        # Sort by allocation % descending
        position_sizing.sort(key=lambda x: x["allocation_pct"], reverse=True)

    # Optional outputs
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
            # trades.csv
            pd.DataFrame([{
                "symbol": g.symbol, "contract_id": g.contract_id,
                "entry_ts": g.entry_ts.isoformat() if g.entry_ts else "",
                "exit_ts": g.exit_ts.isoformat() if g.exit_ts else "", "pnl": g.pnl,
            } for g in contract_groups]).map(
                lambda x: f"'{x}" if isinstance(x, str) and x.startswith(("=", "+", "-", "@")) else x
            ).to_csv(os.path.join(out_dir, "trades.csv"), index=False)

            # report.xlsx
            summary_rows = [
                {"Metric": "Strategy Trades", "Value": len(strategies)},
                {"Metric": "Strategy Win Rate", "Value": win_rate},
                {"Metric": "Strategy Total PnL", "Value": total_pnl},
                {"Metric": "Verdict", "Value": verdict},
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
                if correlation_matrix_df is not None:
                    correlation_matrix_df.to_excel(writer, sheet_name="Correlation")
        except Exception:
            pass

    return {
        "metrics": {
            "num_trades": len(contract_groups), "win_rate": win_rate_contracts,
            "total_pnl": total_pnl_contracts, "avg_hold_days": avg_hold_contracts,
        },
        "strategy_metrics": {"num_trades": len(strategies), "win_rate": win_rate, "total_pnl": total_pnl},
        "verdict": verdict,
        "symbols": symbols_list,
        "strategy_groups": strategy_rows,
        "open_positions": open_rows,
        "broker": chosen_broker,
        "date_window": effective_window,
        "correlation_matrix": correlation_json,
        "account_size_start": account_size_start,
        "net_liquidity_now": net_liquidity_now,
        "buying_power_utilized_percent": buying_power_utilized_percent,
        "position_sizing": position_sizing,
    }
