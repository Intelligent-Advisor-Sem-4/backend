from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Boolean, JSON, Date, ForeignKey, Numeric, BigInteger, \
    Text
from sqlalchemy.orm import relationship, backref, DeclarativeBase
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import enum
import uuid

# SQLAlchemy 2.0 base class
class Base(DeclarativeBase):
    pass

# Create an enum class for access levels
class AccessLevel(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNDEFINED = "undefined"

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    birthday = Column(DateTime, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    access_level = Column(SQLEnum(AccessLevel), default=AccessLevel.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"

class TransactionModel(Base):
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

# Transaction Schemas
class TransactionBase(BaseModel):
    type: TransactionType
    reason: str
    category: str
    amount: float
    user_id: str

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "type": "income",
                "reason": "Salary payment",
                "category": "salary",
                "amount": 1000.00,
                "user_id": "user-123"
            }
        }
    )

class TransactionCreate(TransactionBase):
    created_at: datetime = datetime.now()
    date: str

class Transaction(TransactionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    reason: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None

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

def get_transaction_summary(db: Session, user_id: str) -> TransactionSummary:
    thirty_days_ago = datetime.now() - timedelta(days=30)
    sixty_days_ago = datetime.now() - timedelta(days=60)
    
    # Current period (last 30 days)
    income = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == TransactionType.INCOME,
            TransactionModel.created_at >= thirty_days_ago
        )\
        .scalar() or 0
    
    expense = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == TransactionType.EXPENSE,
            TransactionModel.created_at >= thirty_days_ago
        )\
        .scalar() or 0
    
    # Previous period (30-60 days ago)
    previous_income = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == TransactionType.INCOME,
            TransactionModel.created_at >= sixty_days_ago,
            TransactionModel.created_at < thirty_days_ago
        )\
        .scalar() or 0
    
    previous_expense = db.query(func.sum(TransactionModel.amount))\
        .filter(
            TransactionModel.user_id == user_id,
            TransactionModel.type == TransactionType.EXPENSE,
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
        
        if transaction.type == TransactionType.INCOME:
            daily_balances[date_str] += float(transaction.amount)
        else:
            daily_balances[date_str] -= float(transaction.amount)
    
    daily_balances_list = [
        DailyBalance(date=date, balance=balance)
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

# Test code
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import decimal

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixtures
@pytest.fixture(scope="module")
def db_session():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # Create a test user
    test_user = UserModel(
        id="test-user-123",
        name="Test User",
        birthday=datetime.now(),
        gender=Gender.MALE,
        username="testuser",
        password="hashedpassword",
        email="test@example.com",
        access_level=AccessLevel.USER
    )
    db.add(test_user)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def setup_transactions(db_session):
    # Clear existing transactions
    db_session.query(TransactionModel).delete()
    db_session.commit()
    
    # Helper function to create transactions
    def create_transaction(days_ago: int, amount: float, type: TransactionType, category: str = "general", reason: str = "test"):
        created_at = datetime.now() - timedelta(days=days_ago)
        transaction = TransactionModel(
            type=type,
            reason=reason,
            category=category,
            amount=decimal.Decimal(amount),
            user_id="test-user-123",
            created_at=created_at
        )
        db_session.add(transaction)
    
    return create_transaction

def test_empty_transaction_summary(db_session):
    # Clear all transactions
    db_session.query(TransactionModel).delete()
    db_session.commit()
    
    summary = get_transaction_summary(db_session, "test-user-123")
    
    assert summary.income == 0
    assert summary.expense == 0
    assert summary.balance == 0
    assert summary.previous_income == 0
    assert summary.previous_expense == 0
    assert summary.previous_balance == 0
    assert len(summary.transactions) == 0

def test_only_income_transactions(db_session, setup_transactions):
    setup_transactions(10, 100.0, TransactionType.INCOME)
    setup_transactions(40, 200.0, TransactionType.INCOME)
    db_session.commit()
    
    summary = get_transaction_summary(db_session, "test-user-123")
    
    assert summary.income == 100.0
    assert summary.expense == 0
    assert summary.balance == 100.0
    assert summary.previous_income == 200.0
    assert summary.previous_expense == 0
    assert summary.previous_balance == 200.0
    assert len(summary.transactions) == 2

def test_only_expense_transactions(db_session, setup_transactions):
    setup_transactions(15, 50.0, TransactionType.EXPENSE)
    setup_transactions(45, 75.0, TransactionType.EXPENSE)
    db_session.commit()
    
    summary = get_transaction_summary(db_session, "test-user-123")
    
    assert summary.income == 0
    assert summary.expense == 50.0
    assert summary.balance == -50.0
    assert summary.previous_income == 0
    assert summary.previous_expense == 75.0
    assert summary.previous_balance == -75.0
    assert len(summary.transactions) == 2

def test_mixed_transactions(db_session, setup_transactions):
    # Current period transactions
    setup_transactions(5, 100.0, TransactionType.INCOME, "salary", "paycheck")
    setup_transactions(10, 50.0, TransactionType.INCOME, "bonus", "yearly bonus")
    setup_transactions(15, 30.0, TransactionType.EXPENSE, "food", "groceries")
    setup_transactions(20, 20.0, TransactionType.EXPENSE, "entertainment", "movie tickets")
    
    # Previous period transactions
    setup_transactions(35, 80.0, TransactionType.INCOME, "salary", "paycheck")
    setup_transactions(40, 20.0, TransactionType.INCOME, "bonus", "referral bonus")
    setup_transactions(45, 40.0, TransactionType.EXPENSE, "food", "dining out")
    setup_transactions(50, 10.0, TransactionType.EXPENSE, "transportation", "bus fare")
    
    db_session.commit()
    
    summary = get_transaction_summary(db_session, "test-user-123")
    
    # Current period assertions
    assert summary.income == 150.0
    assert summary.expense == 50.0
    assert summary.balance == 100.0
    
    # Previous period assertions
    assert summary.previous_income == 100.0
    assert summary.previous_expense == 50.0
    assert summary.previous_balance == 50.0
    
    assert len(summary.transactions) == 8

def test_daily_balance_calculation(db_session, setup_transactions):
    same_day = datetime.now() - timedelta(days=10)
    
    db_session.add(TransactionModel(
        type=TransactionType.INCOME,
        reason="salary",
        category="work",
        amount=decimal.Decimal(100.0),
        user_id="test-user-123",
        created_at=same_day
    ))
    
    db_session.add(TransactionModel(
        type=TransactionType.EXPENSE,
        reason="shopping",
        category="retail",
        amount=decimal.Decimal(40.0),
        user_id="test-user-123",
        created_at=same_day
    ))
    
    db_session.add(TransactionModel(
        type=TransactionType.EXPENSE,
        reason="dinner",
        category="food",
        amount=decimal.Decimal(30.0),
        user_id="test-user-123",
        created_at=same_day
    ))
    
    db_session.commit()
    
    summary = get_transaction_summary(db_session, "test-user-123")
    
    assert len(summary.transactions) == 1
    assert summary.transactions[0].balance == 30.0

def test_transactions_outside_period(db_session, setup_transactions):
    setup_transactions(65, 500.0, TransactionType.INCOME)
    setup_transactions(70, 200.0, TransactionType.EXPENSE)
    db_session.commit()
    
    summary = get_transaction_summary(db_session, "test-user-123")
    
    assert summary.income == 0
    assert summary.expense == 0
    assert summary.balance == 0
    assert len(summary.transactions) == 0

def test_transaction_summary_model_validation():
    test_data = {
        "income": 100.0,
        "expense": 50.0,
        "balance": 50.0,
        "previous_income": 80.0,
        "previous_expense": 40.0,
        "previous_balance": 40.0,
        "transactions": [
            {"date": "2023-01-01", "balance": 20.0},
            {"date": "2023-01-02", "balance": 30.0}
        ]
    }
    
    summary = TransactionSummary(**test_data)
    
    assert summary.income == 100.0
    assert summary.expense == 50.0
    assert summary.balance == 50.0
    assert len(summary.transactions) == 2
    assert summary.transactions[0].date == "2023-01-01"
    assert summary.transactions[0].balance == 20.0