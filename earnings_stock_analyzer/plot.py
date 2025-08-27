import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def plot_results(ticker, df_plot, show=True):
    df_plot = df_plot.sort_values(by="Date").copy()
    df_plot["Date"] = pd.to_datetime(df_plot["Date"])

    fig, ax = plt.subplots(figsize=(14, 6))  # ✅ crea fig explícitament

    sns.lineplot(data=df_plot, x='Date', y='C2O', label='Close→Open', ax=ax)
    sns.lineplot(data=df_plot, x='Date', y='C2C', label='Close→Close', ax=ax)
    sns.lineplot(data=df_plot, x='Date', y='O2C', label='Open→Close', ax=ax)

    ax.set_title(f'{ticker} - Earnings Day % Changes')
    ax.set_xlabel("Date")
    ax.set_ylabel("% Change")

    ax.set_xticks(df_plot["Date"])
    ax.set_xticklabels(df_plot["Date"].dt.strftime("%Y-%m-%d"), rotation=45, fontsize=8, ha='center')

    ax.legend()
    ax.grid(True)
    fig.tight_layout()

    if show:
        plt.show()

    return fig  #  per poder fer savefig(...)
