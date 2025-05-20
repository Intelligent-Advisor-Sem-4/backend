from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from db.dbConnect import get_db
from services.asset_management import update_all_stock_risk_scores

router = APIRouter(
    prefix="/triggers",
    tags=["triggers"]
)


@router.post("/update-risk-scores", status_code=200)
def trigger_risk_score_updates(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger risk score updates for all stocks in the database."""
    background_tasks.add_task(update_all_stock_risk_scores, db)
    return {"message": "Risk score update initiated in the background"}
