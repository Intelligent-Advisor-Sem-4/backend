from typing import List, Union, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from tensorflow.python.trackable.asset import Asset

from classes.stock_screener import ScreenerType, ScreenerResponseMinimal, ScreenerRequest
from services.asset_management import run_stock_screen

router = APIRouter(prefix='/assets')


@router.get("/screen/{screen_type}", response_model=Union[Dict[str, Any], ScreenerResponseMinimal])
async def screen_stocks(
        screen_type: ScreenerType,
        offset: int = Query(0, ge=0, description="The starting position in results"),
        size: int = Query(25, gt=0, le=250, description="Number of results to return (max 250)"),
        minimal: bool = Query(True, description="Return minimal data")
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
