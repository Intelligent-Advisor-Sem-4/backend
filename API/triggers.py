from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.dbConnect import get_db
from services.asset_management import update_all_stock_risk_scores

router = APIRouter(
    prefix="/triggers",
    tags=["triggers"]
)


@router.post("/update-risk-scores", status_code=200)
def trigger_risk_score_updates(db: Session = Depends(get_db)):
    """Trigger risk score updates for all stocks in the database."""
    update_all_stock_risk_scores(db)
    return {"message": "Risk score update initiated for all stocks"}
