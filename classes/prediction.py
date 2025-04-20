from pydantic import BaseModel
class InData(BaseModel):
    company: str
    date: str
