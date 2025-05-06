from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

# Transaction Schemas
class TransactionBase(BaseModel):
    type: TransactionType
    reason: str
    category: str
    amount: float
    user_id: str

class TransactionCreate(TransactionBase):
    created_at: datetime = datetime.now()

class Transaction(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    reason: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None

# Budget Goal Schemas
class BudgetGoalBase(BaseModel):
    title: str
    category: str
    amount: float
    user_id: str
    deadline: datetime

class BudgetGoalCreate(BudgetGoalBase):
    created_at: datetime = datetime.now()

class BudgetGoalUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    deadline: Optional[datetime] = None

class BudgetGoal(BudgetGoalBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Analytics Schemas
class DailyBalance(BaseModel):
    date: str
    balance: float

class TransactionSummary(BaseModel):
    income: float
    expense: float
    balance: float
    previous_income: float
    previous_expense: float
    previous_balance: float
    transactions: List[DailyBalance]

class CategorySpending(BaseModel):
    category: str
    amount: float

class MessageResponse(BaseModel):
    message: str