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

def calculate_regulatory_fees(symbol: str, price: float, qty: float, action: str = 'BUY', asset_class: str = 'stock', multiplier: float = 1.0) -> float:
    """
    Calculates regulatory fees (Stamp Duty, STT, SEC, TAF) based on the market.

    :param symbol: Ticker symbol (e.g. REL.L, INF.NS)
    :param price: Price per share
    :param qty: Quantity traded (shares or contracts)
    :param action: 'BUY', 'SELL', etc.
    :param asset_class: 'stock', 'option', etc.
    :param multiplier: Contract multiplier (default 1.0, use 100.0 for standard US options)
    :return: Calculated tax/fee amount.
    """
    fees = 0.0
    val = abs(price * qty * multiplier)
    symbol = symbol.upper()
    action = action.upper()
    asset_class = asset_class.lower()

    # Determine direction
    # If action is vague, use qty sign if available?
    # Current usages pass positive qty. Rely on action string.
    is_buy = action.startswith('BUY') or action == 'OPEN' or (action == 'BOT')
    is_sell = action.startswith('SELL') or action == 'CLOSE' or (action == 'SLD')

    # India STT (0.1% on Equity Delivery)
    # Applied on both Buy and Sell for Delivery.
    if symbol.endswith('.NS') or symbol.endswith('.BO'):
        if asset_class == 'stock':
            fees += val * 0.001

    # UK Stamp Duty (0.5% on Buy only)
    # Applied on LSE stocks (.L)
    elif symbol.endswith('.L'):
        if asset_class == 'stock':
            if is_buy:
                fees += val * 0.005

    # US Markets (Default/fallback if no suffix, or check against known US exchanges if possible)
    # Assuming anything else is US for now, or check for absence of suffix
    else:
        # US Regulatory Fees apply to SELL orders only (SEC, TAF)
        if is_sell:
            # SEC Fee: $27.80 per million (2024 rate) = 0.0000278 * Value
            # Applied to all sales of equities and options
            sec_rate = 0.0000278
            fees += val * sec_rate

            # TAF (Trading Activity Fee)
            # Equity: $0.000166 per share (max $8.30 per trade)
            # Options: $0.00244 per contract (max usually same or similar per trade execution? FINRA says max $8.30)
            taf_cap = 8.30
            taf_fee = 0.0

            abs_qty = abs(qty)

            if asset_class == 'stock':
                taf_fee = abs_qty * 0.000166
            elif asset_class == 'option':
                taf_fee = abs_qty * 0.00244

            # Cap TAF fee per trade
            if taf_fee > taf_cap:
                taf_fee = taf_cap

            fees += taf_fee

    return fees


def calculate_commission(qty: float, price: float, asset_class: str = 'stock', symbol: str = '', commission_model: str = 'tiered', multiplier: float = 1.0) -> float:
    """
    Calculates trading commission based on the model (e.g. Fixed vs Tiered).

    :param qty: Quantity traded (can be negative, we use abs)
    :param price: Execution price
    :param asset_class: 'stock' or 'option'
    :param symbol: Ticker symbol (used to determine market)
    :param commission_model: 'fixed' or 'tiered' (IBKR Pro style)
    :param multiplier: Contract multiplier (default 1.0)
    :return: Estimated commission.
    """
    qty = abs(qty)
    comm = 0.0
    asset_class = asset_class.lower()
    symbol = symbol.upper()

    # Determine Market
    is_india = symbol.endswith('.NS') or symbol.endswith('.BO')
    is_uk = symbol.endswith('.L')
    is_us = not (is_india or is_uk)

    if commission_model == 'fixed':
        # Simple fixed rate examples
        if is_us:
            if asset_class == 'stock':
                comm = max(1.0, qty * 0.005) # $0.005/share, min $1
            elif asset_class == 'option':
                comm = max(1.0, qty * 0.65) # $0.65/contract, min $1
        elif is_india:
            comm = 20.0 # Flat Rs 20 per order usually
        elif is_uk:
            comm = max(6.0, qty * price * 0.0005) # GBP 6 min or 5 bps

    elif commission_model == 'tiered':
        # IBKR Pro Tiered (Approximate)
        if is_us:
            if asset_class == 'stock':
                # <= 300,000 shares: $0.0035/share
                # Min $0.35 per order
                # Max 1% of trade value
                base_comm = qty * 0.0035
                base_comm = max(0.35, base_comm)
                max_comm = qty * price * multiplier * 0.01
                comm = min(base_comm, max_comm)

            elif asset_class == 'option':
                # < 10,000 contracts: $0.65
                # 10k-50k: $0.50
                # > 50k: $0.25
                # Min $1.00 per order

                # Simplified tiered logic
                rate = 0.65
                if qty > 10000:
                    rate = 0.50 # Simplified, normally stepped
                if qty > 50000:
                    rate = 0.25

                base_comm = qty * rate
                base_comm = max(1.00, base_comm)
                comm = base_comm
        else:
             # Fallback to fixed for non-US if tiered data missing
             return calculate_commission(qty, price, asset_class, symbol, 'fixed')

    return comm
