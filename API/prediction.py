from fastapi import FastAPI, HTTPException,APIRouter
from pydantic import BaseModel
from ml_lib.stock_predictor import predict
from ml_lib.stock_predictorV2 import predictV2
from ml_lib.controllers import get_stock_options,get_stock_history,get_predictions
from classes.prediction import InData,getstockhist,getpredictprice
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

@router.post("/getpredictions")
async def get_predicted_price(data:getpredictprice):
    """
    Fetch predicted prices for a given stock ticker symbol and date range.

    Args:
        ticker_symbol: The stock ticker symbol.
        starting_date: The starting date for historical data.
        ending_date: The ending date for historical data.

    Returns:
        A dictionary containing historical data and predictions.

    Raises:
        HTTPException: If no predictions or stock data are found.
    """
    result = get_predictions(data.ticker_symbol, data.starting_date, data.ending_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

