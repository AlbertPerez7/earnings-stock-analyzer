import csv
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

# ------------------------------
# Paths
# ------------------------------
THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parent.parent if THIS.parent.name == "scripts" else THIS.parent

QUADRANTS_DIR = PROJECT_ROOT / "output" / "quadrants"
ANALYSIS_DIR  = PROJECT_ROOT / "output" / "analysis"

TOP25_PATH = ANALYSIS_DIR / "top25_quadrants_momentum_bias.csv"
OUT_PATH   = ANALYSIS_DIR / "momentum_top25_detailed_until2024.csv"

# Out-of-sample trading window (selection uses pre-2017 data; trading starts in 2018)
START_DATE = date(2018, 1, 1)
CUTOFF = date(2024, 12, 31)


def load_top25(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"❌ top25_quadrants_momentum_bias.csv not found at: {path}")
    tickers = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = (row.get("ticker") or row.get("Ticker") or "").strip().upper()
            if t:
                tickers.append(t)
    return sorted(set(tickers))


def main():
    print(f"PROJECT_ROOT = {PROJECT_ROOT}")
    print(f"QUADRANTS_DIR = {QUADRANTS_DIR}")
    print(f"ANALYSIS_DIR = {ANALYSIS_DIR}")
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Load top25
    try:
        tickers = load_top25(TOP25_PATH)
    except Exception as e:
        print(e)
        return

    if not tickers:
        print("❌ No tickers found in top25_quadrants_momentum_bias.csv")
        return

    print(f"✅ Loaded {len(tickers)} tickers:")
    print("   " + ", ".join(tickers))

    trades_by_date = defaultdict(list)
    total_trades = 0
    missing = []

    # 2) Read the *_quadrants_detailed.csv files
    if not QUADRANTS_DIR.exists():
        print(f"❌ Quadrants directory not found: {QUADRANTS_DIR}")
        return

    for ticker in tickers:
        file = QUADRANTS_DIR / f"{ticker}_quadrants_detailed.csv"
        if not file.exists():
            print(f"⚠ Missing detailed file for ticker {ticker}: {file}")
            missing.append(ticker)
            continue

        with file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    d = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
                    c2o = float(row["close_to_open_pct"])
                    o2c = float(row["open_to_close_pct"])
                except Exception:
                    continue

                # Filter to out-of-sample window only
                if d < START_DATE or d > CUTOFF:
                    continue
                if c2o == 0 or o2c == 0:
                    continue

                # Momentum logic
                if c2o > 0:
                    trade_ret = o2c       # LONG
                else:
                    trade_ret = -o2c      # SHORT

                trades_by_date[d].append({
                    "ticker": ticker,
                    "c2o": c2o,
                    "o2c": o2c,
                    "trade_ret": trade_ret
                })
                total_trades += 1

    if not trades_by_date:
        print("❌ No trades found in the out-of-sample window for these tickers.")
        return

    print(f"📅 Trading days with at least one trade: {len(trades_by_date)}")
    print(f"📊 Total individual trades: {total_trades}")

    # 3) Compounding + detailed CSV
    sorted_dates = sorted(trades_by_date.keys())
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

        for d in sorted_dates:
            day_trades = trades_by_date[d]
            rets = [t["trade_ret"] for t in day_trades]
            avg_ret = sum(rets) / len(rets)

            eq_before = equity
            equity *= (1.0 + avg_ret / 100.0)
            eq_after = equity
            cum_pct = (equity - 1.0) * 100.0

            for t in day_trades:
                w.writerow([
                    d.isoformat(),
                    t["ticker"],
                    t["c2o"],
                    t["o2c"],
                    t["trade_ret"],
                    len(day_trades),
                    round(avg_ret, 6),
                    round(eq_before, 8),
                    round(eq_after, 8),
                    round(cum_pct, 6),
                ])

    print("\n✅ Detailed simulation completed.")
    print(f"📁 Output saved to: {OUT_PATH}")
    print(f"📈 Final equity: {equity:.2f}  (≈ {(equity - 1.0)*100:.2f}% return)")


if __name__ == "__main__":
    main()
