from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field
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


class AssetStatusEnum(str, Enum):
    PENDING = "Pending"
    ACTIVE = "Active"
    WARNING = "Warning"
    BLACKLIST = "BlackList"


class StockResponse(BaseModel):
    stock_id: int
    ticker_symbol: str
    asset_name: Optional[str] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    sectorKey: Optional[str] = None
    sectorDisp: Optional[str] = None
    industryKey: Optional[str] = None
    industryDisp: Optional[str] = None
    timezone: Optional[str] = None
    status: AssetStatusEnum = AssetStatusEnum.PENDING
    type: Optional[str] = None
    first_data_point_date: Optional[date] = None
    last_data_point_date: Optional[date] = None
    risk_score: Optional[Decimal] = Field(None, decimal_places=2)
    risk_score_updated: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RiskScoreUpdate(BaseModel):
    risk_score: float
    was_updated: bool
