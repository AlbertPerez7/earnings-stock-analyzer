import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime

API_KEY = "YOUR_ALPHA_VANTAGE_API_KEY"  # Replace with your actual Alpha Vantage API key

# Load tickers from CSV
tickers_df = pd.read_csv("../data/most_volatile_stocks.csv")
tickers_df.columns = tickers_df.columns.str.strip().str.lower()
tickers = tickers_df.iloc[:, 0].dropna().unique().tolist()

results = []

def analyze_average_abs_c2o(ticker):
    try:
        print(f"Analyzing {ticker}...")
        stock_data = yf.Ticker(ticker).history(start="1990-01-01", end=datetime.today().strftime('%Y-%m-%d'))
        if stock_data.empty:
            return None

        stock_data.reset_index(inplace=True)
        stock_data["Date"] = pd.to_datetime(stock_data["Date"]).dt.tz_localize(None).dt.normalize()

        # Fetch earnings data from Alpha Vantage
        url = f"https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={API_KEY}"
        response = requests.get(url)
        earnings_json = response.json()
        if 'quarterlyEarnings' not in earnings_json:
            return None

        earnings_df = pd.DataFrame(earnings_json['quarterlyEarnings'])
        earnings_df['reportedDate'] = pd.to_datetime(earnings_df['reportedDate']).dt.normalize()

        earnings_dates = [
            d for d in earnings_df['reportedDate']
            if (datetime.now().date() - d.date()).days >= 120
        ]

        abs_c2o_changes = []
        for date in earnings_dates:
            prev_day = stock_data[stock_data["Date"] <= date].iloc[-1:]
            next_day = stock_data[stock_data["Date"] > date].iloc[0:1]

            if not prev_day.empty and not next_day.empty:
                close = prev_day["Close"].values[0]
                next_open = next_day["Open"].values[0]

                if pd.notna(close) and pd.notna(next_open):
                    c2o = abs((next_open - close) / close * 100)
                    abs_c2o_changes.append(c2o)

        if not abs_c2o_changes:
            return None

        avg_abs_c2o = sum(abs_c2o_changes) / len(abs_c2o_changes)
        return {"ticker": ticker, "avg_abs_c2o": round(avg_abs_c2o, 2)}

    except Exception as e:
        print(f"Error with {ticker}: {e}")
        return None

# Analyze only the first 25 tickers
for i, ticker in enumerate(tickers[:25], 1):
    result = analyze_average_abs_c2o(ticker)
    if result:
        results.append(result)
    print(f"Done ({i}/{min(len(tickers), 25)})")
    time.sleep(1.5)

# Rank and save top 10 results to CSV
df = pd.DataFrame(results)
df_sorted = df.sort_values(by="avg_abs_c2o", ascending=False).head(10)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
csv_output = f"top10_abs_change_{timestamp}.csv"
df_sorted.to_csv(csv_output, index=False)

print(f"CSV file saved as: {csv_output}")
