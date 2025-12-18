from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from pydantic import BaseModel

@dataclass
class Leg:
    ts: datetime
    qty: float
    price: float
    fees: float
    proceeds: float
    description: str = ""

@dataclass
class TradeGroup:
    contract_id: str
    symbol: str
    expiry: Optional[pd.Timestamp]
    strike: Optional[float]
    right: Optional[str]
    legs: List[Leg] = field(default_factory=list)
    pnl: float = 0.0 # This is Gross PnL (Proceeds)
    fees: float = 0.0
    qty_net: float = 0.0
    entry_ts: Optional[pd.Timestamp] = None
    exit_ts: Optional[pd.Timestamp] = None

    def add_leg(self, leg: Leg):
        self.legs.append(leg)
        self.pnl += leg.proceeds
        self.fees += leg.fees
        self.qty_net += leg.qty
        if self.entry_ts is None or leg.ts < self.entry_ts:
            self.entry_ts = pd.Timestamp(leg.ts)
        if self.exit_ts is None or leg.ts > self.exit_ts:
            self.exit_ts = pd.Timestamp(leg.ts)

    @property
    def is_closed(self) -> bool:
        return abs(self.qty_net) < 1e-9

    @property
    def net_pnl(self) -> float:
        return self.pnl - self.fees

@dataclass
class StrategyGroup:
    id: str
    symbol: str
    expiry: Optional[pd.Timestamp]
    legs: List[TradeGroup] = field(default_factory=list)
    pnl: float = 0.0 # Gross PnL
    fees: float = 0.0
    entry_ts: Optional[pd.Timestamp] = None
    exit_ts: Optional[pd.Timestamp] = None
    strategy_name: str = "Unclassified"
    # Segments track the history of rolls/campaigns.
    # Each segment is a dict with details: {strategy_name, pnl, entry_ts, exit_ts, fees}
    segments: List[Dict[str, Any]] = field(default_factory=list)

    def add_leg_group(self, group: TradeGroup):
        self.legs.append(group)
        self.pnl += group.pnl
        self.fees += group.fees
        if group.entry_ts:
            if self.entry_ts is None or group.entry_ts < self.entry_ts:
                self.entry_ts = group.entry_ts
        if group.exit_ts:
            if self.exit_ts is None or group.exit_ts > self.exit_ts:
                self.exit_ts = group.exit_ts

    def hold_days(self) -> float:
        if not self.entry_ts or not self.exit_ts:
            return 0.0
        delta = (self.exit_ts - self.entry_ts).total_seconds()
        return max(delta / 86400.0, 0.001)

    @property
    def net_pnl(self) -> float:
        return self.pnl - self.fees

    def average_daily_pnl(self) -> float:
        # Renamed from realized_theta as PnL/Day is not Theta.
        # Calculates realized return per day based on Net PnL.
        return self.net_pnl / self.hold_days()

    def record_segment(self):
        """Records the current state as a segment (e.g. before rolling)."""
        pass

# --- FastAPI Models ---
class StockCheckRequest(BaseModel):
    ticker: str
    entry_price: Optional[float] = None
    purchase_date: Optional[str] = None
