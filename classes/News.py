from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class RelatedArticle(BaseModel):
    title: str
    url: str
    content_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    provider_name: Optional[str] = None


class NewsArticle(BaseModel):
    title: str
    news_id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[str] = None
    publish_date: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    canonical_url: Optional[str] = None
    provider_name: Optional[str] = None
    related_articles: List[RelatedArticle] = []
