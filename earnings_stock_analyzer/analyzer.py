### earnings_stock_analyzer/analyzer.py
import pandas as pd

def analyze_absolute_change(df, earnings_dates):
    abs_c2o, abs_c2c, abs_o2c = [], [], []
    pos_c2o, neg_c2o = [], []
    pos_c2c, neg_c2c = [], []
    pos_o2c, neg_o2c = [], []
    success_count = 0
    success_count_8 = 0
    total_valid = 0
    positive_c2o_days = 0
    negative_c2o_days = 0
    trend_continuation_count = 0
    trend_continuation_gains = []
    results_plot = []

    for fecha in earnings_dates:
        fila = df[df['Date'] == fecha]
        if not fila.empty:
            close = fila['Close'].values[0]
            next_open = fila['Next_Open'].values[0]
            next_close = fila['Next_Close'].values[0]

            if pd.notna(next_open) and pd.notna(next_close):
                c2o = (next_open - close) / close * 100
                c2c = (next_close - close) / close * 100
                o2c = (next_close - next_open) / next_open * 100

                abs_c2o.append(abs(c2o))
                abs_c2c.append(abs(c2c))
                abs_o2c.append(abs(o2c))

                results_plot.append({'Date': fecha, 'C2O': c2o, 'C2C': c2c, 'O2C': o2c})

                if c2o > 0:
                    pos_c2o.append(c2o)
                    positive_c2o_days += 1
                elif c2o < 0:
                    neg_c2o.append(c2o)
                    negative_c2o_days += 1

                pos_c2c.append(c2c) if c2c >= 0 else neg_c2c.append(c2c)
                pos_o2c.append(o2c) if o2c >= 0 else neg_o2c.append(o2c)

                if (c2o > 0 and c2c > c2o) or (c2o < 0 and c2c < c2o):
                    trend_continuation_count += 1
                    trend_continuation_gains.append(c2c - c2o)

                total_valid += 1
                if abs(c2o) >= 10:
                    success_count += 1
                if abs(c2o) >= 6:
                    success_count_8 += 1

                print(f"Earnings Date: {fecha.date()}, Close→Open: {c2o:+.2f}%, Close→Close: {c2c:+.2f}%, Open→Close: {o2c:+.2f}%")
        else:
            print(f"No data for earnings date {fecha.date()}.")

    def avg(lst): return sum(lst) / len(lst) if lst else 0

    return {
        "avg_abs": (avg(abs_c2o), avg(abs_c2c), avg(abs_o2c)),
        "avg_pos": (avg(pos_c2o), avg(pos_c2c), avg(pos_o2c)),
        "avg_neg": (avg(neg_c2o), avg(neg_c2c), avg(neg_o2c)),
        "success_rate": (success_count / total_valid * 100) if total_valid else 0,
        "success_rate_8": (success_count_8 / total_valid * 100) if total_valid else 0,
        "pos_pct": (positive_c2o_days / total_valid * 100) if total_valid else 0,
        "neg_pct": (negative_c2o_days / total_valid * 100) if total_valid else 0,
        "trend_continuation_pct": (trend_continuation_count / total_valid * 100) if total_valid else 0,
        "avg_trend_gain": avg(trend_continuation_gains),
        "df_plot": pd.DataFrame(results_plot)
    }
