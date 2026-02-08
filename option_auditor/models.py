from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

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
    notes: str = ""
    emotions: List[str] = field(default_factory=list)
    emotional_state: Optional[str] = None
    is_overtraded: bool = False

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

    def check_overtrading(self, max_legs: int = 10):
        """Checks if the trade group has excessive adjustments."""
        if len(self.legs) > max_legs:
            self.is_overtraded = True

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

@dataclass
class StressTestResult:
    scenario_name: str
    market_move_pct: float
    portfolio_value_change: float
    portfolio_value_change_pct: float
    details: List[str] = field(default_factory=list)

def calculate_regulatory_fees(symbol: str, price: float, qty: float, action: str = 'BUY', asset_class: str = 'stock') -> float:
    """
    Calculates regulatory fees (Stamp Duty, STT) based on the market.

    :param symbol: Ticker symbol (e.g. REL.L, INF.NS)
    :param price: Price per share
    :param qty: Quantity traded
    :param action: 'BUY', 'SELL', etc.
    :param asset_class: 'stock', 'option', etc.
    :return: Calculated tax/fee amount.
    """
    fees = 0.0
    val = abs(price * qty)
    symbol = symbol.upper()
    action = action.upper()

    # India STT (0.1% on Equity Delivery)
    # Applied on both Buy and Sell for Delivery.
    if symbol.endswith('.NS') or symbol.endswith('.BO'):
        if asset_class.lower() == 'stock':
            fees += val * 0.001

    # UK Stamp Duty (0.5% on Buy only)
    # Applied on LSE stocks (.L)
    if symbol.endswith('.L'):
        if asset_class.lower() == 'stock':
            # Check for Buy action.
            # Also assume positive qty with unspecified action implies Buy if needed, but here we check action string.
            is_buy = action.startswith('BUY') or action == 'OPEN' # loose heuristic, caller should pass BUY
            if is_buy:
                fees += val * 0.005

    return fees
