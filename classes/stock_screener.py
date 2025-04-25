from enum import Enum
from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, Field


# Define an Enum for all available screener types
class ScreenerType(str, Enum):
    AGGRESSIVE_SMALL_CAPS = "aggressive_small_caps"
    DAY_GAINERS = "day_gainers"
    DAY_LOSERS = "day_losers"
    GROWTH_TECHNOLOGY_STOCKS = "growth_technology_stocks"
    MOST_ACTIVES = "most_actives"
    MOST_SHORTED_STOCKS = "most_shorted_stocks"
    SMALL_CAP_GAINERS = "small_cap_gainers"
    UNDERVALUED_GROWTH_STOCKS = "undervalued_growth_stocks"
    UNDERVALUED_LARGE_CAPS = "undervalued_large_caps"
    CONSERVATIVE_FOREIGN_FUNDS = "conservative_foreign_funds"
    HIGH_YIELD_BOND = "high_yield_bond"
    PORTFOLIO_ANCHORS = "portfolio_anchors"
    SOLID_LARGE_GROWTH_FUNDS = "solid_large_growth_funds"
    SOLID_MIDCAP_GROWTH_FUNDS = "solid_midcap_growth_funds"
    TOP_MUTUAL_FUNDS = "top_mutual_funds"
    CUSTOM = "custom"  # For custom queries


# Optional query model for custom screeners
class CustomQuery(BaseModel):
    query: Any  # This will be the EqyQy or FndQy object
    sortField: Optional[str] = None
    sortType: Optional[str] = None


# Request model for the screener endpoint
class ScreenerRequest(BaseModel):
    screen_type: ScreenerType
    offset: int = Field(0, ge=0, description="The starting position in results")
    size: int = Field(25, gt=0, le=250, description="Number of results to return (max 250)")
    custom_query: Optional[Dict[str, Any]] = Field(None, description="Custom query parameters")
    minimal: bool = Field(True, description="Return minimal data")


class MinimalStockInfo(BaseModel):
    symbol: str
    name: str
    price: float
    marketCap: Optional[int]
    analystRating: Optional[str]
    dividendYield: Optional[float]
    peRatio: Optional[float]
    priceChangePercent: Optional[float]
    exchange: Optional[str]
    market: Optional[str]
    riskLevel: Optional[str]
    in_db: Optional[bool]


class ScreenerResponseMinimal(BaseModel):
    quotes: List[MinimalStockInfo]
    start: int
    count: int
