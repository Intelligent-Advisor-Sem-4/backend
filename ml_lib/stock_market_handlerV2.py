import yfinance as yf
import requests
import pandas as pd
from db.dbConnect import get_db,SessionLocal
from models.models import Stock, StockPriceHistorical, AssetStatus,PredictionModel,StockPrediction
from classes.prediction import StockPriceHistoricalType
from datetime import datetime
from contextlib import contextmanager

def get_all_available_companies():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    response = requests.get(url)
    if response.status_code == 200:
        data = pd.read_csv(url)
        print("Available columns in the dataset:", data.columns)
        return data['Symbol'].tolist()
    else:
        print("Failed to fetch company data.")
        return []

def get_past_history(company, date=None, size=None, begin_date=None):
    res = yf.Ticker(company)
    data = res.history(period='max')

    if begin_date is not None:
        begin_date = pd.to_datetime(begin_date).tz_localize(data.index.tz)
        data = data[data.index > begin_date]
    if date is not None:
        date = pd.to_datetime(date).tz_localize(data.index.tz)
        data = data[data.index <= date]
    if size is not None:
        li = min(size, len(data))
        data = data[len(data) - li:len(data)]

    return data

def get_data(company, date=None, size=None) -> list[StockPriceHistoricalType] | None:
    db = next(get_db())
    stock_data = db.query(Stock.stock_id, Stock.last_data_point_date).filter(Stock.ticker_symbol == company).first()
    if not stock_data:
        addcompany(company)
        stock_data = db.query(Stock.stock_id, Stock.last_data_point_date).filter(Stock.ticker_symbol == company).first()
    stock_id, last_date = stock_data
    if stock_id is None:
        return None

    if date is None and last_date is not None:
        start_date = last_date
        new_data = get_past_history(company=company, begin_date=start_date)

        if new_data is not None and not new_data.empty:
            for ts_index, row in new_data.iterrows():
                stock_price = StockPriceHistorical(
                    stock_id=stock_id,
                    price_date=ts_index.to_pydatetime().date(),
                    open_price=float(row['Open']) if row['Open'] else None,
                    high_price=float(row['High']) if row['High'] else None,
                    low_price=float(row['Low']) if row['Low'] else None,
                    close_price=float(row['Close']) if row['Close'] else None,
                    volume=int(row['Volume']) if row['Volume'] else None
                )
                db.add(stock_price)
            db.commit()

            last_data_entry = new_data.index.max().date()  # Store only the date
            db.query(Stock).filter(Stock.stock_id == stock_id).update(
                {"last_data_point_date": last_data_entry}
            )
            db.commit()

            print(f"Added data for {company} from {start_date} to the latest date.")
        else:
            print(f"No new data available for {company} from {start_date} to the latest date.")

    elif date is not None and last_date is None:
        new_data = get_past_history(company=company, date=date)

        if new_data is not None and not new_data.empty:
            for ts_index, row in new_data.iterrows():
                stock_price = StockPriceHistorical(
                    stock_id=stock_id,
                    price_date=ts_index.to_pydatetime().date(),  # Store only the date
                    open_price=float(row['Open']) if row['Open'] else None,
                    high_price=float(row['High']) if row['High'] else None,
                    low_price=float(row['Low']) if row['Low'] else None,
                    close_price=float(row['Close']) if row['Close'] else None,
                    volume=int(row['Volume']) if row['Volume'] else None
                )
                db.add(stock_price)
            db.commit()

            last_data_entry = new_data.index.max().date()  # Store only the date
            db.query(Stock).filter(Stock.stock_id == stock_id).update(
                {"last_data_point_date": last_data_entry}
            )
            db.commit()

            print(f"Added data for {company} up to {date}.")
        else:
            print(f"No data available for {company} up to {date}.")

    elif date is None and last_date is None:
        new_data = get_past_history(company=company)

        if new_data is not None and not new_data.empty:
            for ts_index, row in new_data.iterrows():
                stock_price = StockPriceHistorical(
                    stock_id=stock_id,
                    price_date=ts_index.to_pydatetime().date(),  # Store only the date
                    open_price=float(row['Open']) if row['Open'] else None,
                    high_price=float(row['High']) if row['High'] else None,
                    low_price=float(row['Low']) if row['Low'] else None,
                    close_price=float(row['Close']) if row['Close'] else None,
                    volume=int(row['Volume']) if row['Volume'] else None
                )
                db.add(stock_price)
            db.commit()

            last_data_entry = new_data.index.max().date()  # Store only the date
            db.query(Stock).filter(Stock.stock_id == stock_id).update(
                {"last_data_point_date": last_data_entry}
            )
            db.commit()

            print(f"Added all historical data for {company}.")
        else:
            print(f"No data available for {company}.")

    elif date is not None and last_date is not None and pd.to_datetime(date).date() > last_date:
        start_date = last_date
        new_data = get_past_history(company=company, date=date, begin_date=start_date)

        if new_data is not None and not new_data.empty:
            for ts_index, row in new_data.iterrows():
                stock_price = StockPriceHistorical(
                    stock_id=stock_id,
                    price_date=ts_index.to_pydatetime().date(),  # Store only the date
                    open_price=float(row['Open']) if row['Open'] else None,
                    high_price=float(row['High']) if row['High'] else None,
                    low_price=float(row['Low']) if row['Low'] else None,
                    close_price=float(row['Close']) if row['Close'] else None,
                    volume=int(row['Volume']) if row['Volume'] else None
                )
                db.add(stock_price)
            db.commit()

            last_data_entry = new_data.index.max().date()  # Store only the date
            db.query(Stock).filter(Stock.stock_id == stock_id).update(
                {"last_data_point_date": last_data_entry}
            )
            db.commit()

            print(f"Updated data for {company} from {start_date} to {date}.")
        else:
            print(f"No new data available for {company} from {start_date} to {date}.")

    query = db.query(StockPriceHistorical).filter(
        StockPriceHistorical.stock_id == stock_id
    )

    if date:
        query = query.filter(StockPriceHistorical.price_date <= pd.to_datetime(date).date())

    query = query.order_by(StockPriceHistorical.price_date.desc())

    if size:
        historical_data = query.limit(size).all()
    else:
        historical_data = query.all()
    return historical_data[::-1]


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def addcompany(company,db=None):
        existing_stock = db.query(Stock).filter(Stock.ticker_symbol == company).first()
        if existing_stock:
            print(f"{company} already exists in the database.")
            return existing_stock

        company_name = yf.Ticker(company).info.get('longName', 'Unknown Company')
        stock = Stock(
            ticker_symbol=company,
            asset_name=company_name,
            type="STOCK",
            status=AssetStatus.PENDING,
            first_data_point_date=None,
            last_data_point_date=None
        )
        db.add(stock)
        db.commit()
        return stock


def model_regiterer(stock_symbol, time_step, rmse, model_location, scaler_location,last_date):
    with get_db_context() as db:
        stock = addcompany(stock_symbol,db)
        existing_model = db.query(PredictionModel).filter(PredictionModel.target_stock_id == stock.stock_id).first()

        if existing_model:
            existing_model.latest_modified_time = datetime.utcnow()
            existing_model.trained_upto_date = last_date
            db.commit()
            print(f"Updated last_modified_time for model {existing_model.model_id}.")
            return  existing_model
        else:
            model = PredictionModel(
                model_version="v1",
                target_stock_id=stock.stock_id,
                latest_modified_time=datetime.utcnow(),
                time_step=time_step,
                rmse=rmse,
                is_active=True,
                model_location=model_location,
                scaler_location=scaler_location,
                trained_upto_date=last_date
            )
            db.add(model)
            db.commit()
            if stock.status == AssetStatus.PENDING:
                db.query(Stock).filter(Stock.stock_id == stock.stock_id).update({"status": AssetStatus.ACTIVE})
                db.commit()
            print(f"Created a new model for stock {stock_symbol} with model_id {model.model_id}.")
            return model
        
def store_prediction(model_id,last_actual_date,predicted_date,predicted_price):
    with get_db_context() as db:
        existing_prediction = db.query(StockPrediction).filter(StockPrediction.model_id==model_id,StockPrediction.predicted_date == predicted_date).first()

        if existing_prediction != None:
            time_delta_existing = (pd.to_datetime(existing_prediction.predicted_date) - pd.to_datetime(existing_prediction.last_actual_data_date)).days
            time_delta_new = (pd.to_datetime(predicted_date) - pd.to_datetime(last_actual_date)).days

            if time_delta_new < time_delta_existing:
                existing_prediction.last_actual_data_date = last_actual_date
                existing_prediction.predicted_date = predicted_date
                existing_prediction.predicted_price = predicted_price
                existing_prediction.prediction_generated_at = datetime.utcnow()
                db.commit()
                print(f"Updated existing prediction for model_id {model_id} with new values.")
            else:
                print(f"Skipped updating prediction for model_id {model_id} as the new time delta is not greater.")
        else:
            pred = StockPrediction(
                last_actual_data_date = last_actual_date,
                predicted_date = predicted_date,
                predicted_price = predicted_price,
                prediction_generated_at = datetime.utcnow(),
                model_id=model_id
                
            )

            db.add(pred)
            db.commit()



def get_model_details(stock_symbol):
    db = next(get_db())
    stockid = db.query(Stock).filter(Stock.ticker_symbol == stock_symbol).first()
    if stockid == None:
        return None
    else:
        model = db.query(PredictionModel).filter(PredictionModel.target_stock_id == stockid.stock_id).first()
        if model!= None:
            return model
        else:
            return None


# def invoke_prediction(symbol,date):
