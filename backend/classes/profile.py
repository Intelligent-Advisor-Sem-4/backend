from pydantic import BaseModel
from typing import List, Optional
from models.models import AssetStatus


class Input(BaseModel):
    tickers: List[str]
    start_date: str = "2020-01-01"
    end_date: str = "2024-01-01"
    num_portfolios: int = 10000
    investment_amount: float
    target_amount: float
    years: float
    risk_score_percent: Optional[float] = None  # NEW: user's quiz risk percent (0-100)
    use_risk_score: bool = False                # NEW: whether user selects custom risk

class Ticker(BaseModel):
    ticker_symbol: str
    asset_name: Optional[str] = None
    sectorDisp: Optional[str] = None
    currency:str
    status:AssetStatus

class Tickers(BaseModel):
    tickers: List[Ticker]

class RiskScoreIn(BaseModel):
    user_id: str
    score:   float

class RiskScoreOut(BaseModel):
    score: float