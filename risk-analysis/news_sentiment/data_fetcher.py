from datetime import datetime

import yfinance as yf
from sqlalchemy.orm import Session

from db.dbConnect import get_db
from models.models import NewsArticle, RelatedArticle, Stock


def parse_news_article(stock_id: int, article: dict) -> NewsArticle:
    content = article.get("content", {})
    provider = content.get("provider", {})
    canonical_url = content.get("canonicalUrl", {}).get("url", "")
    thumbnail_url = content.get("thumbnail", {}).get("resolutions", [{}])[0].get("url", "")

    news = NewsArticle(
        news_id=article["id"],
        stock_id=stock_id,
        title=content.get("title"),
        summary=content.get("summary"),
        description=content.get("description"),
        content_type=content.get("contentType"),
        publish_date=datetime.fromisoformat(content.get("pubDate").replace("Z", "+00:00")),
        thumbnail_url=thumbnail_url,
        canonical_url=canonical_url,
        provider_name=provider.get("displayName")
    )

    storyline_items = content.get("storyline") or {}
    storyline_items = storyline_items.get("storylineItems", [])

    for item in storyline_items:
        sub = item["content"]
        news.related_articles.append(RelatedArticle(
            title=sub.get("title"),
            url=sub.get("canonicalUrl", {}).get("url", ""),
            content_type=sub.get("contentType"),
            thumbnail_url=sub.get("thumbnail", {}).get("url", ""),
            provider_name=sub.get("provider", {}).get("displayName")
        ))

    return news


def store_news_for_ticker(db: Session, ticker: str):
    stock = db.query(Stock).filter_by(ticker_symbol=ticker).first()
    if not stock:
        raise ValueError(f"Stock with symbol '{ticker}' not found in database")

    yf_data = yf.Ticker(ticker)
    news_list = yf_data.news

    for article in news_list:
        if not db.query(NewsArticle).filter_by(news_id=article["id"]).first():
            news_obj = parse_news_article(stock.stock_id, article)
            db.add(news_obj)

    db.commit()


if __name__ == "__main__":
    db_gen = get_db()
    session = next(db_gen)
    try:
        # Create a new stock
        try:
            store_news_for_ticker(session, 'TSLA')
        except ValueError as e:
            print(e)
    finally:
        db_gen.close()
