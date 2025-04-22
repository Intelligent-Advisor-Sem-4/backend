from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import requests
from sqlalchemy import Transaction

import db.dbConnect as dbConnect
from classes.explainability_intergration import ExplanationRequest

from models.models import ExplainabilityReport, RiskModel

router = APIRouter(prefix='/explainayion')





@router.post("/generate_explanation")
async def generate_explanation(request: ExplanationRequest):
    """
    Generate an explanation for a specific transaction's risk assessment
    """
    # 1. Fetch transaction and model details from DB
    transaction = dbConnect.query(Transaction).filter_by(id=request.transaction_id).first()
    model = dbConnect.query(RiskModel).filter_by(id=request.model_id).first()

    if not transaction or not model:
        raise HTTPException(status_code=404, detail="Transaction or model not found")

    # 2. Generate explanation based on type
    if request.explanation_type == "Gemini":
        # Call Gemini API for natural language explanation
        explanation = get_gemini_explanation(transaction, model)
    elif request.explanation_type == "SHAP":
        explanation = generate_shap_explanation(transaction, model)
    elif request.explanation_type == "LIME":
        explanation = generate_lime_explanation(transaction, model)
    else:
        raise HTTPException(status_code=400, detail="Unsupported explanation type")

    # 3. Save explanation to database
    report = ExplainabilityReport(
        transaction_id=request.transaction_id,
        model_id=request.model_id,
        report_data=explanation,
        explanation_type=request.explanation_type
    )
    dbConnect.add(report)
    dbConnect.commit()

    return {"status": "success", "explanation": explanation}


def get_gemini_explanation(transaction, model):
    """
    Use Gemini API to generate natural language explanations
    """
    prompt = f"""
    Explain why this transaction was flagged with a risk score of {transaction.risk_score}.
    Transaction details:
    - Amount: {transaction.amount}
    - Merchant: {transaction.merchant}
    - Category: {transaction.category}

    Risk model used: {model.name} (v{model.version})
    Model parameters: {model.parameters}

    Provide a clear, concise explanation suitable for a compliance officer.
    Highlight the most influential factors in the risk assessment.
    """

    # Example Gemini API call (adjust based on actual API)
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        },
        params={"key": "YOUR_GEMINI_API_KEY"}
    )

    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return "Could not generate explanation. Please try another method."


def generate_shap_explanation(transaction, model):
    """Generate SHAP values explanation"""
    # Implementation would depend on your risk model
    # This is a placeholder
    return {
        "explanation_type": "SHAP",
        "base_value": 0.5,
        "feature_importances": {
            "amount": 0.3,
            "merchant_category": 0.4,
            "user_history": 0.2,
            "time_of_day": 0.1
        }
    }


def generate_lime_explanation(transaction, model):
    """Generate LIME explanation"""
    # Implementation would depend on your risk model
    return {
        "explanation_type": "LIME",
        "local_prediction": transaction.risk_score,
        "local_interpretation": [
            {"feature": "amount", "weight": 0.35},
            {"feature": "merchant_risk", "weight": 0.45},
            {"feature": "user_behavior", "weight": 0.2}
        ]
    }



@router.get("/{transaction_id}")
async def get_explanation(transaction_id: int, type: Optional[str] = None):
    """
    Retrieve stored explanations for a transaction
    """
    query = dbConnect.query(ExplainabilityReport).filter_by(transaction_id=transaction_id)

    if type:
        query = query.filter_by(explanation_type=type)

    reports = query.all()

    if not reports:
        raise HTTPException(status_code=404, detail="No explanations found")

    return [{
        "id": report.id,
        "model_id": report.model_id,
        "type": report.explanation_type,
        "generated_at": report.generated_at,
        "data": report.report_data
    } for report in reports]


@router.get("/models")
async def list_models():
    """List available risk models with explainability support"""
    models = dbConnect.query(RiskModel).all()
    return [{
        "id": model.id,
        "name": model.name,
        "version": model.version,
        "description": model.description,
        "supports_explainability": True  # Could be a DB field
    } for model in models]