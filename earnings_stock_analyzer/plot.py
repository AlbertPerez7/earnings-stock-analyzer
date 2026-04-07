from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_figure(
    title: str,
    xlabel: str,
    ylabel: str,
    figsize: tuple[int, int] = (10, 6),
) -> tuple:
    """Create a styled figure and axes. Returns (fig, ax)."""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    return fig, ax


def _kde_gaussian(samples: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Gaussian KDE with Silverman bandwidth. No external dependency required."""
    n = samples.size
    if n < 2:
        return np.zeros_like(xs)
    std = samples.std(ddof=1) or 1e-6
    h = max(1.06 * std * n ** (-0.2), 1e-3)
    diffs = (xs[:, None] - samples[None, :]) / h
    return np.exp(-0.5 * diffs ** 2).sum(axis=1) / (n * h * np.sqrt(2 * np.pi))


def _save_and_show(
    fig: plt.Figure,
    show: bool,
    save_path: str | Path | None,
) -> None:
    """Optionally save and/or display a figure, then close it."""
    if save_path is not None:
        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Per-ticker earnings reactions plot
# (used by run_analysis.py)
# ---------------------------------------------------------------------------

def plot_earnings_reactions(
    ticker: str,
    df_plot: pd.DataFrame,
    show: bool = True,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """
    Plot Close->Open, Close->Close, and Open->Close percentage changes
    for each historical earnings event of a single ticker.

    Parameters
    ----------
    ticker : str
        Ticker label used in the plot title.
    df_plot : pd.DataFrame
        Must contain columns: Date, C2O, C2C, O2C.
    show : bool
        Display the plot interactively. Default True.
    save_path : str | Path | None
        If provided, save the figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    required = {"Date", "C2O", "C2C", "O2C"}
    missing = required.difference(df_plot.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = df_plot.copy()
    data["Date"] = pd.to_datetime(data["Date"])
    data = data.sort_values("Date")

    fig, ax = _make_figure(
        title=f"{ticker.upper()} - Earnings Reaction % Changes",
        xlabel="Date",
        ylabel="% Change",
        figsize=(14, 6),
    )
    ax.plot(data["Date"], data["C2O"], label="Close->Open")
    ax.plot(data["Date"], data["C2C"], label="Close->Close")
    ax.plot(data["Date"], data["O2C"], label="Open->Close")
    ax.legend()
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    _save_and_show(fig, show, save_path)
    return fig


# Keep the original name as an alias so existing callers do not break
plot_results = plot_earnings_reactions


# ---------------------------------------------------------------------------
# Strategy vs benchmark - equity curve
# (used by performance_analysis_and_plots.py)
# ---------------------------------------------------------------------------

def plot_equity_curve(
    strategy_eq: pd.Series,
    spx_eq: pd.Series,
    analysis_end: pd.Timestamp,
    show: bool = True,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """
    Plot rebased cumulative equity curves for the strategy and S&P 500.

    Parameters
    ----------
    strategy_eq : pd.Series
        Daily equity series for the strategy, indexed by date.
    spx_eq : pd.Series
        Daily equity series for the S&P 500, indexed by date.
    analysis_end : pd.Timestamp
        Last date to include in the plot.
    show : bool
        Display the plot interactively. Default True.
    save_path : str | Path | None
        If provided, save the figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    common = strategy_eq.index.intersection(spx_eq.index)
    common = common[common <= analysis_end]

    strat_rebased = strategy_eq.loc[common] / float(strategy_eq.loc[common].iloc[0])
    spx_rebased   = spx_eq.loc[common]      / float(spx_eq.loc[common].iloc[0])

    fig, ax = _make_figure(
        title=f"2018-{analysis_end.year} - Equity curve: Strategy vs S&P 500",
        xlabel="Date",
        ylabel="Normalised equity (base 1.0)",
    )
    ax.plot(common, strat_rebased, label="Strategy (rebased)")
    ax.plot(common, spx_rebased,   label="S&P 500 (rebased)")
    ax.legend()
    fig.tight_layout()

    _save_and_show(fig, show, save_path)
    return fig


# ---------------------------------------------------------------------------
# Strategy vs benchmark - monthly returns time series
# (used by performance_analysis_and_plots.py)
# ---------------------------------------------------------------------------

def plot_monthly_returns(
    strat_m: pd.Series,
    spx_m: pd.Series,
    show: bool = True,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """
    Plot monthly returns for the strategy and S&P 500 side-by-side over time.

    Parameters
    ----------
    strat_m : pd.Series
        Monthly return series for the strategy (as fractions, e.g. 0.05 = 5%).
    spx_m : pd.Series
        Monthly return series for the S&P 500 (as fractions).
    show : bool
        Display the plot interactively. Default True.
    save_path : str | Path | None
        If provided, save the figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    common     = strat_m.index.intersection(spx_m.index)
    strat_vals = (strat_m.loc[common] * 100.0).values
    spx_vals   = (spx_m.loc[common]   * 100.0).values

    fig, ax = _make_figure(
        title="2018-2024 - Monthly returns: Strategy vs S&P 500",
        xlabel="Month (YYYY-MM)",
        ylabel="Monthly return (%)",
        figsize=(14, 6),
    )
    ax.plot(common, strat_vals, marker="o", linewidth=1, label="Strategy monthly %")
    ax.plot(common, spx_vals,   marker="o", linewidth=1, label="S&P 500 monthly %")
    ax.axhline(0.0, linewidth=1, color="black")
    ax.legend()
    plt.xticks(rotation=90, fontsize=7)
    fig.tight_layout()

    _save_and_show(fig, show, save_path)
    return fig


# ---------------------------------------------------------------------------
# KDE distribution plot - monthly, yearly, or forward CAGR
# (used by performance_analysis_and_plots.py)
# ---------------------------------------------------------------------------

def plot_kde(
    strat_vals_pct: np.ndarray,
    spx_vals_pct: np.ndarray,
    title: str,
    xlabel: str,
    show: bool = True,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """
    Plot Gaussian KDE distributions for strategy and S&P 500 return series,
    with vertical mean lines for each.

    Parameters
    ----------
    strat_vals_pct : np.ndarray
        Return values for the strategy in percentage points.
    spx_vals_pct : np.ndarray
        Return values for the S&P 500 in percentage points.
    title : str
        Plot title.
    xlabel : str
        X-axis label (e.g. "Monthly return (%)", "Forward CAGR (%/year)").
    show : bool
        Display the plot interactively. Default True.
    save_path : str | Path | None
        If provided, save the figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    strat_vals_pct = np.asarray(strat_vals_pct, dtype=float)
    spx_vals_pct   = np.asarray(spx_vals_pct,   dtype=float)

    xs = np.linspace(
        min(strat_vals_pct.min(), spx_vals_pct.min()),
        max(strat_vals_pct.max(), spx_vals_pct.max()),
        600,
    )
    dens_s = _kde_gaussian(strat_vals_pct, xs)
    dens_b = _kde_gaussian(spx_vals_pct,   xs)

    fig, ax = _make_figure(title=title, xlabel=xlabel, ylabel="Density")

    line_s, = ax.plot(xs, dens_s, label="Strategy KDE")
    line_b, = ax.plot(xs, dens_b, label="S&P 500 KDE")

    ax.axvline(
        strat_vals_pct.mean(), linestyle="--", linewidth=2,
        color=line_s.get_color(),
        label=f"Strategy mean = {strat_vals_pct.mean():.2f}%",
    )
    ax.axvline(
        spx_vals_pct.mean(), linestyle="--", linewidth=2,
        color=line_b.get_color(),
        label=f"S&P 500 mean = {spx_vals_pct.mean():.2f}%",
    )
    ax.legend()
    fig.tight_layout()

    _save_and_show(fig, show, save_path)
    return fig
