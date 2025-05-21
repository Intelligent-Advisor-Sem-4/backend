import yfinance as yf
import pandas as pd
from pypfopt.expected_returns import mean_historical_return,capm_return
from pypfopt.risk_models import sample_cov
from pypfopt.efficient_frontier import EfficientFrontier
from utils.portfolioconfig import BENCHMARK_TICKER

def fetch_price_data(tickers, start_date, end_date):
    try:
        # Add Benchmark ticker to the downloads
        
        all_tickers = tickers + [BENCHMARK_TICKER]
        data = yf.download(all_tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=True)
        if data.empty:
            raise ValueError("No data was fetched. Please check tickers and date range.")
        price_data = pd.DataFrame({ticker: data[ticker]['Close'] for ticker in all_tickers})
        price_data.dropna(inplace=True)
        if price_data.empty:
            raise ValueError("Fetched data contains only NaN values after processing.")
        return price_data
    except Exception as e:
        raise RuntimeError(f"An error occurred while fetching price data: {e}")

def fetch_tbill_data():

    tnx = yf.Ticker("^TNX")
    
    returns = tnx.history(period="1y")['Close']
    if returns.empty:
        raise ValueError("No data was fetched for the 10-year treasury yield.")
    
    
    return returns

# def get_risk_free_rate():
#     """
#     Fetch the risk-free rate from a reliable source.
#     In this case, we are using the 10-year treasury yield as a proxy.
#     """
#     tnx_data = fetch_tbill_data()
#     if tnx_data.empty:
#         raise ValueError("No data was fetched for the 10-year treasury yield.")
    
#     rate_percent = tnx_data.iloc[-1]
#     risk_free_rate = rate_percent / 100  # Convert to decimal
#     print(f"Risk-free rate (10-year treasury yield): {risk_free_rate:.4f}")
#     return risk_free_rate

# # Get the mu value using the MU_METHOD specified in the config
# def get_mu(price_data, tickers, method=MU_METHOD):

#     # Get the prices for the tickers given as input and exclude the benchmark ticker
#     # This is to ensure that the benchmark ticker is not included in the mu calculation
#     ticker_prices = price_data[tickers]
#     market_prices = price_data[BENCHMARK_TICKER].to_frame(name="mkt")
#     risk_free_rate = get_risk_free_rate()

#     if method == 'historical_yearly_return':
#         return mean_historical_return(ticker_prices)
#     elif method == 'capm':
#         print("capm")
#         return capm_return(ticker_prices,market_prices,risk_free_rate=0.02)
#     else:
#         raise ValueError(f"Unknown MU_METHOD: {method}")


# tickers = ['AAPL', 'MSFT', 'GOOGL']  # Example tickers
# start_date = '2024-01-01'
# end_date = '2025-01-01'
# price_data = fetch_price_data(tickers, start_date, end_date)

# def run_markowitz_optimization(price_data, tickers):
   
#     market_prices = price_data[BENCHMARK_TICKER].to_frame(name="mkt")
#     # print(market_prices)
#     mu = get_mu(price_data, tickers, MU_METHOD)
#     cov = sample_cov(price_data[tickers])
#     ef = EfficientFrontier(mu, cov)
#     weights = ef.max_sharpe()
#     cleaned_weights = ef.clean_weights()
#     perf = ef.portfolio_performance(verbose=False)
#     return cleaned_weights, perf, mu, cov
 


# # fetch_tbill_data()
# # get_risk_free_rate()
# print(run_markowitz_optimization(price_data, tickers))