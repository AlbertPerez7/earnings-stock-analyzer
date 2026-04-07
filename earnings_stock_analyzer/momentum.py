from __future__ import annotations

from earnings_stock_analyzer.fetch import get_earnings_data
from earnings_stock_analyzer.schemas import MomentumEntry, MomentumResult



def analyze_momentum(
    ticker: str,
    source: str = "library",
    api_key: str | None = None,
    require_api: bool = False,
) -> MomentumResult | dict:
    """
    Analyze post-earnings continuation.

    A positive momentum event is defined as:
        close_to_open_pct > 0 and open_to_close_pct > 0

    A negative momentum event is defined as:
        close_to_open_pct < 0 and open_to_close_pct < 0
    """
    reactions = get_earnings_data(
        ticker=ticker,
        source=source,
        api_key=api_key,
        require_api=require_api,
    )
    if not reactions:
        return {}

    positive_gap_days = 0
    negative_gap_days = 0
    momentum_positive_count = 0
    momentum_negative_count = 0

    momentum_dates_total: list[MomentumEntry] = []
    momentum_dates_pos: list[MomentumEntry] = []
    momentum_dates_neg: list[MomentumEntry] = []

    for reaction in reactions:
        c2o = reaction["close_to_open_pct"]
        c2c = reaction["close_to_close_pct"]
        o2c = reaction["open_to_close_pct"]
        date = reaction["date"]

        entry: MomentumEntry = {
            "date": date,
            "c2o": c2o,
            "c2c": c2c,
            "o2c": o2c,
        }

        if c2o > 0:
            positive_gap_days += 1
            if o2c > 0:
                momentum_positive_count += 1
                momentum_dates_total.append(entry)
                momentum_dates_pos.append(entry)
        elif c2o < 0:
            negative_gap_days += 1
            if o2c < 0:
                momentum_negative_count += 1
                momentum_dates_total.append(entry)
                momentum_dates_neg.append(entry)

    total_events = len(reactions)
    momentum_total_count = momentum_positive_count + momentum_negative_count

    result: MomentumResult = {
        "ticker": ticker.strip().upper(),
        "total_events": total_events,
        "positive_gap_days": positive_gap_days,
        "negative_gap_days": negative_gap_days,
        "momentum_total_count": momentum_total_count,
        "momentum_positive_count": momentum_positive_count,
        "momentum_negative_count": momentum_negative_count,
        "pct_momentum_total": round(momentum_total_count / total_events * 100, 2),
        "pct_momentum_pos": round(momentum_positive_count / positive_gap_days * 100, 2)
        if positive_gap_days
        else 0.0,
        "pct_momentum_neg": round(momentum_negative_count / negative_gap_days * 100, 2)
        if negative_gap_days
        else 0.0,
        "momentum_dates_total": momentum_dates_total,
        "momentum_dates_pos": momentum_dates_pos,
        "momentum_dates_neg": momentum_dates_neg,
    }
    return result
