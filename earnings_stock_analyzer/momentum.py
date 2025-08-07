# earnings_stock_analyzer/momentum.py

import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

API_KEY = "Q3KR92l9T0mhIOXwHC40P7YLlQpxWhad"

def fetch_stock_data(ticker):
    stock_data = yf.Ticker(ticker).history(start="1990-01-01", end=datetime.today().strftime('%Y-%m-%d'))
    if stock_data.empty:
        return None
    stock_data.reset_index(inplace=True)
    stock_data["Date"] = pd.to_datetime(stock_data["Date"]).dt.tz_localize(None).dt.normalize()
    return stock_data

def fetch_earnings_dates(ticker):
    url = f"https://financialmodelingprep.com/api/v3/earnings-surprises/{ticker}?limit=1000&apikey={API_KEY}"
    response = requests.get(url)
    earnings_json = response.json()
    if not isinstance(earnings_json, list) or not earnings_json:
        return []
    earnings_df = pd.DataFrame(earnings_json)
    earnings_df['reportedDate'] = pd.to_datetime(earnings_df['date']).dt.normalize()
    return earnings_df['reportedDate'].tolist()

def analyze_momentum(ticker):
    try:
        stock_data = fetch_stock_data(ticker)
        if stock_data is None:
            return None

        earnings_dates = fetch_earnings_dates(ticker)
        if not earnings_dates:
            return None

        total_earnings = 0
        total_momentum = 0
        pos_days = 0
        pos_momentum = 0
        neg_days = 0
        neg_momentum = 0

        for fecha in earnings_dates:
            prev_day = stock_data[stock_data['Date'] <= fecha].iloc[-1:]
            next_day = stock_data[stock_data['Date'] > fecha].iloc[0:1]

            if not prev_day.empty and not next_day.empty:
                prev_close = prev_day['Close'].values[0]
                next_open = next_day['Open'].values[0]
                next_close = next_day['Close'].values[0]

                if pd.notna(next_open) and pd.notna(next_close):
                    c2o = (next_open - prev_close) / prev_close
                    c2c = (next_close - prev_close) / prev_close

                    total_earnings += 1

                    if c2o > 0:
                        pos_days += 1
                        if (c2c - c2o) > 0:
                            pos_momentum += 1
                            total_momentum += 1
                    elif c2o < 0:
                        neg_days += 1
                        if (c2c - c2o) < 0:
                            neg_momentum += 1
                            total_momentum += 1

        if total_earnings == 0:
            return None

        return {
            "ticker": ticker,
            "pct_momentum_total": round(100 * total_momentum / total_earnings, 2),
            "pct_momentum_pos": round(100 * pos_momentum / pos_days, 2) if pos_days else 0,
            "pct_momentum_neg": round(100 * neg_momentum / neg_days, 2) if neg_days else 0
        }

    except Exception:
        return None
