from fastapi import FastAPI, HTTPException,APIRouter
from pydantic import BaseModel
from ml_lib.stock_predictor import predict
from ml_lib.pricepredictionretriver import getPredictedPricesFromDB
from ml_lib.stock_predictorV2 import predictV2
from ml_lib.controllers import get_stock_options,get_stock_history
from classes.prediction import InData,getstockhist
app = FastAPI()
router = APIRouter()


@router.post("/predict")
async def get_prediction(data: InData):
    result = predict(data.company, data.date)
    print('dcdcd',data.company,data.date)
    if result is None:
        raise HTTPException(status_code=400, detail="Prediction could not be made. Check the company name or date.")
    return {"predictions": result}

@router.get("/getallsymbols")
async def getallsymbols():
    symbols = get_stock_options()
    if not symbols:
        raise HTTPException(status_code=404, detail="No stock symbols found.")
    return {"symbols": symbols}


@router.get("/getpredictedprices")
async def getpredictedpricesfromDB(ticker_symbol: str, date: str):
    prices = getPredictedPricesFromDB(ticker_symbol, date)
    if prices is None:
        raise HTTPException(status_code=404, detail="No predicted prices found for this ticker symbol and date.")
    return {"predicted_prices": prices}

@router.post("/V2/predict")
async def get_prediction(data: InData):
    result = predictV2(data.company, data.date)
    print('dcdcd',data.company,data.date)
    if result is None:
        raise HTTPException(status_code=400, detail="Prediction could not be made. Check the company name or date.")
    return {"predictions": list(result)}

@router.post("/getstockdata")
async def get_stock_data1(data: getstockhist):
    stock_data = get_stock_history(data.startingdate,data.endingdate,st_sym=data.symbol)
    if not stock_data:
        raise HTTPException(status_code=404, detail="Stock data not found.")
    return stock_data