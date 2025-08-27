from typing import List, Dict

def summarize_reactions(reactions: List[Dict]) -> Dict:
    """
    Summarize averages. Assumes reactions already contain % values
    (from the library stocks_earnings_dates).
    """
    if not reactions:
        return {}

    filtered = [
        r for r in reactions
        if r.get("close_to_open_pct") is not None
        and r.get("close_to_close_pct") is not None
        and r.get("open_to_close_pct") is not None
    ]

    if not filtered:
        return {
            "avg_abs_close_to_open": 0,
            "avg_abs_close_to_close": 0,
            "avg_abs_open_to_close": 0,
            "positive_days": 0,
            "negative_days": 0,
            "total_days": 0,
            "positive_pct": 0,
            "negative_pct": 0,
        }

    summary = {
        "avg_abs_close_to_open": 0.0,
        "avg_abs_close_to_close": 0.0,
        "avg_abs_open_to_close": 0.0,
        "positive_days": 0,
        "negative_days": 0,
        "total_days": 0,
    }

    pos_c2o = pos_c2c = pos_o2c = 0.0
    neg_c2o = neg_c2c = neg_o2c = 0.0

    for r in filtered:
        c2o = r["close_to_open_pct"]
        c2c = r["close_to_close_pct"]
        o2c = r["open_to_close_pct"]

        summary["avg_abs_close_to_open"] += abs(c2o)
        summary["avg_abs_close_to_close"] += abs(c2c)
        summary["avg_abs_open_to_close"] += abs(o2c)
        summary["total_days"] += 1

        if c2o > 0:
            summary["positive_days"] += 1
            pos_c2o += c2o; pos_c2c += c2c; pos_o2c += o2c
        elif c2o < 0:
            summary["negative_days"] += 1
            neg_c2o += c2o; neg_c2c += c2c; neg_o2c += o2c

    td = summary["total_days"]
    for k in ["avg_abs_close_to_open", "avg_abs_close_to_close", "avg_abs_open_to_close"]:
        summary[k] = round(summary[k] / td, 2)

    summary["positive_pct"] = round((summary["positive_days"] / td) * 100, 2) if td else 0
    summary["negative_pct"] = round((summary["negative_days"] / td) * 100, 2) if td else 0

    if summary["positive_days"]:
        summary["avg_pos_close_to_open"] = round(pos_c2o / summary["positive_days"], 2)
        summary["avg_pos_close_to_close"] = round(pos_c2c / summary["positive_days"], 2)
        summary["avg_pos_open_to_close"] = round(pos_o2c / summary["positive_days"], 2)

    if summary["negative_days"]:
        summary["avg_neg_close_to_open"] = round(neg_c2o / summary["negative_days"], 2)
        summary["avg_neg_close_to_close"] = round(neg_c2c / summary["negative_days"], 2)
        summary["avg_neg_open_to_close"] = round(neg_o2c / summary["negative_days"], 2)

    return summary
