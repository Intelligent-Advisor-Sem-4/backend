from datetime import datetime, timedelta
from typing import Dict, Any, List

import yfinance as yf
from sqlalchemy.orm import Session

from classes.Asset import RiskScoreUpdate
from services.risk_analysis.esg_risk import ESGDataService
from services.risk_analysis.news_sentiment import NewsSentimentService
from services.risk_analysis.quantitative_risk import QuantitativeRiskService
from services.risk_analysis.anomalies import AnomalyDetectionService
from services.utils import get_stock_by_ticker, calculate_shallow_risk, calculate_shallow_risk_score
from classes.News import NewsArticle
from classes.Risk_Components import (
    RiskComponent,
    OverallRiskComponents,
    OverallRiskResponse,
    SentimentAnalysisResponse,
    QuantRiskResponse,
    EsgRiskResponse,
    AnomalyDetectionResponse
)


class RiskAnalysis:
    def __init__(self, ticker: str, db: Session, db_stock: Any = None):
        self.ticker = ticker
        self.db = db
        self.risk_components: Dict[str, Any] = {}
        self.stock = db_stock

        ticker_data = yf.Ticker(ticker)
        if ticker_data is None:
            raise ValueError(f"Ticker {ticker} not found.")
        basic_info = ticker_data.fast_info
        if not basic_info:
            raise ValueError(f"No data found for ticker {ticker}.")
        if self.stock is None:
            self.stock = get_stock_by_ticker(db, ticker)
            if self.stock is None:
                raise ValueError(f"Stock {ticker} not found in database.")

        self.ticker_data = ticker_data
        self.news_service = NewsSentimentService(self.db, self.ticker, self.ticker_data)
        self.quant_service = QuantitativeRiskService(self.db, ticker=self.ticker, ticker_data=self.ticker_data)
        self.anomaly_service = AnomalyDetectionService(self.ticker, self.ticker_data)
        self.esg_service = ESGDataService(self.ticker, self.ticker_data)

    def calculate_overall_risk(self) -> OverallRiskResponse:
        """Calculate overall risk score from all components"""
        print("Calculating overall risk")

        # Get components
        news_sentiment = self.risk_components.get("news_sentiment", None)
        quant_risk = self.risk_components.get("quantitative", None)
        anomalies = self.risk_components.get("anomalies", None)
        esg = self.risk_components.get("esg", None)

        # Extract risk scores with defaults
        news_score = getattr(news_sentiment, "risk_score", 5.0)
        quant_score = getattr(quant_risk, "quant_risk_score", 5.0)
        anomaly_score = getattr(anomalies, "anomaly_score", 0.0)
        esg_score = getattr(esg, "esg_risk_score", 5.0)

        # Define weights
        news_weight = 0.30
        quant_weight = 0.35
        anomaly_weight = 0.20
        esg_weight = 0.15

        # Create RiskComponent objects
        news_component = RiskComponent(weight=news_weight, score=news_score)
        quant_component = RiskComponent(weight=quant_weight, score=quant_score)
        anomaly_component = RiskComponent(weight=anomaly_weight, score=anomaly_score)
        esg_component = RiskComponent(weight=esg_weight, score=esg_score)

        # Create OverallRiskComponents object
        components = OverallRiskComponents(
            news_sentiment=news_component,
            quant_risk=quant_component,
            anomaly_detection=anomaly_component,
            esg_risk=esg_component
        )

        # Calculate weighted risk score
        weighted_score = (
                news_component.weight * news_component.score +
                quant_component.weight * quant_component.score +
                anomaly_component.weight * anomaly_component.score +
                esg_component.weight * esg_component.score
        )

        # Determine risk level
        from typing import Literal
        risk_level: Literal["Low", "Medium", "High"] = "Low"
        if weighted_score >= 7:
            risk_level = "High"
        elif weighted_score >= 4:
            risk_level = "Medium"

        overall_score = round(weighted_score, 2)

        # Update the stock's risk score in the database
        if self.stock:
            self.stock.risk_score = overall_score
            self.stock.risk_score_updated = datetime.now()
            self.db.commit()

        # Return OverallRiskResponse
        return OverallRiskResponse(
            overall_risk_score=overall_score,
            risk_level=risk_level,
            components=components
        )

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
            "company_name": self.stock.asset_name if self.stock else None,
            "analysis_date": datetime.now().isoformat(),
            "overall_risk": overall_risk.model_dump(),
            "components": {
                "news_sentiment": self.risk_components["news_sentiment"].dict(),
                "quantitative_metrics": self.risk_components["quantitative"].dict(),
                "anomalies": self.risk_components["anomalies"].dict(),
                "esg": self.risk_components["esg"].dict()
            }
        }

        return final_risk_report

    def _fast_get_risk_report(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Generate a fast risk score (private method)"""

        # If risk score present and not older than one day
        if (self.stock is not None and
                self.stock.risk_score is not None and
                self.stock.risk_score_updated and
                datetime.now() - self.stock.risk_score_updated < timedelta(days=1)):
            print('Returning cached risk score for', self.ticker)
            return {
                "symbol": self.ticker,
                "risk_score": self.stock.risk_score,
                "updated": False,
            }
        else:
            # Calculate risk score
            print('Calculating new risk score for', self.ticker)
            risk_score = calculate_shallow_risk_score(
                market_cap=self.ticker_data.info.get("marketCap"),
                high=self.ticker_data.info.get("fiftyTwoWeekHigh"),
                low=self.ticker_data.info.get("fiftyTwoWeekLow"),
                pe_ratio=self.ticker_data.info.get("forwardPE") or self.ticker_data.info.get("trailingPE"),
                eps=self.ticker_data.info.get("trailingEps"),
                debt_to_equity=self.ticker_data.info.get("debtToEquity"),
                beta=self.ticker_data.info.get("beta"),
            )

            # Update the stock's risk score in the database
            if self.stock:
                self.stock.risk_score = risk_score
                self.stock.risk_score_updated = datetime.now()
                self.db.commit()
                self.db.refresh(self.stock)

            return {
                "symbol": self.ticker,
                "risk_score": risk_score,
                "updated": True,
            }

    def get_news(self) -> List[NewsArticle]:
        """
        Get news articles related to the stock
        Returns:
            News articles
        """
        return self.news_service.get_news_articles(limit=10)

    def get_news_sentiment_risk(self, prefer_newest: bool = False,
                                use_llm: bool = True) -> SentimentAnalysisResponse:
        """
        Get news sentiment risk component

        Args:
            prefer_newest: Whether to prioritize the newest news articles
            use_llm: Whether to use llm for sentiment analysis

        Returns:
            News sentiment analysis results
        """
        if "news_sentiment" not in self.risk_components:
            self.risk_components["news_sentiment"] = self.news_service.get_news_sentiment(
                prefer_newest=prefer_newest,
                use_llm=use_llm
            )
        return self.risk_components["news_sentiment"]

    def get_quantitative_risk(self, lookback_days: int = 30, use_llm: bool = True) -> QuantRiskResponse:
        """
        Get quantitative risk metrics

        Args:
            lookback_days: Number of days to look back for historical data
            use_llm: Whether to use llm for quantitative analysis

        Returns:
            Quantitative risk metrics
        """
        if "quantitative" not in self.risk_components:
            self.risk_components["quantitative"] = self.quant_service.get_quantitative_metrics(
                lookback_days=lookback_days,
                use_llm=use_llm
            )
        return self.risk_components["quantitative"]

    def get_anomaly_risk(self, lookback_days: int = 30) -> AnomalyDetectionResponse:
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

    def get_esg_risk(self) -> EsgRiskResponse:
        """
        Get ESG risk component

        Returns:
            ESG risk data
        """
        if "esg" not in self.risk_components:
            self.risk_components["esg"] = self.esg_service.get_esg_data()
        return self.risk_components["esg"]

    def get_all_risk_components(self, lookback_days: int = 30, use_llm: bool = True) -> Dict[str, Any]:
        """
        Get all risk components at once

        Args:
            lookback_days: Number of days to look back for historical data
            use_llm: Whether to use llm for analysis

        Returns:
            Dictionary containing all risk components
        """
        return {
            "news_sentiment": self.get_news_sentiment_risk(use_llm=use_llm),
            "quantitative": self.get_quantitative_risk(lookback_days=lookback_days, use_llm=use_llm),
            "anomalies": self.get_anomaly_risk(lookback_days=lookback_days),
            "esg": self.get_esg_risk()
        }

    def get_risk_score_and_update(self) -> RiskScoreUpdate:
        """
        Get the risk score of the stock and whether it was just updated.
        Uses cached database score if available and recent,
        otherwise calculates a new risk score.

        Returns:
            RiskScoreUpdate: Object containing risk score and update status

        Raises:
            ValueError: If stock not found in database
        """
        if self.stock is None:
            raise ValueError("Stock not found in database.")

        # Use _fast_get_risk_report which handles caching logic
        fast_report = self._fast_get_risk_report()

        return RiskScoreUpdate(
            risk_score=fast_report["risk_score"],
            was_updated=fast_report["updated"]
        )


# if __name__ == "__main__":
#     # Example usage
#     db_gen = get_db()
#     session = next(db_gen)
#     try:
#         analyzer = RiskAnalysis("TSLA", session)
#         report = analyzer.generate_risk_report(lookback_days=30)
#         print(report)
#     except Exception as e:
#         print(f"Error: {e}")
#     finally:
#         session.close()
