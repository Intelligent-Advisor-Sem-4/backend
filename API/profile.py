from fastapi import APIRouter, HTTPException, status
from classes.profile import Input
from services.portfolio import build_portfolio_response

router = APIRouter(
    prefix="/api/profile",
    tags=["profile"]
)


@router.get("/ping")
def ping():
    return {"msg": "working!"}


@router.post("/optimize_portfolio", status_code=status.HTTP_200_OK)
async def optimize_portfolio(request: Input):
    try:
        return build_portfolio_response(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
