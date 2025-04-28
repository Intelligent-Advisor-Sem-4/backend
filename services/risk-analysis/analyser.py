import os
from datetime import datetime, timedelta
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

        # Get news sentiment risk with a default value of 5
        news_sentiment_risk = getattr(self.risk_components.get("news_sentiment", {}), "risk_score", 5)

        # Safely get quantitative risk score
        quant_component = self.risk_components.get("quantitative", {})
        quant_risk_score = 5  # Default value

        # Handle the case where quant_component could be None or a dictionary
        if quant_component is not None and isinstance(quant_component, dict):
            risk_metrics = quant_component.get("risk_metrics", {})
            if isinstance(risk_metrics, dict):
                quant_risk_score = risk_metrics.get("quant_risk_score", 5)

        # Similar safety for anomalies and ESG
        anomaly_component = self.risk_components.get("anomalies", {})
        anomaly_score = 0  # Default value
        if anomaly_component is not None and isinstance(anomaly_component, dict):
            anomaly_score = anomaly_component.get("anomaly_score", 0)

        esg_component = self.risk_components.get("esg", {})
        esg_risk_score = 5  # Default value
        if esg_component is not None and isinstance(esg_component, dict):
            esg_risk_score = esg_component.get("esg_risk_score", 5)

        components = {
            "news_sentiment": {"weight": 0.30, "score": news_sentiment_risk},
            "quantitative": {"weight": 0.35, "score": quant_risk_score},
            "anomalies": {"weight": 0.20, "score": anomaly_score},
            "esg": {"weight": 0.15, "score": esg_risk_score}
        }

        # Calculate weighted risk score
        weighted_score = sum(comp["weight"] * comp["score"] for comp in components.values())

        # Determine risk level
        risk_level = "Low"
        if weighted_score >= 7:
            risk_level = "High"
        elif weighted_score >= 4:
            risk_level = "Medium"

        overall_score = round(weighted_score, 2)

        # Update the stock's risk score in the database
        self.stock.risk_score = overall_score
        self.stock.risk_score_updated = datetime.now()
        self.db.commit()

        return {
            "overall_risk_score": overall_score,
            "risk_level": risk_level,
            "components": components
        }

    def generate_risk_report(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive risk report for the stock"""
        # Analyze news sentiment
        self.risk_components["news_sentiment"] = self.news_service.get_news_sentiment(prefer_newest=False)

        # Calculate quantitative metrics
        self.risk_components["quantitative"] = self.quant_service.get_quantitative_metrics(lookback_days)

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

    def fast_get_risk_report(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Generate a fast risk score"""

        # If risk score present and not older than one day
        if self.stock.risk_score is not None and self.stock.risk_score_updated and datetime.now() - self.stock.risk_score_updated < timedelta(
                days=1):
            return {
                "symbol": self.ticker,
                "risk_score": self.stock.risk_score,
            }
        else:
            # Calculate risk score
            self.risk_components["news_sentiment"] = self.news_service.get_news_sentiment(prefer_newest=False,
                                                                                          use_gemini=False)
            self.risk_components["quantitative"] = self.quant_service.get_quantitative_metrics(lookback_days,
                                                                                               use_gemini=False)
            self.risk_components["anomalies"] = self.anomaly_service.detect_anomalies(lookback_days)
            self.risk_components["esg"] = self.esg_service.get_esg_data()
            overall_risk = self.calculate_overall_risk()

            return {
                "symbol": self.ticker,
                "risk_score": overall_risk["overall_risk_score"],
            }

    def get_news_sentiment_risk(self, prefer_newest: bool = False, use_gemini: bool = True) -> Dict[str, Any]:
        """
        Get news sentiment risk component

        Args:
            prefer_newest: Whether to prioritize the newest news articles
            use_gemini: Whether to use Gemini for sentiment analysis

        Returns:
            News sentiment analysis results
        """
        if "news_sentiment" not in self.risk_components:
            self.risk_components["news_sentiment"] = self.news_service.get_news_sentiment(
                prefer_newest=prefer_newest,
                use_gemini=use_gemini
            )
        return self.risk_components["news_sentiment"]

    def get_quantitative_risk(self, lookback_days: int = 30, use_gemini: bool = True) -> Dict[str, Any]:
        """
        Get quantitative risk metrics

        Args:
            lookback_days: Number of days to look back for historical data
            use_gemini: Whether to use Gemini for quantitative analysis

        Returns:
            Quantitative risk metrics
        """
        if "quantitative" not in self.risk_components:
            self.risk_components["quantitative"] = self.quant_service.get_quantitative_metrics(
                lookback_days=lookback_days,
                use_gemini=use_gemini
            )
        return self.risk_components["quantitative"]

    def get_anomaly_risk(self, lookback_days: int = 30) -> Dict[str, Any]:
        """
        Get anomaly detection risk component

        Args:
            lookback_days: Number of days to look back for anomaly detection

        Returns:
            Anomaly detection results
        """
        if "anomalies" not in self.risk_components:
            self.risk_components["anomalies"] = self.anomaly_service.detect_anomalies(lookback_days)
        return self.risk_components["anomalies"]

    def get_esg_risk(self) -> Dict[str, Any]:
        """
        Get ESG risk component

        Returns:
            ESG risk data
        """
        if "esg" not in self.risk_components:
            self.risk_components["esg"] = self.esg_service.get_esg_data()
        return self.risk_components["esg"]

    def get_all_risk_components(self, lookback_days: int = 30, use_gemini: bool = True) -> Dict[str, Any]:
        """
        Get all risk components at once

        Args:
            lookback_days: Number of days to look back for historical data
            use_gemini: Whether to use Gemini for analysis

        Returns:
            Dictionary containing all risk components
        """
        return {
            "news_sentiment": self.get_news_sentiment_risk(use_gemini=use_gemini),
            "quantitative": self.get_quantitative_risk(lookback_days=lookback_days, use_gemini=use_gemini),
            "anomalies": self.get_anomaly_risk(lookback_days=lookback_days),
            "esg": self.get_esg_risk()
        }


if __name__ == "__main__":
    # Example usage
    db_gen = get_db()
    session = next(db_gen)
    try:
        analyzer = RiskAnalysis("NVDA", session)
        report = analyzer.generate_risk_report(lookback_days=30)
        print(report)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()
