import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

# Use SQLite in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create engine for test database
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create all tables in the test database
Base.metadata.create_all(bind=test_engine)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db() -> Session:
    """
    Creates and returns a test database session using SQLite in-memory.

    Returns:
        Session: A SQLAlchemy session connected to the in-memory test database

    Usage:
        db = get_test_db()
        try:
            # Perform database operations with db
            ...
        finally:
            db.close()
    """
    db = TestSessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e


def get_test_db_context():
    """
    Context manager for test database sessions.
    Automatically handles closing the session when done.

    Yields:
        Session: A SQLAlchemy session connected to the in-memory test database

    Usage:
        with get_test_db_context() as db:
            # Perform database operations with db
            ...
    """
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_test_db():
    """
    Create all tables in the test database.
    Call this once before running tests.
    """
    Base.metadata.create_all(bind=test_engine)


def teardown_test_db():
    """
    Drop all tables in the test database.
    Call this after tests are complete.
    """
    Base.metadata.drop_all(bind=test_engine)
