from __future__ import annotations

from earnings_stock_analyzer.schemas import EarningsReaction, ReactionSummary



def summarize_reactions(reactions: list[EarningsReaction]) -> ReactionSummary:
    """Return descriptive summary metrics for normalized earnings reactions."""
    filtered = [
        reaction
        for reaction in reactions
        if reaction.get("close_to_open_pct") is not None
        and reaction.get("close_to_close_pct") is not None
        and reaction.get("open_to_close_pct") is not None
    ]

    if not filtered:
        return {
            "avg_abs_close_to_open": 0.0,
            "avg_abs_close_to_close": 0.0,
            "avg_abs_open_to_close": 0.0,
            "positive_days": 0,
            "negative_days": 0,
            "total_days": 0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
        }

    total_days = len(filtered)

    avg_abs_close_to_open = round(
        sum(abs(r["close_to_open_pct"]) for r in filtered) / total_days, 2
    )
    avg_abs_close_to_close = round(
        sum(abs(r["close_to_close_pct"]) for r in filtered) / total_days, 2
    )
    avg_abs_open_to_close = round(
        sum(abs(r["open_to_close_pct"]) for r in filtered) / total_days, 2
    )

    positive_rows = [r for r in filtered if r["close_to_open_pct"] > 0]
    negative_rows = [r for r in filtered if r["close_to_open_pct"] < 0]

    summary: ReactionSummary = {
        "avg_abs_close_to_open": avg_abs_close_to_open,
        "avg_abs_close_to_close": avg_abs_close_to_close,
        "avg_abs_open_to_close": avg_abs_open_to_close,
        "positive_days": len(positive_rows),
        "negative_days": len(negative_rows),
        "total_days": total_days,
        "positive_pct": round(len(positive_rows) / total_days * 100, 2),
        "negative_pct": round(len(negative_rows) / total_days * 100, 2),
    }

    if positive_rows:
        summary["avg_pos_close_to_open"] = round(
            sum(r["close_to_open_pct"] for r in positive_rows) / len(positive_rows), 2
        )
        summary["avg_pos_close_to_close"] = round(
            sum(r["close_to_close_pct"] for r in positive_rows) / len(positive_rows), 2
        )
        summary["avg_pos_open_to_close"] = round(
            sum(r["open_to_close_pct"] for r in positive_rows) / len(positive_rows), 2
        )

    if negative_rows:
        summary["avg_neg_close_to_open"] = round(
            sum(r["close_to_open_pct"] for r in negative_rows) / len(negative_rows), 2
        )
        summary["avg_neg_close_to_close"] = round(
            sum(r["close_to_close_pct"] for r in negative_rows) / len(negative_rows), 2
        )
        summary["avg_neg_open_to_close"] = round(
            sum(r["open_to_close_pct"] for r in negative_rows) / len(negative_rows), 2
        )

    return summary
