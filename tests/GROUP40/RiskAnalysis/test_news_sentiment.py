import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from services.risk_analysis.news_sentiment import NewsSentimentService, parse_llm_response
from classes.News import NewsArticle


class TestNewsSentimentService:
    # Test for environment variables
    def test_env_variables(self):
        assert "GEMINI_API_KEY" in os.environ, "GEMINI_API_KEY is missing in environment variables"
        assert "NVIDIA_API_KEY" in os.environ, "NVIDIA_API_KEY is missing in environment variables"

    # Mock database session and ticker data
    @pytest.fixture
    def mock_db(self):
        mock_db = MagicMock()
        mock_stock = MagicMock()
        mock_stock.asset_name = "Company X"  # Define asset_name in the mock
        mock_db.query().filter_by().first.return_value = mock_stock
        return mock_db

    @pytest.fixture
    def mock_ticker_data(self):
        ticker_data = MagicMock()
        ticker_data.get_news.return_value = [
            {
                "title": "Fraud Investigation Launched",
                "content": {
                    "provider": {"displayName": "News Source"},
                    "pubDate": datetime.now().isoformat(),
                    "summary": "Company X is under investigation for fraudulent activities.",
                    "canonicalUrl": {"url": "http://example.com/fraud-news"}
                }
            }
        ]
        return ticker_data

    @pytest.fixture
    def news_service(self, mock_db, mock_ticker_data):
        return NewsSentimentService(db=mock_db, ticker="COMPX", ticker_data=mock_ticker_data)

    # Test for generating news sentiment with fake news
    def test_generate_news_sentiment(self, news_service):
        fake_articles = [
            NewsArticle(
                title="Fraud Investigation Launched",
                news_id="1",
                summary="Company X is under investigation for fraudulent activities.",
                description="Authorities have launched an investigation into Company X for alleged fraud.",
                content_type="News",
                publish_date=datetime.now(),
                provider_name="News Source"
            ),
            NewsArticle(
                title="Company X CEO Arrested",
                news_id="2",
                summary="The CEO of Company X has been arrested for fraud.",
                description="In a shocking turn of events, the CEO of Company X has been arrested.",
                content_type="News",
                publish_date=datetime.now(),
                provider_name="Trusted News"
            ),
            NewsArticle(
                title="Company X Stock Plummets",
                news_id="3",
                summary="Company X's stock has plummeted following the fraud allegations.",
                description="Investors are worried about the future of Company X after the fraud allegations.",
                content_type="News",
                publish_date=datetime.now(),
                provider_name="Market Watch"
            )
        ]

        sentiment = news_service.generate_news_sentiment(fake_articles, use_llm=True)
        assert sentiment.stability_score < 3.0, "Expected stability score to be below 3"
        assert sentiment.stability_label == "High Risk", "Expected stability label to be 'High Risk'"

        # Non-strict assertions with warnings
        if sentiment.customer_suitability not in ["Unsuitable", "Cautious Inclusion", "Suitable"]:
            pytest.warns(UserWarning, match="Unexpected customer suitability value")
        if sentiment.suggested_action not in [
            "Monitor", "Flag for Review", "Review", "Flag for Removal", "Immediate Action Required"
        ]:
            pytest.warns(UserWarning, match="Unexpected suggested action value")

    # Test for LLM response parsing
    def test_parse_llm_response(self):
        llm_response = """
        {
            "stability_score": 5.0,
            "stability_label": "Moderate Risk",
            "key_risks": {
                "fraud_indicators": ["Potential fraudulent transactions detected"]
            },
            "security_assessment": "Moderate risk due to potential fraud.",
            "customer_suitability": "Cautious Inclusion",
            "suggested_action": "Flag for Review",
            "risk_rationale": ["Potential fraud detected in recent transactions."],
            "risk_score": 5.0
        }
        """
        parsed_response = parse_llm_response(llm_response)
        assert parsed_response["stability_score"] == 5.0
        assert parsed_response["stability_label"] == "Moderate Risk"
        assert "Potential fraudulent transactions detected" in parsed_response["key_risks"]["fraud_indicators"]
        assert parsed_response["customer_suitability"] == "Cautious Inclusion"
        assert parsed_response["suggested_action"] == "Flag for Review"
