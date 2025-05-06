from enum import Enum
from fastapi import Depends,APIRouter
import sys
from pathlib import Path

from db.dbConnect import get_db
sys.path.append(str(Path(__file__).parent.parent))
from llm.temp.main import prediction,getTrascationOfMonth
import llm.sub_llm as sub_llm
from typing import List
from sqlalchemy.orm import Session
# from models.models import Transaction, BudgetGoal
from services.budget_service.schemas import (
    TransactionCreate,
    TransactionUpdate,
    BudgetGoalCreate,
    BudgetGoalUpdate,
    TransactionSummary,
    Transaction,
    BudgetGoal
)
from services.budget_service.budget_services import (
    get_transactions_by_user,
    create_transaction,
    update_transaction,
    delete_transaction,
    get_transactions_by_category,
    get_transaction_summary,
    get_budget_goals,
    create_budget_goal,
    update_budget_goal,
    delete_budget_goal
)
router = APIRouter(prefix='/budget')

@router.get("/predictions")
async def get_predictions(user_id: str):
    """Endpoint 1: Get financial predictions and advice"""
    predictions = prediction(user_id)
    print(predictions)
    advice,goals = sub_llm.getFinancialAdvice(predictions)
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
    print(transactions)
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

@router.get("/transactions/{user_id}", response_model=List[Transaction])
async def get_expenses_by_user_id(user_id: str, db: Session = Depends(get_db)):
    return get_transactions_by_user(db, user_id)

@router.post("/transactions", response_model=Transaction)
async def create_expense(expense: TransactionCreate, db: Session = Depends(get_db)):
    return create_transaction(db, expense)

@router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_expense(
    transaction_id: int, 
    updates: TransactionUpdate, 
    db: Session = Depends(get_db)
):
    return update_transaction(db, transaction_id, updates)

@router.delete("/transactions/{transaction_id}")
async def delete_expense(transaction_id: int, db: Session = Depends(get_db)):
    return delete_transaction(db, transaction_id)

@router.get("/transactions/categories/{user_id}")
async def get_expenses_by_category(user_id: str, db: Session = Depends(get_db)):
    return get_transactions_by_category(db, user_id)

@router.get("/transactions/summary/{user_id}", response_model=TransactionSummary)
async def get_summary_by_user_id(user_id: str, db: Session = Depends(get_db)):
    return get_transaction_summary(db, user_id)

@router.get("/budget-goals/{user_id}", response_model=List[BudgetGoal])
async def get_budget_goals_endpoint(user_id: str, db: Session = Depends(get_db)):
    return get_budget_goals(db, user_id)

@router.post("/budget-goals", response_model=BudgetGoal)
async def create_budget_goal_endpoint(goal: BudgetGoalCreate, db: Session = Depends(get_db)):
    return create_budget_goal(db, goal)

@router.put("/budget-goals/{goal_id}", response_model=BudgetGoal)
async def update_budget_goal_endpoint(
    goal_id: int, 
    updates: BudgetGoalUpdate, 
    db: Session = Depends(get_db)
):
    return update_budget_goal(db, goal_id, updates)

@router.delete("/budget-goals/{goal_id}")
async def delete_budget_goal_endpoint(goal_id: int, db: Session = Depends(get_db)):
    return delete_budget_goal(db, goal_id)