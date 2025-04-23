import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from google import genai
from db.dbConnect import get_db
from models.models import Stock, NewsArticle, RelatedArticle
from utils import parse_news_article

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

router = APIRouter(prefix="/api/risk", tags=["Risk Analysis"])


class RiskAnalysis:
    def __init__(self, ticker: str, db: Session):
        self.ticker = ticker
        self.db = db
        self.stock = self._get_stock()
        self.ticker_data = yf.Ticker(ticker)
        self.risk_components = {}

    def _get_stock(self) -> Stock:
        stock = self.db.query(Stock).filter_by(ticker_symbol=self.ticker).first()
        if not stock:
            raise ValueError(f"Stock with symbol '{self.ticker}' not found in database")
        return stock

    def store_news_for_ticker(self, db: Session, ticker: str):

        yf_data = yf.Ticker(ticker)
        news_list = yf_data.news

        for article in news_list:
            if not db.query(NewsArticle).filter_by(news_id=article["id"]).first():
                news_obj = parse_news_article(self.stock.stock_id, article)
                db.add(news_obj)

        db.commit()

    def get_news_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent news articles for the stock"""
        articles = (self.db.query(NewsArticle)
                    .filter_by(stock_id=self.stock.stock_id)
                    .order_by(NewsArticle.publish_date.desc())
                    .limit(limit)
                    .all())

        results = []
        for article in articles:
            article_dict = {
                "news_id": article.news_id,
                "title": article.title,
                "summary": article.summary,
                "description": article.description,
                "publish_date": article.publish_date.isoformat(),
                "provider_name": article.provider_name,
                "related_articles": []
            }

            for related in article.related_articles:
                article_dict["related_articles"].append({
                    "title": related.title,
                    "provider_name": related.provider_name
                })

            results.append(article_dict)

        return results

    def analyze_news_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use Gemini to analyze news sentiment"""
        if not articles:
            return {
                "sentiment_score": 0,
                "sentiment_label": "Neutral",
                "key_risks": [],
                "analysis": "No recent news articles available for analysis."
            }

        # Prepare news data for Gemini
        news_text = "Recent news articles about " + self.ticker + ":\n\n"
        for i, article in enumerate(articles, 1):
            news_text += f"{i}. Title: {article['title']}\n"
            news_text += f"   Date: {article['publish_date']}\n"
            news_text += f"   Source: {article['provider_name']}\n"
            news_text += f"   Summary: {article['summary']}\n\n"

            if article.get('related_articles'):
                news_text += "   Related articles:\n"
                for related in article['related_articles']:
                    news_text += f"   - {related['title']} ({related['provider_name']})\n"
                news_text += "\n"

        # Create prompt for Gemini
        prompt = f"""
        As a financial risk and compliance analyst for a stock screening platform, analyze the following news articles about {self.ticker} ({self.stock.asset_name}) to assess its stability and security from a regulatory, operational, and investor-protection perspective.

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

        Ensure output is valid JSON and optimized for downstream explainability modules.
        """

        # Get response from Gemini
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)

        try:
            # Parse JSON response
            import json
            sentiment_data = json.loads(response.text)

            # Add risk score based on sentiment
            risk_score = max(0, 10 - sentiment_data["sentiment_score"])  # Convert sentiment to risk (10 = high risk)
            sentiment_data["risk_score"] = risk_score

            return sentiment_data
        except Exception as e:
            print(f"[Gemini Parsing Error] Exception: {e}")
            print(f"[Gemini Raw Response] {response.text}")

            return {
                "stability_score": 0,
                "stability_label": "Moderate Risk",
                "key_risks": {
                    "legal_risks": [],
                    "governance_risks": [],
                    "fraud_indicators": [],
                    "political_exposure": [],
                    "operational_risks": [],
                    "financial_stability_issues": [],
                },
                "security_assessment": "Unable to assess due to analysis error. Recommend manual review before investor exposure.",
                "customer_suitability": "Cautious Inclusion",
                "suggested_action": "Flag for Review",
                "risk_rationale": [
                    "Automated sentiment analysis failed.",
                    "Fallback risk score applied to avoid premature inclusion."
                ],
                "news_highlights": [],
                "error_details": str(e)  # Optional: remove in production
            }


    def calculate_quantitative_metrics(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Calculate quantitative risk metrics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 30)  # Extra data for calculations

        try:
            # Get historical price data
            hist = self.ticker_data.history(start=start_date, end=end_date)
            if hist.empty:
                raise ValueError(f"No historical data available for {self.ticker}")

            # Calculate metrics
            # 1. Volatility (annualized)
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100  # Annualized and in percent

            # 2. Beta (market risk)
            try:
                market_data = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
                market_returns = market_data['Close'].pct_change().dropna()

                # Align both series to have matching dates
                common_idx = daily_returns.index.intersection(market_returns.index)
                stock_returns_aligned = daily_returns.loc[common_idx]
                market_returns_aligned = market_returns.loc[common_idx]

                # Calculate beta
                covariance = stock_returns_aligned.cov(market_returns_aligned)
                market_variance = market_returns_aligned.var()
                beta = covariance / market_variance
            except Exception as e:
                print(f"Error calculating beta: {e}")
                beta = None

            # 3. Volume analysis
            avg_volume = hist['Volume'].mean()
            recent_volume = hist['Volume'].iloc[-5:].mean()  # Last 5 days
            volume_change = ((recent_volume / avg_volume) - 1) * 100  # Percentage change

            # 4. Price momentum
            recent_price = hist['Close'].iloc[-1]
            price_20d_ago = hist['Close'].iloc[-min(21, len(hist)):].iloc[0]
            momentum_20d = ((recent_price / price_20d_ago) - 1) * 100

            # 5. RSI (Relative Strength Index)
            delta = hist['Close'].diff().dropna()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))

            # Calculate risk scores
            volatility_score = min(10, volatility / 5)  # Higher volatility = higher risk

            # Beta risk score (higher beta = higher risk)
            beta_score = min(10, abs(beta) * 3) if beta is not None else 5

            # Volume change risk (abnormal volume = higher risk)
            volume_score = min(10, abs(volume_change) / 10)

            # RSI risk (extreme values = higher risk)
            rsi_risk = min(10, abs(rsi - 50) / 5)

            # Combine into overall quantitative risk score
            quant_risk_score = np.mean([volatility_score, beta_score, volume_score, rsi_risk])

            return {
                "volatility": volatility,
                "beta": beta,
                "volume_change_percent": volume_change,
                "momentum_20d_percent": momentum_20d,
                "rsi": rsi,
                "risk_metrics": {
                    "volatility_score": float(volatility_score),
                    "beta_score": float(beta_score) if beta is not None else None,
                    "volume_risk": float(volume_score),
                    "rsi_risk": float(rsi_risk),
                    "quant_risk_score": float(quant_risk_score)
                }
            }
        except Exception as e:
            print(f"Error calculating quantitative metrics: {e}")
            return {
                "error": str(e),
                "risk_metrics": {
                    "quant_risk_score": 5  # Neutral score on error
                }
            }

    def detect_anomalies(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Detect price, volume and other anomalies"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        try:
            # Get historical data
            hist = self.ticker_data.history(start=start_date, end=end_date)
            if hist.empty:
                return {"flags": [], "anomaly_score": 0}

            flags = []
            flag_scores = []

            # 1. Check for unusual price gaps
            daily_changes = hist['Close'].pct_change().dropna()
            std_change = daily_changes.std()
            unusual_changes = daily_changes[abs(daily_changes) > 3 * std_change]

            for date, change in unusual_changes.items():
                severity = min(10, abs(change) / std_change)
                flag_scores.append(severity)
                flags.append({
                    "type": "Price Gap",
                    "date": date.strftime("%Y-%m-%d"),
                    "description": f"Unusual price change of {change * 100:.2f}% (over 3σ)",
                    "severity": float(severity)
                })

            # 2. Check for unusual volume spikes
            volume_mean = hist['Volume'].mean()
            volume_std = hist['Volume'].std()
            unusual_volume = hist[hist['Volume'] > volume_mean + 2 * volume_std]

            for date, row in unusual_volume.iterrows():
                volume_ratio = row['Volume'] / volume_mean
                severity = min(10, (volume_ratio - 1) / 2)
                flag_scores.append(severity)
                flags.append({
                    "type": "Volume Spike",
                    "date": date.strftime("%Y-%m-%d"),
                    "description": f"Volume {volume_ratio:.1f}x above average",
                    "severity": float(severity)
                })

            # 3. Check for bearish patterns (e.g., consecutive down days)
            price_changes = hist['Close'].pct_change().dropna()
            down_days = (price_changes < 0).astype(int)
            bearish_runs = down_days.rolling(window=5).sum()

            if bearish_runs.max() >= 4:  # 4+ down days in a 5-day window
                severity = min(10, bearish_runs.max() * 2)
                flag_scores.append(severity)
                flags.append({
                    "type": "Bearish Pattern",
                    "date": bearish_runs.idxmax().strftime("%Y-%m-%d"),
                    "description": f"{int(bearish_runs.max())} down days in a 5-day window",
                    "severity": float(severity)
                })

            # Calculate anomaly score
            anomaly_score = max(flag_scores) if flag_scores else 0

            return {
                "flags": flags,
                "anomaly_score": float(anomaly_score)
            }
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            return {"flags": [], "anomaly_score": 0}

    def get_esg_data(self) -> Dict[str, Any]:
        """Get ESG (Environmental, Social, Governance) risk data"""
        try:
            # Try to get ESG data from yfinance
            esg_data = self.ticker_data.sustainability

            if esg_data is not None and not esg_data.empty:
                # Extract ESG scores
                total_esg = esg_data.get('totalEsg', [None])[0]
                env_score = esg_data.get('environmentScore', [None])[0]
                social_score = esg_data.get('socialScore', [None])[0]
                governance_score = esg_data.get('governanceScore', [None])[0]

                # Calculate risk score from ESG (higher ESG risk = higher risk score)
                esg_risk_score = 10 - min(10, total_esg)

                return {
                    "total_esg": total_esg,
                    "environmental_score": env_score,
                    "social_score": social_score,
                    "governance_score": governance_score,
                    "esg_risk_score": float(esg_risk_score) if esg_risk_score is not None else 5
                }
            else:
                return {
                    "esg_risk_score": 5  # Neutral score when data not available
                }
        except Exception as e:
            print(f"Error getting ESG data: {e}")
            return {"esg_risk_score": 5}

    def calculate_overall_risk(self) -> Dict[str, Any]:
        """Calculate overall risk score from all components"""
        # Get all risk components with assigned weights
        components = {
            "news_sentiment": {"weight": 0.30,
                               "score": self.risk_components.get("news_sentiment", {}).get("risk_score", 5)},
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

    def generate_risk_report(self, lookback_days: int = 30, news_limit: int = 10) -> Dict[str, Any]:
        """Generate comprehensive risk report for the stock"""
        # Fetch news articles
        articles = self.get_news_articles(news_limit)

        # Analyze news sentiment
        self.risk_components["news_sentiment"] = self.analyze_news_sentiment(articles)

        # Calculate quantitative metrics
        self.risk_components["quantitative"] = self.calculate_quantitative_metrics(lookback_days)

        # Detect anomalies
        self.risk_components["anomalies"] = self.detect_anomalies(lookback_days)

        # Get ESG data
        self.risk_components["esg"] = self.get_esg_data()

        # Calculate overall risk
        overall_risk = self.calculate_overall_risk()

        # Compile final report
        report = {
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

        return report

# @router.get("/analysis/{ticker}")
# async def get_risk_analysis(
#         ticker: str,
#         lookback_days: int = 30,
#         news_limit: int = 10,
#         db: Session = Depends(get_db)
# ):
#     try:
#         analyzer = RiskAnalysis(ticker, db)
#         report = analyzer.generate_risk_report(lookback_days, news_limit)
#         return report
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error generating risk analysis: {str(e)}")

if __name__ == "__main__":
    # Example usage
    db_gen = get_db()
    session = next(db_gen)
    try:
        analyzer = RiskAnalysis("TSLA", session)
        report = analyzer.generate_risk_report(lookback_days=30, news_limit=5)
        print(report)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()
