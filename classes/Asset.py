from pydantic import BaseModel
from typing import Optional


class DB_Stock(BaseModel):
    """Model for stock table"""
    in_db: Optional[bool] = None
    status: Optional[str] = None
    asset_id: Optional[int] = None
    risk_score: Optional[float] = None
    risk_score_updated: Optional[str] = None


class Asset(BaseModel):
    name: str
    company_url: str
    exchange: str
    ticker: str
    type: str
    sector: str
    industry: str
    currency: str
    prev_close: Optional[float] = None
    open_price: Optional[float] = None
    last_price: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[float] = None
    beta: Optional[float] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    trailing_eps: Optional[float] = None
    trailing_pe: Optional[float] = None
    db: Optional[DB_Stock] = None


class AssetFastInfo(BaseModel):
    currency: str
    prev_close: Optional[float] = None
    last_price: Optional[float] = None
