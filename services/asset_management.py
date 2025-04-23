import yfinance as yf
from classes.stock_screener import ScreenerType
from sqlalchemy.orm import Session
from datetime import date

from db.dbConnect import get_db
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
        basic_info = yf_data.fast_info
        info = yf_data.info
        history_metadata = yf_data.history_metadata
        if not basic_info:
            raise ValueError(f"No data found for symbol '{symbol}'")

        stock = Stock(
            ticker_symbol=symbol,
            asset_name=basic_info.get('shortName') or basic_info.get('longName') or info.get('shortName') or info.get('longName') or history_metadata.get('shortName') or history_metadata.get('longName') or symbol,
            currency=basic_info.currency,
            type=basic_info.quote_type,
            exchange=basic_info.exchange,
            timezone=basic_info.timezone,
            sectorKey=info.get("sectorKey"),
            sectorDisp=info.get("sectorDisp"),
            industryKey=info.get("industryKey"),
            industryDisp=info.get("industryDisp"),
            status=AssetStatus.PENDING,
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
    db_gen = get_db()
    session = next(db_gen)
    try:
        # Create a new stock
        try:
            stock = create_stock(session, "TSLA")
            print(f"Created stock: {stock}")
        except ValueError as e:
            print(e)
    finally:
        db_gen.close()
