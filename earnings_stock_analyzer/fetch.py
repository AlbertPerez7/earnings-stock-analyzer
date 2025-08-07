import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

def fetch_stock_data(ticker):
    """
    Downloads historical stock data from Yahoo Finance for the given ticker.

    Args:
        ticker (str): Stock ticker symbol (e.g., "AAPL").

    Returns:
        pd.DataFrame: DataFrame with historical stock data and derived columns.
    """
    print(f"Fetching stock data for {ticker.upper()}...")
    start_date = '1700-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')

    data = yf.Ticker(ticker).history(start=start_date, end=end_date)
    if data.empty:
        raise ValueError("No stock data found.")

    data['Percent Change'] = data['Close'].pct_change() * 100
    data['Next_Open'] = data['Open'].shift(-1)
    data['Next_Close'] = data['Close'].shift(-1)
    data.reset_index(inplace=True)
    data['Date'] = pd.to_datetime(data['Date'], utc=True).dt.tz_convert(None).dt.normalize()
    data.sort_values(by='Date', inplace=True)

    return data


def fetch_earnings_dates(ticker, api_key, min_age_days=120):
    """
    Fetches historical earnings dates from Alpha Vantage.

    Args:
        ticker (str): Stock ticker symbol.
        api_key (str): Alpha Vantage API key.
        min_age_days (int): Minimum number of days old the earnings should be.

    Returns:
        list of pd.Timestamp: List of earnings dates that are old enough.
    """
    print("Fetching earnings data...")
    earnings_url = f'https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={api_key}'
    response = requests.get(earnings_url)
    earnings_data = response.json()

    if 'quarterlyEarnings' not in earnings_data:
        raise ValueError("No earnings data found.")

    earnings_df = pd.DataFrame(earnings_data['quarterlyEarnings'])
    earnings_df['reportedDate'] = pd.to_datetime(earnings_df['reportedDate'])
    today = datetime.now().date()

    earnings_dates = [
        d.normalize() for d in earnings_df['reportedDate']
        if (today - d.date()).days >= min_age_days
    ]

    print("Earnings data downloaded successfully.")
    return earnings_dates
