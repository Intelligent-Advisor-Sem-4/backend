import os
from datetime import datetime
from typing import Dict, Any

import yfinance as yf
from google import genai
from sqlalchemy.orm import Session

from anomalies import AnomalyDetectionService
from db.dbConnect import get_db
from esg_risk import ESGDataService
from news_sentiment import NewsSentimentService
from quantitative_risk import QuantitativeRiskService
from services.utils import get_stock_by_ticker

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class RiskAnalysis:
    def __init__(self, ticker: str, db: Session):
        self.ticker = ticker
        self.db = db
        self.risk_components = {}
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        ticker_data = yf.Ticker(ticker)
        if ticker_data is None:
            raise ValueError(f"Ticker {ticker} not found.")
        basic_info = ticker_data.fast_info
        if not basic_info:
            raise ValueError(f"No data found for ticker {ticker}.")
        self.stock = get_stock_by_ticker(db, ticker)

        self.ticker_data = ticker_data

        self.news_service = NewsSentimentService(self.gemini_client, self.db, self.ticker, self.ticker_data)
        self.quant_service = QuantitativeRiskService(self.gemini_client, self.db, self.ticker, self.ticker_data)
        self.anomaly_service = AnomalyDetectionService(self.ticker, self.ticker_data)
        self.esg_service = ESGDataService(self.ticker, self.ticker_data)

    def calculate_overall_risk(self) -> Dict[str, Any]:
        """Calculate overall risk score from all components"""
        print("Calculating overall risk")
        # Get all risk components with assigned weights
        news_sentiment_risk = getattr(self.risk_components.get("news_sentiment", {}), "risk_score", 5)

        components = {
            "news_sentiment": {"weight": 0.30,
                               "score": news_sentiment_risk},
            "quantitative": {"weight": 0.35,
                             "score": self.risk_components.get("quantitative", {}).get("risk_metrics", {}).get(
                                 "quant_risk_score", 5)},
            "anomalies": {"weight": 0.20, "score": self.risk_components.get("anomalies", {}).get("anomaly_score", 0)},
            "esg": {"weight": 0.15, "score": self.risk_components.get("esg", {}).get("esg_risk_score", 5)}
        }

        # Calculate weighted risk score
        weighted_score = sum(comp["weight"] * comp["score"] for comp in components.values())

        # Determine risk level
        risk_level = "Low"
        if weighted_score >= 7:
            risk_level = "High"
        elif weighted_score >= 4:
            risk_level = "Medium"

        return {
            "overall_risk_score": round(weighted_score, 2),
            "risk_level": risk_level,
            "components": components
        }

    def generate_risk_report(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive risk report for the stock"""
        # Store news articles in the database
        self.news_service.store_news_for_ticker()

        # Analyze news sentiment
        self.risk_components["news_sentiment"] = self.news_service.get_news_sentiment(prefer_newest=False)

        # Calculate quantitative metrics
        self.risk_components["quantitative"] = self.quant_service.calculate_quantitative_metrics(lookback_days)

        # Detect anomalies
        self.risk_components["anomalies"] = self.anomaly_service.detect_anomalies(lookback_days)

        # Get ESG data
        self.risk_components["esg"] = self.esg_service.get_esg_data()

        # Calculate overall risk
        overall_risk = self.calculate_overall_risk()

        # Compile final report
        final_risk_report = {
            "symbol": self.ticker,
            "company_name": self.stock.asset_name,
            "analysis_date": datetime.now().isoformat(),
            "overall_risk": overall_risk,
            "components": {
                "news_sentiment": self.risk_components["news_sentiment"],
                "quantitative_metrics": self.risk_components["quantitative"],
                "anomalies": self.risk_components["anomalies"],
                "esg": self.risk_components["esg"]
            }
        }

        return final_risk_report


if __name__ == "__main__":
    # Example usage
    db_gen = get_db()
    session = next(db_gen)
    try:
        analyzer = RiskAnalysis("AAPL", session)
        report = analyzer.generate_risk_report(lookback_days=30)
        print(report)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()
