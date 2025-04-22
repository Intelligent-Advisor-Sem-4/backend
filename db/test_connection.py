from sqlalchemy import text
from dbConnect import engine

def test_connection():
    try:
        
        with engine.connect() as connection:
            result = connection.execute(text("select * from stocks"))
            print("Database connection successful!")
            print(result.fetchall())
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection() 