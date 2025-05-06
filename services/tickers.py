from models.models import Stock, AssetStatus
from classes.profile import Tickers, Ticker


def fetch_tickers(db) -> Tickers:
    try:
        results = db.query(
            Stock.ticker_symbol,
            Stock.asset_name,
            Stock.sectorDisp,
            Stock.currency,
            Stock.status
        ).filter(Stock.status.in_([AssetStatus.PENDING, AssetStatus.ACTIVE,AssetStatus.WARNING])).all()

        tickers = Tickers(tickers=[
            Ticker(
                ticker_symbol=r[0],
                asset_name=r[1],
                sectorDisp=r[2],
                currency=r[3],
                status=r[4]
            ) for r in results
        ])

        return tickers
    except Exception as e:
        raise RuntimeError(f"Error fetching tickers: {str(e)}")
