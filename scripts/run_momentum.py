from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from earnings_stock_analyzer.cli import get_cli_args
from earnings_stock_analyzer.momentum import analyze_momentum

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parent.parent if _THIS.parent.name == "scripts" else _THIS.parent

DATA_CSV   = PROJECT_ROOT / "data" / "sp500_and_nasdaq_tickers.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "momentum"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _save_single_ticker(result: dict, output_dir: Path) -> Path:
    """
    Save momentum date lists and summary percentages for a single ticker
    to a structured CSV file.
    """
    ticker     = result["ticker"]
    df_total   = pd.DataFrame(result["momentum_dates_total"])
    df_pos     = pd.DataFrame(result["momentum_dates_pos"])
    df_neg     = pd.DataFrame(result["momentum_dates_neg"])

    out_path = output_dir / f"{ticker.lower()}_momentum.csv"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Post-earnings momentum dates for {ticker}\n")
        df_total.to_csv(f, index=False)

        f.write("\n# Positive momentum dates (positive gap, intraday continuation)\n")
        df_pos.to_csv(f, index=False)

        f.write("\n# Negative momentum dates (negative gap, intraday continuation)\n")
        df_neg.to_csv(f, index=False)

        f.write("\n# Summary\n")
        f.write(f"total_events,{result['total_events']}\n")
        f.write(f"pct_momentum_total,{result['pct_momentum_total']}\n")
        f.write(f"pct_momentum_pos,{result['pct_momentum_pos']}\n")
        f.write(f"pct_momentum_neg,{result['pct_momentum_neg']}\n")

    return out_path


def _save_batch_rankings(results: list[dict], output_dir: Path) -> Path:
    """
    Save Top-30 rankings by total, positive, and negative momentum rate
    to a single structured CSV file.
    """
    df = pd.DataFrame(results)

    top30_total = df.nlargest(30, "pct_momentum_total")[["ticker", "pct_momentum_total"]]
    top30_pos   = df.nlargest(30, "pct_momentum_pos")[["ticker", "pct_momentum_pos"]]
    top30_neg   = df.nlargest(30, "pct_momentum_neg")[["ticker", "pct_momentum_neg"]]

    ts       = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = output_dir / f"top30_momentum_success_rate_{ts}.csv"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Top 30 by total momentum rate (all earnings events)\n")
        top30_total.to_csv(f, index=False)
        f.write("\n# Top 30 by positive momentum rate (positive gap days only)\n")
        top30_pos.to_csv(f, index=False)
        f.write("\n# Top 30 by negative momentum rate (negative gap days only)\n")
        top30_neg.to_csv(f, index=False)

    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    args        = get_cli_args()
    source      = args.source
    api_key     = args.api_key
    require_api = args.require_api

    # Single-ticker mode
    if args.ticker:
        ticker = args.ticker.strip().upper()
        result = analyze_momentum(ticker, source=source, api_key=api_key, require_api=require_api)
        if result:
            out_path = _save_single_ticker(result, OUTPUT_DIR)
            logger.info("Saved to: %s", out_path)
            print(
                f"\n{ticker} momentum summary:\n"
                f"  Total events:       {result['total_events']}\n"
                f"  Momentum rate:      {result['pct_momentum_total']}%\n"
                f"  Positive gap rate:  {result['pct_momentum_pos']}%\n"
                f"  Negative gap rate:  {result['pct_momentum_neg']}%"
            )
        else:
            logger.warning("No momentum data available for %s.", ticker)
        return

    # Batch mode - analyse all tickers from the universe CSV
    if not DATA_CSV.exists():
        logger.error("Ticker CSV not found at: %s", DATA_CSV)
        sys.exit(1)

    tickers = (
        pd.read_csv(DATA_CSV)
        .pipe(lambda df: df.rename(columns=str.lower))
        .iloc[:, 0]
        .dropna()
        .unique()
        .tolist()
    )

    results: list[dict] = []
    for i, ticker in enumerate(tickers, 1):
        logger.info("Analyzing %s (%d/%d)...", ticker, i, len(tickers))
        result = analyze_momentum(ticker, source=source, api_key=api_key, require_api=require_api)
        if result:
            results.append(result)

    if not results:
        logger.error("No results collected.")
        sys.exit(1)

    out_path = _save_batch_rankings(results, OUTPUT_DIR)
    logger.info("Batch rankings saved to: %s", out_path)


if __name__ == "__main__":
    main()
