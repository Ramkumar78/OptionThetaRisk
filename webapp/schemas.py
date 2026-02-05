from pydantic import BaseModel, Field, field_validator, RootModel, ConfigDict, ValidationInfo
from typing import List, Dict, Optional, Union

class PortfolioPositionsRequest(BaseModel):
    positions: List[Dict] = Field(..., min_length=1)

class ScenarioRequest(BaseModel):
    positions: List[Dict] = Field(..., min_length=1)
    scenario: Dict

class CorrelationRequest(BaseModel):
    tickers: Union[List[str], str] = Field(..., min_length=1)
    period: str = "1y"

    @field_validator("tickers")
    @classmethod
    def parse_tickers(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            val = [t.strip() for t in v.split(',') if t.strip()]
            if not val:
                 raise ValueError("Tickers list cannot be empty")
            return val
        if not v:
             raise ValueError("Tickers list cannot be empty")
        return v

class BacktestRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    strategy: str = "master"
    initial_capital: float = 10000.0

class MonteCarloRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    strategy: str = "turtle"
    simulations: int = 10000

class MarketDataRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    period: str = "1y"

class ScreenerFormRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    iv_rank: float = 30.0
    rsi_threshold: float = 50.0
    time_frame: str = "1d"
    region: str = "us"

    @field_validator('iv_rank', 'rsi_threshold', mode='before')
    @classmethod
    def parse_float_or_default(cls, v: Union[str, float], info: ValidationInfo) -> float:
        if v == "" or v is None:
            if info.field_name == 'iv_rank':
                return 30.0
            if info.field_name == 'rsi_threshold':
                return 50.0
        return v

class StockCheckRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    ticker: str = Field(..., min_length=1)
    strategy: str = "isa"
    time_frame: str = "1d"
    entry_price: Optional[float] = None
    entry_date: Optional[str] = None
    account_size: Optional[float] = None

    @field_validator('entry_price', 'account_size', mode='before')
    @classmethod
    def parse_optional_float(cls, v: Union[str, float, None]) -> Optional[float]:
        if isinstance(v, str):
            if v.strip() == "":
                return None
            try:
                return float(v)
            except ValueError:
                raise ValueError("Must be a number")
        return v

class JournalImportRequest(RootModel):
    root: List[Dict] = Field(..., min_length=1)
