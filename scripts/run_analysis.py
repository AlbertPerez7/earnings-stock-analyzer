from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from earnings_stock_analyzer.analyzer import summarize_reactions
from earnings_stock_analyzer.cli import get_cli_args
from earnings_stock_analyzer.fetch import get_earnings_data
from earnings_stock_analyzer.plot import plot_earnings_reactions

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parent.parent if _THIS.parent.name == "scripts" else _THIS.parent

DATA_CSV   = PROJECT_ROOT / "data" / "sp500_and_nasdaq_tickers.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Single-ticker output
# ---------------------------------------------------------------------------

def _save_single_ticker_csv(
    ticker: str,
    reactions: list[dict],
    summary: dict,
    output_dir: Path,
) -> Path:
    """
    Save a per-ticker CSV combining raw earnings reactions and a
    summary statistics block appended at the bottom.
    """
    df_reactions = pd.DataFrame([{
        "Date": r["date"],
        "C2O":  r["close_to_open_pct"],
        "C2C":  r["close_to_close_pct"],
        "O2C":  r["open_to_close_pct"],
    } for r in reactions])

    summary_rows = pd.DataFrame([
        {"Date": "--- SUMMARY ---",  "C2O": "",  "C2C": "",  "O2C": ""},
        {"Date": "Avg |C->O|",       "C2O": summary["avg_abs_close_to_open"]},
        {"Date": "Avg |C->C|",       "C2O": summary["avg_abs_close_to_close"]},
        {"Date": "Avg |O->C|",       "C2O": summary["avg_abs_open_to_close"]},
        {"Date": "Positive days",    "C2O": f"{summary['positive_days']} ({summary['positive_pct']}%)"},
        {"Date": "Avg C->O (pos)",   "C2O": summary.get("avg_pos_close_to_open",  0)},
        {"Date": "Avg C->C (pos)",   "C2O": summary.get("avg_pos_close_to_close", 0)},
        {"Date": "Avg O->C (pos)",   "C2O": summary.get("avg_pos_open_to_close",  0)},
        {"Date": "Negative days",    "C2O": f"{summary['negative_days']} ({summary['negative_pct']}%)"},
        {"Date": "Avg C->O (neg)",   "C2O": summary.get("avg_neg_close_to_open",  0)},
        {"Date": "Avg C->C (neg)",   "C2O": summary.get("avg_neg_close_to_close", 0)},
        {"Date": "Avg O->C (neg)",   "C2O": summary.get("avg_neg_open_to_close",  0)},
    ])

    out_path = output_dir / f"{ticker}_earnings.csv"
    pd.concat([df_reactions, summary_rows], ignore_index=True).to_csv(out_path, index=False)
    return out_path


def _print_single_ticker_summary(
    ticker: str,
    reactions: list[dict],
    summary: dict,
) -> None:
    print(f"\n--- {ticker}: individual earnings reactions ---")
    for r in reactions:
        print(
            f"  {r['date']}:  C->O={r['close_to_open_pct']:+.2f}%  "
            f"C->C={r['close_to_close_pct']:+.2f}%  "
            f"O->C={r['open_to_close_pct']:+.2f}%"
        )

    print(f"\n--- {ticker}: average absolute moves ---")
    print(f"  Close -> Next Open:  {summary['avg_abs_close_to_open']:.2f}%")
    print(f"  Close -> Next Close: {summary['avg_abs_close_to_close']:.2f}%")
    print(f"  Open  -> Next Close: {summary['avg_abs_open_to_close']:.2f}%")

    print(f"\n--- {ticker}: positive overnight gap days ({summary['positive_days']}, {summary['positive_pct']}%) ---")
    print(f"  Avg C->O: {summary.get('avg_pos_close_to_open',  0):+.2f}%")
    print(f"  Avg C->C: {summary.get('avg_pos_close_to_close', 0):+.2f}%")
    print(f"  Avg O->C: {summary.get('avg_pos_open_to_close',  0):+.2f}%")

    print(f"\n--- {ticker}: negative overnight gap days ({summary['negative_days']}, {summary['negative_pct']}%) ---")
    print(f"  Avg C->O: {summary.get('avg_neg_close_to_open',  0):+.2f}%")
    print(f"  Avg C->C: {summary.get('avg_neg_close_to_close', 0):+.2f}%")
    print(f"  Avg O->C: {summary.get('avg_neg_open_to_close',  0):+.2f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args        = get_cli_args()
    source      = args.source
    api_key     = args.api_key
    require_api = args.require_api

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build ticker list - single ticker, comma-separated list, or full CSV batch
    if args.ticker:
        tickers       = [t.strip().upper() for t in args.ticker.replace(",", " ").split() if t.strip()]
        multiple_mode = len(tickers) > 1
    else:
        if not DATA_CSV.exists():
            logger.error("Ticker CSV not found at: %s", DATA_CSV)
            return
        tickers       = pd.read_csv(DATA_CSV).iloc[:, 0].dropna().unique().tolist()
        multiple_mode = True

    summaries: list[dict] = []

    for ticker in tickers:
        logger.info("Analyzing %s (source=%s)...", ticker, source)
        try:
            reactions = get_earnings_data(ticker, source=source, api_key=api_key, require_api=require_api)
            if not reactions:
                logger.warning("No earnings data for %s. Skipping.", ticker)
                continue
        except Exception:
            logger.exception("Failed to fetch data for %s", ticker)
            continue

        summary = summarize_reactions(reactions)
        if not summary:
            logger.warning("Insufficient data for %s.", ticker)
            continue

        if not multiple_mode:
            # Single-ticker mode: print full detail, save CSV, show plot
            _print_single_ticker_summary(ticker, reactions, summary)

            out_path = _save_single_ticker_csv(ticker, reactions, summary, OUTPUT_DIR)
            logger.info("CSV saved to: %s", out_path)

            df_plot = pd.DataFrame([{
                "Date": r["date"],
                "C2O":  r["close_to_open_pct"],
                "C2C":  r["close_to_close_pct"],
                "O2C":  r["open_to_close_pct"],
            } for r in reactions])
            plot_earnings_reactions(ticker, df_plot, show=True)

        else:
            # Batch mode: collect summary row for ranking table
            summaries.append({
                "Ticker":      ticker,
                "Avg % C->O":  summary["avg_abs_close_to_open"],
                "Avg % C->C":  summary["avg_abs_close_to_close"],
                "Avg % O->C":  summary["avg_abs_open_to_close"],
                "% Positive":  summary["positive_pct"],
                "% Negative":  summary["negative_pct"],
            })

    if multiple_mode and summaries:
        df = (
            pd.DataFrame(summaries)
            .sort_values("Avg % C->O", ascending=False)
            .reset_index(drop=True)
        )
        top20 = df.head(20)

        ts         = datetime.now().strftime("%Y-%m-%d_%H-%M")
        out_path   = OUTPUT_DIR / f"top20_avg_abs_C2O_{ts}.csv"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# Top 20 stocks by average absolute overnight earnings gap\n")
            top20.to_csv(f, index=False)

        logger.info("Batch summary saved to: %s", out_path)

    elif multiple_mode and not summaries:
        logger.error("No valid data collected from any ticker.")


if __name__ == "__main__":
    main()
