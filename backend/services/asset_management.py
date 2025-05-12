from datetime import datetime

import yfinance as yf
from sqlalchemy.orm import Session

from classes.Asset import Asset, DB_Stock, AssetFastInfo, StockResponse
from models.models import Stock, AssetStatus
from services.email_service.email_service import send_email_notification
from services.risk_analysis.analyser import RiskAnalysis
from services.utils import calculate_shallow_risk_score


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

        # Send email notification
        company_name = stock.asset_name
        email_subject = f"New Stock Added: {symbol}"
        email_message = f"""
A new stock has been added to the database:

Ticker: {symbol}
Name: {company_name}
Exchange: {stock.exchange}

Initiate the model training process for this stock.
Change the status to 'ACTIVE' when ready.
"""
        send_email_notification(email_subject, email_message)

        db.add(stock)
        db.commit()
        db.refresh(stock)

        # Calculate initial risk score for the newly added stock
        try:
            analyser = RiskAnalysis(ticker=symbol, db=db, db_stock=stock)
            analyser.get_risk_score_and_update()
        except Exception as e:
            print(f"Error calculating initial risk score for {symbol}: {str(e)}")

        return stock

    except Exception as e:
        raise ValueError(f"Failed to fetch data for symbol '{symbol}': {e}")


def update_stock_status(db: Session, stock_id: int, new_status: AssetStatus) -> Stock:
    stock = db.query(Stock).filter_by(stock_id=stock_id).first()
    if not stock:
        raise ValueError(f"Stock with ID {stock_id} not found")

    if stock.status == AssetStatus.PENDING:
        raise ValueError(f"Stock with ID {stock_id} is still pending and cannot be updated")

    if new_status == AssetStatus.PENDING:
        raise ValueError(f"Cannot set status to PENDING for stock with ID {stock_id} manually")

    stock.status = new_status
    db.commit()
    db.refresh(stock)
    return stock


def get_all_stocks(db: Session) -> list[Stock]:
    return db.query(Stock).all()


def update_all_stock_risk_scores(db: Session) -> None:
    """Update risk scores for all stocks in the database."""
    stocks = db.query(Stock).all()

    for stock in stocks:
        try:
            # Get risk score using the analyzer and update it
            analyser = RiskAnalysis(ticker=str(stock.ticker_symbol), db=db, db_stock=stock)
            analyser.get_risk_score_and_update()
        except Exception as e:
            # Log error but continue processing other stocks
            print(f"Error updating risk score for {stock.ticker_symbol}: {str(e)}")


def get_db_stocks(db: Session, offset: int = 0, limit: int = 10) -> list[StockResponse]:
    # Order by updated_at in descending order (most recent first)
    stocks = db.query(Stock).order_by(Stock.updated_at.desc()).offset(offset).limit(limit).all()

    result = []
    for stock in stocks:
        # Use existing risk score from DB instead of recalculating
        # The daily scheduled job will keep these scores updated
        result.append(
            StockResponse(
                stock_id=int(stock.stock_id if stock.stock_id else 0),
                ticker_symbol=str(stock.ticker_symbol),
                asset_name=str(stock.asset_name) if stock.asset_name else None,
                risk_score=float(stock.risk_score) if stock.risk_score else None,
                risk_score_updated=stock.risk_score_updated.isoformat() if stock.risk_score_updated else None,
                status=AssetStatus(stock.status) if stock.status else None,  # Convert to AssetStatus enum
                currency=str(stock.currency) if stock.currency else None,
                type=str(stock.type) if stock.type else None,
                exchange=str(stock.exchange) if stock.exchange else None,
                sectorKey=str(stock.sectorKey) if stock.sectorKey else None,
                sectorDisp=str(stock.sectorDisp) if stock.sectorDisp else None,
                industryKey=str(stock.industryKey) if stock.industryKey else None,
                industryDisp=str(stock.industryDisp) if stock.industryDisp else None,
                created_at=stock.created_at.isoformat() if stock.created_at else None,
                updated_at=stock.updated_at.isoformat() if stock.updated_at else None,
            )
        )
    return result


def get_db_stock_count(db: Session) -> int:
    return db.query(Stock).count()


def delete_stock(db: Session, stock_id: int) -> None:
    stock = db.query(Stock).filter_by(stock_id=stock_id).first()
    if not stock:
        raise ValueError(f"Stock with ID {stock_id} not found")

    db.delete(stock)
    db.commit()


def update_stock_risk_score(db: Session, stock_id: int, risk_score: float) -> Stock:
    stock = db.query(Stock).filter_by(stock_id=stock_id).first()
    if not stock:
        raise ValueError(f"Stock with ID {stock_id} not found")

    stock.risk_score = risk_score
    stock.risk_score_updated = datetime.now()
    db.commit()
    db.refresh(stock)
    return stock


def get_asset_by_ticker(s: Session, t: str) -> Asset:
    """Fetch the asset by ticker symbol"""
    try:
        yt = yf.Ticker(t)
        basic_info = yt.fast_info
        if not basic_info:
            raise ValueError(f"No data found for ticker {t}.")

        history_metadata = yt.history_metadata
        info = yt.info
        db_stock = s.query(Stock).filter(Stock.ticker_symbol == t).first()

        # Create DB_Stock object if we have one in database
        riskScore = calculate_shallow_risk_score(
            market_cap=info.get("marketCap"),
            high=info.get("fiftyTwoWeekHigh"),
            low=info.get("fiftyTwoWeekLow"),
            pe_ratio=info.get("forwardPE") or info.get("trailingPE"),
            eps=info.get("trailingEps"),
            debt_to_equity=info.get("debtToEquity"),
            beta=info.get("beta"),
        )
        db_stock_model = None
        if db_stock:
            db_stock_model = DB_Stock(
                in_db=True,
                status=db_stock.status,
                asset_id=db_stock.stock_id,
                risk_score=riskScore,
                risk_score_updated=db_stock.risk_score_updated.isoformat() if db_stock.risk_score_updated else None
            )
        else:
            db_stock_model = DB_Stock(
                in_db=False,
                risk_score=riskScore,
            )

        return Asset(
            name=history_metadata.get('shortName') or history_metadata.get('longName') or basic_info.get(
                'shortName') or basic_info.get('longName') or t,
            company_url=info.get('website', ''),
            exchange=history_metadata.get('exchangeName') or basic_info.exchange,
            ticker=t,
            type=basic_info.quote_type,
            sector=info.get('sector', ''),
            industry=info.get('industry', ''),
            currency=basic_info.currency,
            prev_close=info.get('previousClose'),
            open_price=info.get('open'),
            last_price=info.get('currentPrice'),
            day_high=info.get('dayHigh'),
            day_low=info.get('dayLow'),
            volume=basic_info.last_volume,
            avg_volume=info.get('averageVolume'),
            beta=info.get('beta'),
            market_cap=info.get('marketCap'),
            fifty_two_week_high=info.get('fiftyTwoWeekHigh'),
            fifty_two_week_low=info.get('fiftyTwoWeekLow'),
            bid=info.get('bid'),
            ask=info.get('ask'),
            trailing_eps=info.get('trailingEps'),
            trailing_pe=info.get('trailingPE'),
            db=db_stock_model
        )
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Error retrieving data for ticker {t}: {str(e)}")


def get_asset_by_ticker_fast(s: Session, t: str) -> AssetFastInfo:
    """Fetch the asset by ticker symbol"""
    try:
        yt = yf.Ticker(t)
        basic_info = yt.fast_info
        if not basic_info:
            raise ValueError(f"No data found for ticker {t}.")

        return AssetFastInfo(
            currency=basic_info.currency,
            prev_close=basic_info.previous_close,
            last_price=basic_info.last_price,
        )
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Error retrieving data for ticker {t}: {str(e)}")


if __name__ == "__main__":
    # Example usage
    from db.dbConnect import get_db

    db_o = get_db()
    session = next(db_o)
    try:
        ticker = get_asset_by_ticker(session, "AEXAF")
        print(ticker)
    finally:
        db_o.close()
