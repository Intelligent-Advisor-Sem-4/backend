from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Replace these values with your actual RDS credentials
DATABASE_URL = "mysql+mysqlconnector://USERNAME:PASSWORD@financial-assistant.csvgkq8kwtb8.us-east-1.rds.amazonaws.com/DB_NAME"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
