from typing import List, Dict
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from stocks_earnings_dates import get_earnings_price_reactions

API_KEY = "YOUR_API_KEY"

def get_earnings_data(ticker: str, source: str = "library") -> List[Dict]:
    """
    Get earnings data either from the local library or from Alpha Vantage API.
    """
    if source == "library":
        return get_earnings_price_reactions(ticker)

    elif source == "api":
        url = f"https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={API_KEY}"
        resp = requests.get(url).json()
        if "quarterlyEarnings" not in resp:
            return []

        earnings_dates = pd.to_datetime(
            [d["reportedDate"] for d in resp["quarterlyEarnings"]]
        )

        # Filtrar mínim 1 dia vell
        today = datetime.now().date()
        earnings_dates = [
            d.normalize() for d in earnings_dates if (today - d.date()).days >= 1
        ]

        if not earnings_dates:
            return []

        # Ara cal obtenir preus de Yahoo per calcular % com fa la llibreria
        data = yf.Ticker(ticker).history(
            start=min(earnings_dates) - pd.Timedelta(days=2),
            end=max(earnings_dates) + pd.Timedelta(days=3),
        )
        if data.empty:
            return []

        data.index = data.index.tz_localize(None)
        data["Next_Open"] = data["Open"].shift(-1)
        data["Next_Close"] = data["Close"].shift(-1)
        data.reset_index(inplace=True)
        data["Date"] = pd.to_datetime(data["Date"]).dt.normalize()

        results = []
        for date in earnings_dates:
            row = data[data["Date"] == date]
            if not row.empty:
                close = row["Close"].values[0]
                next_open = row["Next_Open"].values[0]
                next_close = row["Next_Close"].values[0]
                if pd.notna(next_open) and pd.notna(next_close):
                    results.append({
                        "date": date.date().isoformat(),
                        "close_to_open_pct": round((next_open - close) / close * 100, 2),
                        "close_to_close_pct": round((next_close - close) / close * 100, 2),
                        "open_to_close_pct": round((next_close - next_open) / next_open * 100, 2)
                    })

        return results

    else:
        raise ValueError(f"Unknown source: {source}")
