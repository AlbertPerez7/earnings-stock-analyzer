from __future__ import annotations

from earnings_stock_analyzer.fetch import get_earnings_data



def compute_post_earnings_quadrants(
    ticker: str,
    source: str = "library",
    api_key: str | None = None,
    require_api: bool = False,
) -> dict:
    """
    Classify each earnings event into one of four scenarios using:
    - gap sign: close_to_open_pct
    - intraday continuation sign: open_to_close_pct
    """
    reactions = get_earnings_data(
        ticker=ticker,
        source=source,
        api_key=api_key,
        require_api=require_api,
    )
    if not reactions:
        return {}

    buckets = {
        "pos_then_up": 0,
        "pos_then_down": 0,
        "neg_then_up": 0,
        "neg_then_down": 0,
    }
    dates = {key: [] for key in buckets}

    excluded_c2o_zero = 0
    excluded_o2c_zero = 0
    total_considered = 0
    detailed_rows: list[dict] = []

    for reaction in reactions:
        c2o = reaction.get("close_to_open_pct")
        o2c = reaction.get("open_to_close_pct")
        date = reaction.get("date")

        if c2o is None or o2c is None:
            continue
        if c2o == 0:
            excluded_c2o_zero += 1
            continue
        if o2c == 0:
            excluded_o2c_zero += 1
            continue

        if c2o > 0 and o2c > 0:
            scenario = "pos_then_up"
        elif c2o > 0 and o2c < 0:
            scenario = "pos_then_down"
        elif c2o < 0 and o2c > 0:
            scenario = "neg_then_up"
        else:
            scenario = "neg_then_down"

        total_considered += 1
        buckets[scenario] += 1
        if date:
            dates[scenario].append(date)

        detailed_rows.append(
            {
                "date": date,
                "close_to_open_pct": c2o,
                "close_to_close_pct": reaction.get("close_to_close_pct"),
                "open_to_close_pct": o2c,
                "scenario": scenario,
                "gap_sign": "positive" if c2o > 0 else "negative",
                "intraday_sign": "up" if o2c > 0 else "down",
            }
        )

    percentages = {
        f"{key}_pct": round(value / total_considered * 100, 2) if total_considered else 0.0
        for key, value in buckets.items()
    }

    result = {
        "ticker": ticker.strip().upper(),
        "total_earnings": len(reactions),
        "considered": total_considered,
        "excluded_c2o_zero": excluded_c2o_zero,
        "excluded_o2c_zero": excluded_o2c_zero,
        **buckets,
        **percentages,
        **{f"{key}_dates": value for key, value in dates.items()},
        "detailed": detailed_rows,
    }
    result["sum_pct"] = round(sum(percentages.values()), 2)
    return result
