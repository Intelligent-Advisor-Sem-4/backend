from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class NewsResponse(BaseModel):
    uuid: str
    title: str
    publisher: Optional[str] = None
    link: str
    providerPublishedTime: Optional[str] = None
    thumbnail: Optional[str] = None
    relatedTickers: Optional[List[str]] = None


class QuoteResponse(BaseModel):
    symbol: str
    shortName: Optional[str] = None
    quoteType: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    sectorDisplay: Optional[str] = None
    industry: Optional[str] = None
    industryDisplay: Optional[str] = None


class SearchResult(BaseModel):
    news: List[NewsResponse]
    quotes: List[QuoteResponse]