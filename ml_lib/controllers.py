from sqlalchemy.orm import Session
from db.dbConnect import get_db,SessionLocal
from models.models import Stock, AssetStatus, PredictionModel, StockPrediction
import yfinance as yf
import requests
import pandas as pd
from ml_lib.stock_predictor import getStockData,getStockDataV2
from contextlib import contextmanager

def get_stock_options() -> list[dict]:
    db = next(get_db())
    stocks = db.query(Stock).filter(Stock.status == AssetStatus.ACTIVE).all()
    return [{"value": stock.ticker_symbol, "label": stock.asset_name} for stock in stocks]

def get_stock_history(s_date, e_date, st_id=None, st_sym=None):
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

    data_res = getStockDataV2(company=ticker_symbol, starting_date=s_date, ending_date=e_date)
    data = data_res[0]

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
    return output

@contextmanager
def get_db_local():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_predictions(ticker_symbol,starting_date, ending_date):
    history_data = get_stock_history(starting_date,ending_date,st_sym=ticker_symbol)["history"]
    last_date = history_data[-1]["date"]
    with get_db_local() as db:
        # Query the stock by ticker symbol
        stock = db.query(Stock).filter(Stock.ticker_symbol == ticker_symbol).first()
        if not stock:
            return {"error": f"Stock with ticker symbol '{ticker_symbol}' not found."}

        # Query the prediction model for the stock
        model = db.query(PredictionModel).filter(PredictionModel.target_stock_id == stock.stock_id).first()
        if not model:
            return {"error": f"No prediction model found for stock '{ticker_symbol}'."}

        # Query predictions from the StockPrediction table
        predictions = (
            db.query(StockPrediction)
            .filter(
                StockPrediction.model_id == model.model_id,
                StockPrediction.predicted_date > last_date
            )
            .order_by(StockPrediction.predicted_date.asc())
            .limit(7)  # Fetch a maximum of 7 predictions
            .all()
        )

        # Format the predictions into a list of dictionaries
    
    prediction_list = [
            {
                "date": prediction.predicted_date,
                "predicted": float(prediction.predicted_price)
            }
            for prediction in predictions
    ]

    return {
            "ticker_symbol": ticker_symbol,
            "model_id": model.model_id,
            "predictions": prediction_list,
            "history":history_data
    }


# def get_all_available_companies() -> list[str]:
#     """
#     Fetch all available companies' ticker symbols from a public dataset.
#     """
#     url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
#     response = requests.get(url)
#     if response.status_code == 200:
#         data = pd.read_csv(url)
#         print("Available columns in the dataset:", data.columns)
#         return data['Symbol'].tolist()
#     else:
#         print("Failed to fetch company data.")
#         return []
    


# def addcompany(company: str) -> None:
#     """
#     Add a company to the database if it doesn't already exist.
#     """
#     db = next(get_db())
#     existing_stock = db.query(Stock).filter(Stock.ticker_symbol == company).first()
#     if existing_stock:
#         print(f"{company} already exists in the database.")
#         return

#     try:
#         company_name = yf.Ticker(company).info.get('longName', 'Unknown Company')
#         stock = Stock(
#             ticker_symbol=company,
#             asset_name=company_name,
#             type='STOCK',
#             status=AssetStatus.PENDING,
#             first_data_point_date=None,
#             last_data_point_date=None
#         )
#         db.add(stock)
#         db.commit()
#     except Exception as e:
#         print(f"Failed to fetch or store data for ticker '{company}': {e}")

# def fetch_and_store_ticker_details() -> None:
#     """
#     Fetch details for all available ticker symbols and store them in the Stock model.
#     """
#     ticker_symbols = get_all_available_companies()
#     for ticker in ticker_symbols:
#         addcompany(ticker)




if __name__ == "__main__":
    #fetch_and_store_ticker_details()
    print(get_stock_history(1,"2021-10-21","2022-04-12"))
    None
