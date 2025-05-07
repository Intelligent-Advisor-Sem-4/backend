from ml_lib.stock_predictor import predict, getStockData
from ml_lib.stock_predictorV2 import predictV2
from models.models import Stock, StockPriceHistorical, AssetStatus
from db.dbConnect import get_db
from ml_lib.stock_market_handlerV2 import get_data  # Import the get_data function

def compare_inputs():
    ticker = "AOS"
    date = "2024-03-21"
    input_dim = 90

    # Fetch 90-day input data for predict
    stock_data_predict = getStockData(ticker, date, input_dim)['Close']

    # Fetch 90-day input data for predictV2 using get_data
    stock_data_predictV2 = get_data(ticker, date, input_dim)

    # Print the input data side by side
    print("Input data for predict:")
    print(stock_data_predict)
    print("\nInput data for predictV2:")
    for i in stock_data_predictV2:
        print(f"Date: {i.price_date}, Close Price: {i.close_price}")

if __name__ == "__main__":
    compare_inputs()