from ml_lib.stock_predictor import predict, getStockData
from ml_lib.stock_predictorV2 import predictV2
from models.models import Stock, StockPriceHistorical, AssetStatus,PredictionModel
from db.dbConnect import get_db,SessionLocal
from ml_lib.stock_market_handlerV2 import get_data  # Import the get_data function
from ml_lib.stock_predictor import trainer,predict,getStockData
import contextlib
@contextlib.contextmanager
def get_local_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



if __name__ == "__main__":
    with get_local_session() as db:
        data = db.query(Stock).all()
    for i in data:
        trainer(i.ticker_symbol)
# predict('V','2025-04-21')


