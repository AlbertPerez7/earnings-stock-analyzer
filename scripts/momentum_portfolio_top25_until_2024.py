from __future__ import annotations

import csv
import logging
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parent.parent if _THIS.parent.name == "scripts" else _THIS.parent

QUADRANTS_DIR = PROJECT_ROOT / "output" / "quadrants"
ANALYSIS_DIR  = PROJECT_ROOT / "output" / "analysis"

TOP25_PATH = ANALYSIS_DIR / "top25_quadrants_momentum_bias.csv"
OUT_PATH   = ANALYSIS_DIR / "momentum_top25_detailed_until2024.csv"

# ---------------------------------------------------------------------------
# Out-of-sample trading window
# Selection uses pre-2017 data; trading starts in 2018 to avoid any
# look-ahead bias from the stock selection step.
# ---------------------------------------------------------------------------
START_DATE = date(2018, 1, 1)
CUTOFF     = date(2024, 12, 31)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_top25(path: Path) -> list[str]:
    """Load the pre-selected Top-25 ticker universe from the ranking CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Top-25 ranking file not found at: {path}")
    tickers = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = (row.get("ticker") or row.get("Ticker") or "").strip().upper()
            if t:
                tickers.append(t)
    return sorted(set(tickers))


def _read_trades_for_ticker(
    ticker: str,
    trades_by_date: defaultdict,
) -> int:
    """
    Read the detailed quadrant CSV for a single ticker and append all
    out-of-sample earnings-day trades to trades_by_date.

    Returns the number of trades added.
    """
    file = QUADRANTS_DIR / f"{ticker}_quadrants_detailed.csv"
    if not file.exists():
        logger.warning("Missing detailed file for %s: %s", ticker, file)
        return 0

    count = 0
    with file.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                event_date = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
                c2o = float(row["close_to_open_pct"])
                o2c = float(row["open_to_close_pct"])
            except (KeyError, ValueError):
                continue

            if event_date < START_DATE or event_date > CUTOFF:
                continue
            if c2o == 0 or o2c == 0:
                continue

            # Momentum rule: go long if the overnight gap is positive,
            # short if negative. Position is held intraday only (open -> close).
            trade_ret = o2c if c2o > 0 else -o2c  # LONG or SHORT

            trades_by_date[event_date].append({
                "ticker":    ticker,
                "c2o":       c2o,
                "o2c":       o2c,
                "trade_ret": trade_ret,
            })
            count += 1

    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    tickers = load_top25(TOP25_PATH)
    if not tickers:
        logger.error("No tickers found in %s", TOP25_PATH)
        return

    logger.info("Loaded %d tickers: %s", len(tickers), ", ".join(tickers))

    # Collect all trades grouped by date
    trades_by_date: defaultdict[date, list] = defaultdict(list)
    total_trades = 0
    for ticker in tickers:
        total_trades += _read_trades_for_ticker(ticker, trades_by_date)

    if not trades_by_date:
        logger.error("No trades found in the out-of-sample window.")
        return

    logger.info("Trading days with at least one trade: %d", len(trades_by_date))
    logger.info("Total individual trades: %d", total_trades)

    # Simulate the strategy with equal-weighted daily allocation and compounding.
    # On each trading day, capital is split equally across all active positions.
    # The daily portfolio return is the arithmetic average of individual trade
    # returns, and equity is updated via compounding.
    equity = 1.0

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "date",
            "ticker",
            "close_to_open_pct",
            "open_to_close_pct",
            "trade_return_pct",
            "n_trades_that_day",
            "avg_daily_return_pct",
            "equity_before",
            "equity_after",
            "cumulative_return_pct",
        ])

        for day in sorted(trades_by_date):
            day_trades = trades_by_date[day]
            avg_ret    = sum(t["trade_ret"] for t in day_trades) / len(day_trades)

            eq_before = equity
            equity   *= 1.0 + avg_ret / 100.0
            cum_pct   = (equity - 1.0) * 100.0

            for t in day_trades:
                w.writerow([
                    day.isoformat(),
                    t["ticker"],
                    t["c2o"],
                    t["o2c"],
                    t["trade_ret"],
                    len(day_trades),
                    round(avg_ret, 6),
                    round(eq_before, 8),
                    round(equity,    8),
                    round(cum_pct,   6),
                ])

    logger.info("Simulation complete. Output saved to: %s", OUT_PATH)
    logger.info(
        "Final equity: %.4f  (%.2f%% total return)",
        equity, (equity - 1.0) * 100.0,
    )


if __name__ == "__main__":
    main()
