from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import re
from dateutil import parser as dtparser

class TransactionParser(ABC):
    @abstractmethod
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    def _parse_tasty_datetime(self, val: str) -> Optional[pd.Timestamp]:
        try:
            return pd.Timestamp(dtparser.parse(str(val)))
        except:
            pass
        try:
            s = str(val).strip().lower().replace(",", "")
            now = datetime.now()
            is_pm = 'p' in s
            s = s.replace('p', '').replace('a', '').replace('m', '')
            parts = s.split()
            date_part = parts[0]
            time_part = parts[1]
            dt = datetime.strptime(f"{now.year}/{date_part} {time_part}", "%Y/%m/%d %H:%M")
            if is_pm and dt.hour != 12:
                dt += timedelta(hours=12)
            elif not is_pm and dt.hour == 12:
                dt -= timedelta(hours=12)
            return pd.Timestamp(dt)
        except:
            return None

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
        qty_raw = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(float)
        sign = np.where(action.str.startswith("sell"), -1.0, 1.0)
        out["qty"] = qty_raw * sign
        price = pd.to_numeric(df["Price"], errors="coerce").fillna(0.0)
        out["proceeds"] = -out["qty"] * price * 100.0
        out["fees"] = pd.to_numeric(df["Commissions and Fees"], errors="coerce").fillna(0.0)
        out["expiry"] = pd.to_datetime(df["Expiration Date"], errors="coerce")
        out["strike"] = pd.to_numeric(df["Strike Price"], errors="coerce").astype(float)
        out["right"] = df["Option Type"].astype(str).str.upper().str[0]
        out["asset_type"] = "OPT"
        def _fmt_contract(row):
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
                total_money = float(re.findall(r"[\d\.]+", price_raw)[0]) * 100.0
                if not is_credit:
                    total_money = -total_money
            except:
                total_money = 0.0
            ts = self._parse_tasty_datetime(row.get("Time"))
            total_legs_qty = 0
            parsed_legs = []
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
                        expiry = pd.Timestamp(datetime(expiry_year, month_num, int(d['day'])))
                    except:
                        expiry = pd.NaT
                    total_legs_qty += abs(qty)
                    parsed_legs.append({
                        "symbol": row.get("Symbol"), "datetime": ts, "qty": qty,
                        "strike": float(d['strike']), "right": d['right'][0].upper(),
                        "expiry": expiry, "raw_desc": line
                    })
                else:
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
                        except Exception: continue
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
                            expiry = pd.Timestamp(datetime(expiry_year, month_num, int(re.findall(r"\d+", day_tok)[0])))
                        except Exception:
                            expiry = pd.NaT
                        parsed_legs.append({
                            "symbol": row.get("Symbol"), "datetime": ts, "qty": q,
                            "strike": float(strike_val), "right": right_val,
                            "expiry": expiry, "raw_desc": line
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
        # date, symbol, action, qty, price, fees, expiry, strike, right

        required = ["date", "symbol", "action", "qty", "price", "fees", "expiry", "strike", "right"]
        # Basic validation
        for col in required:
            if col not in df.columns:
                # If dataframe is empty, we can just return empty
                if df.empty:
                    return pd.DataFrame()
                # Otherwise, it might be an issue, but let's be lenient or fill NaN
                df[col] = None

        out = pd.DataFrame()
        out["datetime"] = pd.to_datetime(df["date"], errors="coerce")
        out["symbol"] = df["symbol"].astype(str)

        # Action determines sign.
        # "Buy Open", "Sell Close" -> usually we just need Buy vs Sell.
        # But user input might be specific.
        # Let's assume standard: Buy = positive cost (negative proceeds), Sell = negative cost (positive proceeds).
        # Wait, Qty Sign: Long = +Qty, Short = -Qty.
        # Action:
        # Buy (Open/Close) -> +Qty? No.
        # Buy to Open: +Qty (Long). Pays Debit.
        # Sell to Close: -Qty (Close Long). Receives Credit.
        # Sell to Open: -Qty (Short). Receives Credit.
        # Buy to Close: +Qty (Close Short). Pays Debit.

        # Actually, in our internal model:
        # Long Position = Positive Qty.
        # Short Position = Negative Qty.
        # To OPEN Long: Buy (+Qty).
        # To CLOSE Long: Sell (-Qty).
        # To OPEN Short: Sell (-Qty).
        # To CLOSE Short: Buy (+Qty).

        # So "Buy" always adds Qty, "Sell" always subtracts Qty?
        # TastyParser: `sign = np.where(action.str.startswith("sell"), -1.0, 1.0)`.
        # This implies Sell = -1, Buy = +1.
        # Proceeds: `-out["qty"] * price * 100.0`.
        # If Sell (-1): Proceeds = -(-1)*P*100 = +100P. (Credit)
        # If Buy (+1): Proceeds = -(1)*P*100 = -100P. (Debit)
        # This matches standard accounting.

        action = df["action"].astype(str).str.lower()
        sign = np.where(action.str.contains("sell"), -1.0, 1.0)
        qty_abs = pd.to_numeric(df["qty"], errors="coerce").fillna(0).abs()
        out["qty"] = qty_abs * sign

        price = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
        out["proceeds"] = -out["qty"] * price * 100.0

        out["fees"] = pd.to_numeric(df["fees"], errors="coerce").fillna(0.0)
        out["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
        out["strike"] = pd.to_numeric(df["strike"], errors="coerce").astype(float)

        # Right: C or P
        out["right"] = df["right"].astype(str).str.upper().str[0]
        out["asset_type"] = "OPT"

        def _fmt_contract(row):
            exp = row["expiry"]
            exp_s = exp.date().isoformat() if isinstance(exp, pd.Timestamp) and not pd.isna(exp) else ""
            strike = float(row["strike"]) if pd.notna(row["strike"]) else 0.0
            return f"{row['symbol']}:{exp_s}:{row['right']}:{round(strike,4)}"

        out["contract_id"] = out.apply(_fmt_contract, axis=1)

        # Filter out rows with invalid dates or symbols
        out = out.dropna(subset=["datetime"])
        out = out[out["symbol"] != "nan"]

        return out
