from openai import BaseModel


class CreateStockResponse(BaseModel):
    stock_id: int
    ticker_symbol: str
    asset_name: str
    exchange_name: str
    status: str
