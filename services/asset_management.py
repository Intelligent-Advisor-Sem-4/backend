import yfinance as yf
from classes.stock_screener import ScreenerType
from sqlalchemy.orm import Session
from datetime import date
from models.models import Stock, AssetStatus  # assuming your model is in models.py



def calculate_risk(stock):
    volatility = stock.get("fiftyTwoWeekHigh", 0) - stock.get("fiftyTwoWeekLow", 0)
    market_cap = stock.get("marketCap", 0)
    pe = stock.get("forwardPE", 0) or stock.get("trailingPE", 0)

    if not market_cap or market_cap < 1e9:
        return "High"
    if pe > 40 or volatility > 50:
        return "Medium"
    return "Low"


def run_stock_screen(screen_type: ScreenerType, offset=0, size=25, custom_query=None, minimal=False):
    """
    Run a stock or fund screener using predefined queries or a custom query.
    """
    # Convert the Enum to its string value
    screen_type_str = screen_type.value

    if screen_type == ScreenerType.CUSTOM and custom_query is not None:
        query = custom_query.get('query')
        sort_field = custom_query.get('sortField', None)
        sort_type = custom_query.get('sortType', None)
        sort_asc = True if sort_type and sort_type.upper() == 'ASC' else False
    else:
        # Check if the screen_type is in predefined queries
        if screen_type_str not in yf.PREDEFINED_SCREENER_QUERIES:
            available_types = list(yf.PREDEFINED_SCREENER_QUERIES.keys())
            raise ValueError(f"Screen type '{screen_type_str}' not found in predefined queries. "
                             f"Available types: {available_types}")

        # Get the predefined query
        predefined = yf.PREDEFINED_SCREENER_QUERIES[screen_type_str]
        query = predefined.get('query')
        sort_field = predefined.get('sortField', None)
        sort_type = predefined.get('sortType', None)
        sort_asc = True if sort_type and sort_type.upper() == 'ASC' else False

    # Run the screen
    response = yf.screen(
        query=query,
        offset=offset,
        size=size,
        sortField=sort_field,
        sortAsc=sort_asc
    )

    quotes = response.get("quotes", [])

    if minimal:
        for q in quotes:
            q["riskLevel"] = calculate_risk(q)
        return {
            "quotes": [
                {
                    "symbol": q.get("symbol"),
                    "name": q.get("shortName") or q.get("longName"),
                    "price": q.get("regularMarketPrice"),
                    "marketCap": q.get("marketCap"),
                    "analystRating": q.get("averageAnalystRating"),
                    "dividendYield": q.get("dividendYield"),
                    "peRatio": q.get("forwardPE") or q.get("trailingPE"),
                    "priceChangePercent": q.get("regularMarketChangePercent"),
                    "exchange": q.get("exchange"),
                    "market": q.get("market"),
                    "riskLevel": q.get("riskLevel"),
                }
                for q in quotes
            ],
            "start": response.get("start"),
            "count": response.get("count"),
        }

    return response

def create_stock(db: Session, symbol: str) -> Stock:
    symbol = symbol.upper()
    existing = db.query(Stock).filter_by(ticker_symbol=symbol).first()
    if existing:
        raise ValueError(f"Stock with symbol '{symbol}' already exists")

    try:
        yf_data = yf.Ticker(symbol)
        info = yf_data.info
        history = yf_data.history(period="max")

        stock = Stock(
            ticker_symbol=symbol,
            asset_name=info.get("shortName") or info.get("longName") or symbol,
            currency=info.get("currency", "USD"),
            type="Stock",
            status=AssetStatus.PENDING,
            first_data_point_date=history.index.min().date() if not history.empty else None,
            last_data_point_date=history.index.max().date() if not history.empty else None
        )

        db.add(stock)
        db.commit()
        db.refresh(stock)
        return stock

    except Exception as e:
        raise ValueError(f"Failed to fetch data for symbol '{symbol}': {e}")


def update_stock_status(db: Session, stock_id: int, new_status: AssetStatus) -> Stock:
    stock = db.query(Stock).filter_by(stock_id=stock_id).first()
    if not stock:
        raise ValueError(f"Stock with ID {stock_id} not found")

    stock.status = new_status
    db.commit()
    db.refresh(stock)
    return stock


def get_stock_by_symbol(db: Session, symbol: str) -> Stock:
    return db.query(Stock).filter_by(ticker_symbol=symbol.upper()).first()

def get_all_stocks(db: Session) -> list[Stock]:
    return db.query(Stock).all()


def delete_stock(db: Session, stock_id: int) -> None:
    stock = db.query(Stock).filter_by(stock_id=stock_id).first()
    if not stock:
        raise ValueError(f"Stock with ID {stock_id} not found")

    db.delete(stock)
    db.commit()




if __name__ == "__main__":
    # Example usage
    screener = ScreenerType.MOST_ACTIVES
    result = run_stock_screen(screener, offset=0, size=1, minimal=False)
    print(result)
