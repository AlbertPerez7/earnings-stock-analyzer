from __future__ import annotations

from pathlib import Path
import math
import tempfile
import warnings

import numpy as np
import pandas as pd
from scipy import stats

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

try:
    import statsmodels.api as sm
except Exception:  # pragma: no cover
    sm = None


TRADING_DAYS = 252
BENCHMARK_TICKER = "SPY"   # can be changed to "^GSPC"
ROLLING_WINDOW = 63        # ~ 3 months
YFINANCE_CACHE_DIR = Path(tempfile.gettempdir()) / "earnings_stock_analyzer_yfinance_cache"
STATISTICAL_ANALYSIS_DIR_NAME = "statistical_analysis"


def infer_project_root() -> Path:
    cwd = Path.cwd().resolve()
    candidates = [cwd, cwd / "earnings-stock-analyzer"]
    for candidate in candidates:
        if (candidate / "output" / "analysis" / "momentum_top25_detailed_until2024.csv").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find output/analysis/momentum_top25_detailed_until2024.csv. "
        "Run this script from the project root."
    )


def load_strategy_data(project_root: Path) -> pd.DataFrame:
    path = project_root / "output" / "analysis" / "momentum_top25_detailed_until2024.csv"
    df = pd.read_csv(path)

    required_cols = {"date", "trade_return_pct", "avg_daily_return_pct"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path.name}: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)

    df["strategy_daily_return"] = pd.to_numeric(df["avg_daily_return_pct"], errors="coerce") / 100.0
    df["trade_return_decimal"] = pd.to_numeric(df["trade_return_pct"], errors="coerce") / 100.0

    if "equity_after" in df.columns:
        df["equity_after"] = pd.to_numeric(df["equity_after"], errors="coerce")

    return df


def download_benchmark_prices(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    if yf is None:
        raise ImportError("yfinance is not installed. Install it with: pip install yfinance")

    YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))

    benchmark = yf.download(
        BENCHMARK_TICKER,
        start=(start_date - pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
        end=(end_date + pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )

    if benchmark.empty:
        raise ValueError(f"No data downloaded for benchmark {BENCHMARK_TICKER}")

    close = benchmark["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.squeeze()

    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.dropna()

    out = pd.DataFrame({"date": close.index, "benchmark_close": close.values})
    out["benchmark_return"] = out["benchmark_close"].pct_change()
    out = out.dropna().reset_index(drop=True)
    return out


def build_strategy_daily_frame(strategy_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the strategy on the full benchmark trading calendar.

    Important:
    avg_daily_return_pct is already the portfolio daily return and is repeated
    across ticker rows on the same date. Therefore we take first(), not sum().
    """
    calendar = benchmark_df[["date"]].copy()

    strategy_daily = strategy_df[["date", "strategy_daily_return"]].copy()
    strategy_daily = strategy_daily.dropna(subset=["date", "strategy_daily_return"])
    strategy_daily = strategy_daily.groupby("date", as_index=False)["strategy_daily_return"].first()

    merged = calendar.merge(strategy_daily, on="date", how="left")
    merged["strategy_daily_return"] = merged["strategy_daily_return"].fillna(0.0)
    merged = merged.sort_values("date").reset_index(drop=True)

    merged["strategy_equity"] = (1.0 + merged["strategy_daily_return"]).cumprod()
    return merged


def compute_drawdown_series(equity: pd.Series) -> pd.Series:
    equity = pd.Series(equity).astype(float)
    running_max = equity.cummax()
    return equity / running_max - 1.0


def years_between_dates(dates: pd.Series) -> float:
    dates = pd.to_datetime(pd.Series(dates)).dropna().sort_values().reset_index(drop=True)
    if len(dates) < 2:
        return np.nan
    return (dates.iloc[-1] - dates.iloc[0]).days / 365.25


def compute_basic_metrics(returns: pd.Series, equity: pd.Series, dates: pd.Series) -> dict[str, float]:
    returns = pd.Series(returns).dropna().astype(float).reset_index(drop=True)
    equity = pd.Series(equity).dropna().astype(float).reset_index(drop=True)
    dates = pd.to_datetime(pd.Series(dates)).dropna().reset_index(drop=True)

    n = len(returns)
    if n == 0:
        raise ValueError("No returns available for metric calculation")

    mean_daily = float(returns.mean())
    median_daily = float(returns.median())
    std_daily = float(returns.std(ddof=1)) if n > 1 else np.nan

    downside = returns[returns < 0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else np.nan

    total_return = float(equity.iloc[-1] - 1.0)
    n_years = years_between_dates(dates)

    cagr = np.nan
    if pd.notna(n_years) and n_years > 0:
        cagr = float(equity.iloc[-1] ** (1.0 / n_years) - 1.0)

    annualized_return_arithmetic = mean_daily * TRADING_DAYS
    annualized_volatility = std_daily * math.sqrt(TRADING_DAYS) if pd.notna(std_daily) else np.nan

    sharpe_ratio = np.nan
    if pd.notna(std_daily) and std_daily > 0:
        sharpe_ratio = float((mean_daily / std_daily) * math.sqrt(TRADING_DAYS))

    sortino_ratio = np.nan
    if pd.notna(downside_std) and downside_std > 0:
        sortino_ratio = float((mean_daily / downside_std) * math.sqrt(TRADING_DAYS))

    drawdown = compute_drawdown_series(equity)
    max_drawdown = float(drawdown.min())

    calmar_ratio = np.nan
    if max_drawdown < 0 and pd.notna(cagr):
        calmar_ratio = float(cagr / abs(max_drawdown))

    wins = returns[returns > 0]
    losses = returns[returns < 0]

    win_rate = float((returns > 0).mean())
    positive_sum = float(wins.sum()) if len(wins) else 0.0
    negative_sum_abs = float(abs(losses.sum())) if len(losses) else np.nan
    profit_factor = (
        positive_sum / negative_sum_abs
        if pd.notna(negative_sum_abs) and negative_sum_abs > 0
        else np.nan
    )

    avg_win = float(wins.mean()) if len(wins) else np.nan
    avg_loss = float(losses.mean()) if len(losses) else np.nan
    expectancy = float(returns.mean())

    skewness = float(returns.skew()) if n > 2 else np.nan
    kurtosis = float(returns.kurt()) if n > 3 else np.nan

    return {
        "observations": n,
        "start_date": dates.iloc[0].date().isoformat() if len(dates) else None,
        "end_date": dates.iloc[-1].date().isoformat() if len(dates) else None,
        "years": n_years,
        "mean_daily_return": mean_daily,
        "median_daily_return": median_daily,
        "daily_volatility": std_daily,
        "annualized_return_arithmetic": annualized_return_arithmetic,
        "annualized_volatility": annualized_volatility,
        "cagr": cagr,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "total_return": total_return,
        "ending_equity": float(equity.iloc[-1]),
    }


def one_sample_significance_test(returns: pd.Series, label: str) -> pd.DataFrame:
    returns = pd.Series(returns).dropna().astype(float)
    n = len(returns)

    mean_ = float(returns.mean()) if n > 0 else np.nan
    std_ = float(returns.std(ddof=1)) if n > 1 else np.nan
    se = std_ / math.sqrt(n) if n > 1 and pd.notna(std_) else np.nan

    if n > 1 and pd.notna(std_) and std_ > 0:
        t_stat, p_two_sided = stats.ttest_1samp(returns, popmean=0.0)
        p_right_tail = p_two_sided / 2 if t_stat > 0 else 1.0 - (p_two_sided / 2)
        t_crit = stats.t.ppf(0.975, df=n - 1)
        ci_low = mean_ - t_crit * se
        ci_high = mean_ + t_crit * se
    else:
        t_stat = np.nan
        p_two_sided = np.nan
        p_right_tail = np.nan
        ci_low = np.nan
        ci_high = np.nan

    return pd.DataFrame(
        {
            "series": [label],
            "observations": [n],
            "mean": [mean_],
            "std_dev": [std_],
            "standard_error": [se],
            "null_hypothesis": ["mean_return = 0"],
            "alternative_hypothesis_right_tail": ["mean_return > 0"],
            "t_statistic": [t_stat],
            "p_value_two_sided": [p_two_sided],
            "p_value_one_sided_positive": [p_right_tail],
            "ci_95_low": [ci_low],
            "ci_95_high": [ci_high],
        }
    )


def compute_yearly_metrics(strategy_daily_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    strat = strategy_daily_df.copy()
    bench = benchmark_df.copy()

    strat["year"] = pd.to_datetime(strat["date"]).dt.year
    bench["year"] = pd.to_datetime(bench["date"]).dt.year

    all_years = sorted(set(strat["year"]).intersection(set(bench["year"])))
    rows = []

    for year in all_years:
        g_strat = strat[strat["year"] == year].sort_values("date").reset_index(drop=True)
        g_bench = bench[bench["year"] == year].sort_values("date").reset_index(drop=True)

        strategy_equity = (1.0 + g_strat["strategy_daily_return"]).cumprod()
        benchmark_equity = (1.0 + g_bench["benchmark_return"]).cumprod()

        strat_metrics = compute_basic_metrics(g_strat["strategy_daily_return"], strategy_equity, g_strat["date"])
        bench_metrics = compute_basic_metrics(g_bench["benchmark_return"], benchmark_equity, g_bench["date"])

        rows.append(
            {
                "year": int(year),
                "strategy_total_return": strat_metrics["total_return"],
                "benchmark_total_return": bench_metrics["total_return"],
                "strategy_cagr": strat_metrics["cagr"],
                "benchmark_cagr": bench_metrics["cagr"],
                "strategy_sharpe": strat_metrics["sharpe_ratio"],
                "benchmark_sharpe": bench_metrics["sharpe_ratio"],
                "strategy_annualized_volatility": strat_metrics["annualized_volatility"],
                "benchmark_annualized_volatility": bench_metrics["annualized_volatility"],
                "strategy_max_drawdown": strat_metrics["max_drawdown"],
                "benchmark_max_drawdown": bench_metrics["max_drawdown"],
                "strategy_win_rate": strat_metrics["win_rate"],
                "benchmark_win_rate": bench_metrics["win_rate"],
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def compute_rolling_metrics(strategy_daily_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    temp = benchmark_df[["date", "benchmark_return"]].copy()
    temp = temp.merge(
        strategy_daily_df[["date", "strategy_daily_return", "strategy_equity"]],
        on="date",
        how="left",
    )

    temp["strategy_daily_return"] = temp["strategy_daily_return"].fillna(0.0)

    if "strategy_equity" not in temp or temp["strategy_equity"].isna().all():
        temp["strategy_equity"] = (1.0 + temp["strategy_daily_return"]).cumprod()

    temp["benchmark_equity"] = (1.0 + temp["benchmark_return"]).cumprod()
    temp = temp.sort_values("date").reset_index(drop=True)

    strategy_roll_mean = temp["strategy_daily_return"].rolling(ROLLING_WINDOW).mean()
    strategy_roll_std = temp["strategy_daily_return"].rolling(ROLLING_WINDOW).std(ddof=1)

    benchmark_roll_mean = temp["benchmark_return"].rolling(ROLLING_WINDOW).mean()
    benchmark_roll_std = temp["benchmark_return"].rolling(ROLLING_WINDOW).std(ddof=1)

    temp["strategy_rolling_sharpe_63d"] = (strategy_roll_mean / strategy_roll_std) * math.sqrt(TRADING_DAYS)
    temp["benchmark_rolling_sharpe_63d"] = (benchmark_roll_mean / benchmark_roll_std) * math.sqrt(TRADING_DAYS)

    temp["strategy_rolling_vol_63d"] = strategy_roll_std * math.sqrt(TRADING_DAYS)
    temp["benchmark_rolling_vol_63d"] = benchmark_roll_std * math.sqrt(TRADING_DAYS)

    temp["strategy_drawdown"] = compute_drawdown_series(temp["strategy_equity"])
    temp["benchmark_drawdown"] = compute_drawdown_series(temp["benchmark_equity"])

    return temp


def compute_regression(strategy_daily_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    aligned = benchmark_df[["date", "benchmark_return"]].copy()
    aligned = aligned.merge(
        strategy_daily_df[["date", "strategy_daily_return"]],
        on="date",
        how="left",
    )
    aligned["strategy_daily_return"] = aligned["strategy_daily_return"].fillna(0.0)

    aligned = aligned.rename(
        columns={
            "strategy_daily_return": "strategy_return",
            "benchmark_return": "benchmark_return",
        }
    ).dropna()

    if sm is None:
        return pd.DataFrame(
            {
                "metric": ["regression_skipped"],
                "value": ["statsmodels not installed; run poetry add statsmodels or pip install statsmodels"],
            }
        )

    X = sm.add_constant(aligned["benchmark_return"])
    model = sm.OLS(aligned["strategy_return"], X).fit(cov_type="HC1")

    alpha_daily = float(model.params["const"])
    beta = float(model.params["benchmark_return"])
    alpha_annualized_approx = alpha_daily * TRADING_DAYS

    return pd.DataFrame(
        {
            "metric": [
                "alpha_daily",
                "alpha_annualized_approx",
                "beta",
                "r_squared",
                "alpha_t_stat",
                "alpha_p_value",
                "beta_t_stat",
                "beta_p_value",
                "observations",
            ],
            "value": [
                alpha_daily,
                alpha_annualized_approx,
                beta,
                float(model.rsquared),
                float(model.tvalues["const"]),
                float(model.pvalues["const"]),
                float(model.tvalues["benchmark_return"]),
                float(model.pvalues["benchmark_return"]),
                int(model.nobs),
            ],
        }
    )


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def format_pct(x: float) -> str:
    if pd.isna(x):
        return "nan"
    return f"{x * 100:.2f}%"


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)

    project_root = infer_project_root()
    analysis_dir = project_root / "output" / "analysis" / STATISTICAL_ANALYSIS_DIR_NAME

    strategy_df_raw = load_strategy_data(project_root)

    benchmark_df = download_benchmark_prices(
        start_date=strategy_df_raw["date"].min(),
        end_date=strategy_df_raw["date"].max(),
    )

    strategy_daily_df = build_strategy_daily_frame(strategy_df_raw, benchmark_df)

    benchmark_df = benchmark_df.sort_values("date").reset_index(drop=True)
    benchmark_df["benchmark_equity"] = (1.0 + benchmark_df["benchmark_return"]).cumprod()

    strategy_metrics = compute_basic_metrics(
        returns=strategy_daily_df["strategy_daily_return"],
        equity=strategy_daily_df["strategy_equity"],
        dates=strategy_daily_df["date"],
    )

    benchmark_metrics = compute_basic_metrics(
        returns=benchmark_df["benchmark_return"],
        equity=benchmark_df["benchmark_equity"],
        dates=benchmark_df["date"],
    )

    summary = pd.DataFrame(
        [
            {"series": "strategy", **strategy_metrics},
            {"series": BENCHMARK_TICKER, **benchmark_metrics},
        ]
    )
    save_dataframe(summary, analysis_dir / "statistical_summary_vs_benchmark.csv")

    significance = pd.concat(
        [
            one_sample_significance_test(strategy_daily_df["strategy_daily_return"], "strategy_daily_returns"),
            one_sample_significance_test(strategy_df_raw["trade_return_decimal"], "trade_returns"),
            one_sample_significance_test(benchmark_df["benchmark_return"], f"{BENCHMARK_TICKER}_daily_returns"),
        ],
        ignore_index=True,
    )
    save_dataframe(significance, analysis_dir / "significance_tests.csv")

    yearly = compute_yearly_metrics(strategy_daily_df, benchmark_df)
    save_dataframe(yearly, analysis_dir / "yearly_risk_metrics_vs_benchmark.csv")

    rolling = compute_rolling_metrics(strategy_daily_df, benchmark_df)
    save_dataframe(rolling, analysis_dir / "rolling_metrics_63d.csv")

    regression = compute_regression(strategy_daily_df, benchmark_df)
    save_dataframe(regression, analysis_dir / "capm_regression_vs_benchmark.csv")

    aligned_export = benchmark_df[["date", "benchmark_return", "benchmark_equity"]].copy()
    aligned_export = aligned_export.merge(
        strategy_daily_df[["date", "strategy_daily_return", "strategy_equity"]],
        on="date",
        how="left",
    )
    aligned_export["strategy_daily_return"] = aligned_export["strategy_daily_return"].fillna(0.0)
    aligned_export["strategy_equity"] = aligned_export["strategy_equity"].ffill().fillna(1.0)
    save_dataframe(aligned_export, analysis_dir / "aligned_daily_returns_vs_benchmark.csv")

    print("Saved files:")
    print(f"- {analysis_dir / 'statistical_summary_vs_benchmark.csv'}")
    print(f"- {analysis_dir / 'significance_tests.csv'}")
    print(f"- {analysis_dir / 'yearly_risk_metrics_vs_benchmark.csv'}")
    print(f"- {analysis_dir / 'rolling_metrics_63d.csv'}")
    print(f"- {analysis_dir / 'capm_regression_vs_benchmark.csv'}")
    print(f"- {analysis_dir / 'aligned_daily_returns_vs_benchmark.csv'}")
    print()
    print("Headline metrics:")
    print(
        f"Strategy CAGR: {format_pct(strategy_metrics['cagr'])} | "
        f"Annualized vol: {format_pct(strategy_metrics['annualized_volatility'])} | "
        f"Sharpe: {strategy_metrics['sharpe_ratio']:.3f} | "
        f"Max drawdown: {format_pct(strategy_metrics['max_drawdown'])}"
    )
    print(
        f"{BENCHMARK_TICKER} CAGR: {format_pct(benchmark_metrics['cagr'])} | "
        f"Annualized vol: {format_pct(benchmark_metrics['annualized_volatility'])} | "
        f"Sharpe: {benchmark_metrics['sharpe_ratio']:.3f} | "
        f"Max drawdown: {format_pct(benchmark_metrics['max_drawdown'])}"
    )


if __name__ == "__main__":
    main()