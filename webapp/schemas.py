from pydantic import BaseModel, Field, field_validator, RootModel, ConfigDict, BeforeValidator
from typing import List, Dict, Optional, Any, Union, Annotated
import json

def empty_to_none(v):
    if v == "":
        return None
    return v

OptionalFloat = Annotated[Optional[float], BeforeValidator(empty_to_none)]

# Analysis Schemas
class AnalyzeRequest(BaseModel):
    broker: str = Field("auto")
    manual_trades: Optional[List[Dict[str, Any]]] = None
    account_size_start: OptionalFloat = None
    net_liquidity_now: OptionalFloat = None
    buying_power_available_now: OptionalFloat = None
    style: str = Field("income")
    fee_per_trade: OptionalFloat = None
    csv_fee_per_trade: OptionalFloat = None
    date_mode: str = Field("all")
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @field_validator('manual_trades', mode='before')
    @classmethod
    def parse_manual_trades(cls, v):
        if isinstance(v, str):
            try:
                if not v.strip():
                    return None
                parsed = json.loads(v)
                if isinstance(parsed, list):
                     filtered = [
                        row for row in parsed
                        if isinstance(row, dict) and row.get("date") and row.get("symbol") and row.get("action")
                     ]
                     return filtered if filtered else None
                return None
            except json.JSONDecodeError:
                return None
        return v

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def empty_str_date(cls, v):
        if v == "":
            return None
        return v

class PortfolioAnalysisRequest(BaseModel):
    positions: List[Dict[str, Any]] = Field(..., min_length=1, description="List of positions to analyze")

class ScenarioAnalysisRequest(BaseModel):
    positions: List[Dict[str, Any]] = Field(..., min_length=1, description="List of positions")
    scenario: Dict[str, Any] = Field(..., description="Scenario parameters")

class CorrelationRequest(BaseModel):
    tickers: Union[List[str], str] = Field(..., description="List of tickers or comma-separated string")
    period: str = Field("1y", description="Lookback period")

    @field_validator('tickers')
    @classmethod
    def parse_tickers(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(',') if t.strip()]
        return v

class BacktestRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    strategy: str = Field("master")
    initial_capital: float = Field(10000.0, gt=0)

class MonteCarloRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    strategy: str = Field("turtle")
    simulations: int = Field(10000, gt=0)

class MarketDataRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    period: str = Field("1y")

# Screener Schemas (mostly for query params, so fields are often optional/defaulted string inputs that need coercion)
class ScreenerBaseRequest(BaseModel):
    region: str = Field("us")
    time_frame: str = Field("1d")

class ScreenerRunRequest(BaseModel):
    iv_rank: float = Field(30.0)
    rsi_threshold: float = Field(50.0)
    time_frame: str = Field("1d")
    region: str = Field("us")

class IsaCheckRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    account_size: Optional[float] = Field(None)
    entry_price: Optional[float] = Field(None)

class BacktestRunRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    strategy: str = Field("master")

class FourierScreenRequest(ScreenerBaseRequest):
    ticker: Optional[str] = None

class CheckStockRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    strategy: str = Field("isa")
    time_frame: str = Field("1d")
    entry_price: Optional[float] = None
    entry_date: Optional[str] = None
    account_size: Optional[float] = None

# Journal Schemas
class JournalEntryRequest(BaseModel):
    # Allowing flexible dict for now as structure isn't fully clear from routes alone
    # But enforcing it's a non-empty dict
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    pnl: Optional[float] = None
    notes: Optional[str] = None
    emotions: Optional[List[str]] = None
    # We can use extra='allow' to accept other fields

    model_config = ConfigDict(extra='allow')

class JournalImportRequest(RootModel):
    root: List[Dict[str, Any]]


class IsaScreenRequest(ScreenerBaseRequest):
    account_size: Optional[float] = None

class FeedbackRequest(BaseModel):
    message: str = Field(..., min_length=1)
    name: Optional[str] = None
    email: Optional[str] = None
