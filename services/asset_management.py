import yfinance as yf
from sqlalchemy.orm import Session

from models.models import Stock, AssetStatus


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
            asset_name=basic_info.get('shortName') or basic_info.get('longName') or info.get('shortName') or info.get(
                'longName') or history_metadata.get('shortName') or history_metadata.get('longName') or symbol,
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


def get_all_stocks(db: Session) -> list[Stock]:
    return db.query(Stock).all()


def delete_stock(db: Session, stock_id: int) -> None:
    stock = db.query(Stock).filter_by(stock_id=stock_id).first()
    if not stock:
        raise ValueError(f"Stock with ID {stock_id} not found")

    db.delete(stock)
    db.commit()
