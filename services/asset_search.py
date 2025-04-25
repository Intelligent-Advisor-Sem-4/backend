import yfinance as yf
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


def yfinance_search(query: str, news_count: int = 8, quote_count: int = 5) -> SearchResult:
    """
    Perform a search using Yahoo Finance API.

    :param query: The search query string.
    :param news_count: Number of news articles to fetch.
    :param quote_count: Number of quotes to fetch.
    :return: A SearchResult object containing news and quotes data.
    """
    response = yf.Search(
        query=query,
        news_count=news_count,
        max_results=quote_count,
    )

    news_data = response.response.get("news", [])
    quotes_data = response.response.get("quotes", [])

    # Process news: handling thumbnails and related tickers
    processed_news = []
    for item in news_data:
        thumbnail_url = None
        if item.get("thumbnail") and item["thumbnail"].get("resolutions"):
            # Find the smallest thumbnail
            smallest_resolution = min(
                item["thumbnail"]["resolutions"],
                key=lambda x: x.get("width", float("inf")) * x.get("height", float("inf"))
            )
            thumbnail_url = smallest_resolution.get("url")

        news_item = NewsResponse(
            uuid=item.get("uuid", ""),
            title=item.get("title", ""),
            publisher=item.get("publisher", None),
            link=item.get("link", ""),
            providerPublishedTime=item.get("providerPublishedTime", None),
            thumbnail=thumbnail_url,
            relatedTickers=item.get("relatedTickers", None)
        )
        processed_news.append(news_item)

    # Process quotes: sort by score and limit to quote_count
    sorted_quotes = sorted(
        quotes_data,
        key=lambda x: x.get("score", 0),
        reverse=True
    )[:quote_count]

    processed_quotes = []
    for item in sorted_quotes:
        quote_item = QuoteResponse(
            symbol=item.get("symbol", ""),
            shortName=item.get("shortName", None),
            quoteType=item.get("quoteType", None),
            exchange=item.get("exchange", None),
            sector=item.get("sector", None),
            sectorDisplay=item.get("sectorDisplay", None),
            industry=item.get("industry", None),
            industryDisplay=item.get("industryDisplay", None)
        )
        processed_quotes.append(quote_item)

    return SearchResult(news=processed_news, quotes=processed_quotes)


if __name__ == "__main__":
    # Example usage
    result = yfinance_search("samsung")
    print(f"Found {len(result.news)} news items and {len(result.quotes)} quotes")
    print("\nFirst news item:", result.news[0].model_dump() if result.news else "None")
    print("\nFirst quote:", result.quotes[0].model_dump() if result.quotes else "None")
