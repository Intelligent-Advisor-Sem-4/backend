from fastapi import APIRouter, HTTPException, status,Depends
from classes.profile import Input,Tickers
from services.portfolio import build_portfolio_response
from db.dbConnect import get_db
from sqlalchemy.orm import Session
from services.tickers import fetch_tickers

router = APIRouter(
    prefix="/profile",
    tags=["profile"]
)


@router.get("/ping")
def ping():
    return {"msg": "working!"}

@router.post("/optimize_portfolio", status_code=status.HTTP_200_OK)
async def optimize_portfolio(request: Input):
    try:
        return build_portfolio_response(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected Error: {str(e)}")


@router.get("/get_portfolio", status_code=status.HTTP_200_OK, response_model=Tickers)
async def get_ticker_details(db: Session = Depends(get_db)):

    try:
        tickers = fetch_tickers(db)
        return tickers

    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

