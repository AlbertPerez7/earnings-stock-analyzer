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
BENCHMARK_TICKER = "SPY"  # can be changed to "^GSPC" if preferred
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
    required_cols = {
        "date",
        "trade_return_pct",
        "avg_daily_return_pct",
        "equity_after",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path.name}: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["strategy_daily_return"] = df["avg_daily_return_pct"] / 100.0
    df["trade_return_decimal"] = df["trade_return_pct"] / 100.0

    # Rebuild equity from returns if needed; otherwise keep provided equity_after
    if df["equity_after"].isna().any():
        df["equity_after"] = (1 + df["strategy_daily_return"]).cumprod()

    return df


def load_benchmark_returns(start_date: pd.Timestamp, end_date: pd.Timestamp, strategy_dates: pd.Series) -> pd.Series:
    if yf is None:
        raise ImportError(
            "yfinance is not installed. Install it with: pip install yfinance"
        )

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

    returns = close.pct_change().dropna()
    returns.index = pd.to_datetime(returns.index).tz_localize(None)

    aligned = returns.reindex(pd.to_datetime(strategy_dates))
    aligned = aligned.fillna(0.0)
    aligned.name = "benchmark_return"
    return aligned


def compute_drawdown_series(equity: pd.Series) -> pd.Series:
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return drawdown


def compute_basic_metrics(returns: pd.Series, equity: pd.Series) -> dict[str, float]:
    returns = pd.Series(returns).dropna()
    equity = pd.Series(equity).dropna()

    n = len(returns)
    if n == 0:
        raise ValueError("No returns available for metric calculation")

    mean_daily = float(returns.mean())
    median_daily = float(returns.median())
    std_daily = float(returns.std(ddof=1)) if n > 1 else 0.0
    downside = returns[returns < 0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0

    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else float(equity.iloc[0] - 1.0)
    n_years = n / TRADING_DAYS
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / n_years) - 1) if n_years > 0 and len(equity) > 1 else np.nan

    ann_return = mean_daily * TRADING_DAYS
    ann_vol = std_daily * math.sqrt(TRADING_DAYS)
    sharpe = ann_return / ann_vol if ann_vol > 0 else np.nan
    sortino = ann_return / (downside_std * math.sqrt(TRADING_DAYS)) if downside_std > 0 else np.nan

    drawdown = compute_drawdown_series(equity)
    max_drawdown = float(drawdown.min())
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 and pd.notna(cagr) else np.nan

    wins = returns[returns > 0]
    losses = returns[returns < 0]
    win_rate = float((returns > 0).mean())
    positive_sum = float(wins.sum()) if len(wins) else 0.0
    negative_sum_abs = float(abs(losses.sum())) if len(losses) else np.nan
    profit_factor = positive_sum / negative_sum_abs if negative_sum_abs and negative_sum_abs > 0 else np.nan
    avg_win = float(wins.mean()) if len(wins) else np.nan
    avg_loss = float(losses.mean()) if len(losses) else np.nan
    expectancy = float(returns.mean())

    skewness = float(returns.skew()) if n > 2 else np.nan
    kurtosis = float(returns.kurt()) if n > 3 else np.nan

    return {
        "observations": n,
        "mean_daily_return": mean_daily,
        "median_daily_return": median_daily,
        "daily_volatility": std_daily,
        "annualized_return_approx": ann_return,
        "annualized_volatility": ann_vol,
        "cagr": cagr,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "total_return": total_return,
    }


def one_sample_significance_test(returns: pd.Series, label: str) -> pd.DataFrame:
    returns = pd.Series(returns).dropna()
    n = len(returns)
    mean_ = float(returns.mean())
    std_ = float(returns.std(ddof=1)) if n > 1 else 0.0
    se = std_ / math.sqrt(n) if n > 0 else np.nan

    if n > 1 and std_ > 0:
        t_stat, p_two_sided = stats.ttest_1samp(returns, popmean=0.0)
        p_right_tail = p_two_sided / 2 if t_stat > 0 else 1 - (p_two_sided / 2)
        t_crit = stats.t.ppf(0.975, df=n - 1)
        ci_low = mean_ - t_crit * se
        ci_high = mean_ + t_crit * se
    else:
        t_stat = np.nan
        p_two_sided = np.nan
        p_right_tail = np.nan
        ci_low = np.nan
        ci_high = np.nan

    result = pd.DataFrame(
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
    return result


def compute_yearly_metrics(df: pd.DataFrame, benchmark_returns: pd.Series) -> pd.DataFrame:
    temp = df.copy()
    temp["year"] = temp["date"].dt.year
    temp["benchmark_return"] = benchmark_returns.values

    rows = []
    for year, g in temp.groupby("year"):
        strategy_equity = (1 + g["strategy_daily_return"]).cumprod()
        bench_equity = (1 + g["benchmark_return"]).cumprod()
        strat = compute_basic_metrics(g["strategy_daily_return"], strategy_equity)
        bench = compute_basic_metrics(g["benchmark_return"], bench_equity)
        rows.append(
            {
                "year": year,
                "strategy_total_return": strat["total_return"],
                "benchmark_total_return": bench["total_return"],
                "strategy_sharpe": strat["sharpe_ratio"],
                "benchmark_sharpe": bench["sharpe_ratio"],
                "strategy_annualized_volatility": strat["annualized_volatility"],
                "benchmark_annualized_volatility": bench["annualized_volatility"],
                "strategy_max_drawdown": strat["max_drawdown"],
                "benchmark_max_drawdown": bench["max_drawdown"],
                "strategy_win_rate": strat["win_rate"],
                "benchmark_win_rate": bench["win_rate"],
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def compute_rolling_metrics(df: pd.DataFrame, benchmark_returns: pd.Series) -> pd.DataFrame:
    temp = pd.DataFrame(
        {
            "date": pd.to_datetime(df["date"]),
            "strategy_return": df["strategy_daily_return"].values,
            "benchmark_return": benchmark_returns.values,
            "equity": df["equity_after"].values,
        }
    )
    temp = temp.sort_values("date").reset_index(drop=True)

    temp["strategy_rolling_sharpe_63d"] = (
        temp["strategy_return"].rolling(ROLLING_WINDOW).mean()
        / temp["strategy_return"].rolling(ROLLING_WINDOW).std(ddof=1)
        * math.sqrt(TRADING_DAYS)
    )
    temp["benchmark_rolling_sharpe_63d"] = (
        temp["benchmark_return"].rolling(ROLLING_WINDOW).mean()
        / temp["benchmark_return"].rolling(ROLLING_WINDOW).std(ddof=1)
        * math.sqrt(TRADING_DAYS)
    )
    temp["strategy_rolling_vol_63d"] = (
        temp["strategy_return"].rolling(ROLLING_WINDOW).std(ddof=1) * math.sqrt(TRADING_DAYS)
    )
    temp["benchmark_rolling_vol_63d"] = (
        temp["benchmark_return"].rolling(ROLLING_WINDOW).std(ddof=1) * math.sqrt(TRADING_DAYS)
    )
    temp["strategy_drawdown"] = compute_drawdown_series(temp["equity"])

    return temp


def compute_regression(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> pd.DataFrame:
    aligned = pd.DataFrame(
        {
            "strategy_return": pd.Series(strategy_returns).reset_index(drop=True),
            "benchmark_return": pd.Series(benchmark_returns).reset_index(drop=True),
        }
    ).dropna()

    if sm is None:
        return pd.DataFrame(
            {
                "metric": ["regression_skipped"],
                "value": ["statsmodels not installed; run pip install statsmodels to enable alpha/beta regression"],
            }
        )

    X = sm.add_constant(aligned["benchmark_return"])
    model = sm.OLS(aligned["strategy_return"], X).fit(cov_type="HC1")

    alpha_daily = float(model.params["const"])
    beta = float(model.params["benchmark_return"])
    alpha_annualized = alpha_daily * TRADING_DAYS

    out = pd.DataFrame(
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
                alpha_annualized,
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
    return out


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

    strategy_df = load_strategy_data(project_root)
    strategy_returns = strategy_df["strategy_daily_return"].copy()
    trade_returns = strategy_df["trade_return_decimal"].copy()
    equity = strategy_df["equity_after"].copy()

    benchmark_returns = load_benchmark_returns(
        start_date=strategy_df["date"].min(),
        end_date=strategy_df["date"].max(),
        strategy_dates=strategy_df["date"],
    )

    benchmark_equity = (1 + benchmark_returns).cumprod()

    strategy_metrics = compute_basic_metrics(strategy_returns, equity)
    benchmark_metrics = compute_basic_metrics(benchmark_returns, benchmark_equity)

    summary = pd.DataFrame(
        [
            {"series": "strategy", **strategy_metrics},
            {"series": BENCHMARK_TICKER, **benchmark_metrics},
        ]
    )
    save_dataframe(summary, analysis_dir / "statistical_summary_vs_benchmark.csv")

    significance = pd.concat(
        [
            one_sample_significance_test(strategy_returns, "strategy_daily_returns"),
            one_sample_significance_test(trade_returns, "trade_returns"),
            one_sample_significance_test(benchmark_returns, f"{BENCHMARK_TICKER}_daily_returns"),
        ],
        ignore_index=True,
    )
    save_dataframe(significance, analysis_dir / "significance_tests.csv")

    yearly = compute_yearly_metrics(strategy_df, benchmark_returns)
    save_dataframe(yearly, analysis_dir / "yearly_risk_metrics_vs_benchmark.csv")

    rolling = compute_rolling_metrics(strategy_df, benchmark_returns)
    save_dataframe(rolling, analysis_dir / "rolling_metrics_63d.csv")

    regression = compute_regression(strategy_returns, benchmark_returns)
    save_dataframe(regression, analysis_dir / "capm_regression_vs_benchmark.csv")

    print("Saved files:")
    print(f"- {analysis_dir / 'statistical_summary_vs_benchmark.csv'}")
    print(f"- {analysis_dir / 'significance_tests.csv'}")
    print(f"- {analysis_dir / 'yearly_risk_metrics_vs_benchmark.csv'}")
    print(f"- {analysis_dir / 'rolling_metrics_63d.csv'}")
    print(f"- {analysis_dir / 'capm_regression_vs_benchmark.csv'}")
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
