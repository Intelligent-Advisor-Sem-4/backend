from fastapi import FastAPI, HTTPException,APIRouter
from pydantic import BaseModel
from ml_lib.stock_predictor import predict
from ml_lib.stock_predictorV2 import predictV2
from ml_lib.controllers import get_stock_options,get_stock_history,get_predictions,getPredictedPricesFromDB
from classes.prediction import InData,getstockhist,getpredictprice
app = FastAPI()
router = APIRouter()


# @router.post("/predict")
# async def get_prediction(data: InData):
#     result = predict(data.company, data.date)
#     print('dcdcd',data.company,data.date)
#     if result is None:
#         raise HTTPException(status_code=400, detail="Prediction could not be made. Check the company name or date.")
#     return {"predictions": result}

@router.get("/get-active-symbols")
async def getallsymbols():
    symbols = get_stock_options()
    if not symbols:
        raise HTTPException(status_code=404, detail="No stock symbols found.")
    return {"symbols": symbols}


@router.post("/get-predicted-prices")
async def getpredictedpricesfromDB(data:InData):
    prices = getPredictedPricesFromDB(data.company, data.date)
    if prices is None:
        raise HTTPException(status_code=404, detail="No predicted prices found for this ticker symbol and date.")
    return {"predicted_prices": prices}

# @router.post("/V2/predict")
# async def get_prediction(data: InData):
#     result = predictV2(data.company, data.date)
#     print('dcdcd',data.company,data.date)
#     if result is None:
#         raise HTTPException(status_code=400, detail="Prediction could not be made. Check the company name or date.")
#     return {"predictions": list(result)}

@router.post("/get-stock-history")
async def get_stock_data1(data: getstockhist):
    stock_data = get_stock_history(data.starting_date,data.ending_date,st_sym=data.symbol)
    if not stock_data:
        raise HTTPException(status_code=404, detail="Stock data not found.")
    return stock_data

@router.post("/V2/get-predicted-prices")
async def get_predicted_price(data:getpredictprice):

    result = get_predictions(data.ticker_symbol, data.starting_date, data.ending_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

