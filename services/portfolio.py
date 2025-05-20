import numpy as np
import copy
import pandas as pd
from fastapi import HTTPException,status
from pypfopt.expected_returns import mean_historical_return,capm_return,ema_historical_return
from pypfopt.risk_models import sample_cov
from pypfopt.efficient_frontier import EfficientFrontier
from utils.finance import fetch_price_data, fetch_tbill_data
from utils.portfolioconfig import MU_METHOD, BENCHMARK_TICKER,RISK_FREE_RATE,NUMBER_OF_SIMULATIONS
from classes.profile import Input


def get_risk_free_rate():
    """
    Fetch the risk-free rate from a reliable source.
    In this case, we are using the 10-year treasury yield as a proxy.
    """
    tnx_data = fetch_tbill_data()
    if tnx_data.empty:
        raise ValueError("No data was fetched for the 10-year treasury yield.")
    
    rate_percent = tnx_data.iloc[-1]
    risk_free_rate = rate_percent / 100  # Convert to decimal
    return risk_free_rate

# Get the mu value using the MU_METHOD specified in the config
def get_mu(price_data, tickers, method=MU_METHOD):

    # Get the prices for the tickers given as input and exclude the benchmark ticker
    # This is to ensure that the benchmark ticker is not included in the mu calculation
    ticker_prices = price_data[tickers]
    market_prices = price_data[BENCHMARK_TICKER].to_frame(name="mkt")
    risk_free_rate = get_risk_free_rate()

    if method == 'historical_yearly_return':
        return mean_historical_return(ticker_prices)

    elif method == 'capm':
        return capm_return(ticker_prices,market_prices,risk_free_rate=RISK_FREE_RATE)
    else:
        raise ValueError(f"Unknown MU_METHOD: {method}")



def run_markowitz_optimization(price_data, tickers, risk_free_rate=0.02):
    
    # Fetch the price data for the tickers given as input and exclude the benchmark ticker
    prices = price_data[tickers]
    
    mu = get_mu(price_data, tickers, MU_METHOD)
    cov = sample_cov(prices)
    ef = EfficientFrontier(mu, cov)
    weights = ef.max_sharpe()
    cleaned_weights = ef.clean_weights()
    perf = ef.portfolio_performance(verbose=False)
    return cleaned_weights, perf, mu, cov


def run_custom_risk_optimization(price_data, tickers, risk_score_percent):

    prices = price_data[tickers]
    mu = get_mu(price_data, tickers, MU_METHOD)
    cov = sample_cov(prices)

    ef = EfficientFrontier(mu, cov)

    ef_clone = copy.deepcopy(ef)

    # Compute min volatility
    ef.min_volatility()
    _, min_vol, _ = ef.portfolio_performance()

    # Compute max volatility using max Sharpe
    ef_clone.max_sharpe()
    _, max_vol, _ = ef_clone.portfolio_performance()
    #max_vol = max(np.std(price_data[ticker].pct_change().dropna()) * np.sqrt(252) for ticker in tickers)


    # Dynamically map user's risk score to volatility
    target_volatility = min_vol + (risk_score_percent / 100) * (max_vol - min_vol)

    # Safety check: ensure the volatility is still feasible
    if target_volatility < min_vol or target_volatility > max_vol:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Target volatility {target_volatility:.3f} is outside feasible range ({min_vol:.3f} - {max_vol:.3f})"
        )

    ef_final = EfficientFrontier(mu, cov)
    ef_final.efficient_risk(target_volatility)

    cleaned_weights = ef_final.clean_weights()
    perf = ef_final.portfolio_performance(verbose=False, risk_free_rate=RISK_FREE_RATE)

    return cleaned_weights, perf, mu, cov


def simulate_monte_carlo_for_weights(mu, cov, weights_dict, investment_amount, target_amount, years, num_simulations=10000):
    tickers = list(weights_dict.keys())
    weights = np.array([weights_dict[t] for t in tickers])
    mu_values = mu[tickers].values
    cov_matrix = cov.loc[tickers, tickers].values

    port_return = np.dot(weights, mu_values)
    port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

    results = []
    successes = 0

    for _ in range(num_simulations):
        simulated_return = np.random.normal(port_return, port_volatility)
        projected_value = investment_amount * ((1 + simulated_return) ** years)
        results.append(projected_value)
        if projected_value >= target_amount:
            successes += 1

    return {
        "expected_final_value": round(float(np.mean(results)), 2),
        "min_final_value": round(float(np.min(results)), 2),
        "max_final_value": round(float(np.max(results)), 2),
        "success_rate_percent": round((successes / num_simulations) * 100, 2)
    }


def build_portfolio_response(request: Input):
    all_tickers = request.tickers + ["SPY"]

    price_data = fetch_price_data(all_tickers, request.start_date, request.end_date)
    
    if request.use_risk_score and request.risk_score_percent is not None:
        weights, (exp_return, volatility, sharpe), mu, cov = run_custom_risk_optimization(
            price_data, request.tickers, request.risk_score_percent
        )
        method_used = f"Custom Risk Level ({request.risk_score_percent:.1f}%)"
    else:
        # Default: maximize Sharpe ratio
        weights, (exp_return, volatility, sharpe), mu, cov = run_markowitz_optimization(
            price_data, request.tickers
        )
        method_used = "Max Sharpe Ratio"

    monte_carlo_result = simulate_monte_carlo_for_weights(
        mu, cov, weights,
        request.investment_amount, request.target_amount,
        request.years,
        num_simulations=NUMBER_OF_SIMULATIONS
    )

    return {
        "method_used": method_used,  # NEW: indicates chosen method clearly
        "optimal_weights": {k: round(v, 4) for k, v in weights.items()},
        "expected_return": round(exp_return, 4),
        "volatility": round(volatility, 4),
        "sharpe_ratio": round(sharpe, 4),
        "goal": f"${request.investment_amount:,.2f} → ${request.target_amount:,.2f} in {request.years} year(s)",
        "monte_carlo_projection": monte_carlo_result
    }


