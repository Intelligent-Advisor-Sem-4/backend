from ml_lib.stock_predictor import predict, getStockData
from ml_lib.stock_predictorV2 import predictV2
from models.models import Stock, StockPriceHistorical, AssetStatus,PredictionModel
from db.dbConnect import get_db,SessionLocal
from ml_lib.stock_market_handlerV2 import get_data  # Import the get_data function
from ml_lib.stock_predictor import trainer,predict
import contextlib
@contextlib.contextmanager
def get_local_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



if __name__ == "__main__":
    # with get_local_session() as db:
    #     data = db.query(Stock).all()
    # print(data)
    # for i in data:
    #     stock_id = db.query(Stock.stock_id).filter(Stock.ticker_symbol==i.ticker_symbol).first()
    #     prediction_model = db.query(PredictionModel).filter(PredictionModel.target_stock_id == i.stock_id).first()
    #     if prediction_model:
    #         prediction_model.trained_upto_date = '2025-05-04'
    #         db.commit()
    trainer('META')

