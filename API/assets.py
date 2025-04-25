from typing import List, Union, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session

from classes.Stock import StockResponse
from classes.ScreenerQueries import ScreenerType, ScreenerResponseMinimal, ScreenerRequest
from db.dbConnect import get_db
from services.asset_management import run_stock_screen, create_stock

router = APIRouter(prefix='/assets')


@router.get("/screen/{screen_type}", response_model=Union[Dict[str, Any], ScreenerResponseMinimal],
            status_code=status.HTTP_200_OK)
async def screen_stocks(
        screen_type: ScreenerType,
        offset: int = Query(0, ge=0, description="The starting position in results"),
        size: int = Query(25, gt=0, le=250, description="Number of results to return (max 250)"),
        minimal: bool = Query(True, description="Return minimal data"),
        db: Session = Depends(get_db)
):
    """
    Run a stock or fund screener using predefined queries

    Path Parameters:
    - screen_type: Type of screener to use

    Query Parameters:
    - offset: Starting position for pagination
    - size: Number of results to return (max 250)
    - minimal: Whether to return minimal data
    """
    try:
        response = run_stock_screen(
            db=db,
            screen_type=screen_type,
            offset=offset,
            size=size,
            minimal=minimal
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running stock screen: {str(e)}")


# For demonstration purposes, add an endpoint that lists available screener types
@router.get("/screener-types", response_model=List[str])
async def get_screener_types():
    """
    Get a list of all available stock screener types.
    """
    return [t.value for t in ScreenerType]


@router.post('/create-stock', response_model=StockResponse, status_code=status.HTTP_201_CREATED)
def api_create_stock(ticker: str, db: Session = Depends(get_db)):
    """
    Create a new stock entry in the database.

    Args:
        ticker: The stock ticker symbol
        db: Database session

    Returns:
        The created stock object

    Raises:
        HTTPException: If stock already exists or data can't be retrieved
    """
    try:
        stock = create_stock(db, ticker)
        return StockResponse(
            stock_id=stock.stock_id,
            ticker_symbol=stock.ticker_symbol,
            asset_name=stock.asset_name,
            status=stock.status,
            exchange_name=stock.exchange,
        )
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        elif "No data found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        # Log the unexpected exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
