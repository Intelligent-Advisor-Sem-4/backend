from datetime import datetime
from typing import Any, Dict

import numpy as np
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


def calculate_risk_scores(volatility, beta, rsi, volume_change, debt_to_equity):
    """
    Calculate standardized risk scores on a 0-10 scale for different metrics.

    Args:
        volatility (float): Annualized volatility percentage
        beta (float or None): Market beta coefficient
        rsi (float): Relative Strength Index value
        volume_change (float): Recent volume change percentage
        debt_to_equity (float or None): Debt to equity ratio

    Returns:
        dict: Dictionary containing individual risk scores and overall risk score
    """
    # Calculate individual risk scores (0-10 scale)
    volatility_score = min(10.0, volatility / 5)  # Higher volatility = higher risk
    beta_score = min(10.0, abs(beta) * 3) if beta is not None else 5  # Higher absolute beta = higher risk
    rsi_risk = min(10.0, abs(rsi - 50) / 5)  # Extreme RSI = higher risk
    volume_score = min(10.0, abs(volume_change) / 10)  # Abnormal volume = higher risk
    debt_risk = min(10.0, debt_to_equity / 100) if debt_to_equity is not None else 5  # Higher debt = higher risk

    # Combine into overall quantitative risk score
    quant_risk_score = np.mean(
        [x for x in [volatility_score, beta_score, rsi_risk, volume_score, debt_risk] if x is not None])

    return {
        "volatility_score": float(volatility_score),
        "beta_score": float(beta_score) if beta is not None else None,
        "rsi_risk": float(rsi_risk),
        "volume_risk": float(volume_score),
        "debt_risk": float(debt_risk) if debt_to_equity is not None else None,
        "quant_risk_score": float(quant_risk_score)
    }


def calculate_risk_scores(volatility, beta, rsi, volume_change, debt_to_equity):
    """
    Calculate standardized risk scores on a 0-10 scale for different metrics.

    Args:
        volatility (float): Annualized volatility percentage
        beta (float or None): Market beta coefficient
        rsi (float): Relative Strength Index value
        volume_change (float): Recent volume change percentage
        debt_to_equity (float or None): Debt to equity ratio

    Returns:
        dict: Dictionary containing individual risk scores and overall risk score
    """
    # Calculate individual risk scores (0-10 scale)
    volatility_score = min(10.0, volatility / 5)  # Higher volatility = higher risk
    beta_score = min(10.0, abs(beta) * 3) if beta is not None else 5  # Higher absolute beta = higher risk
    rsi_risk = min(10.0, abs(rsi - 50) / 5)  # Extreme RSI = higher risk
    volume_score = min(10.0, abs(volume_change) / 10)  # Abnormal volume = higher risk
    debt_risk = min(10.0, debt_to_equity / 100) if debt_to_equity is not None else 5  # Higher debt = higher risk

    # Combine into overall quantitative risk score
    quant_risk_score = np.mean(
        [x for x in [volatility_score, beta_score, rsi_risk, volume_score, debt_risk] if x is not None])

    return {
        "volatility_score": float(volatility_score),
        "beta_score": float(beta_score) if beta is not None else None,
        "rsi_risk": float(rsi_risk),
        "volume_risk": float(volume_score),
        "debt_risk": float(debt_risk) if debt_to_equity is not None else None,
        "quant_risk_score": float(quant_risk_score)
    }


def parse_gemini_response(response) -> Dict[str, Any]:
    """Parse and clean Gemini's response"""
    import json
    response_text = response.text.strip()

    # Remove markdown code block formatting if present
    if response_text.startswith('```json'):
        json_content = response_text[7:].strip()
        if json_content.endswith('```'):
            json_content = json_content[:-3].strip()
    elif response_text.startswith('```') and response_text.endswith('```'):
        json_content = response_text[3:-3].strip()
    else:
        json_content = response_text

    sentiment_data = json.loads(json_content)

    # Add risk score based on sentiment if it's not already there
    if "risk_score" not in sentiment_data:
        risk_score = max(0, 10 - sentiment_data.get("stability_score", 0))
        sentiment_data["risk_score"] = risk_score

    return sentiment_data
