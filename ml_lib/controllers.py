from sqlalchemy.orm import Session
from db.dbConnect import get_db,SessionLocal
from models.models import Stock, AssetStatus, PredictionModel, StockPrediction
import yfinance as yf
import requests
import pandas as pd
from ml_lib.stock_predictor import getStockData,predict
from contextlib import contextmanager
from datetime import datetime, timedelta


def get_stock_options() -> list[dict]:
    try:
        db = next(get_db())
        stocks = db.query(Stock).filter(Stock.status == AssetStatus.ACTIVE).all()
        return [{"value": stock.ticker_symbol, "label": stock.asset_name} for stock in stocks]
    except Exception as e:
        print(f"Error fetching stock options: {e}")
        return []


def getPredictedPricesFromDB(ticker_symbol, date):
    """
    Retrieve the predicted prices for a week (7 days) from the given date (inclusive) from the database.
    Args:
        ticker_symbol (str): The stock ticker symbol.
        date (str or datetime.date): The start date for predictions (YYYY-MM-DD).
    Returns:
        dict: PredictionData structure with keys 'ticker', 'predictions' (list of PredictionItem), and 'nextWeek' (PredictionItem).
    """
    try:
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
    except Exception as e:
        print(f"Error in getPredictedPricesFromDB: {e}")
        return None


def getlast_date(symbol):
    """
    Get the last available date for the given stock ticker symbol using yfinance.
    Args:
        symbol (str): The stock ticker symbol.
    Returns:
        str: The last available date in YYYY-MM-DD format, or None if not found.
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="1d")
        if not history.empty:
            last_date = history.index[-1].date()
            return str(last_date)
        else:
            return None
    except Exception as e:
        print(f"Error fetching last date for symbol '{symbol}': {e}")
        return None

def get_stock_history(s_date, e_date, st_id=None, st_sym=None):
    try:
        ticker_symbol = None
        if st_id is None and st_sym is not None:
            ticker_symbol = st_sym
        elif st_id is not None:
            db = next(get_db())
            stock = db.query(Stock).filter(Stock.stock_id == st_id).first()
            if not stock:
                return None
            ticker_symbol = stock.ticker_symbol
        else:
            return None

        data_res = getStockData(company=ticker_symbol, starting_date=s_date, ending_date=e_date)
        data = data_res[0]
        print("point 4 pass")

        # Check if the index is already timezone-aware
        if data.index.tz is None:
            data.index = pd.to_datetime(data.index).tz_localize('UTC')
        else:
            data.index = data.index.tz_convert('UTC')

        history_list = []
        for index, row in data.iterrows():
            history_list.append({
                "date": str(index.date()),
                "price": float(row['Close']),
                "volume": float(row['Volume'])
            })
        output = {"ticker": ticker_symbol, "currentPrice": data_res[1], "priceChange": data_res[2], "history": history_list}
        print("point 5 pass")
        return output
    except Exception as e:
        print(f"Error in get_stock_history: {e}")
        return None

@contextmanager
def get_db_local():
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        print(f"Error in get_db_local: {e}")
    finally:
        db.close()


def get_model_details(ticker_symbol: str):
    """
    Fetch details of the prediction model for the given ticker symbol.
    Args:
        ticker_symbol (str): The stock ticker symbol.
    Returns:
        dict: A dictionary containing model_version, latest_modified_time, and rmse, or None if not found.
    """
    try:
        session = next(get_db())
        try:
            # Query the stock by ticker symbol
            stock = session.query(Stock).filter(Stock.ticker_symbol == ticker_symbol).first()
            if not stock:
                return {"error": f"Stock with ticker symbol '{ticker_symbol}' not found."}

            # Query the prediction model for the stock
            model = (
                session.query(PredictionModel)
                .filter(PredictionModel.target_stock_id == stock.stock_id, PredictionModel.is_active == True)
                .order_by(PredictionModel.latest_modified_time.desc())
                .first()
            )
            if not model:
                return {"error": f"No active prediction model found for stock '{ticker_symbol}'."}

            return {
                # "ticker": ticker_symbol,
                "modelType":"LSTM Neural Network",
                "version": model.model_version,
                "lastUpdated": str(model.latest_modified_time) if model.latest_modified_time else None,
                "maeScore": float(model.rmse) if model.rmse is not None else None,
                "trainedOn": str(model.trained_upto_date) if model.trained_upto_date else None,
                "trainingDataPoints":int(model.data_points)
            }
        finally:
            session.close()
    except Exception as e:
        print(f"Error in get_model_details: {str(e)}")
        return {"error": f"An error occurred while fetching model details: {str(e)}"}


def get_predictions(ticker_symbol,starting_date, ending_date):
    try:
        data = get_stock_history(starting_date,ending_date,st_sym=ticker_symbol)

        history_data = data["history"]
        last_date = history_data[-1]["date"]
        available_date = getlast_date(ticker_symbol)
        print("point 6 pass")
        
        #if (available_date<ending_date)
        with get_db_local() as db:
            # Query the stock by ticker symbol
            stock = db.query(Stock).filter(Stock.ticker_symbol == ticker_symbol).first()
            if not stock:
                print(f"Stock with ticker symbol '{ticker_symbol}' not found.")
                return {"error": f"Stock with ticker symbol '{ticker_symbol}' not found."}

            # Query the prediction model for the stock
            model = db.query(PredictionModel).filter(PredictionModel.target_stock_id == stock.stock_id).first()
            if not model:
                print(f"No prediction model found for stock '{ticker_symbol}'.")
                return {"error": f"No prediction model found for stock '{ticker_symbol}'."}

            # Query predictions from the StockPrediction table

            predictions = (
                db.query(StockPrediction)
                .filter(
                    StockPrediction.model_id == model.model_id,
                    StockPrediction.predicted_date > last_date,
                    StockPrediction.predicted_date <= (datetime.strptime(last_date, "%Y-%m-%d").date() + timedelta(days=7))
                )
                .order_by(StockPrediction.predicted_date.asc())
                .limit(7)  # Fetch a maximum of 7 predictions
                .all())
            print("point 7 pass")
            if len(predictions) < 7:
                # if available_date >= ending_date:
                    try:
                        predict(ticker_symbol, last_date)
                    except Exception as e:
                        return {"error": f"An error occurred while predicting: {str(e)}"}
                    predictions = (
                        db.query(StockPrediction)
                        .filter(
                            StockPrediction.model_id == model.model_id,
                            StockPrediction.predicted_date > last_date,
                            StockPrediction.predicted_date <= (datetime.strptime(last_date, "%Y-%m-%d").date() + timedelta(days=7))
                        )
                        .order_by(StockPrediction.predicted_date.asc())
                        .limit(7)  # Fetch a maximum of 7 predictions
                        .all()
                    )
                    print("point 8 pass")
                # elif(len(predictions)==0):
                #     print(f"Please provide a date by or earlier than {available_date}.")
                #     return {"error": f"Please provide a date by or earlier than {available_date}."}
                    

            # Format the predictions into a list of dictionaries
        prediction_list = []
        prev_val = float(history_data[-1]["price"])
        for i in predictions:
                change = ((float(i.predicted_price)-prev_val)/prev_val)*100
                prev_val = float(i.predicted_price)
                curr = {
                    "date": i.predicted_date,
                    "predicted": float(i.predicted_price),
                    "confidenceLow": float(i.predicted_price)-float(i.confidence_score),
                    "confidenceHigh": float(i.predicted_price)+float(i.confidence_score),
                    "change":change
                }
                prediction_list.append(curr)


        
        modeldata = get_model_details(ticker_symbol=ticker_symbol)
        print("point 9 pass")
        if "error" in modeldata:
            print("point 10 pass")
            return modeldata
        

        return {
            "stockData":{
                "ticker":ticker_symbol,
                "currentPrice": data["currentPrice"],
                "priceChange": data["priceChange"],
                "history":history_data
            },
            "predictionData":{
                "ticker": ticker_symbol,
                "predictions": prediction_list,
                "nextWeek": prediction_list[-1]
            },
            "modelMetadata": modeldata

        }
    except Exception as e:
        print(f"Error in get_predictions: {e}")
        return {"error": f"An error occurred while fetching predictions: {str(e)}"}



