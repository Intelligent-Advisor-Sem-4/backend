import json
from datetime import datetime, timedelta
from typing import Dict

import numpy as np
from sqlalchemy.orm import Session

import yfinance as yf
from yfinance import Ticker

from models.models import QuantitativeRiskAnalysis
from services.utils import calculate_risk_scores, to_python_type, get_stock_by_ticker, parse_gemini_json_response
from classes.Risk_Components import QuantRiskResponse, QuantRiskMetrics


class QuantitativeRiskService:
    def __init__(self, gemini_client, db: Session, ticker: str, ticker_data: Ticker):
        self.gemini_client = gemini_client
        self.db = db
        self.ticker_data = ticker_data
        self.ticker = ticker
        self.stock = get_stock_by_ticker(db, ticker)

    def _generate_quantitative_risk_explanation(self, ticker, volatility, beta, rsi, volume_change, debt_to_equity,
                                                quant_risk_score, eps=None, use_gemini=True) -> Dict[str, str]:
        """Generate a risk explanation and label using Google Gemini API if you use_gemini is True"""
        print("Generating risk explanation")
        try:
            # If Gemini integration is disabled, return default response
            if not use_gemini:
                # Provide a default risk assessment based on the quantitative score
                if quant_risk_score >= 8:
                    risk_label = "High Risk"
                    explanation = f"{ticker} shows significant volatility and concerning financial metrics. Current metrics indicate heightened investment risk."
                elif quant_risk_score >= 6:
                    risk_label = "Moderate Risk"
                    explanation = f"{ticker} exhibits some concerning financial indicators. Consider the volatility and debt levels before investing."
                elif quant_risk_score >= 4:
                    risk_label = "Slight Risk"
                    explanation = f"{ticker} shows moderate stability with some risk factors. Financial metrics suggest caution is warranted."
                elif quant_risk_score >= 2:
                    risk_label = "Stable"
                    explanation = f"{ticker} demonstrates good stability across key metrics. Overall financial health appears solid."
                else:
                    risk_label = "Very Stable"
                    explanation = f"{ticker} shows excellent stability and strong financial metrics. Risk factors appear well-managed."

                return {
                    "risk_label": risk_label,
                    "explanation": explanation
                }

            # Format values properly with conditional handling
            beta_str = f"{beta:.2f}" if beta is not None else "N/A"
            debt_str = f"{debt_to_equity:.2f}" if debt_to_equity is not None else "N/A"
            eps_str = f"{eps:.2f}" if eps is not None else "N/A"

            # Prepare the prompt for Gemini
            prompt = f"""
           As a financial risk and compliance analyst for a stock screening platform, that identifies and flags risky financial assets, analyze the following stock metrics for {ticker}:

            - Volatility: {volatility:.2f}% (annualized)
            - Beta: {beta_str}
            - RSI: {rsi:.2f}
            - Recent Volume Change: {volume_change:.2f}%
            - Debt-to-Equity Ratio: {debt_str}
            - Overall Risk Score: {quant_risk_score:.2f}/10

            Our mission is NOT to advise on investments but to identify and flag potentially risky assets that could harm retail investors.

            Provide your analysis in JSON format with exactly these two fields:
            1. "risk_label": Choose exactly one label from ["High Risk", "Moderate Risk", "Slight Risk", "Stable", "Very Stable"]
            2. "explanation": A concise explanation (2-3 sentences) of the primary risk factors and their implications, mentioning EPS if it's a significant factor

            Return only valid JSON with no additional text, comments, or markdown formatting.
            """

            # Call the Gemini API
            response = self.gemini_client.models.generate_content(model='gemini-2.0-flash-lite', contents=prompt)
            response_text = response.text

            # Parse the JSON response using the common utility function
            try:
                result = parse_gemini_json_response(response_text)

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

    def _store_quantitative_risk_analysis(self, volatility, beta, rsi, volume_change, debt_to_equity, eps=None) -> None:
        """Store or update quantitative risk analysis in the database"""
        print("Storing quantitative analysis record")
        # Return early if stock is None
        if self.stock is None:
            print("No stock in database to store")
            return None

        try:
            existing_analysis = self.db.query(QuantitativeRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

            if existing_analysis:
                print("Updating existing report")
                # Update existing record - convert NumPy types to Python native types
                existing_analysis.volatility = float(volatility) if volatility is not None else None
                existing_analysis.beta = float(beta) if beta is not None else None
                existing_analysis.rsi = float(rsi) if rsi is not None else None
                existing_analysis.volume_change = float(volume_change) if volume_change is not None else None
                existing_analysis.debt_to_equity = float(debt_to_equity) if debt_to_equity is not None else None
                existing_analysis.updated_at = datetime.now()
            else:
                # Create new record
                print("Creating new report")
                quantitative_analysis = QuantitativeRiskAnalysis(
                    volatility=to_python_type(volatility),
                    beta=to_python_type(beta),
                    rsi=to_python_type(rsi),
                    volume_change=to_python_type(volume_change),
                    debt_to_equity=to_python_type(debt_to_equity),
                    stock_id=self.stock.stock_id,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    eps=to_python_type(eps),
                )
                self.db.add(quantitative_analysis)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"[Database Error] Failed to store quantitative risk analysis: {e}")

    def calculate_quantitative_metrics(self, lookback_days: int = 30, use_gemini: bool = True) -> QuantRiskResponse:
        """Calculate key quantitative risk metrics"""
        print('Calculating quantitative metrics')
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
                # Check if beta is available in info
                beta = info.get('beta')
                if beta is not None:
                    beta = float(beta)
                else:
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

            # Check for EPS in info dictionary
            eps = info.get('trailingEps')  # Most commonly available EPS metric
            if eps is None:
                eps = info.get('forwardEps')  # Alternative if trailing EPS not available

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

            # Call the risk scoring function
            risk_scores = calculate_risk_scores(
                volatility=volatility,
                beta=beta,
                rsi=rsi,
                volume_change=volume_change,
                debt_to_equity=debt_to_equity,
                eps=eps
            )

            # Store the quantitative risk analysis in the database
            self._store_quantitative_risk_analysis(
                volatility=volatility,
                beta=beta,
                rsi=rsi,
                eps=eps,
                volume_change=volume_change,
                debt_to_equity=debt_to_equity
            )

            # Get the overall risk score for the Gemini explanation
            quant_risk_score = risk_scores["quant_risk_score"]

            # Generate AI explanation
            risk_analysis = self._generate_quantitative_risk_explanation(
                ticker=self.ticker,
                volatility=volatility,
                beta=beta,
                rsi=rsi,
                volume_change=volume_change,
                debt_to_equity=debt_to_equity,
                quant_risk_score=quant_risk_score,
                eps=eps,
                use_gemini=use_gemini
            )

            # Convert risk_scores dictionary to QuantRiskMetrics Pydantic model
            risk_metrics = QuantRiskMetrics(
                volatility_score=risk_scores.get("volatility_score"),
                beta_score=risk_scores.get("beta_score"),
                rsi_risk=risk_scores.get("rsi_risk"),
                volume_risk=risk_scores.get("volume_risk"),
                debt_risk=risk_scores.get("debt_risk"),
                eps_risk=risk_scores.get("eps_risk"),
                quant_risk_score=risk_scores.get("quant_risk_score")
            )

            # Return the complete results as a Pydantic model
            return QuantRiskResponse(
                volatility=volatility,
                beta=beta,
                rsi=rsi,
                volume_change_percent=volume_change,
                debt_to_equity=debt_to_equity,
                risk_metrics=risk_metrics,
                risk_label=risk_analysis["risk_label"],
                risk_explanation=risk_analysis["explanation"]
            )
        except Exception as e:
            print(f"Error calculating quantitative metrics: {e}")
            # Return error response as a Pydantic model
            return QuantRiskResponse(
                error=str(e),
                risk_metrics=QuantRiskMetrics(
                    quant_risk_score=5  # Neutral score on error
                ),
                risk_explanation="Unable to calculate risk metrics due to an error."
            )

    def get_quantitative_metrics(self, lookback_days: int = 30, use_gemini: bool = True) -> QuantRiskResponse:
        """Check if there is an existing metric for the symbol and if exists it is not older than 2 days return it"""
        print("Get quantitative metrics")

        # If stock is None, always calculate new metrics
        if self.stock is None:
            print("No stock in database, calculating new metrics")
            return self.calculate_quantitative_metrics(lookback_days, use_gemini)

        quantitative_analysis = self.db.query(QuantitativeRiskAnalysis).filter_by(stock_id=self.stock.stock_id).first()

        if quantitative_analysis and quantitative_analysis.updated_at > datetime.now() - timedelta(days=1):
            print("Existing metric exists")
            risk_scores = calculate_risk_scores(
                volatility=quantitative_analysis.volatility,
                beta=quantitative_analysis.beta,
                rsi=quantitative_analysis.rsi,
                volume_change=quantitative_analysis.volume_change,
                debt_to_equity=quantitative_analysis.debt_to_equity,
                eps=quantitative_analysis.eps
            )

            # Generate AI explanation
            risk_analysis = self._generate_quantitative_risk_explanation(
                ticker=self.ticker,
                volatility=quantitative_analysis.volatility,
                beta=quantitative_analysis.beta,
                rsi=quantitative_analysis.rsi,
                volume_change=quantitative_analysis.volume_change,
                debt_to_equity=quantitative_analysis.debt_to_equity,
                quant_risk_score=risk_scores["quant_risk_score"],
                use_gemini=use_gemini
            )

            # Convert risk_scores dictionary to QuantRiskMetrics Pydantic model
            risk_metrics = QuantRiskMetrics(
                volatility_score=risk_scores.get("volatility_score"),
                beta_score=risk_scores.get("beta_score"),
                rsi_risk=risk_scores.get("rsi_risk"),
                volume_risk=risk_scores.get("volume_risk"),
                debt_risk=risk_scores.get("debt_risk"),
                eps_risk=risk_scores.get("eps_risk"),
                quant_risk_score=risk_scores.get("quant_risk_score")
            )

            # Return the results as a Pydantic model
            return QuantRiskResponse(
                volatility=quantitative_analysis.volatility,
                beta=quantitative_analysis.beta,
                rsi=quantitative_analysis.rsi,
                volume_change_percent=quantitative_analysis.volume_change,
                debt_to_equity=quantitative_analysis.debt_to_equity,
                risk_metrics=risk_metrics,
                risk_label=risk_analysis["risk_label"],
                risk_explanation=risk_analysis["explanation"]
            )

        # If no recent analysis exists, calculate new metrics
        print("No recent analysis found, calculating new metrics")
        return self.calculate_quantitative_metrics(lookback_days, use_gemini)
