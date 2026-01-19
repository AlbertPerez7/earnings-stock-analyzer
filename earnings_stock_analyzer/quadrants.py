
from typing import Dict, List, Tuple
from earnings_stock_analyzer.fetch import get_earnings_data

def compute_post_earnings_quadrants(ticker: str, source: str = "library") -> Dict:
    """
    For each earnings date of a ticker, classify into one of four buckets:
      1) c2o > 0 and o2c > 0   -> "pos_then_up"
      2) c2o > 0 and o2c < 0   -> "pos_then_down"
      3) c2o < 0 and o2c > 0   -> "neg_then_up"
      4) c2o < 0 and o2c < 0   -> "neg_then_down"
    Returns counts, percentages and the list of dates for each scenario.
    We also return a detailed list of all considered rows with their assigned scenario.
    """
    reactions: List[Dict] = get_earnings_data(ticker, source=source)
    if not reactions:
        return {}

    buckets = {
        "pos_then_up": 0,
        "pos_then_down": 0,
        "neg_then_up": 0,
        "neg_then_down": 0,
    }
    dates = {}
    for k in buckets:
        dates[k] = []

    excluded_c2o_zero = 0
    excluded_o2c_zero = 0
    total_considered = 0
    detailed_rows: List[Dict] = []

    for r in reactions:
        c2o = r.get("close_to_open_pct")
        o2c = r.get("open_to_close_pct")
        date = r.get("date")
        if c2o is None or o2c is None:
            continue

        if c2o == 0:
            excluded_c2o_zero += 1
            continue
        if o2c == 0:
            excluded_o2c_zero += 1
            continue

        # Determine scenario
        scenario = None
        if c2o > 0 and o2c > 0:
            scenario = "pos_then_up"
        elif c2o > 0 and o2c < 0:
            scenario = "pos_then_down"
        elif c2o < 0 and o2c > 0:
            scenario = "neg_then_up"
        elif c2o < 0 and o2c < 0:
            scenario = "neg_then_down"

        if scenario is None:
            continue

        total_considered += 1
        buckets[scenario] += 1
        if date:
            dates[scenario].append(date)

        detailed_rows.append({
            "date": date,
            "close_to_open_pct": c2o,
            "open_to_close_pct": o2c,
            "close_to_close_pct": r.get("close_to_close_pct"),
            "scenario": scenario,
            "conditional_sign": "positive" if c2o > 0 else "negative",
            "next_day_sign": "up" if o2c > 0 else "down",
        })

    # Percentages over the considered cases
    pct = {}
    if total_considered > 0:
        for k, v in buckets.items():
            pct[k] = round(100.0 * v / total_considered, 2)

    result = {
        "ticker": ticker,
        "total_earnings": len(reactions),
        "considered": total_considered,
        "excluded_c2o_zero": excluded_c2o_zero,
        "excluded_o2c_zero": excluded_o2c_zero,
        **{k: buckets[k] for k in buckets},
        **{f"{k}_pct": pct.get(k, 0.0) for k in buckets},
        **{f"{k}_dates": dates.get(k, []) for k in buckets},
        "detailed": detailed_rows,
    }
    result["sum_pct"] = round(sum(result[f"{k}_pct"] for k in buckets), 2)
    return result
