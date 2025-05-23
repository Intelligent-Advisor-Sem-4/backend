from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from core.password import get_password_hash
from models import Base, UserModel
from models.models import Gender, AccessLevel

# Load environment variables from .env file
load_dotenv()

# Get database credentials from environment variables
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Create PostgresSQL connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# python
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # number of connections to keep open
    max_overflow=10,  # number of additional connections allowed
    pool_timeout=30,  # seconds to wait before giving up on a connection
    pool_recycle=1800,  # seconds after which a connection is recycled
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Seed user
def seed_user():
    db = SessionLocal()
    try:
        users_to_seed = [
            {
                "id": uuid4(),
                "name": "John Doe",
                "birthday": datetime(1990, 1, 1, tzinfo=timezone.utc),
                "gender": Gender.MALE,
                "username": "johndoe",
                "password": get_password_hash("123"),
                "email": "johndoe@example.com",
                "access_level": AccessLevel.USER,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid4(),
                "name": "Jhon Smith",
                "birthday": datetime(1985, 5, 15, tzinfo=timezone.utc),
                "gender": Gender.MALE,
                "username": "johnsmith",
                "password": get_password_hash("admin123"),
                "email": "admin@example.com",
                "access_level": AccessLevel.ADMIN,
                "created_at": datetime.now(timezone.utc),
            },
        ]

        for user_data in users_to_seed:
            existing_user = (
                db.query(UserModel)
                .filter(
                    (UserModel.username == user_data["username"])
                    | (UserModel.email == user_data["email"])
                )
                .first()
            )

            if existing_user:
                print(f"User '{user_data['username']}' already exists. Skipping.")
                continue

            new_user = UserModel(**user_data)
            db.add(new_user)

        db.commit()
        print("Sample users seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


# Seed the database with initial data
def seed_database():
    seed_user()


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


# Drop all tables in the database
def drop_tables():
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped successfully.")


# Reset the database (drop + create)
def reset_database():
    drop_tables()
    create_tables()
    seed_database()
    print("Database reset successfully.")


# reset_database()
if __name__ == "__main__":
    # Uncomment the following line to reset the database
    # reset_database()
    # Uncomment the following line to create tables
    create_tables()
    # Uncomment the following line to drop tables
    # drop_tables()
    pass
