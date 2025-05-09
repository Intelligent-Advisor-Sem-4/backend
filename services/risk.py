from decimal import Decimal
from typing  import Optional

from sqlalchemy.orm import Session
from models.models import RiskAnalysis

def fetch_user_risk_score(db: Session, user_id: str) -> Optional[Decimal]:
    rec = (
        db.query(RiskAnalysis)
          .filter(RiskAnalysis.user_id == user_id)
          .first()
    )
    return rec.risk_score if rec else None


def upsert_user_risk_score(db: Session, user_id: str, score: Decimal) -> RiskAnalysis:
    rec = (
        db.query(RiskAnalysis)
          .filter(RiskAnalysis.user_id == user_id)
          .first()
    )
    if rec:
        rec.risk_score = score
    else:
        rec = RiskAnalysis(user_id=user_id, risk_score=score)
        db.add(rec)

    db.commit()
    db.refresh(rec)
    return rec
