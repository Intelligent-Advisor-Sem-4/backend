from fastapi import  APIRouter,HTTPException,Depends,status
from classes.portfolio import Profile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from pypfopt.expected_returns import mean_historical_return
from pypfopt.risk_models import sample_cov

router = APIRouter(
    prefix='/api/profile',
    tags=['profile']
)


@router.get("/test")
def test():
    return {'message': 'Hello World'}



@router.post("/optimize_portfolio",status_code=status.HTTP_200_OK)
async def optimize_portfolio(request:Profile):


    try:
        # Step 1: Get stock data
        data = yf.download(request.tickers, start=request.start_date, end=request.end_date, group_by='ticker', auto_adjust=True)
        price_data = pd.DataFrame({ticker: data[ticker]['Close'] for ticker in request.tickers})
        price_data.dropna(inplace=True)

        # Step 2: Calculate expected returns and covariances
        mu = mean_historical_return(price_data)
        cov = sample_cov(price_data)
        mu_values = mu.values
        cov_matrix = cov.values

        results = np.zeros((3, request.num_portfolios))
        weights_record = []
        num_successes = 0

        for _ in range(request.num_portfolios):
            weights = np.random.random(len(request.tickers))
            weights /= np.sum(weights)
            weights_record.append(weights)

            port_return = np.dot(weights, mu_values)
            port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe_ratio = port_return / port_volatility

            results[0, _] = port_return
            results[1, _] = port_volatility
            results[2, _] = sharpe_ratio

            projected_value = request.investment_amount * ((1 + port_return) ** request.years)
            if projected_value >= request.target_amount:
                num_successes += 1

        max_sharpe_idx = np.argmax(results[2])
        optimal_weights = weights_record[max_sharpe_idx]

        response = {
            "optimal_weights": {request.tickers[i]: round(float(optimal_weights[i]), 4) for i in range(len(request.tickers))},
            "expected_return": round(float(results[0, max_sharpe_idx]), 4),
            "volatility": round(float(results[1, max_sharpe_idx]), 4),
            "sharpe_ratio": round(float(results[2, max_sharpe_idx]), 4),
            "success_rate_percent": round(num_successes / request.num_portfolios * 100, 2),
            "goal": f"${request.investment_amount:,.2f} → ${request.target_amount:,.2f} in {request.years} year(s)"
        }

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return response