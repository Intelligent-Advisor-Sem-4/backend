from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.concurrency import run_in_threadpool
import pandas as pd
from pydantic import BaseModel
from ml_lib.stock_predictor import getStockData, predict,trainer
from ml_lib.stock_predictorV2 import predictV2
from ml_lib.controllers import get_stock_options, get_stock_history, get_predictions, getPredictedPricesFromDB, get_model_details
from classes.prediction import InData, getstockhist, getpredictprice, ModelDetails,trainrequestdata

app = FastAPI()
router = APIRouter()

# @router.post("/train_model")
# async def trainsymbol(data:trainrequestdata):
#     try:
#         background_tasks.add_task(trainer, data.ticker_symbol)
#         return {"message": f"Model training initiated for {data.ticker_symbol}"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        


@router.get("/get-active-symbols")
async def getallsymbols():
    try:
        symbols = get_stock_options()
        if not symbols:
            raise HTTPException(status_code=404, detail="No stock symbols found.")
        return {"symbols": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching active symbols: {str(e)}")

@router.post("/get-forward-prices")
async def get_stock_data2(data: getstockhist):
    try:
        data_res = getStockData(company=data.symbol, starting_date=data.starting_date, size=7, size_dir=1)
        if not data_res:
            raise HTTPException(status_code=404, detail="Stock data not found.")
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
        output = {"ticker": data_res[3], "currentPrice": data_res[1], "priceChange": data_res[2], "history": history_list}
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching forward prices: {str(e)}")

@router.post("/get-predicted-prices")
async def getpredictedpricesfromDB(data: InData):
    try:
        prices = getPredictedPricesFromDB(data.company, data.date)
        if prices is None:
            raise HTTPException(status_code=404, detail="No predicted prices found for this ticker symbol and date.")
        return {"predicted_prices": prices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching predicted prices: {str(e)}")

@router.post("/get-stock-history")
async def get_stock_data1(data: getstockhist):
    try:
        stock_data = get_stock_history(data.starting_date, data.ending_date, st_sym=data.symbol)
        if not stock_data:
            raise HTTPException(status_code=404, detail="Stock data not found.")
        return stock_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock history: {str(e)}")

@router.post("/V2/get-predicted-prices")
async def get_predicted_price(data: getpredictprice):
    try:
        result = get_predictions(data.ticker_symbol, data.starting_date, data.ending_date)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching predicted prices (V2): {str(e)}")

@router.post("/get_model_details")
async def get_model_detail(data: ModelDetails):
    try:
        result = get_model_details(data.ticker)
        if result is None:
            raise HTTPException(status_code=404, detail="Model details not found for the given ticker symbol.")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching model details: {str(e)}")

