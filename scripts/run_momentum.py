import pandas as pd
from datetime import datetime
from pathlib import Path
from earnings_stock_analyzer.momentum import analyze_momentum
from earnings_stock_analyzer.cli import get_cli_args

# Paths
BASE_DIR = Path(__file__).parent.parent
csv_path = BASE_DIR / "data" / "sp500_and_nasdaq_tickers.csv"
output_dir = BASE_DIR /"output" / "momentum"
output_dir.mkdir(parents=True, exist_ok=True)

# CLI arguments
args = get_cli_args()
source = args.source
ticker_arg = args.ticker

# Single ticker mode
if ticker_arg:
    result = analyze_momentum(ticker_arg.upper(), source=source)
    if result:
        df_all = pd.DataFrame(result["momentum_dates_total"])
        df_pos = pd.DataFrame(result["momentum_dates_pos"])
        df_neg = pd.DataFrame(result["momentum_dates_neg"])

        output_file = output_dir / f"{ticker_arg.lower()}_momentum.csv"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# MOMENTUM EARNINGS DATES for {ticker_arg.upper()}\n")
            df_all.to_csv(f, index=False)
            f.write(f"\n# POSITIVE MOMENTUM DATES (Positive Open → Stronger Close)\n")
            df_pos.to_csv(f, index=False)
            f.write(f"\n# NEGATIVE MOMENTUM DATES (Negative Open → Weaker Close)\n")
            df_neg.to_csv(f, index=False)

            f.write(f"\n# PERCENTAGES OF MOMENTUM\n")
            f.write(f"Total Momentum %:,{result['pct_momentum_total']}\n")
            f.write(f"Positive Momentum %:,{result['pct_momentum_pos']}\n")
            f.write(f"Negative Momentum %:,{result['pct_momentum_neg']}\n")

        print(f"\n📁 CSV saved to: {output_file}")
    else:
        print(f"⚠️ No momentum data available for {ticker_arg.upper()}.")
    exit()

# 📅 Load tickers from CSV
tickers_df = pd.read_csv(csv_path)
tickers_df.columns = tickers_df.columns.str.strip().str.lower()
tickers = tickers_df.iloc[:, 0].dropna().unique().tolist()

results = []

# 🔁 Analyze each ticker
for i, ticker in enumerate(tickers, 1):
    print(f"⏳ Analyzing {ticker} ({i}/{len(tickers)})...")
    result = analyze_momentum(ticker, source=source)
    if result:
        results.append(result)

df = pd.DataFrame(results)

# 📊 Rankings
top30_total = df.sort_values(by="pct_momentum_total", ascending=False).head(30)[["ticker", "pct_momentum_total"]]
top30_pos = df.sort_values(by="pct_momentum_pos", ascending=False).head(30)[["ticker", "pct_momentum_pos"]]
top30_neg = df.sort_values(by="pct_momentum_neg", ascending=False).head(30)[["ticker", "pct_momentum_neg"]]

# 🕒 Save results
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
output_file = output_dir / f"top30_momentum_success_rate_{timestamp}.csv"

with open(output_file, "w", encoding="utf-8") as f:
    f.write("# TOP 30 TOTAL MOMENTUM (Earnings Days)\n")
    top30_total.to_csv(f, index=False)
    f.write("\n# TOP 30 POSITIVE MOMENTUM (Positive Open → Stronger Close)\n")
    top30_pos.to_csv(f, index=False)
    f.write("\n# TOP 30 NEGATIVE MOMENTUM (Negative Open → Weaker Close)\n")
    top30_neg.to_csv(f, index=False)

print(f"\n📁 CSV saved to: {output_file}")
