from enum import Enum
from datetime import datetime, timedelta, timezone
import json
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
import sys
import os
import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from llm.ml_model.manual_model import (
    predict_next_day,
    predict_next_week,
    predict_next_month,
    predict_category_spending
)

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

def prediction_advisor_agent(predictions,transactions, client):
    """Generates actionable advice from budget predictions with robust error handling"""
    try:
        # Phase 1: Generate analysis with strict validation
        analysis = generate_analysis_phase(predictions,transactions, client)
        
        # Phase 2: Generate recommendation with strict validation
        recommendation = generate_recommendation_phase(predictions, client)
        
        return analysis, recommendation
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {str(e)}")
        # Return fallback responses if parsing fails
        return get_fallback_responses(predictions)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return get_fallback_responses(predictions)

def generate_analysis_phase(predictions,transactions, client):
    """First phase with stricter prompt and validation"""
    data = []
    for txn in transactions:
        data.append((txn['date'],txn['type'],txn['reason'],txn['category'],txn['amount']))
    prompt = f"""
    STRICTLY follow these instructions to analyze financial predictions:

    Predictions Data: {json.dumps(predictions)}
    Last Month Transaction Data [(date, type, reason, category, amount )]: {data}

    Respond text should be in following format:
    observations,...|daily_action|weekly_action|monthly_action|risks,...|long_term_insights,...

    RULES:
    1. Use direct commands ("Do X" not "Consider Y")
    2. Include numbers when possible
    3. Keep ALL responses under 2 sentences
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.1,  # Lower temperature for more predictable output
        response_format={"type": "text"}
    )
    
    res = completion.choices[0].message.content.replace("\n","").replace("\\","").replace("\n","").replace("\"","").split("|")

    print("Raw Analysis Output:", res)

    return {
        "observations": res[0].split(","),
        "daily_actions": res[1].split(","),
        "weekly_actions": res[2].split(","),
        "monthly_actions": res[3].split(","),
        "risks": res[4].split(","),
        "long_term_insights": res[5].split(",")
    }

def generate_recommendation_phase(predictions, client):
    """Second phase with stricter validation"""
    prompt = f"""
    Create ONE budget recommendation using this format ONLY:
    
    {{
        "time_period": "weekly|monthly",
        "amount": 123.45,
        "description": "Verb-starting 5-8 word instruction"
    }}

    Data: {json.dumps(predictions)}

    REQUIREMENTS:
    1. time_period must be exactly "weekly" or "monthly"
    2. amount must be positive with 2 decimal places
    3. description must start with a verb (Save, Reduce, etc.)
    4. No additional text outside the JSON
    5. JSON must be syntactically perfect
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,  # Fewer tokens for simpler response
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    result = completion.choices[0].message.content
    print("Raw Recommendation Output:", result)
    
    # Validate JSON structure before returning
    parsed = json.loads(result)
    if not all(k in parsed for k in ["time_period", "amount", "description"]):
        raise ValueError("Missing required keys in recommendation")
    if parsed["time_period"] not in ["weekly", "monthly"]:
        raise ValueError("Invalid time_period value")
    
    return parsed

def get_fallback_responses(predictions):
    """Provides fallback responses when LLM fails"""
    fallback_analysis = {
        "observations": "Review your recent financial activity for patterns.",
        "daily_actions": "Track all expenses today to identify savings opportunities.",
        "weekly_actions": "Set aside 10% of weekly income for savings.",
        "monthly_actions": "Review monthly subscriptions and cancel unused services.",
        "risks": "Unplanned expenses could disrupt your cash flow.",
        "long_term_insights": "Consistent saving will build financial resilience."
    }
    
    fallback_recommendation = {
        "time_period": "weekly",
        "amount": 100.00,
        "description": "Save 10% of weekly income automatically"
    }
    
    return fallback_analysis, fallback_recommendation
class MockLLMClient:
    def __init__(self):
        self.chat = self  # Make chat attribute return self
        self.completions = self  # Make completions attribute return self
    
    def create(self, model=None, messages=None, temperature=None, response_format=None, max_tokens=None):
        """Updated mock create method to handle all expected parameters"""
        if response_format and response_format.get("type") == "json_object":
            content = '{"time_period": "weekly", "amount": 100.0, "description": "Save 10% of income"}'
        else:
            content = 'observations1,observations2|daily_action|weekly_action|monthly_action|risks1,risks2|insights1,insights2'
        
        return type('MockResponse', (), {
            "choices": [
                type('MockChoice', (), {
                    "message": type('MockMessage', (), {
                        "content": content
                    })
                })
            ]
        })


class TestFinancialPredictionSystem:
    @pytest.fixture
    def sample_data(self):
        """Generate sample transaction data for testing"""
        dates = pd.date_range(start='2023-01-01', periods=30)
        amounts = np.random.randint(10, 100, size=30)
        return pd.DataFrame({
            'date': dates,
            'total_spent': amounts,
            'day_of_week': [d.weekday() + 1 for d in dates]
        })

    @pytest.fixture
    def sample_category_data(self):
        """Generate sample category data for testing"""
        dates = pd.date_range(start='2023-01-01', periods=30)
        return {
            'food': pd.DataFrame({
                'date': dates[:15],
                'amount': np.random.randint(5, 50, size=15)
            }),
            'transport': pd.DataFrame({
                'date': dates[10:25],
                'amount': np.random.randint(10, 30, size=15)
            })
        }

    @pytest.fixture
    def sample_transactions(self):
        """Sample transaction records for LLM testing"""
        return [
            {'date': '2023-01-01', 'type': 'expense', 'reason': 'Groceries', 'category': 'food', 'amount': 50.0},
            {'date': '2023-01-02', 'type': 'expense', 'reason': 'Gas', 'category': 'transport', 'amount': 30.0}
        ]

    # Manual Model Tests
    def test_manual_predictions_day(self, sample_data):
        """Test daily prediction returns valid float"""
        result = predict_next_day(sample_data)
        assert isinstance(result, float)
        assert result >= 0

    def test_manual_predictions_week(self, sample_data):
        """Test weekly prediction returns valid float"""
        result = predict_next_week(sample_data)
        assert isinstance(result, float)
        assert result >= 0

    def test_manual_predictions_month(self, sample_data):
        """Test monthly prediction returns valid float"""
        result = predict_next_month(sample_data)
        assert isinstance(result, float)
        assert result >= 0

    def test_category_predictions(self, sample_category_data):
        """Test category predictions return valid dictionary"""
        results = predict_category_spending(sample_category_data, 'day')
        assert isinstance(results, dict)
        for val in results.values():
            assert isinstance(val, float)
            assert val >= 0

    # LLM Advisory Tests
    def test_llm_advisor_with_mock(self):
        """Test LLM advisor with mock client"""
        mock_client = MockLLMClient()
        predictions = {
            'day': 50.0,
            'week': 350.0,
            'month': 1500.0,
            'categories': {
                'food': {'day': 20.0, 'week': 140.0, 'month': 600.0},
                'transport': {'day': 10.0, 'week': 70.0, 'month': 300.0}
            }
        }
        transactions = [
            {'date': '2023-01-01', 'type': 'expense', 'reason': 'Groceries', 'category': 'food', 'amount': 50.0}
        ]
        
        analysis, recommendation = prediction_advisor_agent(predictions, transactions, mock_client)
        
        assert isinstance(analysis, dict)
        assert isinstance(recommendation, dict)
        assert 'observations' in analysis
        assert 'daily_actions' in analysis
        assert 'time_period' in recommendation

    def test_llm_analysis_phase(self):
        """Test analysis phase with mocked LLM response"""
        mock_client = MockLLMClient()
        
        predictions = {'day': 50.0}
        transactions = [{'date': '2023-01-01', 'type': 'expense', 'reason': 'test', 'category': 'test', 'amount': 10.0}]
        
        result = generate_analysis_phase(predictions, transactions, mock_client)
        
        assert isinstance(result, dict)
        assert len(result['observations']) == 2
        assert 'daily_action' in result['daily_actions']

    def test_llm_recommendation_phase(self):
        """Test recommendation phase with mocked LLM response"""
        mock_client = MockLLMClient()
        
        predictions = {'day': 50.0}
        result = generate_recommendation_phase(predictions, mock_client)
        
        assert isinstance(result, dict)
        assert result['time_period'] in ['weekly', 'monthly']
        assert result['amount'] > 0

    # Integration Tests
    def test_full_integration(self, sample_data, sample_category_data, sample_transactions):
        """Test full workflow from manual predictions to LLM advice"""
        # Generate manual predictions
        daily_pred = predict_next_day(sample_data)
        weekly_pred = predict_next_week(sample_data)
        monthly_pred = predict_next_month(sample_data)
        category_preds = predict_category_spending(sample_category_data, 'day')
        
        # Prepare prediction structure for LLM
        predictions = {
            'day': daily_pred,
            'week': weekly_pred,
            'month': monthly_pred,
            'categories': {
                cat: {'day': val} for cat, val in category_preds.items()
            }
        }
        
        # Get LLM advice
        mock_client = MockLLMClient()
        analysis, recommendation = prediction_advisor_agent(predictions, sample_transactions, mock_client)
        
        # Validate results
        assert isinstance(analysis, dict)
        assert isinstance(recommendation, dict)
        assert all(k in analysis for k in ['observations', 'daily_actions', 'risks'])
        assert all(k in recommendation for k in ['time_period', 'amount', 'description'])

    # Edge Case Tests
    def test_empty_data(self):
        """Test system handles empty data gracefully"""
        empty_df = pd.DataFrame(columns=['date', 'total_spent'])
        
        # Manual predictions with empty data
        assert predict_next_day(empty_df) == 0.0
        assert predict_next_week(empty_df) == 0.0
        assert predict_next_month(empty_df) == 0.0
        
        # LLM with empty predictions
        empty_preds = {'day': 0.0, 'week': 0.0, 'month': 0.0, 'categories': {}}
        mock_client = MockLLMClient()
        analysis, recommendation = prediction_advisor_agent(empty_preds, [], mock_client)
        
        assert isinstance(analysis, dict)
        assert isinstance(recommendation, dict)

    def test_single_value_data(self):
        """Test system handles single data point"""
        single_df = pd.DataFrame({
            'date': [datetime.now()],
            'total_spent': [100],
            'day_of_week': [1]
        })
        
        assert predict_next_day(single_df) == 100.0
        assert predict_next_week(single_df) > 0
        assert predict_next_month(single_df) > 0

    def test_llm_fallback(self):
        """Test system falls back gracefully when LLM fails"""
        mock_client = MockLLMClient()
        mock_client.create = Mock(side_effect=Exception("API Error"))
        
        predictions = {'day': 50.0}
        transactions = [{'date': '2023-01-01', 'type': 'expense', 'category': 'test', 'amount': 10.0}]
        
        analysis, recommendation = prediction_advisor_agent(predictions, transactions, mock_client)
        
        # Should return fallback responses
        assert isinstance(analysis, dict)
        assert isinstance(recommendation, dict)