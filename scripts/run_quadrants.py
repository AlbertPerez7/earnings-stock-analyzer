import pandas as pd
from pathlib import Path
from datetime import datetime
from earnings_stock_analyzer.cli import get_cli_args
from earnings_stock_analyzer.quadrants import compute_post_earnings_quadrants

# Resolve project root whether this file lives in root or in /scripts
_THIS = Path(__file__).resolve()
if _THIS.parent.name == "scripts":
    PROJECT_ROOT = _THIS.parent.parent
else:
    PROJECT_ROOT = _THIS.parent

DATA_CSV = (PROJECT_ROOT / "data" / "sp500_and_nasdaq_tickers.csv")
OUT_DIR = (PROJECT_ROOT / "output" / "quadrants")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ORDERED = [
    ("pos_then_up", "After +C→O, next day UP"),
    ("pos_then_down", "After +C→O, next day DOWN"),
    ("neg_then_up", "After −C→O, next day UP"),
    ("neg_then_down", "After −C→O, next day DOWN"),
]

def _scenario_rows(result: dict):
    denom = result["considered"] or 1
    rows = []
    for key, label in ORDERED:
        num = result[key]
        pct = result[f"{key}_pct"]
        rows.append({
            "Scenario": label,
            "Count": num,
            "Denominator": result["considered"],
            "Fraction": f"{num}/{denom} = {pct:.2f}%",
            "Percent": pct,
            "Dates": ";".join(result.get(f"{key}_dates", [])),  # ISO dates
        })
    return rows

def save_single(result: dict):
    ticker = result["ticker"].upper()
    summary_path = OUT_DIR / f"{ticker}_quadrants.csv"
    detail_path = OUT_DIR / f"{ticker}_quadrants_detailed.csv"
    one_line_summary_path = OUT_DIR / f"{ticker}_quadrants_summary.csv"

    # Per-scenario table (with dates and "x/y = z%" fractions)
    df = pd.DataFrame(_scenario_rows(result))
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Post-Earnings Next-Day Outcomes for {ticker}\n")
        f.write(
            f"# total_earnings={result['total_earnings']}, "
            f"considered={result['considered']}, "
            f"excluded_c2o_zero={result['excluded_c2o_zero']}, "
            f"excluded_o2c_zero={result['excluded_o2c_zero']}\n"
        )
        f.write(f"# sum_pct={result['sum_pct']}\n")
        df.to_csv(f, index=False)

    # Detailed rows: one line per earnings date with assigned scenario
    detail_df = pd.DataFrame(result["detailed"])
    if not detail_df.empty:
        detail_df = detail_df.sort_values("date")
    detail_df.to_csv(detail_path, index=False)

    # One-line compact summary per ticker (fractions + %)
    ol = pd.DataFrame([{
        "Ticker": ticker,
        "pos_then_up_fraction":   f"{result['pos_then_up']}/{result['considered']} = {result['pos_then_up_pct']:.2f}%",
        "pos_then_down_fraction": f"{result['pos_then_down']}/{result['considered']} = {result['pos_then_down_pct']:.2f}%",
        "neg_then_up_fraction":   f"{result['neg_then_up']}/{result['considered']} = {result['neg_then_up_pct']:.2f}%",
        "neg_then_down_fraction": f"{result['neg_then_down']}/{result['considered']} = {result['neg_then_down_pct']:.2f}%",
        "considered": result["considered"],
        "total_earnings": result["total_earnings"],
        "sum_pct": result["sum_pct"],
    }])
    ol.to_csv(one_line_summary_path, index=False)

    print(f"📁 Saved summary: {summary_path}")
    print(f"📁 Saved detail:  {detail_path}")
    print(f"📁 Saved one-line ticker summary: {one_line_summary_path}")

def save_batch(results: list):
    if not results:
        print("No data to save.")
        return

    # Wide table with percentages
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_pct = OUT_DIR / f"quadrants_spread_{ts}.csv"
    df = pd.DataFrame([{
        "Ticker": r["ticker"].upper(),
        "pos_then_up_pct": r["pos_then_up_pct"],
        "pos_then_down_pct": r["pos_then_down_pct"],
        "neg_then_up_pct": r["neg_then_up_pct"],
        "neg_then_down_pct": r["neg_then_down_pct"],
        "considered": r["considered"],
        "total_earnings": r["total_earnings"],
        "sum_pct": r["sum_pct"],
    } for r in results])
    with open(out_pct, "w", encoding="utf-8") as f:
        f.write("# Percentages of next-day outcomes conditional on earnings-day open move\n")
        df.to_csv(f, index=False)

    # Fractions table with numerator/denominator strings
    out_frac = OUT_DIR / f"quadrants_spread_fractions_{ts}.csv"
    df_frac = pd.DataFrame([{
        "Ticker": r["ticker"].upper(),
        "pos_then_up":   f"{r['pos_then_up']}/{r['considered']} = {r['pos_then_up_pct']:.2f}%",
        "pos_then_down": f"{r['pos_then_down']}/{r['considered']} = {r['pos_then_down_pct']:.2f}%",
        "neg_then_up":   f"{r['neg_then_up']}/{r['considered']} = {r['neg_then_up_pct']:.2f}%",
        "neg_then_down": f"{r['neg_then_down']}/{r['considered']} = {r['neg_then_down_pct']:.2f}%",
        "considered": r["considered"],
        "total_earnings": r["total_earnings"],
        "sum_pct": r["sum_pct"],
    } for r in results])
    df_frac.to_csv(out_frac, index=False)

    print(f"📁 Saved: {out_pct}")
    print(f"📁 Saved: {out_frac}")

def main():
    args = get_cli_args()
    source = args.source

    if args.ticker:
        res = compute_post_earnings_quadrants(args.ticker.upper(), source=source)
        if not res:
            print(f"⚠️ No earnings data for {args.ticker.upper()}")
            return
        save_single(res)
        return

    # Batch mode from CSV
    if not DATA_CSV.exists():
        raise FileNotFoundError(f"Tickers CSV not found at: {DATA_CSV}")
    tickers_df = pd.read_csv(DATA_CSV)
    tickers = tickers_df.iloc[:, 0].dropna().unique().tolist()

    results = []
    for t in tickers:
        try:
            print(f"⏳ {t} ...")
            r = compute_post_earnings_quadrants(t, source=source)
            if r:
                save_single(r)          # also write per-ticker files in batch
                results.append(r)
        except Exception as e:
            print(f"❌ {t}: {e}")
    save_batch(results)

if __name__ == "__main__":
    main()
