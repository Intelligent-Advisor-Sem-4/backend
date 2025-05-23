from typing import List, Union, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, status,BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ml_lib.stock_predictor import getStockData, predict,trainer
from classes.Asset import Asset, AssetFastInfo, StockResponse
from classes.Stock import CreateStockResponse
from classes.ScreenerQueries import ScreenerType, ScreenerResponseMinimal
from core.middleware import logger
from db.dbConnect import get_db
from models.models import AssetStatus
from services.asset_screening import run_stock_screen
from services.asset_management import create_stock, get_asset_by_ticker, get_asset_by_ticker_fast, update_stock_status, \
    delete_stock, get_db_stocks as get_db_stocks_function, get_db_stock_count
from classes.Search import SearchResult
from services.asset_search import yfinance_search

router = APIRouter(prefix='/assets', tags=["asset-management"])


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


@router.post('/create-stock', response_model=CreateStockResponse, status_code=status.HTTP_201_CREATED)
def api_create_stock(ticker: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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
        background_tasks.add_task(trainer, ticker)
        return CreateStockResponse(
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


@router.get("/search", response_model=SearchResult)
async def search(
        query: str = Query(..., description="Search query string"),
        news_count: Optional[int] = Query(8, description="Number of news articles to fetch", ge=1, le=50),
        quote_count: Optional[int] = Query(5, description="Number of quotes to fetch", ge=1, le=20)
) -> SearchResult:
    """
    Search Yahoo Finance for news and quotes related to the query.

    Parameters:
    - query: Search term
    - news_count: Number of news articles to return (default: 8)
    - quote_count: Number of quotes to return (default: 5)

    Returns:
    - SearchResult object containing lists of news articles and quotes
    """
    try:
        result = yfinance_search(query=query, news_count=news_count, quote_count=quote_count)
        return result
    except ValueError as e:
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            logger.error(f"Connection error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        # Log the unexpected exception
        logger.error(f"Unexpected error in search endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{ticker}", response_model=Asset)
async def get_asset(ticker: str, db: Session = Depends(get_db)):
    """
    Get asset details by ticker symbol.

    Args:
        ticker: The stock ticker symbol
        db: Database session

    Returns:
        The asset object

    Raises:
        HTTPException: If asset not found or error occurs
    """
    try:
        asset = get_asset_by_ticker(db, ticker)
        return asset
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/fast-info/{ticker}", response_model=AssetFastInfo)
async def get_asset(ticker: str, db: Session = Depends(get_db)):
    """
    Get asset details by ticker symbol.

    Args:
        ticker: The stock ticker symbol
        db: Database session

    Returns:
        The asset object

    Raises:
        HTTPException: If asset not found or error occurs
    """
    try:
        asset = get_asset_by_ticker_fast(db, ticker)
        return asset
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class StockStatusUpdate(BaseModel):
    status: AssetStatus


@router.put("/{stock_id}/status", response_model=Dict[str, str])
async def update_status(
        stock_id: int,
        status_update: StockStatusUpdate,
        db: Session = Depends(get_db)
):
    """
    Update the status of a stock by ID
    """
    try:
        update_stock_status(db, stock_id=stock_id, new_status=status_update.status)

        return {
            "message": f"Stock {stock_id} status updated to {status_update.status.value}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the exception here if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stock status: {str(e)}"
        )


@router.delete("/{stock_id}", response_model=Dict[str, str])
async def delete_stock_by_id(
        stock_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete a stock by ID
    """
    try:
        delete_stock(db, stock_id=stock_id)
        return {
            "message": f"Stock {stock_id} deleted successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Log the exception here if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete stock: {str(e)}"
        )


@router.get("/db/stocks", response_model=List[StockResponse])
async def get_db_stocks(
        offset: int = Query(0, ge=0, description="The starting position in results"),
        limit: int = Query(10, gt=0, le=100, description="Number of results to return (max 100)"),
        db: Session = Depends(get_db)
):
    """
    Get stocks from the database with pagination

    Query Parameters:
    - offset: Starting position for pagination
    - limit: Number of results to return (max 100)
    """
    try:
        stocks = get_db_stocks_function(db=db, offset=offset, limit=limit)
        return stocks
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class CountResponse(BaseModel):
    count: int

@router.get("/db/stocks/count", response_model=CountResponse)
async def get_db_stocks_count(
        db: Session = Depends(get_db)
):
    """
    Get the total count of stocks in the database
    """
    try:
        count = get_db_stock_count(db=db)
        return {
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
