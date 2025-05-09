from decimal import Decimal
import logging
from fastapi import APIRouter, Form, HTTPException, status,Depends, Query, Response
from classes.profile import Input,Tickers,RiskScoreIn, RiskScoreOut
from services.portfolio import build_portfolio_response
from db.dbConnect import get_db
from sqlalchemy.orm import Session
from services.tickers import fetch_tickers
from services.risk  import fetch_user_risk_score, upsert_user_risk_score


router = APIRouter(
    prefix="/profile",
    tags=["profile"]
)


@router.get("/ping",status_code=status.HTTP_200_OK)
def ping():
    try:
        return {"msg": "working!"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail=f"Unexpected Error: {str(e)}")

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
    
    
@router.get( "/risk_score", response_model=RiskScoreOut,responses={200: {"model": RiskScoreOut},204: {"description": "No risk score found for that user_id"},},
 )
async def get_risk_score(user_id: str= Query(..., description="UUID of the user"), db: Session = Depends(get_db)):

    try:
        raw = fetch_user_risk_score(db, user_id)
        if raw is None:
            # 204 No Content means “no record” — client can treat that as null
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # **always** convert Decimal → float before returning
        return RiskScoreOut(score=float(raw))

    except Exception as e:
        logging.exception("error in GET /risk_score")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.post("/risk_score",status_code=status.HTTP_201_CREATED,response_model=RiskScoreOut)
async def post_risk_score( user_id: str = Form(...),score:  float = Form(...),db: Session= Depends(get_db)):
    
    try:
        rec = upsert_user_risk_score(
            db,
            user_id,
            Decimal(str(score))
        )
        return RiskScoreOut(score=float(rec.risk_score))
    except Exception as e:
        logging.exception("error in POST /risk_score")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save risk score: {e}"
        )