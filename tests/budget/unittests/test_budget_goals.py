from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, 
    ForeignKey, func, create_engine, Enum
)
from sqlalchemy.orm import Session, relationship, backref, sessionmaker, declarative_base
from fastapi import HTTPException
import enum
import uuid

# Enums
class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNDEFINED = "undefined"

class AccessLevel(enum.Enum):
    USER = "user"
    ADMIN = "admin"

# SQLAlchemy Base (updated import)
Base = declarative_base()

# Database Models
class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    birthday = Column(DateTime, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    access_level = Column(Enum(AccessLevel), default=AccessLevel.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class BudgetGoalModel(Base):
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
        return f"<BudgetGoalModel(id={self.id}, title='{self.title}', amount={self.amount})>"
    
# Pydantic Schemas
class BudgetGoalBase(BaseModel):
    title: str
    category: str
    amount: float
    user_id: str
    deadline: datetime

class BudgetGoalCreate(BudgetGoalBase):
    created_at: datetime = datetime.now(timezone.utc)

class BudgetGoalUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    deadline: Optional[datetime] = None

class BudgetGoal(BudgetGoalBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    message: str

# Update the CRUD operations to use BudgetGoalModel
def get_budget_goals(db: Session, user_id: str) -> List[BudgetGoal]:
    return db.query(BudgetGoalModel)\
        .filter(BudgetGoalModel.user_id == user_id)\
        .order_by(BudgetGoalModel.deadline.asc())\
        .all()

def create_budget_goal(db: Session, goal: BudgetGoalCreate) -> BudgetGoal:
    db_goal = BudgetGoalModel(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return BudgetGoal.model_validate(db_goal)

def update_budget_goal(
    db: Session, 
    goal_id: int, 
    updates: BudgetGoalUpdate
) -> BudgetGoal:
    db_goal = db.query(BudgetGoalModel).filter(BudgetGoalModel.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Budget goal not found")
    
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_goal, key, value)
    
    db.commit()
    db.refresh(db_goal)
    return BudgetGoal.model_validate(db_goal)

def delete_budget_goal(db: Session, goal_id: int) -> MessageResponse:
    db_goal = db.query(BudgetGoalModel).filter(BudgetGoalModel.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Budget goal not found")
    
    db.delete(db_goal)
    db.commit()
    return MessageResponse(message="Budget goal deleted successfully")
# Test Fixtures
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create test user
    test_user = UserModel(
        id="test_user_123",
        name="Test User",
        birthday=datetime(1990, 1, 1),
        gender=Gender.MALE,
        username="testuser",
        password="hashed_password",
        email="test@example.com",
        access_level=AccessLevel.USER
    )
    session.add(test_user)
    session.commit()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)

# Tests
def test_budget_goal_base_schema():
    goal_data = {
        "title": "Vacation Savings",
        "category": "Travel",
        "amount": 2000.0,
        "user_id": "user123",
        "deadline": datetime.now(timezone.utc) + timedelta(days=30)
    }
    goal = BudgetGoalBase(**goal_data)
    assert goal.title == "Vacation Savings"
    assert goal.category == "Travel"
    assert goal.amount == 2000.0
    assert goal.user_id == "user123"
    assert isinstance(goal.deadline, datetime)

def test_budget_goal_create_schema():
    goal_data = {
        "title": "New Car",
        "category": "Transportation",
        "amount": 15000.0,
        "user_id": "user123",
        "deadline": datetime.now(timezone.utc) + timedelta(days=180)
    }
    goal = BudgetGoalCreate(**goal_data)
    assert hasattr(goal, "created_at")
    assert isinstance(goal.created_at, datetime)

def test_budget_goal_update_schema():
    update_data = {
        "title": "Updated Title",
        "amount": 2500.0
    }
    update = BudgetGoalUpdate(**update_data)
    assert update.title == "Updated Title"
    assert update.amount == 2500.0
    assert update.category is None
    assert update.deadline is None

def test_budget_goal_schema():
    goal_data = {
        "id": 1,
        "title": "Full Goal",
        "category": "Test",
        "amount": 100.0,
        "user_id": "user123",
        "deadline": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    }
    goal = BudgetGoal(**goal_data)
    assert goal.id == 1
    assert isinstance(goal.created_at, datetime)

# Update the test to use BudgetGoalModel
def test_get_budget_goals(db_session: Session):
    # Create goals using SQLAlchemy model
    goal1 = BudgetGoalModel(
        title="Goal 1",
        category="Cat1",
        amount=100,
        user_id="test_user_123",
        deadline=datetime.now(timezone.utc) + timedelta(days=5)
    )
    goal2 = BudgetGoalModel(
        title="Goal 2",
        category="Cat2",
        amount=200,
        user_id="test_user_123",
        deadline=datetime.now(timezone.utc) + timedelta(days=10)
    )
    db_session.add_all([goal1, goal2])
    db_session.commit()
    
    result = get_budget_goals(db_session, "test_user_123")
    assert len(result) == 2
    assert result[0].title == "Goal 1"
    assert result[1].title == "Goal 2"
    assert result[0].deadline < result[1].deadline

def test_create_budget_goal(db_session: Session):
    goal_data = BudgetGoalCreate(
        title="New Goal",
        category="Test",
        amount=500.0,
        user_id="test_user_123",
        deadline=datetime.now(timezone.utc) + timedelta(days=30)
    )
    
    result = create_budget_goal(db_session, goal_data)
    assert result.id is not None
    assert result.title == "New Goal"
    assert result.amount == 500.0
    
    db_goal = db_session.query(BudgetGoalModel).filter(BudgetGoalModel.id == result.id).first()
    assert db_goal is not None
    assert db_goal.user_id == "test_user_123"

def test_update_budget_goal(db_session: Session):
    goal = BudgetGoalModel(
        title="Original",
        category="Old",
        amount=100,
        user_id="test_user_123",
        deadline=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(goal)
    db_session.commit()
    
    updates = BudgetGoalUpdate(
        title="Updated",
        amount=200.0
    )
    
    result = update_budget_goal(db_session, goal.id, updates)
    assert result.title == "Updated"
    assert result.amount == 200.0
    assert result.category == "Old"

    db_goal = db_session.query(BudgetGoalModel).filter(BudgetGoalModel.id == goal.id).first()
    assert db_goal.title == "Updated"

def test_update_budget_goal_not_found(db_session: Session):
    updates = BudgetGoalUpdate(title="Should Fail")
    with pytest.raises(HTTPException) as exc_info:
        update_budget_goal(db_session, 999, updates)
    assert exc_info.value.status_code == 404
    assert "Budget goal not found" in str(exc_info.value.detail)

def test_delete_budget_goal(db_session: Session):
    goal = BudgetGoalModel(
        title="To Delete",
        category="Test",
        amount=100,
        user_id="test_user_123",
        deadline=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(goal)
    db_session.commit()
    goal_id = goal.id
    
    result = delete_budget_goal(db_session, goal_id)
    assert result.message == "Budget goal deleted successfully"
    db_goal = db_session.query(BudgetGoalModel).filter(BudgetGoalModel.id == goal_id).first()
    assert db_goal is None

def test_delete_budget_goal_not_found(db_session: Session):
    with pytest.raises(HTTPException) as exc_info:
        delete_budget_goal(db_session, 999)
    assert exc_info.value.status_code == 404
    assert "Budget goal not found" in str(exc_info.value.detail)