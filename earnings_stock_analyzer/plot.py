import matplotlib.pyplot as plt
import seaborn as sns

def plot_results(ticker, df_plot):
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
