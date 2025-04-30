import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session
from yfinance import Ticker

from classes.Risk_Components import SentimentAnalysisResponse
from models.models import NewsRiskAnalysis
from services.utils import parse_news_article, default_sentiment, get_stock_by_ticker, parse_gemini_json_response
from classes.News import NewsArticle


def parse_gemini_response(response) -> Dict[str, Any]:
    """Parse and clean Gemini's response"""
    try:
        # Use common utility function to parse the response
        sentiment_data = parse_gemini_json_response(response.text)

        # Add risk score based on sentiment if it's not already there
        if "risk_score" not in sentiment_data:
            risk_score = max(0, 10 - sentiment_data.get("stability_score", 0))
            sentiment_data["risk_score"] = risk_score

        return sentiment_data

    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini response: {e}")
        # Return default sentiment data or raise the exception
        raise


class NewsSentimentService:
    def __init__(self, gemini_client, db: Session, ticker: str, ticker_data: Ticker):
        self.db = db
        self.stock = get_stock_by_ticker(db, ticker)
        self.gemini_client = gemini_client
        self.ticker = ticker
        self.ticker_data = ticker_data

    def get_news_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Fetch recent news articles for the stock"""
        print('Fetching news articles for stock')
        articles = self.ticker_data.get_news(count=limit)
        return [parse_news_article(article) for article in articles]

    def generate_news_sentiment(self, articles: List[NewsArticle], use_gemini: bool = True) -> Optional[
        SentimentAnalysisResponse]:
        """Use Gemini to analyze news sentiment and store results in database if you use_gemini is True"""
        print('Generating news sentiment analysis')
        # Default sentiment for no articles or error cases
        default_sentiment_data = {
            "stability_score": 0,
            "stability_label": "Stable",
            "key_risks": {
                "legal_risks": [],
                "governance_risks": [],
                "fraud_indicators": [],
                "political_exposure": [],
                "operational_risks": [],
                "financial_stability_issues": [],
            },
            "security_assessment": "No recent news articles available for analysis. Default stable assessment applied.",
            "customer_suitability": "Suitable",
            "suggested_action": "Monitor",
            "risk_rationale": ["No recent news available for analysis."],
            "news_highlights": [],
            "risk_score": 0,
            "updated_at": datetime.now(),
        }

        if not articles:
            print('No articles found for sentiment analysis')
            sentiment_data = default_sentiment_data
        elif not use_gemini:
            if self.stock is None:
                print('No stock in database and Gemini disabled')
                return None
            # If Gemini is disabled, check if we have data in the database first
            existing_analysis = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()
            if existing_analysis:
                try:
                    return SentimentAnalysisResponse(**existing_analysis.response_json)
                except ValidationError:
                    pass  # If validation fails, continue to return None
            return None  # Return None if Gemini is disabled and no valid database entry exists
        else:
            sentiment_response = None
            try:
                # Prepare news data for Gemini
                news_text = self._format_news_articles(articles)
                prompt = self._create_sentiment_prompt(news_text)
                # Get response from Gemini
                print('Generating sentiment analysis with Gemini')
                sentiment_response = self.gemini_client.models.generate_content(model='gemini-2.0-flash',
                                                                                contents=prompt)
                sentiment_data = parse_gemini_response(sentiment_response)

            except Exception as e:
                print(f"[Gemini Analysis Error] Exception: {e}")
                print(f"[Gemini Raw Response] {getattr(sentiment_response, 'text', 'No response')}")

                sentiment_data = default_sentiment_data.copy()
                sentiment_data.update({
                    "stability_label": "Moderate Risk",
                    "customer_suitability": "Cautious Inclusion",
                    "suggested_action": "Flag for Review",
                    "security_assessment": "Unable to assess due to analysis error. Recommend manual review before investor exposure.",
                    "risk_rationale": [
                        "Automated sentiment analysis failed.",
                        "Fallback risk score applied to avoid premature inclusion."
                    ],
                    "error_details": str(e)
                })

        # Validate and store in database
        return self._validate_and_store_sentiment(sentiment_data)

    def _validate_and_store_sentiment(self, sentiment_data: Dict[str, Any]) -> SentimentAnalysisResponse:
        """Validate sentiment data and store it in the database"""
        print('Validating and storing sentiment data')
        try:
            # Parse the data through the Pydantic model for validation
            sentiment_model = SentimentAnalysisResponse(**sentiment_data, updated_at=str(datetime.now()))

            if not self.stock:
                print("No stock in database to store")
                return sentiment_model
            try:
                # Check if an analysis already exists for this stock
                existing_analysis = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

                if existing_analysis:
                    # Update fields using validated data
                    for key, value in sentiment_model.model_dump().items():
                        setattr(existing_analysis, key, value) if hasattr(existing_analysis, key) else None

                    # Always update these fields
                    existing_analysis.response_json = sentiment_model.model_dump()
                    existing_analysis.updated_at = datetime.now()
                else:
                    # Create new record
                    news_analysis = NewsRiskAnalysis(
                        stock_id=self.stock.stock_id,
                        response_json=sentiment_model.model_dump(),
                        stability_score=sentiment_model.stability_score,
                        stability_label=sentiment_model.stability_label,
                        customer_suitability=sentiment_model.customer_suitability,
                        suggested_action=sentiment_model.suggested_action,
                        risk_score=sentiment_model.risk_score,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db.add(news_analysis)

                # Commit the changes
                self.db.commit()

            except Exception as e:
                self.db.rollback()
                print(f"[Database Error] Failed to store news analysis: {e}")

            # Return the validated model
            return sentiment_model

        except ValidationError as e:
            print(f"[Validation Error] Gemini response doesn't match expected schema: {e}")

            # Create a fallback valid model with error details
            fallback_model = default_sentiment

            # Store the fallback in database
            self._store_fallback_sentiment(fallback_model)

            return fallback_model

    def _store_fallback_sentiment(self, fallback_model: SentimentAnalysisResponse) -> None:
        """Store fallback sentiment in the database"""
        print("Something has gone wrong storing fallback sentiment")
        if not self.stock:
            print("No stock in database to store")
            return None
        try:
            existing_analysis = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

            if existing_analysis:
                existing_analysis.response_json = fallback_model.model_dump()
                existing_analysis.stability_score = fallback_model.stability_score
                existing_analysis.stability_label = fallback_model.stability_label
                existing_analysis.customer_suitability = fallback_model.customer_suitability
                existing_analysis.suggested_action = fallback_model.suggested_action
                existing_analysis.updated_at = datetime.now()
                existing_analysis.risk_score = fallback_model.risk_score
            else:
                news_analysis = NewsRiskAnalysis(
                    stock_id=self.stock.stock_id,
                    response_json=fallback_model.model_dump(),
                    stability_score=fallback_model.stability_score,
                    stability_label=fallback_model.stability_label,
                    customer_suitability=fallback_model.customer_suitability,
                    suggested_action=fallback_model.suggested_action,
                    risk_score=fallback_model.risk_score,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(news_analysis)

            self.db.commit()
        except Exception as db_err:
            self.db.rollback()
            print(f"[Database Error] Failed to store fallback analysis: {db_err}")

    def _format_news_articles(self, articles: List[NewsArticle]) -> str:
        """Format news articles for the Gemini prompt"""
        print('Formatting news articles for Gemini')
        news_text = f"Recent news articles about {self.ticker}:\n\n"

        for i, article in enumerate(articles, 1):
            news_text += f"{i}. Title: {article.title}\n"
            news_text += f"   Date: {article.publish_date}\n"
            news_text += f"   Source: {article.provider_name}\n"
            news_text += f"   Summary: {article.summary}\n\n"

            if article.related_articles:
                news_text += "   Related articles:\n"
                for related in article.related_articles:
                    news_text += f"   - {related.title} ({related.title})\n"
                news_text += "\n"

        return news_text

    def _create_sentiment_prompt(self, news_text: str) -> str:
        """Create the prompt for Gemini"""
        print('Creating sentiment analysis prompt for Gemini')
        asset_name = self.stock.asset_name if self.stock else self.ticker
        return f"""
        As a financial risk and compliance analyst for a stock screening platform, analyze the following news articles about {self.ticker} ({asset_name}) to assess its stability and security from a regulatory, operational, and investor-protection perspective.

        {news_text}

        Provide a structured JSON response focused on risk factors and investor suitability for inclusion in a regulated financial product. Ensure the analysis is explainable, auditable, and suitable for display in an admin dashboard.

        Output must include:

        1. **stability_score** (numeric): A score from -10 (extremely unstable/high risk) to +10 (extremely stable/secure)
        2. **stability_label** (string): One of ["High Risk", "Moderate Risk", "Slight Risk", "Stable", "Very Stable"]
        3. **key_risks** (object): Key risk factors identified, categorized as:
           - legal_risks (lawsuits, investigations, compliance failures)
           - governance_risks (executive exits, board conflicts, control disputes)
           - fraud_indicators (misstatements, shell entities, shady transactions)
           - political_exposure (foreign influence, sanctions, subsidies, regulations)
           - operational_risks (supply disruptions, recalls, safety breaches)
           - financial_stability_issues (high leverage, poor liquidity, debt covenant stress)
        4. **security_assessment** (string, max 150 words): Objective summary of potential threats to investor security and financial exposure.
        5. **customer_suitability** (string): One of ["Unsuitable", "Cautious Inclusion", "Suitable"], based on investor protection concerns.
        6. **suggested_action** (string): One of ["Monitor", "Flag for Review", "Review", "Flag for Removal", "Immediate Action Required"]
        7. **risk_rationale** (array of strings): 2-3 concise bullet points justifying the score, label, and action using news-derived evidence.
        8. **news_highlights** (array of strings, optional): If applicable, list key headline-worthy excerpts that triggered concern or affected scoring.
        9. **risk_score** Derived risk score Float (0-10) based on stability score and other risk factors.

        Ensure output is valid JSON and optimized for downstream explainability modules.
        """

    def get_news_sentiment(self, prefer_newest: bool = True, use_gemini: bool = True) -> Optional[
        SentimentAnalysisResponse]:
        """Fetch news sentiment for the stock"""
        print("Getting news sentiment")

        # Return early if stock is None and we're not using Gemini
        if self.stock is None and not use_gemini:
            print("No stock in database and Gemini disabled, returning None")
            return None

        # If Gemini is disabled, check if we have existing sentiment data
        if not use_gemini:
            print("Gemini disabled, checking database only")
            news_sentiment_not_gemini = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()
            if news_sentiment_not_gemini:
                try:
                    print("Returning existing sentiment report")
                    return SentimentAnalysisResponse(**news_sentiment_not_gemini.response_json)
                except ValidationError:
                    print("Invalid sentiment data in database")
            return None

        # Normal processing with Gemini enabled
        if prefer_newest or self.stock is None:
            print("Generating brand new sentiment")
            articles = self.get_news_articles(limit=10)
            return self.generate_news_sentiment(articles, use_gemini=use_gemini)

        # Check if sentiment already exists in the database
        print("Checking existing sentiment")
        news_sentiment = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

        # If no sentiment exists, or it's older than 6 hours, fetch new sentiment
        if not news_sentiment or news_sentiment.updated_at < datetime.now() - timedelta(hours=6):
            print("No sentiment found or found older sentiment")
            articles = self.get_news_articles(limit=10)
            return self.generate_news_sentiment(articles, use_gemini=use_gemini)

        try:
            print("Returning existing sentiment report")
            return SentimentAnalysisResponse(**news_sentiment.response_json)
        except ValidationError:
            # If the stored JSON is invalid, generate a new sentiment
            articles = self.get_news_articles(limit=10)
            return self.generate_news_sentiment(articles, use_gemini=use_gemini)
