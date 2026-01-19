import matplotlib
matplotlib.use("TkAgg")  # interactive backend → shows external window

from earnings_stock_analyzer.cli import get_cli_args
from earnings_stock_analyzer.fetch import get_earnings_data
from earnings_stock_analyzer.analyzer import summarize_reactions
from earnings_stock_analyzer.plot import plot_results

import pandas as pd
from pathlib import Path
from datetime import datetime


def main():
    args = get_cli_args()
    raw_input = args.ticker
    source = args.source   # defaults to "library" via cli.py

    BASE_DIR = Path(__file__).parent.parent
    csv_path = BASE_DIR / "data" / "sp500_and_nasdaq_tickers.csv"
    output_dir = BASE_DIR /"output" / "analysis"
    plots_dir = output_dir / "top_20_plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    if not raw_input:
        # Analyze all tickers from CSV
        tickers_df = pd.read_csv(csv_path)
        tickers = tickers_df.iloc[:, 0].dropna().unique().tolist()
        multiple_mode = True
    else:
        tickers = [t.strip().upper() for t in raw_input.replace(",", " ").split() if t.strip()]
        multiple_mode = len(tickers) > 1

    summaries = []
    enriched_dict = {}

    for ticker in tickers:
        print(f"\n📊 Analyzing {ticker} from source '{source}'...")
        try:
            earnings_data = get_earnings_data(ticker, source=source)
            if not earnings_data:
                print(f"⚠️  No earnings data found for {ticker}. Skipping.")
                continue
        except Exception as e:
            print(f"❌ Error fetching data for {ticker}: {e}")
            continue

        enriched = earnings_data
        summary = summarize_reactions(enriched)
        if not summary:
            print(f"⚠️  Not enough data for {ticker}.")
            continue

        if not multiple_mode:
            print("\n📅 INDIVIDUAL EARNINGS DAY REACTIONS:")
            for d in enriched:
                print(f"{d['date']}: C→O={d['close_to_open_pct']}%  "
                      f"C→C={d['close_to_close_pct']}%  "
                      f"O→C={d['open_to_close_pct']}%")

            print("\n📊 AVERAGE ABSOLUTE PERCENTAGE CHANGE AFTER EARNINGS:")
            print(f"• Close → Next Open: {summary['avg_abs_close_to_open']:.2f}%")
            print(f"• Close → Next Close: {summary['avg_abs_close_to_close']:.2f}%")
            print(f"• Next Open → Next Close: {summary['avg_abs_open_to_close']:.2f}%")

            print("\n📈 POSITIVE DAY STATISTICS:")
            print(f"• Positive Days: {summary['positive_days']} ({summary['positive_pct']}%)")
            print(f"• Avg Close→Open: {summary.get('avg_pos_close_to_open', 0):.2f}%")
            print(f"• Avg Close→Close: {summary.get('avg_pos_close_to_close', 0):.2f}%")
            print(f"• Avg Open→Close: {summary.get('avg_pos_open_to_close', 0):.2f}%")

            print("\n📉 NEGATIVE DAY STATISTICS:")
            print(f"• Negative Days: {summary['negative_days']} ({summary['negative_pct']}%)")
            print(f"• Avg Close→Open: {summary.get('avg_neg_close_to_open', 0):.2f}%")
            print(f"• Avg Close→Close: {summary.get('avg_neg_close_to_close', 0):.2f}%")
            print(f"• Avg Open→Close: {summary.get('avg_neg_open_to_close', 0):.2f}%")

            df_plot = pd.DataFrame([{
                "Date": r["date"],
                "C2O": r["close_to_open_pct"],
                "C2C": r["close_to_close_pct"],
                "O2C": r["open_to_close_pct"]
            } for r in enriched])

            # Append summary to bottom of CSV
            summary_rows = pd.DataFrame([
                {"Date": "SUMMARY", "C2O": "", "C2C": "", "O2C": ""},
                {"Date": "Avg Abs C→O", "C2O": summary['avg_abs_close_to_open']},
                {"Date": "Avg Abs C→C", "C2O": summary['avg_abs_close_to_close']},
                {"Date": "Avg Abs O→C", "C2O": summary['avg_abs_open_to_close']},
                {"Date": "Positive Days", "C2O": f"{summary['positive_days']} ({summary['positive_pct']}%)"},
                {"Date": "Avg C→O (pos)", "C2O": summary.get('avg_pos_close_to_open', 0)},
                {"Date": "Avg C→C (pos)", "C2O": summary.get('avg_pos_close_to_close', 0)},
                {"Date": "Avg O→C (pos)", "C2O": summary.get('avg_pos_open_to_close', 0)},
                {"Date": "Negative Days", "C2O": f"{summary['negative_days']} ({summary['negative_pct']}%)"},
                {"Date": "Avg C→O (neg)", "C2O": summary.get('avg_neg_close_to_open', 0)},
                {"Date": "Avg C→C (neg)", "C2O": summary.get('avg_neg_close_to_close', 0)},
                {"Date": "Avg O→C (neg)", "C2O": summary.get('avg_neg_open_to_close', 0)},
            ])

            df_full = pd.concat([df_plot, summary_rows], ignore_index=True)
            output_file = output_dir / f"{ticker}_earnings.csv"
            df_full.to_csv(output_file, index=False)
            print(f"\n📁 CSV saved to: {output_file}")

            # Plot → external window
            plot_results(ticker, df_plot, show=True)

        else:
            summaries.append({
                "Ticker": ticker,
                "Avg % C→O": summary["avg_abs_close_to_open"],
                "Avg % C→C": summary["avg_abs_close_to_close"],
                "Avg % O→C": summary["avg_abs_open_to_close"],
                "% Positive": summary["positive_pct"],
                "% Negative": summary["negative_pct"]
            })
            enriched_dict[ticker] = enriched

    if multiple_mode and summaries:
        df = pd.DataFrame(summaries)
        df = df.sort_values(by="Avg % C→O", ascending=False).reset_index(drop=True)
        top20 = df.head(20)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_file = output_dir / f"top20_avg_abs_C2O_{timestamp}.csv"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Top 20 Stocks by Avg Absolute C→O %\n")
            top20.to_csv(f, index=False)

        print(f"\n📁 CSV saved to: {output_file}")
        print(f"🖼️  Plots saved to: {plots_dir}")

    elif not summaries and multiple_mode:
        print("\n❌ No valid data collected from any ticker.")


if __name__ == "__main__":
    main()
