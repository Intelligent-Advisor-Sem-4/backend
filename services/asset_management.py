import yfinance as yf

from classes.stock_screener import ScreenerType


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


if __name__ == "__main__":
    # Example usage
    screener = ScreenerType.MOST_ACTIVES
    result = run_stock_screen(screener, offset=0, size=1, minimal=True)
    print(result)
