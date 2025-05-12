import shap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import os
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(
    prefix="/portfolio-explanation",
    tags=["Portfolio Explanation"],
)

# === Models ===
class MonteCarloProjection(BaseModel):
    expected_final_value: float
    min_final_value: float
    max_final_value: float
    success_rate_percent: float

class PortfolioRequest(BaseModel):
    optimal_weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    goal: str
    monte_carlo_projection: MonteCarloProjection

class ShapContribution(BaseModel):
    stock: str
    weight: float
    contribution_to_return: float
    shap_value: float
    percentage_contribution: float

class ExplanationResponse(BaseModel):
    explanation: str
    shap_explanation: List[ShapContribution]
    shap_plot_base64: str

# === SHAP Explanation ===
def explain_with_shap(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    optimal_weights = portfolio_data["optimal_weights"]
    expected_return = portfolio_data["expected_return"]
    stocks = list(optimal_weights.keys())
    weights = list(optimal_weights.values())
    X = np.array([weights]).reshape(1, -1)
    background = np.zeros((1, len(weights)))

    explainer = shap.Explainer(lambda x: x.dot(np.array([expected_return] * len(weights))), background)
    shap_values = explainer(X)
    shap_vals = shap_values.values[0]

    sorted_indices = np.argsort(np.abs(shap_vals))[::-1]
    sorted_stocks = [stocks[i] for i in sorted_indices]
    sorted_shap_vals = [shap_vals[i] for i in sorted_indices]

    plt.figure(figsize=(12, 7))
    colors = ['green' if val >= 0 else 'red' for val in sorted_shap_vals]
    bars = plt.bar(sorted_stocks, sorted_shap_vals, color=colors)

    for bar, val in zip(bars, sorted_shap_vals):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                 f'{val:.4f}', ha='center', va='bottom' if val > 0 else 'top',
                 fontsize=10, fontweight='bold')

    plt.axhline(0, color='gray', linestyle='--')
    plt.title("Stock Impact on Portfolio Return (SHAP Values)", fontsize=14, weight='bold')
    plt.suptitle("Green = Positive Impact, Red = Negative", fontsize=10)
    plt.xlabel("Stocks")
    plt.ylabel("SHAP Value (Impact on Return)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    contributions = {stock: weight * expected_return for stock, weight in optimal_weights.items()}
    total_contribution = sum(contributions.values())
    percentage_contributions = {stock: (contribution / total_contribution) * 100 
                                for stock, contribution in contributions.items()}

    shap_contributions = []
    for i in range(len(stocks)):
        idx = sorted_indices[i]
        stock = stocks[idx]
        shap_contributions.append({
            "stock": stock,
            "weight": optimal_weights[stock],
            "contribution_to_return": contributions[stock],
            "shap_value": float(shap_vals[idx]),
            "percentage_contribution": percentage_contributions[stock]
        })

    return {
        "shap_contributions": shap_contributions,
        "shap_plot_base64": image_base64
    }

# === Gemini Text Explanation ===
def generate_text_explanation(portfolio_data: Dict[str, Any], shap_data: Dict[str, Any]) -> str:
    sorted_stocks = sorted(shap_data["shap_contributions"], key=lambda x: x["percentage_contribution"], reverse=True)

    stock_lines = []
    for stock in sorted_stocks:
        stock_lines.append(
            f"{stock['stock']}: allocated {stock['weight']:.2%} of the portfolio, contributing approximately {stock['percentage_contribution']:.2f}% to the overall return."
        )

    monte_carlo = portfolio_data["monte_carlo_projection"]

    base_text = (
        f"This portfolio includes {len(portfolio_data['optimal_weights'])} different stocks, tailored to the goal: {portfolio_data['goal']}.\n\n"
        f"The expected annual return is {portfolio_data['expected_return']:.2%}, with a volatility of {portfolio_data['volatility']:.2%}. "
        f"The Sharpe ratio is {portfolio_data['sharpe_ratio']:.4f}, indicating the risk-adjusted performance.\n\n"
        f"Stock-wise, here's how each contributes:\n"
        + "\n".join(f"- {line}" for line in stock_lines) + "\n\n"
        f"The Monte Carlo simulation predicts an expected final portfolio value of ${monte_carlo['expected_final_value']:.2f}, "
        f"with possible outcomes ranging from ${monte_carlo['min_final_value']:.2f} to ${monte_carlo['max_final_value']:.2f}. "
        f"The estimated success rate of meeting your goal is {monte_carlo['success_rate_percent']:.2f}%."
    )

    if monte_carlo["success_rate_percent"] < 30:
        risk_note = (
            "Risk Level: High. The chance of reaching your investment goal is quite low. "
            "You might want to consider changing your strategy or goal."
        )
    elif monte_carlo["success_rate_percent"] < 50:
        risk_note = (
            "Risk Level: Moderate. There's a significant chance of underperformance. "
            "Reviewing your asset allocation could be helpful."
        )
    else:
        risk_note = (
            "Risk Level: Favorable. The portfolio has a strong likelihood of success. "
            "Still, periodic review is advised."
        )

    full_prompt = (
        f"You are a financial assistant. Based on the portfolio summary below, write a clear, concise explanation in plain English. "
        f"Do not use markdown or formatting. Write in friendly, professional language with short paragraphs.\n\n"
        f"---\n\n{base_text}\n\n{risk_note}"
    )

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return base_text + "\n\n" + risk_note + f"\n\nNote: Gemini explanation failed.\nError: {str(e)}"


# === FastAPI Endpoint ===
@router.post("/explain", response_model=ExplanationResponse)
async def explain_portfolio(portfolio: PortfolioRequest = Body(...)):
    try:
        portfolio_data = portfolio.dict()
        shap_data = explain_with_shap(portfolio_data)
        explanation = generate_text_explanation(portfolio_data, shap_data)
        return {
            "explanation": explanation,
            "shap_explanation": shap_data["shap_contributions"],
            "shap_plot_base64": shap_data["shap_plot_base64"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating explanation: {str(e)}")
