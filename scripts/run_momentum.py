# scripts/run_momentum.py

import pandas as pd
import time
from datetime import datetime
from pathlib import Path
from earnings_stock_analyzer.momentum import analyze_momentum

# 📁 Paths
BASE_DIR = Path(__file__).parent.parent
csv_path = BASE_DIR / "data" / "nasdaq_tickers.csv"
output_dir = BASE_DIR / "data" / "output"
output_dir.mkdir(parents=True, exist_ok=True)

# 📥 Load tickers from CSV
tickers_df = pd.read_csv(csv_path)
tickers_df.columns = tickers_df.columns.str.strip().str.lower()
tickers = tickers_df.iloc[:, 0].dropna().unique().tolist()

results = []

# 🔁 Analyze each ticker
for i, ticker in enumerate(tickers, 1):
    print(f"⏳ Analyzing {ticker} ({i}/{len(tickers)})...")
    result = analyze_momentum(ticker)
    if result:
        results.append(result)
    time.sleep(1.5)  # avoid overloading API

# ✅ Convert to DataFrame
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
