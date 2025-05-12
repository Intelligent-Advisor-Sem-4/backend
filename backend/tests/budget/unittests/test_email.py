# models.py
from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, JSON, Date, ForeignKey, Numeric, BigInteger, \
    Text
from sqlalchemy.orm import relationship, backref, Session  # Added Session import here
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base  # Updated import for SQLAlchemy 2.0
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import enum
import uuid
import pytest
from unittest.mock import create_autospec, patch
from datetime import datetime, timezone

Base = declarative_base()

class AccessLevel(enum.Enum):
    ADMIN = "admin"
    USER = "user"

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNDEFINED = "undefined"

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

    def __init__(self, **kwargs):
        # Validate required fields
        required_fields = ['name', 'birthday', 'gender', 'username', 'password', 'email']
        for field in required_fields:
            if field not in kwargs:
                raise TypeError(f"Missing required field: {field}")
        
        # Validate enum values
        if 'gender' in kwargs and not isinstance(kwargs['gender'], Gender):
            raise ValueError("gender must be a valid Gender enum value")
        if 'access_level' in kwargs and not isinstance(kwargs.get('access_level'), AccessLevel):
            raise ValueError("access_level must be a valid AccessLevel enum value")
        
        # Set default values
        kwargs.setdefault('access_level', AccessLevel.USER)
        kwargs.setdefault('created_at', datetime.now(timezone.utc))
        kwargs.setdefault('id', str(uuid.uuid4()))
        
        super().__init__(**kwargs)

def getAllUsers(db: Session):
    return db.query(UserModel).all()

@pytest.fixture
def mock_db():
    return create_autospec(Session, instance=True)

@pytest.fixture
def sample_user_data():
    return {
        "name": "John Doe",
        "birthday": datetime(1990, 1, 1, tzinfo=timezone.utc),
        "gender": Gender.MALE,
        "username": "johndoe",
        "password": "securepassword",
        "email": "john@example.com",
        "avatar": "http://example.com/avatar.jpg",
        "access_level": AccessLevel.USER
    }

def test_user_model_creation(sample_user_data):
    """Test that a UserModel can be created with all required fields."""
    user = UserModel(**sample_user_data)
    
    assert isinstance(user.id, str)
    assert user.name == sample_user_data["name"]
    assert user.birthday == sample_user_data["birthday"]
    assert user.gender == sample_user_data["gender"]
    assert user.username == sample_user_data["username"]
    assert user.password == sample_user_data["password"]
    assert user.email == sample_user_data["email"]
    assert user.avatar == sample_user_data["avatar"]
    assert user.access_level == sample_user_data["access_level"]
    assert isinstance(user.created_at, datetime)

def test_user_model_defaults(sample_user_data):
    """Test that UserModel has correct default values."""
    minimal_data = {
        "name": "Jane Doe",
        "birthday": datetime(1995, 1, 1, tzinfo=timezone.utc),
        "gender": Gender.FEMALE,
        "username": "janedoe",
        "password": "anotherpassword",
        "email": "jane@example.com"
    }
    
    user = UserModel(**minimal_data)
    
    assert isinstance(user.id, str)
    assert user.access_level == AccessLevel.USER
    assert isinstance(user.created_at, datetime)
    uuid.UUID(user.id)  # Should not raise

def test_get_all_users(mock_db, sample_user_data):
    """Test that getAllUsers returns all users from the database."""    
    user1 = UserModel(**sample_user_data)
    user2 = UserModel(
        name="Jane Doe",
        birthday=datetime(1995, 1, 1, tzinfo=timezone.utc),
        gender=Gender.FEMALE,
        username="janedoe",
        password="anotherpassword",
        email="jane@example.com"
    )
    
    mock_db.query.return_value.all.return_value = [user1, user2]
    result = getAllUsers(mock_db)
    
    assert len(result) == 2
    assert result[0].username == "johndoe"
    assert result[1].username == "janedoe"
    mock_db.query.assert_called_once_with(UserModel)

def test_user_model_validation():
    """Test that required fields are properly validated."""
    with pytest.raises(TypeError):
        UserModel()  # Missing all required fields
    
    with pytest.raises(TypeError):
        UserModel(name="Test")  # Missing other required fields

def test_user_model_unique_constraints():
    """Test that username and email must be unique."""
    username_column = UserModel.__table__.c.username
    email_column = UserModel.__table__.c.email
    
    assert username_column.unique is True
    assert email_column.unique is True

def test_user_model_enum_values(sample_user_data):
    """Test that enum fields only accept valid values."""
    with pytest.raises(ValueError):
        invalid_data = sample_user_data.copy()
        invalid_data["gender"] = "invalid_gender"
        UserModel(**invalid_data)
    
    with pytest.raises(ValueError):
        invalid_data = sample_user_data.copy()
        invalid_data["access_level"] = "invalid_level"
        UserModel(**invalid_data)

def test_user_model_id_generation():
    """Test that IDs are automatically generated as UUID strings."""
    user = UserModel(
        name="No ID User",
        birthday=datetime(1990, 1, 1, tzinfo=timezone.utc),
        gender=Gender.MALE,
        username="noiduser",
        password="noidpass",
        email="noid@example.com"
    )
    
    # Check it's a valid UUID string
    uuid.UUID(user.id)