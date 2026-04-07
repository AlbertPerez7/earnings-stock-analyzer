from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from earnings_stock_analyzer.plot import plot_equity_curve, plot_monthly_returns, plot_kde

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parent.parent if _THIS.parent.name == "scripts" else _THIS.parent
ANALYSIS_DIR = PROJECT_ROOT / "output" / "analysis"

CSV_PATH         = ANALYSIS_DIR / "momentum_top25_detailed_until2024.csv"
MONTHLY_CSV      = ANALYSIS_DIR / "monthly_returns_vs_sp500_2018_2024.csv"
YEARLY_CSV       = ANALYSIS_DIR / "yearly_returns_vs_sp500_2018_2024.csv"
FORWARD_CAGR_CSV = ANALYSIS_DIR / "forward_cagr_entry_month_vs_sp500_2018_2024.csv"

START_DATE = pd.Timestamp("2018-01-01")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_detailed(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Detailed CSV not found at: {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def download_sp500_daily(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Download S&P 500 (^SPX) daily OHLC from Stooq and filter to [start, end]."""
    logger.info("Downloading S&P 500 data (%s - %s) from Stooq...", start.date(), end.date())
    try:
        spx = pd.read_csv("https://stooq.com/q/d/l/?s=^spx&i=d")
    except Exception as exc:
        logger.warning("Stooq download failed (%s). Falling back to yfinance...", exc)
        return download_sp500_daily_yfinance(start, end)

    if spx.empty or "Date" not in spx.columns:
        logger.warning("No usable data downloaded from Stooq. Falling back to yfinance...")
        return download_sp500_daily_yfinance(start, end)

    spx["Date"] = pd.to_datetime(spx["Date"])
    spx = spx.sort_values("Date").reset_index(drop=True)
    spx = spx[(spx["Date"] >= start) & (spx["Date"] <= end)].copy()
    if spx.empty:
        raise RuntimeError("Filtered S&P 500 date range is empty.")
    return spx


def download_sp500_daily_yfinance(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Download S&P 500 (^GSPC) daily OHLC from yfinance and normalize columns."""
    yf.set_tz_cache_location(str(Path(tempfile.gettempdir()) / "earnings_stock_analyzer_yfinance_cache"))
    yf_end = end + pd.Timedelta(days=1)
    spx = yf.download(
        "^GSPC",
        start=start.strftime("%Y-%m-%d"),
        end=yf_end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=False,
    )
    if spx.empty:
        raise RuntimeError("No S&P 500 data downloaded from yfinance.")
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)
    spx = spx.reset_index().rename(columns={"index": "Date"})
    spx["Date"] = pd.to_datetime(spx["Date"])
    spx = spx[(spx["Date"] >= start) & (spx["Date"] <= end)].copy()
    if spx.empty:
        raise RuntimeError("Filtered yfinance S&P 500 date range is empty.")
    return spx


# ---------------------------------------------------------------------------
# Strategy equity series
# ---------------------------------------------------------------------------

def strategy_daily_equity(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.Series:
    """Return the last equity_after value per trading day within [start, end]."""
    df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
    if df.empty:
        raise ValueError("Strategy DataFrame is empty after date filter.")
    return df.groupby("date")["equity_after"].last().sort_index()


def compute_strategy_monthly_returns(equity_daily: pd.Series) -> pd.Series:
    per = equity_daily.index.to_period("M")
    monthly = (equity_daily.groupby(per).last() / equity_daily.groupby(per).first()) - 1.0
    monthly.index = monthly.index.astype(str)
    monthly.name = "strategy_monthly_return"
    return monthly


def compute_strategy_yearly_returns(equity_daily: pd.Series) -> pd.Series:
    per = equity_daily.index.to_period("Y")
    yearly = (equity_daily.groupby(per).last() / equity_daily.groupby(per).first()) - 1.0
    yearly.index = yearly.index.astype(str)
    yearly.name = "strategy_yearly_return"
    return yearly


# ---------------------------------------------------------------------------
# S&P 500 equity series
# ---------------------------------------------------------------------------

def compute_sp500_equity_series(spx: pd.DataFrame) -> pd.Series:
    spx = spx.sort_values("Date").copy()
    eq = spx["Close"].astype(float) / float(spx.iloc[0]["Open"])
    eq.index = spx["Date"]
    return eq


def compute_sp500_monthly_returns(spx: pd.DataFrame) -> pd.Series:
    spx = spx.sort_values("Date").copy()
    per = spx["Date"].dt.to_period("M")
    monthly = spx.groupby(per).agg(open_first=("Open", "first"), close_last=("Close", "last"))
    ret = (monthly["close_last"].astype(float) / monthly["open_first"].astype(float)) - 1.0
    ret.index = ret.index.astype(str)
    ret.name = "sp500_monthly_return"
    return ret


def compute_sp500_yearly_returns(spx: pd.DataFrame) -> pd.Series:
    spx = spx.sort_values("Date").copy()
    per = spx["Date"].dt.to_period("Y")
    yearly = spx.groupby(per).agg(open_first=("Open", "first"), close_last=("Close", "last"))
    ret = (yearly["close_last"].astype(float) / yearly["open_first"].astype(float)) - 1.0
    ret.index = ret.index.astype(str)
    ret.name = "sp500_yearly_return"
    return ret


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------

def compute_cagr_from_equity(equity: pd.Series) -> float:
    """Return annualised CAGR (%) over the full span of the equity series."""
    equity = equity.dropna()
    if equity.empty:
        return float("nan")
    num_years = (equity.index[-1] - equity.index[0]).days / 365.25
    if num_years <= 0:
        return float("nan")
    return (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / num_years) - 1.0) * 100.0


def compute_forward_cagr(
    equity: pd.Series,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    min_years: float = 0.25,
) -> float:
    """
    CAGR (%) from start_date to end_date within the equity series.
    Returns NaN if the horizon is shorter than min_years (~3 months by default)
    to avoid exploding annualisation on very short windows.
    """
    eq = equity[(equity.index >= start_date) & (equity.index <= end_date)].dropna()
    if len(eq) < 2:
        return float("nan")
    num_years = (eq.index[-1] - eq.index[0]).days / 365.25
    if num_years < min_years:
        return float("nan")
    return (float(eq.iloc[-1] / eq.iloc[0]) ** (1.0 / num_years) - 1.0) * 100.0


# ---------------------------------------------------------------------------
# Print tables
# ---------------------------------------------------------------------------

def _print_returns_table(
    strat: pd.Series,
    spx: pd.Series,
    period_label: str,
    col_label: str,
) -> None:
    common = strat.index.intersection(spx.index)
    strat  = strat.loc[common]
    spx    = spx.loc[common]

    print("\n" + "-" * 80)
    print(f"2018-2024 — {period_label} returns (Strategy vs S&P 500)")
    print("-" * 80)
    print(f"{col_label}, strategy_{col_label}_%, sp500_{col_label}_%, diff_pp")
    for period in common:
        s = strat.loc[period] * 100.0
        b = spx.loc[period]   * 100.0
        print(f"{period}, {s: .3f}, {b: .3f}, {s - b: .3f}")

    outperform = (strat > spx).mean() * 100.0
    print(f"\nSUMMARY ({col_label}):")
    print(f"% {period_label}s Strategy > S&P 500: {outperform:.1f}%")
    print(f"Mean Strategy {col_label} return: {(strat.mean() * 100.0):.3f}%")
    print(f"Mean S&P 500  {col_label} return: {(spx.mean()   * 100.0):.3f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_detailed(CSV_PATH)
    ANALYSIS_END = df["date"].max()
    if pd.isna(ANALYSIS_END):
        raise RuntimeError("Could not determine ANALYSIS_END from strategy CSV.")

    print("\n" + "=" * 80)
    print(f"ANALYSIS: 2018-{ANALYSIS_END.year} (Strategy vs S&P 500) — END={ANALYSIS_END.date()}")
    print("=" * 80)

    # Strategy equity
    strat_eq_daily = strategy_daily_equity(df, START_DATE, ANALYSIS_END)

    # S&P 500
    spx    = download_sp500_daily(START_DATE, ANALYSIS_END)
    spx_eq = compute_sp500_equity_series(spx)

    # Align on common trading days
    common_daily     = strat_eq_daily.index.intersection(spx_eq.index)
    common_daily     = common_daily[common_daily <= ANALYSIS_END]
    strat_eq_aligned = strat_eq_daily.loc[common_daily]
    spx_eq_aligned   = spx_eq.loc[common_daily]

    # --- Equity curve + CAGR ---
    plot_equity_curve(strat_eq_aligned, spx_eq_aligned, ANALYSIS_END)

    strat_cagr = compute_cagr_from_equity(strat_eq_aligned)
    spx_cagr   = compute_cagr_from_equity(spx_eq_aligned)
    print("\nCAGR:")
    print(f"Strategy CAGR: {strat_cagr:.3f}%/year")
    print(f"S&P 500 CAGR:  {spx_cagr:.3f}%/year")
    print(f"Difference:    {strat_cagr - spx_cagr:.3f} pp")

    # --- Monthly ---
    strat_m  = compute_strategy_monthly_returns(strat_eq_aligned)
    spx_m    = compute_sp500_monthly_returns(spx)
    common_m = strat_m.index.intersection(spx_m.index)

    _print_returns_table(strat_m, spx_m, "Monthly", "month")
    plot_monthly_returns(strat_m, spx_m)
    plot_kde(
        strat_vals_pct=(strat_m.loc[common_m] * 100.0).values,
        spx_vals_pct=(spx_m.loc[common_m] * 100.0).values,
        title=f"2018-{ANALYSIS_END.year} — KDE of monthly returns: Strategy vs S&P 500",
        xlabel="Monthly return (%)",
    )

    # --- Yearly ---
    strat_y  = compute_strategy_yearly_returns(strat_eq_aligned)
    spx_y    = compute_sp500_yearly_returns(spx)
    common_y = strat_y.index.intersection(spx_y.index)

    _print_returns_table(strat_y, spx_y, "Yearly", "year")
    plot_kde(
        strat_vals_pct=(strat_y.loc[common_y] * 100.0).values,
        spx_vals_pct=(spx_y.loc[common_y] * 100.0).values,
        title=f"2018-{ANALYSIS_END.year} — KDE of yearly returns: Strategy vs S&P 500",
        xlabel="Yearly return (%)",
    )

    # --- Forward CAGR ---
    print("\n" + "=" * 80)
    print(f"FORWARD CAGR (entry month -> {ANALYSIS_END.date()}): Strategy vs S&P 500")
    print("=" * 80)

    rows = []
    for m in strat_eq_aligned.index.to_period("M").unique():
        month_dates = strat_eq_aligned.index[strat_eq_aligned.index.to_period("M") == m]
        if len(month_dates) == 0:
            continue
        entry_date = month_dates[0]
        strat_fwd = compute_forward_cagr(strat_eq_aligned, entry_date, ANALYSIS_END)
        spx_fwd   = compute_forward_cagr(spx_eq_aligned,  entry_date, ANALYSIS_END)
        rows.append({
            "entry_month":               str(m),
            "entry_date":                entry_date.date().isoformat(),
            "strategy_forward_cagr_pct": strat_fwd,
            "sp500_forward_cagr_pct":    spx_fwd,
            "diff_pp":                   strat_fwd - spx_fwd,
        })

    fwd_df = pd.DataFrame(rows).dropna()

    print("entry_month, strategy_forward_cagr_%, sp500_forward_cagr_%, diff_pp")
    for _, row in fwd_df.iterrows():
        print(
            f"{row['entry_month']}, "
            f"{row['strategy_forward_cagr_pct']: .3f}, "
            f"{row['sp500_forward_cagr_pct']: .3f}, "
            f"{row['diff_pp']: .3f}"
        )

    outperform = (fwd_df["strategy_forward_cagr_pct"] > fwd_df["sp500_forward_cagr_pct"]).mean() * 100.0
    print("\nSUMMARY (forward CAGR):")
    print(f"% entry months Strategy forward CAGR > S&P 500: {outperform:.1f}%")
    print(f"Mean Strategy forward CAGR: {fwd_df['strategy_forward_cagr_pct'].mean():.3f}%")
    print(f"Mean S&P 500 forward CAGR:  {fwd_df['sp500_forward_cagr_pct'].mean():.3f}%")

    plot_kde(
        strat_vals_pct=fwd_df["strategy_forward_cagr_pct"].values,
        spx_vals_pct=fwd_df["sp500_forward_cagr_pct"].values,
        title=f"2018-{ANALYSIS_END.year} — KDE of forward CAGR (entry month -> {ANALYSIS_END.date()})",
        xlabel="Forward CAGR (%/year)",
    )

    # --- Save CSVs ---
    fwd_df.to_csv(FORWARD_CAGR_CSV, index=False)
    logger.info("Forward CAGR saved to: %s", FORWARD_CAGR_CSV)

    monthly_df = pd.DataFrame({
        "month":                       common_m,
        "strategy_monthly_return_pct": (strat_m.loc[common_m] * 100.0).values,
        "sp500_monthly_return_pct":    (spx_m.loc[common_m]   * 100.0).values,
    })
    monthly_df["diff_pp"] = (
        monthly_df["strategy_monthly_return_pct"] - monthly_df["sp500_monthly_return_pct"]
    )
    monthly_df.to_csv(MONTHLY_CSV, index=False)
    logger.info("Monthly returns saved to: %s", MONTHLY_CSV)

    yearly_df = pd.DataFrame({
        "year":                       common_y,
        "strategy_yearly_return_pct": (strat_y.loc[common_y] * 100.0).values,
        "sp500_yearly_return_pct":    (spx_y.loc[common_y]   * 100.0).values,
    })
    yearly_df["diff_pp"] = (
        yearly_df["strategy_yearly_return_pct"] - yearly_df["sp500_yearly_return_pct"]
    )
    yearly_df.to_csv(YEARLY_CSV, index=False)
    logger.info("Yearly returns saved to: %s", YEARLY_CSV)


if __name__ == "__main__":
    main()
