from datetime import datetime
from typing import Any, Dict
import numpy as np
from sqlalchemy.orm import Session

from classes.Sentiment import SentimentAnalysisResponse, KeyRisks
from classes.News import NewsArticle, RelatedArticle
from models.models import Stock


def parse_news_article(article: dict) -> NewsArticle:
    content = article.get("content", {})
    provider = content.get("provider", {})
    canonical_url = content.get("canonicalUrl", {}).get("url", "")
    thumbnail_data = content.get("thumbnail", {})
    resolutions = thumbnail_data.get("resolutions", [])

    if resolutions:
        # Find the smallest thumbnail by area (width × height)
        smallest_resolution = min(
            resolutions,
            key=lambda x: x.get("width", float("inf")) * x.get("height", float("inf"))
        )
        thumbnail_url = smallest_resolution.get("url", "")
    else:
        thumbnail_url = ""

    news = NewsArticle(
        news_id=article["id"],
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


def calculate_risk_scores(volatility, beta, rsi, volume_change, debt_to_equity, eps=None):
    """
    Calculate standardized risk scores on a 0-10 scale for different metrics.

    Args:
        volatility (float): Annualized volatility percentage
        beta (float or None): Market beta coefficient
        rsi (float): Relative Strength Index value
        volume_change (float): Recent volume change percentage
        debt_to_equity (float or None): Debt to equity ratio
        eps (float or None): Trailing Earnings Per Share

    Returns:
        dict: Dictionary containing individual risk scores and overall risk score
    """
    # Calculate individual risk scores (0-10 scale)
    volatility_score = min(10.0, volatility / 5)  # Higher volatility = higher risk
    beta_score = min(10.0, abs(beta) * 3) if beta is not None else 5  # Higher absolute beta = higher risk
    rsi_risk = min(10.0, abs(rsi - 50) / 5)  # Extreme RSI = higher risk
    volume_score = min(10.0, abs(volume_change) / 10)  # Abnormal volume = higher risk
    debt_risk = min(10.0, debt_to_equity / 100) if debt_to_equity is not None else 5  # Higher debt = higher risk

    # Non-linear EPS risk scoring
    eps_risk = 5  # Default neutral score if EPS is None
    if eps is not None:
        if eps < 0:
            # Negative EPS = higher risk (non-linear: more negative = exponentially higher risk)
            eps_risk = min(10.0, 7.0 + min(3.0, abs(eps) / 2))  # 7-10 range for negative EPS
        else:
            # Positive EPS = lower risk (non-linear: diminishing returns for very high EPS)
            eps_risk = max(0.0, 5.0 - min(5.0, np.sqrt(eps)))  # 0-5 range for positive EPS

    # Combine into overall quantitative risk score
    quant_risk_score = np.mean(
        [x for x in [volatility_score, beta_score, rsi_risk, volume_score, debt_risk, eps_risk] if x is not None])

    return {
        "volatility_score": float(volatility_score),
        "beta_score": float(beta_score) if beta is not None else None,
        "rsi_risk": float(rsi_risk),
        "volume_risk": float(volume_score),
        "debt_risk": float(debt_risk) if debt_to_equity is not None else None,
        "eps_risk": float(eps_risk) if eps is not None else None,
        "quant_risk_score": float(quant_risk_score)
    }


# def parse_gemini_response(response) -> Dict[str, Any]:
#     """Parse and clean Gemini's response"""
#     import json
#     response_text = response.text.strip()
#
#     # Remove markdown code block formatting if present
#     if response_text.startswith('```json'):
#         json_content = response_text[7:].strip()
#         if json_content.endswith('```'):
#             json_content = json_content[:-3].strip()
#     elif response_text.startswith('```') and response_text.endswith('```'):
#         json_content = response_text[3:-3].strip()
#     else:
#         json_content = response_text
#
#     sentiment_data = json.loads(json_content)
#
#     # Add risk score based on sentiment if it's not already there
#     if "risk_score" not in sentiment_data:
#         risk_score = max(0, 10 - sentiment_data.get("stability_score", 0))
#         sentiment_data["risk_score"] = risk_score
#
#     return sentiment_data

def parse_gemini_json_response(response_text: str) -> dict:
    """
    Parse JSON response from Gemini API, handling different response formats.

    Args:
        response_text (str): The raw text response from Gemini

    Returns:
        dict: Parsed JSON content

    Raises:
        json.JSONDecodeError: If parsing fails
    """
    import json

    # Clean up the response text
    response_text = response_text.strip()

    # Remove markdown code block formatting if present
    if response_text.startswith('```json'):
        json_content = response_text[7:].strip()
        if json_content.endswith('```'):
            json_content = json_content[:-3].strip()
    elif response_text.startswith('```') and response_text.endswith('```'):
        json_content = response_text[3:-3].strip()
    else:
        json_content = response_text

    # Parse the JSON content
    return json.loads(json_content)


def to_python_type(value):
    """Convert numpy types to Python native types."""
    if value is None:
        return None
    if hasattr(value, "item"):  # This checks if it's a numpy type
        return value.item()  # .item() converts numpy scalar to Python scalar
    return value


default_sentiment = SentimentAnalysisResponse(
    stability_score=0,
    stability_label="Stable",
    key_risks=KeyRisks(),
    security_assessment="No recent news articles available for analysis.",
    customer_suitability="Suitable",
    suggested_action="Monitor",
    risk_rationale=["No recent news available for analysis."],
    news_highlights=[],
    risk_score=5
)


def get_stock_by_ticker(db: Session, ticker: str) -> Stock:
    stock = db.query(Stock).filter_by(ticker_symbol=ticker).first()
    if not stock:
        raise ValueError(f"Stock with symbol '{ticker}' not found in database")
    return stock


def calculate_shallow_risk(s):
    """
    Calculate risk level for a stock based on available financial metrics.
    Handles missing data gracefully and provides a risk assessment
    based on multiple factors.

    Args:
        s (dict): Stock quote data containing financial metrics

    Returns:
        str: Risk level - "High", "Medium", or "Low"
    """
    # Initialize risk points system
    risk_points = 0
    metrics_used = 0

    # --- Market Cap (size risk) ---
    market_cap = s.get("marketCap")
    if market_cap is not None:
        metrics_used += 1
        if market_cap < 1e9:  # Small cap (below $1B)
            risk_points += 3
        elif market_cap < 10e9:  # Mid cap ($1B-$10B)
            risk_points += 1

    # --- Volatility risk ---
    high = s.get("fiftyTwoWeekHigh")
    low = s.get("fiftyTwoWeekLow")
    if high is not None and low is not None and low > 0:
        metrics_used += 1
        # Calculate volatility as percentage between high and low
        volatility = ((high - low) / low) * 100
        if volatility > 70:
            risk_points += 3
        elif volatility > 40:
            risk_points += 2
        elif volatility > 20:
            risk_points += 1

    # --- PE ratio (valuation risk) ---
    pe = s.get("forwardPE") or s.get("trailingPE")
    if pe is not None:
        metrics_used += 1
        if pe < 0:  # Negative earnings
            risk_points += 3
        elif pe > 50:  # Very high PE
            risk_points += 2
        elif pe > 30:  # High PE
            risk_points += 1

    # --- EPS (earnings risk) ---
    eps = s.get("epsTrailingTwelveMonths") or s.get("epsCurrentYear") or s.get("epsForward")
    if eps is not None:
        metrics_used += 1
        if eps < 0:  # Negative earnings
            risk_points += 3
        elif eps < 1 and market_cap and market_cap > 1e9:  # Low earnings for larger companies
            risk_points += 2

    # --- Debt (if available) ---
    debt_to_equity = s.get("debtToEquity")
    if debt_to_equity is not None:
        metrics_used += 1
        if debt_to_equity > 200:  # Very high debt
            risk_points += 3
        elif debt_to_equity > 100:  # High debt
            risk_points += 2
        elif debt_to_equity > 50:  # Moderate debt
            risk_points += 1

    # --- Beta (market correlation risk) ---
    beta = s.get("beta")
    if beta is not None:
        metrics_used += 1
        if abs(beta) > 2:  # Very volatile compared to market
            risk_points += 2
        elif abs(beta) > 1.5:  # More volatile than market
            risk_points += 1

    # Calculate average risk score, ensuring at least one metric was used
    avg_risk = risk_points / max(metrics_used, 1)

    # Set minimum metrics threshold to have confidence in assessment
    if metrics_used < 2:
        # With limited data, err on the side of caution
        return "Medium" if avg_risk < 1.5 else "High"

    # Determine risk level based on average risk score
    if avg_risk < 0.8:
        return "Low"
    elif avg_risk < 1.8:
        return "Medium"
    else:
        return "High"