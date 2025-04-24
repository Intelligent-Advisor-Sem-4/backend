import json
import os
import re
from datetime import datetime, timedelta
import numpy as np
import yfinance
import yfinance as yf
from pydantic import ValidationError
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from google import genai

from classes.Sentiment import SentimentAnalysisResponse, KeyRisks
from db.dbConnect import get_db
from models.models import Stock, NewsArticle, RelatedArticle, NewsRiskAnalysis
from utils import parse_news_article

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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


class RiskAnalysis:
    def __init__(self, ticker: str, db: Session):
        self.ticker = ticker
        self.db = db
        self.stock = self._get_stock()
        self.ticker_data = yf.Ticker(ticker)
        self.risk_components = {}
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)

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

    def generate_news_sentiment(self, articles: List[Dict[str, Any]]) -> SentimentAnalysisResponse:
        """Use Gemini to analyze news sentiment and store results in database"""
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
            "risk_score": 0
        }

        if not articles:
            sentiment_data = default_sentiment_data
        else:
            sentiment_response = None
            try:
                # Prepare news data for Gemini
                news_text = self._format_news_articles(articles)
                prompt = self._create_sentiment_prompt(news_text)

                # Get response from Gemini
                sentiment_response = self.gemini_client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
                sentiment_data = self._parse_gemini_response(sentiment_response)

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

    def _format_news_articles(self, articles: List[Dict[str, Any]]) -> str:
        """Format news articles for the Gemini prompt"""
        news_text = f"Recent news articles about {self.ticker}:\n\n"

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

        return news_text

    def _create_sentiment_prompt(self, news_text: str) -> str:
        """Create the prompt for Gemini"""
        return f"""
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
        9. **risk_score** Derived risk score Float (0-10) based on stability score and other risk factors.

        Ensure output is valid JSON and optimized for downstream explainability modules.
        """

    def _parse_gemini_response(self, response) -> Dict[str, Any]:
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

    def _validate_and_store_sentiment(self, sentiment_data: Dict[str, Any]) -> SentimentAnalysisResponse:
        """Validate sentiment data and store it in the database"""
        try:
            # Parse the data through the Pydantic model for validation
            sentiment_model = SentimentAnalysisResponse(**sentiment_data)

            try:
                # Check if an analysis already exists for this stock
                existing_analysis = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

                if existing_analysis:
                    # Update fields using validated data
                    for key, value in sentiment_model.model_dump().items():
                        setattr(existing_analysis, key, value) if hasattr(existing_analysis, key) else None

                    # Always update these fields
                    existing_analysis.response_json = sentiment_model.model_dump()
                    existing_analysis.updated_at = datetime.utcnow()
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
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
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
        try:
            existing_analysis = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

            if existing_analysis:
                existing_analysis.response_json = fallback_model.model_dump()
                existing_analysis.stability_score = fallback_model.stability_score
                existing_analysis.stability_label = fallback_model.stability_label
                existing_analysis.customer_suitability = fallback_model.customer_suitability
                existing_analysis.suggested_action = fallback_model.suggested_action
                existing_analysis.updated_at = datetime.utcnow()
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
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(news_analysis)

            self.db.commit()
        except Exception as db_err:
            self.db.rollback()
            print(f"[Database Error] Failed to store fallback analysis: {db_err}")

    def get_news_sentiment(self, prefer_newest: bool = True) -> SentimentAnalysisResponse:
        """Fetch news sentiment for the stock"""
        if prefer_newest:
            articles = self.get_news_articles(limit=10)
            return self.generate_news_sentiment(articles)

        # Check if sentiment already exists in the database
        news_sentiment = self.db.query(NewsRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

        # If no sentiment exists or it's older than 6 hours, fetch new sentiment
        if not news_sentiment or news_sentiment.created_at < datetime.utcnow() - timedelta(hours=6):
            articles = self.get_news_articles(limit=10)
            return self.generate_news_sentiment(articles)

        # Otherwise, construct a SentimentAnalysisResponse from the database record
        try:
            return SentimentAnalysisResponse(**news_sentiment.response_json)
        except ValidationError:
            # If the stored JSON is invalid, generate a new sentiment
            articles = self.get_news_articles(limit=10)
            return self.generate_news_sentiment(articles)

    def _generate_risk_explanation(self, ticker, volatility, beta, rsi, volume_change, debt_to_equity,
                                  quant_risk_score) -> Dict[str, str]:
        """Generate a risk explanation and label using Google Gemini API"""
        try:
            # Format values properly with conditional handling
            beta_str = f"{beta:.2f}" if beta is not None else "N/A"
            debt_str = f"{debt_to_equity:.2f}" if debt_to_equity is not None else "N/A"

            # Prepare the prompt for Gemini
            prompt = f"""
            As a financial risk analyst, analyze the following stock metrics for {ticker}:

            - Volatility: {volatility:.2f}% (annualized)
            - Beta: {beta_str}
            - RSI: {rsi:.2f}
            - Recent Volume Change: {volume_change:.2f}%
            - Debt-to-Equity Ratio: {debt_str}
            - Overall Risk Score: {quant_risk_score:.2f}/10

            Provide your analysis in JSON format with exactly these two fields:
            1. "risk_label": Choose exactly one label from ["High Risk", "Moderate Risk", "Slight Risk", "Stable", "Very Stable"]
            2. "explanation": A concise explanation (2-3 sentences) of the primary risk factors and their implications

            Return only valid JSON with no additional text, comments, or markdown formatting.
            """

            # Call the Gemini API
            response = self.gemini_client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
            response_text = response.text

            # Parse the JSON response
            # First, try to find JSON between code blocks if present
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            json_match = re.search(json_pattern, response_text)

            if json_match:
                json_text = json_match.group(1)
            else:
                # If no code blocks, treat the entire response as JSON
                json_text = response_text

            # Clean up any remaining markdown or text artifacts
            json_text = json_text.strip()

            # Parse JSON
            try:
                result = json.loads(json_text)

                # Validate the response has required fields
                if "risk_label" not in result or "explanation" not in result:
                    raise ValueError("Response missing required fields")

                # Validate the risk label is one of the expected values
                valid_labels = ["High Risk", "Moderate Risk", "Slight Risk", "Stable", "Very Stable"]
                if result["risk_label"] not in valid_labels:
                    result["risk_label"] = "Moderate Risk"  # Default if invalid

                return result
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "risk_label": "Moderate Risk",
                    "explanation": "Unable to parse risk analysis. Defaulting to moderate risk assessment."
                }

        except Exception as e:
            print(f"Error generating risk explanation: {e}")
            return {
                "risk_label": "Moderate Risk",
                "explanation": "Risk analysis not available due to an error."
            }

    def calculate_quantitative_metrics(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Calculate key quantitative risk metrics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 30)  # Extra data for calculations

        try:
            # Get historical price data
            hist = self.ticker_data.history(start=start_date, end=end_date)
            if hist.empty:
                raise ValueError(f"No historical data available for {self.ticker}")

            # Get info data
            info = self.ticker_data.info

            # 1. Volatility (annualized)
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100  # Annualized and in percent

            # 2. Beta (market risk)
            try:
                market_data = yf.Ticker('^GSPC').history(start=start_date, end=end_date)  # S&P 500 as market index
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

            # 3. RSI (Relative Strength Index)
            delta = hist['Close'].diff().dropna()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))

            # 4. Volume change
            avg_volume = hist['Volume'].mean()
            recent_volume = hist['Volume'].iloc[-5:].mean()  # Last 5 days
            volume_change = ((recent_volume / avg_volume) - 1) * 100  # Percentage change

            # 5. Debt to Equity ratio
            debt_to_equity = info.get('debtToEquity')

            # Calculate risk scores (0-10 scale)
            volatility_score = min(10, volatility / 5)  # Higher volatility = higher risk
            beta_score = min(10, abs(beta) * 3) if beta is not None else 5  # Higher absolute beta = higher risk
            rsi_risk = min(10, abs(rsi - 50) / 5)  # Extreme RSI = higher risk
            volume_score = min(10, abs(volume_change) / 10)  # Abnormal volume = higher risk
            debt_risk = min(10, debt_to_equity / 100) if debt_to_equity is not None else 5  # Higher debt = higher risk

            # Combine into overall quantitative risk score
            quant_risk_score = np.mean(
                [x for x in [volatility_score, beta_score, rsi_risk, volume_score, debt_risk] if x is not None])

            # Gemini Risk Analysis
            risk_analysis = self._generate_risk_explanation(
                ticker=self.ticker,
                volatility=volatility,
                beta=beta,
                rsi=rsi,
                volume_change=volume_change,
                debt_to_equity=debt_to_equity,
                quant_risk_score=quant_risk_score
            )

            return {
                "volatility": volatility,
                "beta": beta,
                "rsi": rsi,
                "volume_change_percent": volume_change,
                "debt_to_equity": debt_to_equity,
                "risk_metrics": {
                    "volatility_score": float(volatility_score),
                    "beta_score": float(beta_score) if beta is not None else None,
                    "rsi_risk": float(rsi_risk),
                    "volume_risk": float(volume_score),
                    "debt_risk": float(debt_risk) if debt_to_equity is not None else None,
                    "quant_risk_score": float(quant_risk_score)
                },
                "risk_label": risk_analysis["risk_label"],
                "risk_explanation": risk_analysis["explanation"]
            }
        except Exception as e:
            print(f"Error calculating quantitative metrics: {e}")
            return {
                "error": str(e),
                "risk_metrics": {
                    "quant_risk_score": 5  # Neutral score on error
                },
                "risk_explanation": "Unable to calculate risk metrics due to an error."
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
        # Store news articles in the database
        # print('Storing news articles in the database...')
        # self.store_news_for_ticker(self.db, self.ticker)
        #
        # # Analyze news sentiment
        # print('Analyzing news sentiment...')
        # self.risk_components["news_sentiment"] = self.get_news_sentiment(prefer_newest=False)

        # Calculate quantitative metrics
        print('Calculating quantitative metrics...')
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
        report = analyzer.generate_risk_report(lookback_days=30, news_limit=10)
        print(report)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()
