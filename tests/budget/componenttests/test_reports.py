from enum import Enum
from datetime import datetime, timedelta, timezone
import os
from typing import Optional
import openai
from pydantic import BaseModel
from collections import defaultdict
import pytest
from sqlalchemy import create_engine, Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid
from unittest.mock import Mock
from pydantic import ConfigDict
# SQLAlchemy setup
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
# Enum definitions
class AccessLevel(str, Enum):
    ADMIN = "admin"
    USER = "user"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNDEFINED = "undefined"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

# Database models
class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    birthday = Column(DateTime, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)  # Note: Using SQLEnum here
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    access_level = Column(SQLEnum(AccessLevel), default=AccessLevel.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class BudgetGoal(Base):
    __tablename__ = "budget_goal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)

    user = relationship("UserModel", backref=backref("budget_goal", lazy="dynamic"))

    def __repr__(self):
        return f"<BudgetGoal(id={self.id}, title='{self.title}', amount={self.amount})>"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    type = Column(SQLEnum(TransactionType), nullable=False)
    reason = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    user = relationship("UserModel", backref=backref("transactions", lazy="dynamic"))

    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.type}', amount={self.amount})>"

# Pydantic schemas
class TransactionBase(BaseModel):
    type: TransactionType
    reason: str
    category: str
    amount: float
    user_id: str

class TransactionCreate(TransactionBase):
    created_at: datetime = datetime.now()
    date: str

class TransactionModel(TransactionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    reason: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None

# Rest of your code (calculate_financial_summary, recommendations_agent, etc.) remains the same


from collections import defaultdict


client = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

client1 = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

client2 = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

def calculate_financial_summary(transaction_history):
    """Manually calculates financial metrics from transaction history"""
    total_income = 0.0
    total_expenses = 0.0
    category_spending = defaultdict(float)
    
    for transaction in transaction_history:
        amount = transaction['amount']  # Assuming amount is the last element
        if transaction['type'].lower() == 'income':  # Assuming type is at index 3
            total_income += amount
        else:
            total_expenses += amount
            category = transaction['category']  # Assuming category is at index 5
            category_spending[category] += amount
    
    net_savings = total_income - total_expenses
    
    # Calculate top spending categories
    total_spending = sum(category_spending.values())
    top_categories = []
    if total_spending > 0:
        top_categories = sorted(
            [(cat, (amt/total_spending)*100) for cat, amt in category_spending.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]  # Get top 3 categories
    
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_savings": net_savings,
        "top_spending_categories": top_categories
    }

def recommendations_agent(transaction_history,client):
    prompt = f"""
    Analyze this transaction history for the past month and provide specific optimization recommendations and Any urgent alerts

    Transaction History: [(date, type, reason, category, amount )]
    {transaction_history}

    Just give me a text response in this format
    recomendation1,recomendation2,recomendation3,...|alert1,alert2,alert3,...
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Lower for more factual analysis
        response_format={"type": "json_object"}
    )

    recomendations, alerts = completion.choices[0].message.content.replace("\n","").replace("\\","").replace("\n","").replace("\"","").split("|") 
    return recomendations.split(","),alerts.split(",")

def budget_analyst_agent(transaction_history,clients):
    """Analyzes past month's spending patterns and gives recommendations"""
    data = []
    for txn in transaction_history:
        data.append((txn['date'],txn['type'],txn['reason'],txn['category'],txn['amount']))

    if len(data)==0:
        r,a = [],['None']
    else:
        r,a = recommendations_agent(data,clients[1])
    return {
        "summary": calculate_financial_summary(transaction_history),
        "assessment": "",
        "recommendations": r,
        "alerts": a
    }

# Test data
# SAMPLE_TRANSACTIONS = [
    {
        "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "type": TransactionType.INCOME,
        "reason": "Salary",
        "category": "Income",
        "amount": 3000.00,
        "user_id": "test_user"
    },
    {
        "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "type": TransactionType.EXPENSE,
        "reason": "Groceries",
        "category": "Food",
        "amount": 150.50,
        "user_id": "test_user"
    },
    {
        "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        "type": TransactionType.EXPENSE,
        "reason": "Dinner",
        "category": "Food",
        "amount": 75.25,
        "user_id": "test_user"
    },
    {
        "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "type": TransactionType.EXPENSE,
        "reason": "Electricity",
        "category": "Utilities",
        "amount": 120.00,
        "user_id": "test_user"
    }
# ]

class MockLLMClient:
    def __init__(self):
        self.chat = self  # Make chat attribute return self
        self.completions = self  # Make completions attribute return self
    
    def create(self, model, messages, temperature, response_format):
        return type('MockResponse', (), {
            "choices": [
                type('MockChoice', (), {
                    "message": type('MockMessage', (), {
                        "content": '{"response":"Reduce food spending,Review utility bills,Consider meal planning|High food spending,None"}'
                    })
                })
            ]
        })
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_clients():
    return [None, MockLLMClient()]
# Update your test functions to use the mock database

def test_calculate_financial_summary(db_session):
    # Create test transactions in the database
    transactions = [
        Transaction(
            type=TransactionType.INCOME,
            reason="Salary",
            category="Income",
            amount=3000.00,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=5)
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            reason="Groceries",
            category="Food",
            amount=150.50,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=3)
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            reason="Dinner",
            category="Food",
            amount=75.25,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            reason="Electricity",
            category="Utilities",
            amount=120.00,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
    ]
    
    # Add transactions to the database
    for txn in transactions:
        db_session.add(txn)
    db_session.commit()
    
    # Get transactions from the database
    db_transactions = db_session.query(Transaction).filter(
        Transaction.user_id == "test_user"
    ).all()
    
    # Convert to the format expected by calculate_financial_summary
    transaction_history = [
        {
            "date": txn.created_at.strftime("%Y-%m-%d"),
            "type": txn.type,
            "reason": txn.reason,
            "category": txn.category,
            "amount": float(txn.amount),
            "user_id": txn.user_id
        }
        for txn in db_transactions
    ]
    
    result = calculate_financial_summary(transaction_history)
    
    assert result["total_income"] == 3000.00
    assert result["total_expenses"] == pytest.approx(150.50 + 75.25 + 120.00)
    assert result["net_savings"] == pytest.approx(3000.00 - (150.50 + 75.25 + 120.00))
    
    # Test top categories calculation
    assert len(result["top_spending_categories"]) <= 3
    if result["top_spending_categories"]:
        assert result["top_spending_categories"][0][0] == "Food"  # Should be top category

def test_calculate_financial_summary_empty(db_session):
    # Ensure no transactions exist for test user
    db_transactions = db_session.query(Transaction).filter(
        Transaction.user_id == "test_user"
    ).all()
    
    transaction_history = [
        {
            "date": txn.created_at.strftime("%Y-%m-%d"),
            "type": txn.type,
            "reason": txn.reason,
            "category": txn.category,
            "amount": float(txn.amount),
            "user_id": txn.user_id
        }
        for txn in db_transactions
    ]
    
    result = calculate_financial_summary(transaction_history)
    
    assert result["total_income"] == 0.0
    assert result["total_expenses"] == 0.0
    assert result["net_savings"] == 0.0
    assert result["top_spending_categories"] == []

def test_budget_analyst_agent(db_session, mock_clients):
    # Create test transactions in the database
    transactions = [
        Transaction(
            type=TransactionType.INCOME,
            reason="Salary",
            category="Income",
            amount=3000.00,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=5)
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            reason="Groceries",
            category="Food",
            amount=150.50,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=3)
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            reason="Dinner",
            category="Food",
            amount=75.25,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            reason="Electricity",
            category="Utilities",
            amount=120.00,
            user_id="test_user",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
    ]
    
    # Add transactions to the database
    for txn in transactions:
        db_session.add(txn)
    db_session.commit()
    
    # Get transactions from the database
    db_transactions = db_session.query(Transaction).filter(
        Transaction.user_id == "test_user"
    ).all()
    
    # Convert to the format expected by budget_analyst_agent
    transaction_history = [
        {
            "date": txn.created_at.strftime("%Y-%m-%d"),
            "type": txn.type,
            "reason": txn.reason,
            "category": txn.category,
            "amount": float(txn.amount),
            "user_id": txn.user_id
        }
        for txn in db_transactions
    ]
    
    result = budget_analyst_agent(transaction_history, mock_clients)
    
    assert isinstance(result, dict)
    assert "summary" in result
    assert "recommendations" in result
    assert "alerts" in result
    
    assert len(result["recommendations"]) > 0
    assert isinstance(result["alerts"], list)

def test_budget_analyst_agent_empty(db_session, mock_clients):
    # Ensure no transactions exist for test user
    db_transactions = db_session.query(Transaction).filter(
        Transaction.user_id == "test_user"
    ).all()
    
    transaction_history = [
        {
            "date": txn.created_at.strftime("%Y-%m-%d"),
            "type": txn.type,
            "reason": txn.reason,
            "category": txn.category,
            "amount": float(txn.amount),
            "user_id": txn.user_id
        }
        for txn in db_transactions
    ]
    
    result = budget_analyst_agent(transaction_history, mock_clients)
    
    assert result["summary"]["total_income"] == 0.0
    assert result["alerts"] == ["None"]

