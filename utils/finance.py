import yfinance as yf
import pandas as pd

def fetch_price_data(tickers, start_date, end_date):
    # Add Benchmark ticker to the downloads
    benchmark_ticker = 'SPY'
    all_tickers = tickers + [benchmark_ticker]
    data = yf.download(all_tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=True)
    price_data = pd.DataFrame({ticker: data[ticker]['Close'] for ticker in all_tickers})
    price_data.dropna(inplace=True)
    return price_data