from pydantic import BaseModel

class RiskQuizAnswers(BaseModel):
    age: str
    investment_duration: str
    investment_objective: str
    financial_knowledge: str
    market_reaction: str
    income_stability: str