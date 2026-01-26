import csv
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ------------------------------
# Paths
# ------------------------------
THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parent.parent if THIS.parent.name == "scripts" else THIS.parent
ANALYSIS_DIR = PROJECT_ROOT / "output" / "analysis"

# Backtest (strategy) detailed CSV (must contain: date, equity_after, equity_before)
CSV_PATH = ANALYSIS_DIR / "momentum_top25_detailed_until2024.csv"

# Outputs
MONTHLY_CSV = ANALYSIS_DIR / "monthly_returns_vs_sp500_2018_2024.csv"
YEARLY_CSV = ANALYSIS_DIR / "yearly_returns_vs_sp500_2018_2024.csv"
FORWARD_CAGR_CSV = ANALYSIS_DIR / "forward_cagr_entry_month_vs_sp500_2018_2024.csv"

START_DATE = pd.Timestamp("2018-01-01")


# =====================================================================
# Helpers
# =====================================================================

def load_detailed(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"❌ Detailed CSV not found at: {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def download_sp500_daily(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """
    Download S&P 500 (^SPX) daily OHLC from Stooq and filter by [start, end].
    """
    print(f"\n📥 Downloading S&P 500 data ({start.date()}–{end.date()}) from Stooq...")
    url = "https://stooq.com/q/d/l/?s=^spx&i=d"
    spx = pd.read_csv(url)

    if spx.empty:
        raise RuntimeError("❌ Error: No data downloaded from Stooq.")

    spx["Date"] = pd.to_datetime(spx["Date"])
    spx = spx.sort_values("Date").reset_index(drop=True)

    spx = spx[(spx["Date"] >= start) & (spx["Date"] <= end)].copy()
    if spx.empty:
        raise RuntimeError("❌ Error: filtered S&P 500 range is empty.")

    return spx


def compute_cagr_from_equity(equity: pd.Series) -> float:
    """
    equity: indexed by datetime, values are equity level
    returns CAGR % over full span.
    """
    equity = equity.dropna()
    if equity.empty:
        return float("nan")
    start_dt = equity.index[0]
    end_dt = equity.index[-1]
    num_years = (end_dt - start_dt).days / 365.25
    if num_years <= 0:
        return float("nan")
    total_mult = float(equity.iloc[-1] / equity.iloc[0])
    return (total_mult ** (1.0 / num_years) - 1.0) * 100.0


def compute_forward_cagr(
    equity: pd.Series,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    min_years: float = 0.25
) -> float:
    """
    Forward CAGR from start_date to end_date (both within equity index).

    Note: annualizing very short horizons can explode, so we return NaN if
    horizon < min_years (default ~3 months).
    """
    eq = equity[(equity.index >= start_date) & (equity.index <= end_date)].dropna()
    if len(eq) < 2:
        return float("nan")

    start_dt = eq.index[0]
    end_dt = eq.index[-1]
    num_years = (end_dt - start_dt).days / 365.25
    if num_years <= 0 or num_years < min_years:
        return float("nan")

    total_mult = float(eq.iloc[-1] / eq.iloc[0])
    return (total_mult ** (1.0 / num_years) - 1.0) * 100.0


# =====================================================================
# Strategy series
# =====================================================================

def strategy_daily_equity(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """
    Build a daily equity series for the strategy using the last equity_after per date.
    """
    df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
    if df.empty:
        raise ValueError("❌ Strategy DF empty after date filter.")

    equity_daily = df.groupby("date")["equity_after"].last().sort_index()
    return equity_daily


def compute_strategy_monthly_returns(equity_daily: pd.Series) -> pd.Series:
    per = equity_daily.index.to_period("M")
    start_equity = equity_daily.groupby(per).first()
    end_equity = equity_daily.groupby(per).last()
    monthly_ret = (end_equity / start_equity) - 1.0
    monthly_ret.index = monthly_ret.index.astype(str)
    monthly_ret.name = "strategy_monthly_return"
    return monthly_ret


def compute_strategy_yearly_returns(equity_daily: pd.Series) -> pd.Series:
    per = equity_daily.index.to_period("Y")
    start_equity = equity_daily.groupby(per).first()
    end_equity = equity_daily.groupby(per).last()
    yearly_ret = (end_equity / start_equity) - 1.0
    yearly_ret.index = yearly_ret.index.astype(str)
    yearly_ret.name = "strategy_yearly_return"
    return yearly_ret


# =====================================================================
# S&P 500 returns
# =====================================================================

def compute_sp500_equity_series(spx: pd.DataFrame) -> pd.Series:
    spx = spx.sort_values("Date").copy()
    first_open = float(spx.iloc[0]["Open"])
    eq = spx["Close"].astype(float) / first_open
    eq.index = spx["Date"]
    return eq


def compute_sp500_monthly_returns(spx: pd.DataFrame) -> pd.Series:
    spx = spx.sort_values("Date").copy()
    per = spx["Date"].dt.to_period("M")
    monthly = spx.groupby(per).agg(open_first=("Open", "first"), close_last=("Close", "last"))
    monthly_ret = (monthly["close_last"].astype(float) / monthly["open_first"].astype(float)) - 1.0
    monthly_ret.index = monthly_ret.index.astype(str)
    monthly_ret.name = "sp500_monthly_return"
    return monthly_ret


def compute_sp500_yearly_returns(spx: pd.DataFrame) -> pd.Series:
    spx = spx.sort_values("Date").copy()
    per = spx["Date"].dt.to_period("Y")
    yearly = spx.groupby(per).agg(open_first=("Open", "first"), close_last=("Close", "last"))
    yearly_ret = (yearly["close_last"].astype(float) / yearly["open_first"].astype(float)) - 1.0
    yearly_ret.index = yearly_ret.index.astype(str)
    yearly_ret.name = "sp500_yearly_return"
    return yearly_ret


# =====================================================================
# Printing + plots
# =====================================================================

def print_monthly_table_and_summary(strat_m: pd.Series, spx_m: pd.Series):
    common = strat_m.index.intersection(spx_m.index)
    strat_m = strat_m.loc[common]
    spx_m = spx_m.loc[common]

    print("\n" + "-" * 80)
    print("2018–2024 — Monthly returns (Strategy vs S&P 500)")
    print("-" * 80)
    print("month, strategy_monthly_%, sp500_monthly_%, diff_pp")
    for m in common:
        s = strat_m.loc[m] * 100.0
        b = spx_m.loc[m] * 100.0
        d = s - b
        print(f"{m}, {s: .3f}, {b: .3f}, {d: .3f}")

    outperform_pct = (strat_m > spx_m).mean() * 100.0
    print("\nSUMMARY (monthly):")
    print(f"% months Strategy > S&P 500: {outperform_pct:.1f}%")
    print(f"Mean Strategy monthly return: {(strat_m.mean() * 100.0):.3f}%")
    print(f"Mean S&P 500 monthly return:  {(spx_m.mean() * 100.0):.3f}%")


def print_yearly_table_and_summary(strat_y: pd.Series, spx_y: pd.Series):
    common = strat_y.index.intersection(spx_y.index)
    strat_y = strat_y.loc[common]
    spx_y = spx_y.loc[common]

    print("\n" + "-" * 80)
    print("2018–2024 — Yearly returns (Strategy vs S&P 500)")
    print("-" * 80)
    print("year, strategy_yearly_%, sp500_yearly_%, diff_pp")
    for y in common:
        s = strat_y.loc[y] * 100.0
        b = spx_y.loc[y] * 100.0
        d = s - b
        print(f"{y}, {s: .3f}, {b: .3f}, {d: .3f}")

    outperform_pct = (strat_y > spx_y).mean() * 100.0
    print("\nSUMMARY (yearly):")
    print(f"% years Strategy > S&P 500: {outperform_pct:.1f}%")
    print(f"Mean Strategy yearly return: {(strat_y.mean() * 100.0):.3f}%")
    print(f"Mean S&P 500 yearly return:  {(spx_y.mean() * 100.0):.3f}%")


def kde_gaussian(samples: np.ndarray, xs: np.ndarray) -> np.ndarray:
    samples = np.asarray(samples, dtype=float)
    n = samples.size
    if n < 2:
        return np.zeros_like(xs)

    std = samples.std(ddof=1)
    if std == 0:
        std = 1e-6
    h = 1.06 * std * (n ** (-1 / 5))
    if h <= 0:
        h = 1e-3

    diffs = (xs[:, None] - samples[None, :]) / h
    dens = np.exp(-0.5 * diffs ** 2).sum(axis=1) / (n * h * np.sqrt(2 * np.pi))
    return dens


def plot_bell_kde(strat_vals_pct: np.ndarray, spx_vals_pct: np.ndarray, title: str, xlabel: str):
    strat_vals_pct = np.asarray(strat_vals_pct, dtype=float)
    spx_vals_pct = np.asarray(spx_vals_pct, dtype=float)

    xs_min = float(min(strat_vals_pct.min(), spx_vals_pct.min()))
    xs_max = float(max(strat_vals_pct.max(), spx_vals_pct.max()))
    xs = np.linspace(xs_min, xs_max, 600)

    dens_s = kde_gaussian(strat_vals_pct, xs)
    dens_b = kde_gaussian(spx_vals_pct, xs)

    plt.figure(figsize=(10, 6))

    # KDE lines (capture colors)
    line_s, = plt.plot(xs, dens_s, label="Strategy KDE")
    line_b, = plt.plot(xs, dens_b, label="S&P 500 KDE")

    strat_color = line_s.get_color()
    spx_color = line_b.get_color()

    # Mean lines (match each KDE color)
    plt.axvline(
        strat_vals_pct.mean(),
        linestyle="--",
        linewidth=2,
        color=strat_color,
        label=f"Strategy mean = {strat_vals_pct.mean():.2f}%"
    )
    plt.axvline(
        spx_vals_pct.mean(),
        linestyle="--",
        linewidth=2,
        color=spx_color,
        label=f"S&P 500 mean = {spx_vals_pct.mean():.2f}%"
    )

    plt.xlabel(xlabel)
    plt.ylabel("Density")
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()



def plot_equity_curve(strategy_eq: pd.Series, spx_eq: pd.Series, analysis_end: pd.Timestamp):
    common = strategy_eq.index.intersection(spx_eq.index)
    common = common[common <= analysis_end]
    strat = strategy_eq.loc[common]
    spx = spx_eq.loc[common]

    strat_rebased = strat / float(strat.iloc[0])
    spx_rebased = spx / float(spx.iloc[0])

    plt.figure(figsize=(10, 6))
    plt.plot(common, strat_rebased, label="Strategy (rebased)")
    plt.plot(common, spx_rebased, label="S&P 500 (rebased)")
    plt.xlabel("Date")
    plt.ylabel("Normalized equity (base 1.0)")
    plt.title(f"2018–{analysis_end.year} — Equity curve: Strategy vs S&P 500")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_monthly_returns_by_month(strat_m: pd.Series, spx_m: pd.Series):
    common = strat_m.index.intersection(spx_m.index)
    strat_vals = (strat_m.loc[common] * 100.0).values
    spx_vals = (spx_m.loc[common] * 100.0).values

    plt.figure(figsize=(14, 6))
    plt.plot(common, strat_vals, marker="o", linewidth=1, label="Strategy monthly %")
    plt.plot(common, spx_vals, marker="o", linewidth=1, label="S&P 500 monthly %")
    plt.axhline(0.0, linewidth=1)
    plt.xlabel("Month (YYYY-MM)")
    plt.ylabel("Monthly return (%)")
    plt.title("2018–2024 — Monthly returns by month: Strategy vs S&P 500")
    plt.grid(True)
    plt.legend()
    plt.xticks(rotation=90, fontsize=7)
    plt.tight_layout()
    plt.show()


# =====================================================================
# MAIN
# =====================================================================

def main():
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_detailed(CSV_PATH)

    # ✅ Dynamically set ANALYSIS_END to the last available strategy trading date
    ANALYSIS_END = df["date"].max()
    if pd.isna(ANALYSIS_END):
        raise RuntimeError("❌ Could not determine ANALYSIS_END from strategy CSV.")

    print("\n" + "=" * 80)
    print(f"ANALYSIS: 2018–{ANALYSIS_END.year} ONLY (Strategy vs S&P 500) — END={ANALYSIS_END.date()}")
    print("=" * 80)

    # Strategy daily equity (trimmed to analysis window)
    strat_eq_daily = strategy_daily_equity(df, START_DATE, ANALYSIS_END)

    # S&P daily (same window)
    spx = download_sp500_daily(START_DATE, ANALYSIS_END)
    spx_eq = compute_sp500_equity_series(spx)

    # Align both equity series on common daily dates
    common_daily = strat_eq_daily.index.intersection(spx_eq.index)
    common_daily = common_daily[common_daily <= ANALYSIS_END]

    strat_eq_aligned = strat_eq_daily.loc[common_daily]
    spx_eq_aligned = spx_eq.loc[common_daily]

    # Equity curve plot + CAGR
    plot_equity_curve(strat_eq_aligned, spx_eq_aligned, ANALYSIS_END)
    strat_cagr = compute_cagr_from_equity(strat_eq_aligned)
    spx_cagr = compute_cagr_from_equity(spx_eq_aligned)

    print("\nCAGR:")
    print(f"Strategy CAGR: {strat_cagr:.3f}%/year")
    print(f"S&P 500 CAGR:  {spx_cagr:.3f}%/year")
    print(f"Difference:    {(strat_cagr - spx_cagr):.3f} pp")

    # Monthly: table + month-by-month plot + bell
    strat_m = compute_strategy_monthly_returns(strat_eq_aligned)
    spx_m = compute_sp500_monthly_returns(spx)

    print_monthly_table_and_summary(strat_m, spx_m)
    plot_monthly_returns_by_month(strat_m, spx_m)

    common_m = strat_m.index.intersection(spx_m.index)
    plot_bell_kde(
        strat_vals_pct=(strat_m.loc[common_m] * 100.0).values,
        spx_vals_pct=(spx_m.loc[common_m] * 100.0).values,
        title=f"2018–{ANALYSIS_END.year} — Bell plot (KDE) of MONTHLY returns: Strategy vs S&P 500",
        xlabel="Monthly return (%)",
    )

    # Yearly: table + bell
    strat_y = compute_strategy_yearly_returns(strat_eq_aligned)
    spx_y = compute_sp500_yearly_returns(spx)

    print_yearly_table_and_summary(strat_y, spx_y)

    common_y = strat_y.index.intersection(spx_y.index)
    plot_bell_kde(
        strat_vals_pct=(strat_y.loc[common_y] * 100.0).values,
        spx_vals_pct=(spx_y.loc[common_y] * 100.0).values,
        title=f"2018–{ANALYSIS_END.year} — Bell plot (KDE) of YEARLY returns: Strategy vs S&P 500",
        xlabel="Yearly return (%)",
    )

    # -----------------------------------------------------------------
    # Forward CAGR from each ENTRY MONTH to ANALYSIS_END
    # -----------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"FORWARD CAGR (entry month → {ANALYSIS_END.date()}): Strategy vs S&P 500")
    print("=" * 80)

    entry_months = strat_eq_aligned.index.to_period("M").unique()

    rows = []
    for m in entry_months:
        month_dates = strat_eq_aligned.index[strat_eq_aligned.index.to_period("M") == m]
        if len(month_dates) == 0:
            continue
        entry_date = month_dates[0]  # first trading day in that month (for strategy)

        strat_fwd = compute_forward_cagr(strat_eq_aligned, entry_date, ANALYSIS_END, min_years=0.25)
        spx_fwd = compute_forward_cagr(spx_eq_aligned, entry_date, ANALYSIS_END, min_years=0.25)

        rows.append({
            "entry_month": str(m),
            "entry_date": entry_date.date().isoformat(),
            "strategy_forward_cagr_pct": strat_fwd,
            "sp500_forward_cagr_pct": spx_fwd,
            "diff_pp": strat_fwd - spx_fwd,
        })

    fwd_df = pd.DataFrame(rows).dropna()

    print("entry_month, strategy_forward_cagr_%, sp500_forward_cagr_%, diff_pp")
    for _, r in fwd_df.iterrows():
        print(f"{r['entry_month']}, {r['strategy_forward_cagr_pct']: .3f}, {r['sp500_forward_cagr_pct']: .3f}, {r['diff_pp']: .3f}")

    outperform_pct = (fwd_df["strategy_forward_cagr_pct"] > fwd_df["sp500_forward_cagr_pct"]).mean() * 100.0
    print("\nSUMMARY (forward CAGR):")
    print(f"% entry months Strategy forward CAGR > S&P 500: {outperform_pct:.1f}%")
    print(f"Mean Strategy forward CAGR: {fwd_df['strategy_forward_cagr_pct'].mean():.3f}%")
    print(f"Mean S&P 500 forward CAGR:  {fwd_df['sp500_forward_cagr_pct'].mean():.3f}%")

    # Bell plot of forward CAGR distributions
    plot_bell_kde(
        strat_vals_pct=fwd_df["strategy_forward_cagr_pct"].values,
        spx_vals_pct=fwd_df["sp500_forward_cagr_pct"].values,
        title=f"2018–{ANALYSIS_END.year} — Bell plot (KDE) of FORWARD CAGR (entry month → {ANALYSIS_END.date()})",
        xlabel="Forward CAGR (% per year)",
    )

    # Save forward CAGR CSV
    fwd_df.to_csv(FORWARD_CAGR_CSV, index=False)
    print(f"\n📝 Forward CAGR CSV saved to: {FORWARD_CAGR_CSV}")

    # Save monthly/yearly CSVs
    monthly_df = pd.DataFrame({
        "month": common_m,
        "strategy_monthly_return_pct": (strat_m.loc[common_m] * 100.0).values,
        "sp500_monthly_return_pct": (spx_m.loc[common_m] * 100.0).values,
    })
    monthly_df["diff_pp"] = monthly_df["strategy_monthly_return_pct"] - monthly_df["sp500_monthly_return_pct"]
    monthly_df.to_csv(MONTHLY_CSV, index=False)
    print(f"\n📝 Monthly CSV saved to: {MONTHLY_CSV}")

    yearly_df = pd.DataFrame({
        "year": common_y,
        "strategy_yearly_return_pct": (strat_y.loc[common_y] * 100.0).values,
        "sp500_yearly_return_pct": (spx_y.loc[common_y] * 100.0).values,
    })
    yearly_df["diff_pp"] = yearly_df["strategy_yearly_return_pct"] - yearly_df["sp500_yearly_return_pct"]
    yearly_df.to_csv(YEARLY_CSV, index=False)
    print(f"📝 Yearly CSV saved to: {YEARLY_CSV}")


if __name__ == "__main__":
    main()
