from pydantic import BaseModel
from typing import List
from models.models import AssetStatus


class Input(BaseModel):
    tickers: List[str]
    start_date: str = "2020-01-01"
    end_date: str = "2024-01-01"
    num_portfolios: int = 10000
    investment_amount: float
    target_amount: float
    years: float

class Ticker(BaseModel):
    ticker_symbol: str
    asset_name: str
    sectorDisp:str
    currency:str
    status:AssetStatus

class Tickers(BaseModel):
    tickers: List[Ticker]
