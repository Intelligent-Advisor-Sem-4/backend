from pydantic import BaseModel
from typing import List

class Input(BaseModel):
    tickers: List[str]
    start_date: str
    end_date: str
    num_portfolios: int
    investment_amount: float
    target_amount: float
    years:float