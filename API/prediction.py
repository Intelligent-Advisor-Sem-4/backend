from fastapi import FastAPI, HTTPException,APIRouter
from pydantic import BaseModel
from ml_lib.stock_predictor import predict
from ml_lib.controllers import get_stock_options
from classes.prediction import InData
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
