import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Demanar el ticker de l'acció
ticker = input("Enter the stock ticker symbol: ").upper()

# Introdueix aquí la teva API Key d'Alpha Vantage
api_key = 'YOUR_API_KEY'  # Substitueix-ho per la teva clau

# Definir dates
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = '1700-01-01'

# Descarregar dades de Yahoo Finance
try:
    print(f"Fetching stock data for {ticker}...")
    data = yf.Ticker(ticker).history(start=start_date, end=end_date)
    if data.empty:
        print("No data found.")
        exit()

    data['Percent Change'] = data['Close'].pct_change() * 100
    data['Next_Open'] = data['Open'].shift(-1)
    data['Next_Close'] = data['Close'].shift(-1)
    data.reset_index(inplace=True)

except Exception as e:
    print(f"Error downloading stock data: {e}")
    exit()

# Preparar dates
data['Date'] = pd.to_datetime(data['Date'], utc=True).dt.tz_convert(None).dt.normalize()
data.sort_values(by='Date', inplace=True)

# Descarregar dades d’earnings amb Alpha Vantage
earnings_url = f'https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={api_key}'
try:
    response = requests.get(earnings_url)
    earnings_data = response.json()
    if 'quarterlyEarnings' not in earnings_data:
        print("No earnings data found.")
        exit()

    earnings_df = pd.DataFrame(earnings_data['quarterlyEarnings'])
    earnings_df['reportedDate'] = pd.to_datetime(earnings_df['reportedDate'])

    # Filtrar només earnings amb 4 mesos (120 dies) o més d'antiguitat
    min_age_days = 120
    today = datetime.now().date()
    earnings_dates = [
        d.normalize() for d in earnings_df['reportedDate']
        if (today - d.date()).days >= min_age_days
    ]

    print("Earnings data downloaded successfully.")
except Exception as e:
    print(f"Error fetching earnings data: {e}")
    exit()

# Funció d’anàlisi de variacions percentuals
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

                if c2c >= 0:
                    pos_c2c.append(c2c)
                else:
                    neg_c2c.append(c2c)
                if o2c >= 0:
                    pos_o2c.append(o2c)
                else:
                    neg_o2c.append(o2c)

                if (c2o > 0 and c2c > c2o) or (c2o < 0 and c2c < c2o):
                    trend_continuation_count += 1
                    trend_continuation_gains.append(c2c - c2o)

                total_valid += 1
                if abs(c2o) >= 10:
                    success_count += 1
                if abs(c2o) >= 6:
                    success_count_8 += 1

                print(f"Earnings Date: {fecha.date()}, "
                      f"Close→Open: {c2o:+.2f}%, "
                      f"Close→Close: {c2c:+.2f}%, "
                      f"Open→Close: {o2c:+.2f}%")
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

# Executar l'anàlisi
results = analyze_absolute_change(data, earnings_dates)

# Mostrar resultats
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

# 🔍 Visualització
df_plot = results["df_plot"]

plt.figure(figsize=(10, 5))
sns.lineplot(data=df_plot, x='Date', y='C2O', label='Close→Open')
sns.lineplot(data=df_plot, x='Date', y='C2C', label='Close→Close')
sns.lineplot(data=df_plot, x='Date', y='O2C', label='Open→Close')
plt.title(f'{ticker} - Earnings Day % Changes')
plt.xlabel("Date")
plt.ylabel("% Change")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
