from openai import BaseModel


class StockResponse(BaseModel):
    stock_id: int
    ticker_symbol: str
    asset_name: str
    exchange_name: str
    status: str
