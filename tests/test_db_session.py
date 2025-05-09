from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

# PostgreSQL test database credentials
TEST_DB_NAME = "financial-assistant-test"  # Using a separate test database
TEST_DB_USER = "postgres"
TEST_DB_PASSWORD = "NissanSB14"
TEST_DB_HOST = "localhost"
TEST_DB_PORT = "5432"

# Test database connection URL
TEST_DATABASE_URL = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"

# Create engine for test database
test_engine = create_engine(TEST_DATABASE_URL)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db() -> Session:
    """
    Creates and returns a test database session using a local PostgreSQL database.

    Returns:
        Session: A SQLAlchemy session connected to the test database

    Usage:
        db = get_test_db()
        try:
            # Perform database operations with db
            ...
        finally:
            db.close()
    """
    db = TestSessionLocal()
    return db


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


def clean_test_db():
    """
    Delete all data from tables without dropping the tables.
    Useful to run between tests to ensure a clean slate.
    """
    # Get list of all tables
    connection = test_engine.connect()
    transaction = connection.begin()

    try:
        # Loop through all tables and delete all rows
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        transaction.commit()
    except Exception as e:
        transaction.rollback()
        raise e
    finally:
        connection.close()
