from sqlalchemy.orm import Session
from models.models import Stock, AssetStatus

def is_model_ready_by_symbol(db: Session, stock_identifier: str) -> bool:
    """
    Check if the stock model is ready for prediction.
    
    Args:
        db: Database session
        stock_identifier: Stock symbol (str)
        
    Returns:
        bool: True if the model is ready (status is ACTIVE), False otherwise
    """
    try:
        stock = db.query(Stock).filter(Stock.ticker_symbol == stock_identifier.upper()).first()
        
        # Check if stock exists and has status ACTIVE
        if stock and stock.status == AssetStatus.ACTIVE:
            return True
        return False
    
    except Exception as e:
        print(f"Error checking model status: {e}")
        return False
    

def is_model_ready_by_id(db: Session, stock_id: int) -> bool:
    """
    Check if the stock model is ready for prediction by stock ID.
    
    Args:
        db: Database session
        stock_id: Stock ID (int)
        
    Returns:
        bool: True if the model is ready (status is ACTIVE), False otherwise
    """
    try:
        stock = db.query(Stock).filter(Stock.stock_id == stock_id).first()
        
        # Check if stock exists and has status ACTIVE
        if stock and stock.status == AssetStatus.ACTIVE:
            return True
        return False
    
    except Exception as e:
        print(f"Error checking model status: {e}")
        return False


if __name__ == "__main__":
    ##### Example Usage #################################################
    from db.dbConnect import get_db

    # Using a session from your connection pool
    db = next(get_db())

    # Check by ticker symbol
    print(is_model_ready_by_symbol(db, "NVDA"))  # Example ticker symbol

    # Check by stock ID
    print(is_model_ready_by_id(db, 1))  # Example stock ID

    # Close the session
    db.close()