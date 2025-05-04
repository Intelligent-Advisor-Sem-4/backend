from pydantic import BaseModel
from typing import List, Optional

class Input(BaseModel):
    tickers: List[str]
    start_date: str = "2020-01-01"
    end_date: str = "2024-01-01"
    num_portfolios: int = 10000
    investment_amount: float
    target_amount: float
    years: float
    risk_score_percent: Optional[float] = None  # NEW: user's quiz risk percent (0-100)
    use_risk_score: bool = False                # NEW: whether user selects custom risk
