from fastapi import FastAPI, HTTPException,APIRouter
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from llm.temp.main import prediction,getTrascationOfMonth
import llm.sub_llm as sub_llm

router = APIRouter(prefix='/budget')

@router.get("/predictions")
async def get_predictions(user_id: str):
    """Endpoint 1: Get financial predictions and advice"""
    predictions = prediction(user_id)
    advice,goals = sub_llm.getFinancialAdvice(predictions)
    print(predictions)
    print(advice)
    print(goals)
    return {
        "predictions": predictions,
        "financial_advice": advice,
        "budget_goals": [goals]
    }

@router.get("/budget-report")
async def get_budget_report(user_id: str):
    """Endpoint 2: Get budget report for a specific month"""
    transactions = getTrascationOfMonth(user_id)
    budget = sub_llm.getBudgetReport(transactions)
    print(transactions)
    print(budget)
    return {
        "transactions": transactions,
        "budget_report": budget
    }

@router.post("/categorize-transaction")
async def categorize_transaction(description: str, amount: float, type: str):
    """Endpoint 3: Categorize a new transaction"""
    res = sub_llm.getTransactionCategories(description, amount, type)
    print(res)
    return res

@router.get("/chat")
async def chat(prompt: str):
    """Endpoint 4: Chat with the LLM"""
    print(prompt)
    response = sub_llm.getChat(prompt)
    print(response)
    return {
        "response": response
    }

