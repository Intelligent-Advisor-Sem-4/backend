import yfinance as yf
import pandas as pd


def fetch_price_data(tickers, start_date, end_date):
    try:
        # Add Benchmark ticker to the downloads
        benchmark_ticker = 'SPY'
        all_tickers = tickers + [benchmark_ticker]
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
