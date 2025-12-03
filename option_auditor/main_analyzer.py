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

def _detect_broker(df: pd.DataFrame) -> Optional[str]:
    cols = {c.strip(): True for c in df.columns}
    if "Underlying Symbol" in cols:
        return "tasty"
    if "Description" in cols and "Symbol" in cols:
        return "tasty"
    # IBKR Detection
    if "ClientAccountID" in cols or "IBCommission" in cols:
        return "ibkr"
    # Generic IBKR Flex match
    if "Comm/Fee" in cols and "T. Price" in cols:
        return "ibkr"
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

def _normalize_ticker(broker_symbol: str) -> str:
    """Maps broker symbols to yfinance tickers."""
    if not isinstance(broker_symbol, str):
        return str(broker_symbol)
    s = broker_symbol.upper().strip()

    # Map common Indices
    index_map = {
        "SPX": "^SPX", "VIX": "^VIX", "DJX": "^DJI", "NDX": "^NDX", "RUT": "^RUT"
    }
    if s in index_map:
        return index_map[s]

    # Map Futures (Tastytrade uses /ES, Yahoo uses ES=F)
    if s.startswith("/"):
        return f"{s[1:]}=F"

    # Map Classes (BRK/B -> BRK-B)
    if "/" in s:
        return s.replace("/", "-")

    return s

def _fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetches live prices for a list of symbols using yfinance.
    Returns a dictionary mapping symbol -> current_price.
    """
    if not symbols:
        return {}

    # Filter out empty or non-string symbols
    valid_symbols = [s for s in symbols if isinstance(s, str) and s]
    if not valid_symbols:
        return {}

    # Deduplicate
    unique_symbols = list(set(valid_symbols))

    price_map = {}

    # Use Tickers for potentially bulk efficiency, though we might iterate to be safe
    # yfinance Tickers object allows access to each ticker
    try:
        tickers = yf.Tickers(" ".join(unique_symbols))
        for sym in unique_symbols:
            try:
                t = tickers.tickers[sym]
                # Try fast_info first (new API), then info (slower, detailed), then history
                price = None

                # fast_info
                if hasattr(t, "fast_info"):
                    # fast_info keys: 'last_price', 'regular_market_price', etc.
                    # 'last_price' is usually what we want
                    val = t.fast_info.get("last_price")
                    if val is not None and not pd.isna(val):
                        price = float(val)

                # Fallback to info
                if price is None:
                    info = t.info
                    # Try various keys
                    for k in ['currentPrice', 'regularMarketPrice', 'bid', 'ask']:
                        val = info.get(k)
                        if val is not None and not pd.isna(val):
                            price = float(val)
                            break

                # Fallback to history (last close)
                if price is None:
                    hist = t.history(period="1d")
                    if not hist.empty:
                        price = float(hist["Close"].iloc[-1])

                if price is not None:
                    price_map[sym] = price
            except Exception:
                # Individual ticker failure should not fail batch
                continue
    except Exception:
        # If bulk fails, try one by one? Or just return what we have.
        pass

    return price_map

def _check_itm_risk(open_groups: List[TradeGroup], prices: Dict[str, float]) -> Tuple[bool, float, List[str]]:
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

        # Calculate what the portfolio would be worth *intrinsically* right now
        # (Ignoring extrinsic/time value, focusing on hard assignment risk)
        for g in groups:
            qty = g.qty_net

            # Stock
            if g.right not in ['C', 'P']:
                # For stock, we consider the full liquidation value at current price.
                # This naturally offsets any short calls (Covered Call).
                net_intrinsic_val += current_price * qty

            # Options
            elif g.strike:
                intrinsic = 0.0
                if g.right == 'C': # Call
                    # Intrinsic = Max(0, Price - Strike)
                    val = max(0.0, current_price - g.strike)
                    # If Short (-1), we owe this value. If Long (+1), we own this value.
                    intrinsic = val * qty * 100
                elif g.right == 'P': # Put
                    # Intrinsic = Max(0, Strike - Price)
                    val = max(0.0, g.strike - current_price)
                    intrinsic = val * qty * 100

                net_intrinsic_val += intrinsic

        # 3. Verdict on this Symbol
        # If Net Intrinsic Value is significantly negative, it means the Long legs aren't covering the Short legs.
        # Threshold: -$500 exposure
        if net_intrinsic_val < -500:
            risky = True
            total_net_exposure += abs(net_intrinsic_val)
            details.append(f"{symbol}: Net ITM Exposure -${abs(net_intrinsic_val):,.0f} (Net Risk)")

        # 4. Secondary Check: Bag Holding Stock (The logic you already had)
        for g in groups:
             if g.right not in ['C', 'P'] and g.qty_net > 0:
                 # Re-implement Bag Holding Logic
                 total_buy_qty = sum(l.qty for l in g.legs if l.qty > 0)
                 total_buy_cost = sum(-l.proceeds for l in g.legs if l.qty > 0)

                 if total_buy_qty > 0:
                     avg_price = total_buy_cost / total_buy_qty
                     unrealized = (current_price - avg_price) * g.qty_net

                     pct_down = (avg_price - current_price) / avg_price if avg_price > 0 else 0
                     if pct_down > 0.05: # > 5% Down
                         risky = True
                         # Add to exposure if we haven't already counted this symbol as a "Net Risk"
                         # (To avoid double counting if the stock drop is the reason net risk triggered)
                         # However, Net Risk is about *Liquidation Value* being negative.
                         # Bag Holding is about *Loss of Capital*.
                         # They are different metrics.
                         # But if we return a single "Total Intrinsic Exposure", we should probably sum them up.
                         # Let's add it.
                         exposure = abs(unrealized)
                         total_net_exposure += exposure
                         details.append(f"{symbol}: Bag Holding Stock Down {pct_down:.1%} (-${exposure:,.0f})")

    return risky, total_net_exposure, details

def analyze_csv(csv_path: Optional[str] = None,
                broker: str = "auto",
                account_size_start: Optional[float] = None,
                net_liquidity_now: Optional[float] = None,
                buying_power_available_now: Optional[float] = None,
                out_dir: Optional[str] = None, report_format: str = "all",
                start_date: Optional[str] = None, end_date: Optional[str] = None,
                manual_data: Optional[List[Dict[str, Any]]] = None,
                global_fees: Optional[float] = None,
                style: str = "income") -> Dict:
    
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

    if open_groups:
        try:
            # 1. Identify symbols needed
            raw_symbols = list({g.symbol for g in open_groups if g.symbol})

            # 2. Create a map of Raw -> Normalized
            sym_map = {raw: _normalize_ticker(raw) for raw in raw_symbols}

            # 3. Fetch prices using NORMALIZED symbols
            fetched_prices = _fetch_live_prices(list(sym_map.values()))

            # 4. Map back to raw symbols for the risk check logic
            for raw, norm in sym_map.items():
                if norm in fetched_prices:
                    live_prices[raw] = fetched_prices[norm]
                else:
                    missing_data_warning.append(raw) # Track failures

            itm_risk_flag, itm_risk_amount, itm_risk_details = _check_itm_risk(open_groups, live_prices)

        except Exception as e:
            # Log error if needed
            print(f"Live price fetch failed: {e}")
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

    if total_strategy_pnl_gross > 0:
        fee_drag = (total_strategy_fees / total_strategy_pnl_gross) * 100
        leakage_metrics["fee_drag"] = round(fee_drag, 2)
        if fee_drag > 10.0:
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
    if itm_risk_flag:
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
        row = {
            "symbol": s.symbol,
            "expiry": s.expiry.date().isoformat() if s.expiry and not pd.isna(s.expiry) else "",
            "strategy": s.strategy_name,
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

        row = {
            "symbol": agg["symbol"],
            "expiry": agg["expiry"].date().isoformat() if agg["expiry"] and not pd.isna(agg["expiry"]) else "",
            "contract": f"{agg['right'] or ''} {agg['strike']}",
            "qty_open": qty,
            "avg_price": avg_price,
            "breakeven": breakeven,
            "opened": agg["entry_ts"].isoformat() if agg["entry_ts"] else "",
            "days_open": (pd.Timestamp(datetime.now()) - agg["entry_ts"]).total_seconds() / 86400.0 if agg["entry_ts"] else 0.0,
            "description": _sym_desc(agg["symbol"])
        }

        # Add risk annotation if applicable
        if itm_risk_flag:
            if agg["symbol"] in live_prices and agg["strike"] and qty < 0:
                cp = live_prices[agg["symbol"]]
                is_risky_pos = False
                if agg["right"] == 'P' and cp < agg["strike"]:
                    if (agg["strike"] - cp)/agg["strike"] > 0.01: is_risky_pos = True
                elif agg["right"] == 'C' and cp > agg["strike"]:
                    if (cp - agg["strike"])/agg["strike"] > 0.01: is_risky_pos = True

                if is_risky_pos:
                    row["risk_alert"] = "ITM Risk"

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
        "excel_report": excel_buffer
    }
