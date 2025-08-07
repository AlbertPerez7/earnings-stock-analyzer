from earnings_stock_analyzer.cli import get_user_ticker
from earnings_stock_analyzer.fetch import fetch_stock_data, fetch_earnings_dates
from earnings_stock_analyzer.analyzer import analyze_absolute_change
from earnings_stock_analyzer.plot import plot_results


def main():
    api_key = "YOUR_API_KEY"  # Replace with your real Alpha Vantage API key

    while True:
        ticker = get_user_ticker()
        try:
            stock_data = fetch_stock_data(ticker)
            earnings_dates = fetch_earnings_dates(ticker, api_key)
            break  # exit loop if both succeeded
        except ValueError as ve:
            print(f"\n❌ Error: {ve}")
            print("Please enter a valid stock ticker symbol.\n")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("Please try again.\n")

    # If we reach here, we have valid stock_data and earnings_dates
    results = analyze_absolute_change(stock_data, earnings_dates)

    print("\n📊 AVERAGE ABSOLUTE PERCENTAGE CHANGE AFTER EARNINGS:")
    print(f"• Close → Next Open: {results['avg_abs'][0]:.2f}%")
    print(f"• Close → Next Close: {results['avg_abs'][1]:.2f}%")
    print(f"• Next Open → Next Close: {results['avg_abs'][2]:.2f}%")

    print("\n📈 AVERAGE FOR POSITIVE DAYS:")
    print(f"• Close → Next Open: {results['avg_pos'][0]:.2f}%")
    print(f"• Close → Next Close: {results['avg_pos'][1]:.2f}%")
    print(f"• Next Open → Next Close: {results['avg_pos'][2]:.2f}%")

    print("\n📉 AVERAGE FOR NEGATIVE DAYS:")
    print(f"• Close → Next Open: {results['avg_neg'][0]:.2f}%")
    print(f"• Close → Next Close: {results['avg_neg'][1]:.2f}%")
    print(f"• Next Open → Next Close: {results['avg_neg'][2]:.2f}%")

    print(f"\n✅ STRATEGY SUCCESS RATE (Close → Next Open ≥ 10%): {results['success_rate']:.2f}%")
    print(f"✅ STRATEGY SUCCESS RATE (Close → Next Open ≥ 6%): {results['success_rate_8']:.2f}%")
    print(f"\n📊 % of Earnings Days Positive (Close → Next Open): {results['pos_pct']:.2f}%")
    print(f"📊 % of Earnings Days Negative (Close → Next Open): {results['neg_pct']:.2f}%")
    print(f"\n📈 % Trend Continuation (strict): {results['trend_continuation_pct']:.2f}%")
    print(f"📈 Average Extra Gain if Trend Continued: {results['avg_trend_gain']:.2f}%")

    plot_results(ticker, results["df_plot"])


if __name__ == "__main__":
    main()
