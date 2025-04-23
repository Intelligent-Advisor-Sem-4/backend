import numpy as np
from pypfopt.expected_returns import mean_historical_return,capm_return
from pypfopt.risk_models import sample_cov
from pypfopt.efficient_frontier import EfficientFrontier
from utils.finance import fetch_price_data
from classes.profile import Input


def run_markowitz_optimization(price_data, tickers):
    # Changed to use CAPM instead of mean historical return
    # with "SPY" as the benchmark ticker
    benchmark_ticker = 'SPY'
    prices = price_data[tickers]
    market_prices = price_data['SPY']
    # mu = mean_historical_return(price_data)
    mu = capm_return(prices, market_prices, risk_free_rate=0.02)
    cov = sample_cov(prices)
    ef = EfficientFrontier(mu, cov)
    weights = ef.max_sharpe()
    cleaned_weights = ef.clean_weights()
    perf = ef.portfolio_performance(verbose=False)
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
    price_data = fetch_price_data(request.tickers, request.start_date, request.end_date)

    weights, (exp_return, volatility, sharpe), mu, cov = run_markowitz_optimization(price_data, request.tickers)

    monte_carlo_result = simulate_monte_carlo_for_weights(
        mu, cov, weights,
        request.investment_amount, request.target_amount,
        request.years
    )

    return {
        "optimal_weights": {k: round(v, 4) for k, v in weights.items()},
        "expected_return": round(exp_return, 4),
        "volatility": round(volatility, 4),
        "sharpe_ratio": round(sharpe, 4),
        "goal": f"${request.investment_amount:,.2f} → ${request.target_amount:,.2f} in {request.years} year(s)",
        "monte_carlo_projection": monte_carlo_result
    }
