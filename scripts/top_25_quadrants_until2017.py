from __future__ import annotations

import csv
import logging
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parent.parent if _THIS.parent.name == "scripts" else _THIS.parent

QDIR     = PROJECT_ROOT / "output" / "quadrants"
OUT_PATH = PROJECT_ROOT / "output" / "analysis" / "top25_quadrants_momentum_bias.csv"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
# Only earnings events up to this date are used for stock selection,
# ensuring strict separation between the in-sample ranking period and
# the out-of-sample evaluation period (2018-2024).
CUTOFF_DATE   = date(2017, 12, 31)

# Minimum number of classifiable earnings events (c2o != 0 and o2c != 0)
# required for a ticker to enter the ranking. Filters out stocks with
# insufficient history to produce a reliable momentum bias estimate.
MIN_CONSIDERED = 40

# Number of top stocks to select for the out-of-sample portfolio.
TOP_N = 25

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-ticker processing
# ---------------------------------------------------------------------------

def _process_ticker(path: Path) -> dict | None:
    """
    Read a single *_quadrants_detailed.csv file and compute momentum bias
    using only earnings events up to CUTOFF_DATE.

    Returns a result dict if the ticker meets MIN_CONSIDERED, else None.
    """
    ticker = path.stem.split("_")[0].upper()

    total_earnings = 0  # all events within the cutoff window
    considered     = 0  # events where both c2o and o2c are non-zero
    pos_then_up    = 0
    pos_then_down  = 0
    neg_then_up    = 0
    neg_then_down  = 0

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                event_date = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
                if event_date > CUTOFF_DATE:
                    continue
                c2o = float(row["close_to_open_pct"])
                o2c = float(row["open_to_close_pct"])
            except (KeyError, ValueError):
                continue  # skip malformed rows

            total_earnings += 1

            # Events where either return is zero have undefined direction
            # and are excluded from the quadrant classification.
            if c2o == 0 or o2c == 0:
                continue

            considered += 1

            if c2o > 0 and o2c > 0:
                pos_then_up += 1
            elif c2o > 0 and o2c < 0:
                pos_then_down += 1
            elif c2o < 0 and o2c > 0:
                neg_then_up += 1
            else:
                neg_then_down += 1

    if considered < MIN_CONSIDERED:
        return None

    pos_up_pct   = 100.0 * pos_then_up   / considered
    pos_down_pct = 100.0 * pos_then_down / considered
    neg_up_pct   = 100.0 * neg_then_up   / considered
    neg_down_pct = 100.0 * neg_then_down / considered

    continuation  = pos_up_pct + neg_down_pct
    reversal      = pos_down_pct + neg_up_pct
    momentum_bias = continuation - reversal

    return {
        "ticker":        ticker,
        "considered":    considered,
        "total_earnings": total_earnings,
        "pos_then_up":   pos_up_pct,
        "pos_then_down": pos_down_pct,
        "neg_then_up":   neg_up_pct,
        "neg_then_down": neg_down_pct,
        "continuation":  continuation,
        "reversal":      reversal,
        "momentum_bias": momentum_bias,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not QDIR.exists():
        logger.error("Quadrants directory not found: %s", QDIR)
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for path in sorted(QDIR.glob("*_quadrants_detailed.csv")):
        try:
            result = _process_ticker(path)
            if result is not None:
                results.append(result)
        except Exception:
            logger.exception("Failed to process %s", path.name)

    if not results:
        logger.error(
            "No valid quadrant files found with >= %d considered earnings on or before %s.",
            MIN_CONSIDERED, CUTOFF_DATE,
        )
        return

    # Rank by momentum bias descending and select top N
    results.sort(key=lambda r: r["momentum_bias"], reverse=True)
    top_n = results[:TOP_N]

    _COLUMNS = [
        "rank", "ticker", "considered", "total_earnings",
        "pos_then_up", "pos_then_down", "neg_then_up", "neg_then_down",
        "continuation", "reversal", "momentum_bias",
    ]

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(_COLUMNS)
        for rank, r in enumerate(top_n, start=1):
            w.writerow([rank] + [r[col] for col in _COLUMNS[1:]])

    logger.info(
        "Wrote Top-%d momentum-bias stocks (>= %d events, data <= %s) to: %s",
        TOP_N, MIN_CONSIDERED, CUTOFF_DATE, OUT_PATH,
    )

    print("\nTop 5 preview:")
    for r in top_n[:5]:
        print(
            f"  {r['ticker']}: momentum_bias={r['momentum_bias']:.4f} "
            f"(continuation={r['continuation']:.2f}%, "
            f"reversal={r['reversal']:.2f}%, "
            f"considered={r['considered']})"
        )


if __name__ == "__main__":
    main()
