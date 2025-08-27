from typing import Dict
from earnings_stock_analyzer.fetch import get_earnings_data  # ✅ use unified fetch

def analyze_momentum(ticker: str, source: str = "library") -> Dict:
    """
    Analitza el momentum després d'earnings.
    Pot utilitzar 'library' (SQLite/yfinance) o 'api' (Alpha Vantage).
    """

    # Get earnings reactions from chosen source
    reactions = get_earnings_data(ticker, source=source)
    if not reactions:
        return {}

    total = len(reactions)
    pos_days = 0
    neg_days = 0
    pos_momentum = 0
    neg_momentum = 0
    total_momentum = 0

    momentum_dates_total = []
    momentum_dates_pos = []
    momentum_dates_neg = []

    for r in reactions:
        c2o = r["close_to_open_pct"]
        c2c = r["close_to_close_pct"]
        o2c = r["open_to_close_pct"]
        date = r["date"]

        if c2o > 0:  # dia positiu
            pos_days += 1
            if o2c > 0:  # momentum positiu
                pos_momentum += 1
                total_momentum += 1
                entry = {"date": date, "c2o": c2o, "c2c": c2c, "o2c": o2c}
                momentum_dates_total.append(entry)
                momentum_dates_pos.append(entry)

        elif c2o < 0:  # dia negatiu
            neg_days += 1
            if o2c < 0:  # momentum negatiu
                neg_momentum += 1
                total_momentum += 1
                entry = {"date": date, "c2o": c2o, "c2c": c2c, "o2c": o2c}
                momentum_dates_total.append(entry)
                momentum_dates_neg.append(entry)

    return {
        "ticker": ticker,
        "pct_momentum_total": round(total_momentum / total * 100, 2),
        "pct_momentum_pos": round(pos_momentum / pos_days * 100, 2) if pos_days else 0,
        "pct_momentum_neg": round(neg_momentum / neg_days * 100, 2) if neg_days else 0,
        "momentum_dates_total": momentum_dates_total,
        "momentum_dates_pos": momentum_dates_pos,
        "momentum_dates_neg": momentum_dates_neg
    }
