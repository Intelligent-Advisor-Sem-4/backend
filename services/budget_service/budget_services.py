from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func

from models.models import Transaction as TransactionModel, BudgetGoal as BudgetGoalModel
from services.budget_service.schemas import (
    TransactionCreate,
    TransactionUpdate,
    BudgetGoalCreate,
    BudgetGoalUpdate,
    TransactionSummary,
    Transaction as TransactionSchema,
    BudgetGoal as BudgetGoalSchema,
    MessageResponse,
    CategorySpending
)

def get_transactions_by_user(db: Session, user_id: str) -> List[TransactionSchema]:
    return db.query(TransactionModel)\
        .filter(TransactionModel.user_id == user_id)\
        .order_by(TransactionModel.created_at.desc())\
        .all()

from datetime import datetime

def create_transaction(db: Session, transaction: TransactionCreate) -> TransactionSchema:
    # Create a dictionary of the transaction data without the 'date' field
    transaction_data = transaction.model_dump(exclude={'date'})
    
    # Parse the datetime string and update the dictionary
    if 'created_at' in transaction_data and transaction_data['created_at']:
        # Parse the string to datetime object
        created_at_str = transaction_data['created_at']
        if isinstance(created_at_str, str):
            # Handle both "2025-05-03 00:00:00" and "2025-05-03" formats
            try:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d')
            transaction_data['created_at'] = created_at
    
    print(transaction_data)
    
    db_transaction = TransactionModel(**transaction_data)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def update_transaction(
    db: Session, 
    transaction_id: int, 
    updates: TransactionUpdate
) -> TransactionSchema:
    db_transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_transaction, key, value)
    
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def delete_transaction(db: Session, transaction_id: int) -> MessageResponse:
    db_transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(db_transaction)
    db.commit()
    return MessageResponse(message="Transaction deleted successfully")

def get_transactions_by_category(db: Session, user_id: str) -> List[CategorySpending]:
    sixty_days_ago = datetime.now() - timedelta(days=60)
    
    expenses = db.query(
        TransactionModel.category, 
        func.sum(TransactionModel.amount).label("total_amount")
    )\
    .filter(
        TransactionModel.user_id == user_id,
        TransactionModel.type == "expense",
        TransactionModel.created_at >= sixty_days_ago
    )\
    .group_by(TransactionModel.category)\
    .all()

    incomes = db.query(
        TransactionModel.category, 
        func.sum(TransactionModel.amount).label("total_amount")
    )\
    .filter(
        TransactionModel.user_id == user_id,
        TransactionModel.type == "income",
        TransactionModel.created_at >= sixty_days_ago
    )\
    .group_by(TransactionModel.category)\
    .all()

    if len(expenses)==0 and len(incomes)==0:
        return [[],[]]
    if len(expenses)==0:
        return [[],[CategorySpending(category=e.category, amount=float(e.total_amount)) for e in incomes]]
    if len(incomes)==0:
        return [[CategorySpending(category=e.category, amount=float(e.total_amount)) for e in expenses],[]]
    
    return [[CategorySpending(category=e.category, amount=float(e.total_amount)) for e in expenses],[CategorySpending(category=e.category, amount=float(e.total_amount)) for e in incomes]]

def get_transaction_summary(db: Session, user_id: str) -> TransactionSummary:
    thirty_days_ago = datetime.now() - timedelta(days=30)
    sixty_days_ago = datetime.now() - timedelta(days=60)
    
    # Current period (last 30 days)
    income = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == "income",
            TransactionModel.created_at >= thirty_days_ago
        )\
        .scalar() or 0
    
    expense = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == "expense",
            TransactionModel.created_at >= thirty_days_ago
        )\
        .scalar() or 0
    
    # Previous period (30-60 days ago)
    previous_income = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == "income",
            TransactionModel.created_at >= sixty_days_ago,
            TransactionModel.created_at < thirty_days_ago
        )\
        .scalar() or 0
    
    previous_expense = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == "expense",
            TransactionModel.created_at >= sixty_days_ago,
            TransactionModel.created_at < thirty_days_ago
        )\
        .scalar() or 0
    
    # Daily balances
    transactions = db.query(TransactionModel)\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.created_at >= sixty_days_ago
        )\
        .order_by(TransactionModel.created_at.asc())\
        .all()
    
    daily_balances = {}
    for transaction in transactions:
        date_str = transaction.created_at.date().isoformat()
        if date_str not in daily_balances:
            daily_balances[date_str] = 0
        
        if transaction.type == "income":
            daily_balances[date_str] += float(transaction.amount)
        else:
            daily_balances[date_str] -= float(transaction.amount)
    
    daily_balances_list = [
        {"date": date, "balance": balance} 
        for date, balance in sorted(daily_balances.items())
    ]
    
    return TransactionSummary(
        income=float(income),
        expense=float(expense),
        balance=float(income - expense),
        previous_income=float(previous_income),
        previous_expense=float(previous_expense),
        previous_balance=float(previous_income - previous_expense),
        transactions=daily_balances_list
    )

def get_budget_goals(db: Session, user_id: str) -> List[BudgetGoalSchema]:
    return db.query(BudgetGoalModel)\
        .filter(BudgetGoalModel.user_id == user_id)\
        .order_by(BudgetGoalModel.deadline.asc())\
        .all()

def create_budget_goal(db: Session, goal: BudgetGoalCreate) -> BudgetGoalSchema:
    db_goal = BudgetGoalModel(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    print(goal,db_goal.id)
    return BudgetGoalModel(**goal.model_dump(), id=db_goal.id)

def update_budget_goal(
    db: Session, 
    goal_id: int, 
    updates: BudgetGoalUpdate
) -> BudgetGoalSchema:
    db_goal = db.query(BudgetGoalModel).filter(BudgetGoalModel.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Budget goal not found")
    
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_goal, key, value)
    
    db.commit()
    db.refresh(db_goal)
    return db_goal

def delete_budget_goal(db: Session, goal_id: int) -> MessageResponse:
    db_goal = db.query(BudgetGoalModel).filter(BudgetGoalModel.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Budget goal not found")
    
    db.delete(db_goal)
    db.commit()
    return MessageResponse(message="Budget goal deleted successfully")