from pydantic import BaseModel
class InData(BaseModel):
    company: str
    date: str

class getstockhist(BaseModel):
    starting_date: str
    ending_date: str
    symbol: str

class getpredictprice(BaseModel):
    ticker_symbol: str
    starting_date: str
    ending_date: str

class StockHistoryItem(BaseModel):
    date: str
    price: float
    volume: int


class StockData(BaseModel):
    ticker: str
    currentPrice: float
    priceChange: float
    history: list[StockHistoryItem]

class StockPriceHistoricalType(BaseModel):
    id: int
    stock_id: int
    price_date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    fetched_at: str