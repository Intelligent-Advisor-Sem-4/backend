from sqlalchemy.orm import Session
from db.dbConnect import get_db
from models.models import Stock, AssetStatus, PredictionModel, StockPrediction
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, timedelta


def getPredictedPricesFromDB(ticker_symbol, date):
    """
    Retrieve the predicted prices for a week (7 days) from the given date (inclusive) from the database.
    Args:
        ticker_symbol (str): The stock ticker symbol.
        date (str or datetime.date): The start date for predictions (YYYY-MM-DD).
    Returns:
        dict: PredictionData structure with keys 'ticker', 'predictions' (list of PredictionItem), and 'nextWeek' (PredictionItem).
    """
    session = next(get_db())
    try:
        # Ensure date is in correct format
        if isinstance(date, str):
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            date_obj = date

        # 1. Get the stock_id for the ticker_symbol
        stock = session.query(Stock).filter(Stock.ticker_symbol == ticker_symbol).first()
        if not stock:
            return None

        # 2. Get the active prediction model for this stock
        model = (
            session.query(PredictionModel)
            .filter(PredictionModel.target_stock_id == stock.stock_id, PredictionModel.is_active == True)
            .order_by(PredictionModel.latest_modified_time.desc())
            .first()
        )
        if not model:
            return None

        # 3. Get the predicted prices for the next 7 days (including given date)
        dates = [date_obj + timedelta(days=i) for i in range(8)]
        predictions = (
            session.query(StockPrediction)
            .filter(
                StockPrediction.model_id == model.model_id,
                StockPrediction.predicted_date.in_(dates)
            )
            .order_by(StockPrediction.predicted_date.asc())
            .all()
        )
        # Map predictions by date for quick lookup
        pred_map = {p.predicted_date: float(p.predicted_price) for p in predictions}
        prediction_items = []
        prev_price = None
        for d in dates:
            price = pred_map.get(d, None)
            if price is None:
                # If any day is missing, skip or return None (could also fill with None or 0)
                return None
            change = 0 if prev_price is None else price - prev_price
            prediction_items.append({
                "date": str(d),
                "predicted": price,
                "change": change
            })
            prev_price = price
        output = {
            "ticker": ticker_symbol,
            "predictions": prediction_items,
            "nextWeek": prediction_items[-1]
        }
        return output
    finally:
        session.close()


