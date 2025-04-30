from typing import Union, Dict, Any

import yfinance as yf
from classes.ScreenerQueries import ScreenerType, ScreenerResponseMinimal, SECTOR_SCREENER_QUERIES
from sqlalchemy.orm import Session

from db.dbConnect import get_db
from models.models import Stock  # assuming your model is in models.py
from services.utils import calculate_shallow_risk


def run_stock_screen(db: Session, screen_type: ScreenerType = ScreenerType.MOST_ACTIVES, offset=0, size=25,
                     custom_query=None,
                     minimal: bool = False) -> Union[Dict[str, Any], ScreenerResponseMinimal]:
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
        if screen_type_str in yf.PREDEFINED_SCREENER_QUERIES:
            # Get the predefined query
            predefined = yf.PREDEFINED_SCREENER_QUERIES[screen_type_str]
            query = predefined.get('query')
            sort_field = predefined.get('sortField', None)
            sort_type = predefined.get('sortType', None)
            sort_asc = True if sort_type and sort_type.upper() == 'ASC' else False
        elif screen_type_str in SECTOR_SCREENER_QUERIES:
            # Get the predefined query
            predefined = SECTOR_SCREENER_QUERIES[screen_type_str]
            query = predefined.get('query')
            sort_field = predefined.get('sortField', None)
            sort_type = predefined.get('sortType', None)
            sort_asc = True if sort_type and sort_type.upper() == 'ASC' else False
        else:
            available_types = list(yf.PREDEFINED_SCREENER_QUERIES.keys())
            available_types.append(list(SECTOR_SCREENER_QUERIES.keys()))
            raise ValueError(f"Screen type '{screen_type_str}' not found in predefined queries. "
                             f"Available types: {available_types}")

    # Run the screen
    response = yf.screen(
        query=query,
        offset=offset,
        size=size,
        sortField=sort_field,
        sortAsc=sort_asc,
    )

    quotes = response.get("quotes", [])

    if minimal:
        # Calculate risk for each quote
        for q in quotes:
            q["risk_score"] = calculate_shallow_risk(q)

        # Get all symbols from the quotes
        symbols = [q["symbol"] for q in quotes]

        # Fetch all stocks with these symbols in a single query
        db_stocks = db.query(Stock.ticker_symbol).filter(Stock.ticker_symbol.in_(symbols)).all()

        # Create a set of symbols that exist in the database for O(1) lookups
        db_symbols = {stock.ticker_symbol for stock in db_stocks}

        # Now create the minimal response with efficient in_db check
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
                    "risk_score": q.get("risk_score"),
                    "in_db": q.get("symbol") in db_symbols,  # O(1) lookup in a set
                }
                for q in quotes
            ],
            "start": response.get("start"),
            "count": response.get("count"),
        }

    return response


if __name__ == "__main__":
    # Example usage
    db_gen = get_db()
    session = next(db_gen)
    try:
        # Create a new stock
        try:
            run_stock_screen(db=session, screen_type=ScreenerType.TECHNOLOGY, offset=0, size=10, minimal=True)
        except ValueError as e:
            print(e)
    finally:
        db_gen.close()
