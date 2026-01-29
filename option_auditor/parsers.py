from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import re
from dateutil import parser as dtparser
import logging

logger = logging.getLogger(__name__)

class TransactionParser(ABC):
    @abstractmethod
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    def _parse_tasty_datetime(self, val: str) -> Optional[pd.Timestamp]:
        dt = None
        now = datetime.now()

        # Try dateutil first
        try:
            dt = pd.Timestamp(dtparser.parse(str(val)))
        except Exception:
            # Expected if format is custom
            pass

        # Fallback to custom parsing
        if dt is None:
            try:
                s = str(val).strip().lower().replace(",", "")
                is_pm = 'p' in s
                s = s.replace('p', '').replace('a', '').replace('m', '')
                parts = s.split()
                date_part = parts[0]
                time_part = parts[1]
                dt_obj = datetime.strptime(f"{now.year}/{date_part} {time_part}", "%Y/%m/%d %H:%M")
                if is_pm and dt_obj.hour != 12:
                    dt_obj += timedelta(hours=12)
                elif not is_pm and dt_obj.hour == 12:
                    dt_obj -= timedelta(hours=12)
                dt = pd.Timestamp(dt_obj)
            except:
                return None

        # Year adjustment logic (for both paths)
        if dt is not None:
            if dt > pd.Timestamp(now + timedelta(days=2)):
                dt = dt.replace(year=dt.year - 1)

        return dt

class TastytradeParser(TransactionParser):
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        required = ["Time", "Underlying Symbol", "Quantity", "Action", "Price", "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"]
        for col in required:
            if col not in df.columns:
                raise KeyError(f"Tasty CSV missing '{col}' column")
        out = pd.DataFrame()
        out["datetime"] = pd.to_datetime(df["Time"].astype(str), errors="coerce")
        out["symbol"] = df["Underlying Symbol"].astype(str)
        action = df["Action"].astype(str).str.lower()
        qty_raw = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0.0).astype(float)
        # Sell -> Short (-1.0). Exercise -> Close Long (-1.0).
        # Buy/Assignment -> Open/Close Short (1.0).
        sign = np.where(action.str.startswith("sell") | action.str.contains("exercise"), -1.0, 1.0)
        out["qty"] = qty_raw * sign

        # Determine Asset Type
        # If Option Type is missing or not C/P, treat as STOCK
        # Also check Strike and Expiration Date
        opt_type = df["Option Type"].astype(str).str.upper().str.strip()
        out["right"] = opt_type.str[0] # 'C', 'P', 'N' (for nan), or empty

        # Helper to identify stock rows: Option Type is NaN or empty
        is_stock = (df["Option Type"].isna()) | (df["Option Type"].astype(str).str.strip() == "") | (df["Option Type"].astype(str).str.lower() == "nan")
        out["asset_type"] = np.where(is_stock, "STOCK", "OPT")

        # Clean up 'right' for stock
        out["right"] = out["right"].astype(object)
        out.loc[out["asset_type"] == "STOCK", "right"] = ""

        # Price & Proceeds
        price = pd.to_numeric(df["Price"], errors="coerce").fillna(0.0)

        # Multiplier: 100 for OPT, 1 for STOCK
        multiplier = np.where(out["asset_type"] == "STOCK", 1.0, 100.0)
        out["proceeds"] = -out["qty"] * price * multiplier

        out["fees"] = pd.to_numeric(df["Commissions and Fees"], errors="coerce").fillna(0.0)
        out["expiry"] = pd.to_datetime(df["Expiration Date"], errors="coerce")
        out["strike"] = pd.to_numeric(df["Strike Price"], errors="coerce").astype(float)

        def _fmt_contract(row):
            if row["asset_type"] == "STOCK":
                # Unique ID for stock: SYMBOL:::0.0
                return f"{row['symbol']}:::0.0"

            exp = row["expiry"]
            exp_s = exp.date().isoformat() if isinstance(exp, pd.Timestamp) and not pd.isna(exp) else ""
            strike = float(row["strike"]) if pd.notna(row["strike"]) else 0.0
            return f"{row['symbol']}:{exp_s}:{row['right']}:{round(strike,4)}"

        out["contract_id"] = out.apply(_fmt_contract, axis=1)
        return out

class TastytradeFillsParser(TransactionParser):
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        desc_pattern = re.compile(
            r"^(?P<qty_sign>-)?(?P<qty>\d+)\s+"
            r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+"
            r"(?:(?P<dte>\d+)d|Exp)?\s*"
            r"(?P<strike>[\d\.]+)\s+"
            r"(?P<right>Call|Put)\s+"
            r"(?P<action>\w{3})",
            re.IGNORECASE
        )
        for _, row in df.iterrows():
            desc_block = str(row.get("Description", ""))
            lines = desc_block.split('\n')
            price_raw = str(row.get("Price", "")).lower().replace(",", "")
            is_credit = "cr" in price_raw
            try:
                raw_val = float(re.findall(r"[\d\.]+", price_raw)[0])
                # For this parser, we need to know if it is stock or option to multiply by 100
                # But this parser parses "fills" text which is usually options format.
                # If the description matches the option regex, it uses 100.
                total_money = raw_val * 100.0
                if not is_credit:
                    total_money = -total_money
            except:
                total_money = 0.0

            ts = self._parse_tasty_datetime(row.get("Time"))
            total_legs_qty = 0
            parsed_legs = []

            # Stock logic could be needed here too if fills include stock
            # But the regex is specific to options.
            # If line doesn't match regex, it might be stock?

            for line in lines:
                line = line.strip()
                match = desc_pattern.search(line)
                if match:
                    d = match.groupdict()
                    qty = float(d['qty'])
                    if d['qty_sign'] == '-':
                        qty = -qty
                    trade_year = ts.year
                    try:
                        month_num = datetime.strptime(d['month'], "%b").month
                        expiry_year = trade_year
                        if ts.month > 10 and month_num < 3:
                            expiry_year += 1

                        day_val = d.get('day')
                        if day_val is None:
                            raise ValueError("Missing day")
                        expiry = pd.Timestamp(datetime(expiry_year, month_num, int(day_val)))
                    except:
                        expiry = pd.NaT
                    total_legs_qty += abs(qty)
                    parsed_legs.append({
                        "symbol": row.get("Symbol"), "datetime": ts, "qty": qty,
                        "strike": float(d['strike']), "right": d['right'][0].upper(),
                        "expiry": expiry, "raw_desc": line, "asset_type": "OPT"
                    })
                else:
                    # Fallback or Stock?
                    # "Bought 100 AAPL @ 150.00"
                    # If we see "Bought X SYMBOL @" or similar.
                    # Current fallback logic tries to parse as option too.
                    # For now, keeping legacy behavior unless stock is explicitly requested for FillsParser too.
                    # The prompt focused on TastytradeParser and IBKRParser.

                    toks = line.replace(",", " ").split()
                    if len(toks) >= 6:
                        try:
                            q = float(toks[0])
                        except Exception:
                            continue
                        mon = toks[1][:3]
                        day_tok = toks[2]
                        k = 3
                        if k < len(toks) and (toks[k].endswith('d') or toks[k].lower() == 'exp'):
                            k += 1
                        if k >= len(toks): continue
                        try:
                            strike_val = float(toks[k])
                        except Exception:
                            continue
                        if k + 1 >= len(toks): continue
                        right_tok = toks[k + 1]
                        if right_tok.lower().startswith('put'):
                            right_val = 'P'
                        elif right_tok.lower().startswith('call'):
                            right_val = 'C'
                        else:
                            continue
                        try:
                            month_num = datetime.strptime(mon, "%b").month
                            expiry_year = ts.year if ts else datetime.now().year
                            if ts and ts.month > 10 and month_num < 3:
                                expiry_year += 1

                            found_days = re.findall(r"\d+", str(day_tok))
                            if not found_days:
                                raise ValueError("No day found")
                            expiry = pd.Timestamp(datetime(expiry_year, month_num, int(found_days[0])))
                        except Exception:
                            expiry = pd.NaT
                        parsed_legs.append({
                            "symbol": row.get("Symbol"), "datetime": ts, "qty": q,
                            "strike": float(strike_val), "right": right_val,
                            "expiry": expiry, "raw_desc": line, "asset_type": "OPT"
                        })

            for leg in parsed_legs:
                ratio = abs(leg['qty']) / total_legs_qty if total_legs_qty > 0 else 0
                leg_proceeds = total_money * ratio
                contract_id = f"{leg['symbol']}:{leg['expiry'].date()}:{leg['right']}:{leg['strike']}"
                rows.append({
                    "contract_id": contract_id, "datetime": leg['datetime'], "symbol": leg['symbol'],
                    "expiry": leg['expiry'], "strike": leg['strike'], "right": leg['right'],
                    "qty": leg['qty'], "proceeds": leg_proceeds,
                    "fees": float(row.get("Commissions", 0) or 0) + float(row.get("Fees", 0) or 0) * ratio,
                    "asset_type": "OPT"
                })
        return pd.DataFrame(rows)

class ManualInputParser(TransactionParser):
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        # Expected columns from manual input list-of-dicts:
        # date, symbol, action, qty, price, fees, expiry, strike, opt (mapped to right)

        # Mapping 'opt' -> 'right' if needed (frontend uses 'opt')
        if "opt" in df.columns and "right" not in df.columns:
            df["right"] = df["opt"]

        required = ["date", "symbol", "action", "qty", "price", "fees", "expiry", "strike", "right"]
        # Basic validation
        for col in required:
            if col not in df.columns:
                if df.empty:
                    return pd.DataFrame()
                df[col] = None

        out = pd.DataFrame()
        out["datetime"] = pd.to_datetime(df["date"], errors="coerce")
        out["symbol"] = df["symbol"].astype(str)

        action = df["action"].astype(str).str.lower()
        # Handle "sell" (full word) or "s" (STO/STC)
        is_sell = action.str.contains("sell") | action.str.startswith("s")
        sign = np.where(is_sell, -1.0, 1.0)
        qty_abs = pd.to_numeric(df["qty"], errors="coerce").fillna(0.0).abs()
        out["qty"] = qty_abs * sign

        price = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)

        # Determine Asset Type based on Right/Strike/Expiry presence
        # If right is missing or not C/P, assume stock?
        # Manual input UI usually forces these fields for options.
        # Let's check 'right'.
        out["right"] = df["right"].astype(str).str.upper().str[0]
        is_opt = out["right"].isin(['C', 'P'])
        out["asset_type"] = np.where(is_opt, "OPT", "STOCK")

        # Reset right for stock
        out["right"] = out["right"].astype(object)
        out.loc[~is_opt, "right"] = ""

        multiplier = np.where(out["asset_type"] == "STOCK", 1.0, 100.0)
        out["proceeds"] = -out["qty"] * price * multiplier

        out["fees"] = pd.to_numeric(df["fees"], errors="coerce").fillna(0.0)
        out["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
        out["strike"] = pd.to_numeric(df["strike"], errors="coerce").fillna(0.0).astype(float)

        def _fmt_contract(row):
            if row["asset_type"] == "STOCK":
                return f"{row['symbol']}:::0.0"
            exp = row["expiry"]
            exp_s = exp.date().isoformat() if isinstance(exp, pd.Timestamp) and not pd.isna(exp) else ""
            strike = float(row["strike"]) if pd.notna(row["strike"]) else 0.0
            return f"{row['symbol']}:{exp_s}:{row['right']}:{round(strike,4)}"

        out["contract_id"] = out.apply(_fmt_contract, axis=1)

        out = out.dropna(subset=["datetime"])
        out = out[out["symbol"] != "nan"]

        return out


class IBKRParser(TransactionParser):
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        # Helper to find column by loose match
        def find_col(candidates):
            for cand in candidates:
                for c in df.columns:
                    if c.strip().lower() == cand.lower():
                        return c
            return None

        sym_col = find_col(["Symbol", "UnderlyingSymbol"])
        date_col = find_col(["DateTime", "Date/Time", "TradeDate"])
        qty_col = find_col(["Quantity", "Qty"])
        price_col = find_col(["T. Price", "TradePrice", "Price"])
        proceeds_col = find_col(["Proceeds", "Amount"])
        fee_col = find_col(["Comm/Fee", "Commission", "IBCommission"])
        strike_col = find_col(["Strike", "StrikePrice"])
        expiry_col = find_col(["Expiry", "ExpirationDate", "Expiration"])
        right_col = find_col(["Put/Call", "Right", "C/P"])
        # Asset class column might be available
        asset_col = find_col(["AssetClass", "Asset Class"])

        if not (sym_col and date_col and qty_col):
             if not sym_col: raise KeyError("IBKR Parser: Missing Symbol column")
             if not date_col: raise KeyError("IBKR Parser: Missing Date column")
             if not qty_col: raise KeyError("IBKR Parser: Missing Quantity column")

        out = pd.DataFrame()

        def _parse_ib_dt(x):
            try:
                if ";" in str(x):
                    parts = str(x).split(";")
                    d = parts[0].replace("-", "")
                    t = parts[1].replace(":", "")
                    return datetime.strptime(f"{d} {t}", "%Y%m%d %H%M%S")
                return dtparser.parse(str(x))
            except:
                return pd.NaT

        out["datetime"] = df[date_col].apply(_parse_ib_dt)
        out["symbol"] = df[sym_col].astype(str)
        out["qty"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0.0)

        if price_col:
            price = pd.to_numeric(df[price_col], errors="coerce").fillna(0.0)
        else:
            price = 0.0

        if right_col:
            # str[0] on empty string produces NaN, which casts column to float. FillNa("") ensures object/string dtype.
            out["right"] = df[right_col].astype(str).str.upper().str[0].fillna("")
        else:
            out["right"] = ""

        # Determine Asset Type
        if asset_col:
            # If explicit column exists, use it
            raw_asset = df[asset_col].astype(str).str.upper()
            out["asset_type"] = np.where(raw_asset.isin(["STK", "EQUITY", "STOCK"]), "STOCK", "OPT")
        else:
            # Infer from right/strike/expiry
            # If right is C/P, it's OPT. Otherwise STOCK (if not empty row)
            out["asset_type"] = np.where(out["right"].isin(["C", "P"]), "OPT", "STOCK")

        # Ensure 'right' is empty for STOCK
        out["right"] = out["right"].astype(object)
        out.loc[out["asset_type"] == "STOCK", "right"] = ""

        if proceeds_col:
            out["proceeds"] = pd.to_numeric(df[proceeds_col], errors="coerce").fillna(0.0)
        else:
            # Fallback
            multiplier = np.where(out["asset_type"] == "STOCK", 1.0, 100.0)
            out["proceeds"] = -out["qty"] * price * multiplier

        if fee_col:
            raw_fee = pd.to_numeric(df[fee_col], errors="coerce").fillna(0.0)
            out["fees"] = raw_fee.abs()
        else:
            out["fees"] = 0.0

        if strike_col:
            out["strike"] = pd.to_numeric(df[strike_col], errors="coerce").fillna(0.0)
        else:
            out["strike"] = 0.0

        if expiry_col:
            out["expiry"] = pd.to_datetime(df[expiry_col].astype(str), errors="coerce")
        else:
            out["expiry"] = pd.NaT

        def _fmt_contract(row):
            if row["asset_type"] == "STOCK":
                 return f"{row['symbol']}:::0.0"
            exp = row["expiry"]
            exp_s = exp.date().isoformat() if isinstance(exp, pd.Timestamp) and not pd.isna(exp) else ""
            strike = float(row["strike"]) if pd.notna(row["strike"]) else 0.0
            right = row["right"] if row["right"] in ['C', 'P'] else ""
            return f"{row['symbol']}:{exp_s}:{right}:{round(strike,4)}"

        out["contract_id"] = out.apply(_fmt_contract, axis=1)

        # Filter out rows with 0 qty
        out = out[out["qty"] != 0]

        # Valid rows: Must be OPT or STOCK.
        # If OPT, must have expiry and right.
        # If STOCK, just need symbol (which is checked above).

        is_valid_opt = (out["asset_type"] == "OPT") & (pd.notna(out["expiry"])) & (out["right"].isin(["C", "P"]))
        is_valid_stock = (out["asset_type"] == "STOCK")

        out = out[is_valid_opt | is_valid_stock].copy()

        return out
