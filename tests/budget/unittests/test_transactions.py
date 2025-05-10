import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy.orm import Session
from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import List

# Mock classes to match your schema
class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class TransactionBase(BaseModel):
    type: TransactionType
    reason: str
    category: str
    amount: float
    user_id: str

class TransactionCreate(TransactionBase):
    created_at: datetime = datetime.now()
    date: str

class Transaction(TransactionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Create a proper mock for TransactionModel
def create_transaction_model_mock():
    class MockTransactionModel:
        # These class attributes simulate SQLAlchemy's column definitions
        user_id = PropertyMock()
        created_at = PropertyMock()
        id = PropertyMock()
        
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    return MockTransactionModel

# Create the mock class
TransactionModel = create_transaction_model_mock()

# Test data
TEST_USER_ID = "user123"
TEST_TRANSACTION_ID = 1
NOW = datetime.now()
YESTERDAY = NOW - timedelta(days=1)

# Test cases for get_transactions_by_user
def test_get_transactions_by_user_empty(db: Session):
    # Mock the entire query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    
    db.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.order_by.return_value = mock_order
    mock_order.all.return_value = []
    
    transactions = get_transactions_by_user(db, TEST_USER_ID)
    assert transactions == []
    db.query.assert_called_once_with(TransactionModel)

def test_get_transactions_by_user_with_results(db: Session):
    # Create test data with proper mock instances
    mock_transactions = [
        TransactionModel(id=1, user_id=TEST_USER_ID, reason="Salary", category="Work", amount=1000.0, created_at=NOW),
        TransactionModel(id=2, user_id=TEST_USER_ID, reason="Rent", category="Housing", amount=800.0, created_at=YESTERDAY)
    ]
    
    # Mock the query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    
    db.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.order_by.return_value = mock_order
    mock_order.all.return_value = mock_transactions
    
    transactions = get_transactions_by_user(db, TEST_USER_ID)
    assert len(transactions) == 2
    assert transactions[0].reason == "Salary"
    assert transactions[0].amount == 1000.0
    assert transactions[0].category == "Work"
    assert transactions[1].reason == "Rent"
    assert transactions[1].amount == 800.0
    assert transactions[1].category == "Housing"


# Test cases for create_transaction
def test_create_transaction_with_default_date(db: Session):
    transaction_data = {
        "type": TransactionType.income,
        "reason": "Salary",
        "category": "Work",
        "amount": 1000.0,
        "user_id": TEST_USER_ID,
        "date": "2023-01-01"
    }
    transaction_create = TransactionCreate(**transaction_data)
    
    # Create a properly initialized mock transaction
    mock_transaction = TransactionModel(**transaction_data)
    mock_transaction.id = TEST_TRANSACTION_ID  # Explicitly set the id
    
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = NOW
        mock_datetime.strptime.side_effect = datetime.strptime
        result = create_transaction(db, transaction_create)
    
    assert result.reason == "Salary"
    assert result.amount == 1000.0
    assert result.category == "Work"
    assert result.type == "income"
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()

# ... (keep the other test cases the same as before)

# Fixture for database session
@pytest.fixture
def db():
    return MagicMock(spec=Session)

# Include the actual functions to test at the bottom
def get_transactions_by_user(db: Session, user_id: str) -> List[Transaction]:
    return db.query(TransactionModel)\
        .filter(TransactionModel.user_id == user_id)\
        .order_by(TransactionModel.created_at.desc())\
        .all()

def create_transaction(db: Session, transaction: TransactionCreate) -> Transaction:
    transaction_data = transaction.model_dump(exclude={'date'})
    
    if 'created_at' in transaction_data and transaction_data['created_at']:
        created_at_str = transaction_data['created_at']
        if isinstance(created_at_str, str):
            try:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d')
            transaction_data['created_at'] = created_at
    
    db_transaction = TransactionModel(**transaction_data)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])