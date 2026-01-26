#  Post-Earnings Momentum Strategy — Pipeline & Analysis

This repository contains the full implementation of an **event-driven post-earnings momentum strategy**, developed as an applied quantitative finance project.  
The objective is to study whether **stock-specific momentum effects following earnings announcements** can be systematically identified and translated into a profitable out-of-sample trading strategy.

The project follows a **clean, reproducible execution pipeline**, from earnings-level signal construction to portfolio backtesting and performance evaluation.

---

##  Project Objective

The project addresses three core research questions:

1. **How do stock prices react around earnings announcements?**  
   Earnings reactions are decomposed into overnight (Close → Open) and intraday (Open → Close) price movements.

2. **Is post-earnings momentum a universal market effect or stock-specific?**  
   A market-wide diagnostic test is used to assess whether continuation dominates reversal at the index level.

3. **Can a subset of stocks with persistent post-earnings momentum be identified ex-ante and traded profitably out-of-sample surpassing a passive index like sp500?**  
   Stocks are ranked using only pre-2017 data, a fixed universe is selected, and performance is evaluated strictly out-of-sample.

---

##  Methodology Overview

- Earnings announcements are aligned to the **next trading day**.
- For each earnings event, two returns are computed:
  - **Close → Open** (overnight reaction)
  - **Open → Close** (intraday continuation or reversal)
- Each event is classified into one of four **post-earnings quadrants**:
  - `pos_then_up`
  - `pos_then_down`
  - `neg_then_up`
  - `neg_then_down`
- Stocks are ranked by **historical momentum bias** using only information available up to 2017.
- A **Top-25 stock universe** is selected and traded from 2017–2024.
- The strategy is evaluated using equity curves, rolling forward CAGRs, monthly and yearly returns, and return distributions.

---

## ⚙ Execution Pipeline (Reproducible)

```
run_quadrants.py
        ↓
top_25_quadrants_until2017.py
        ↓
momentum_portfolio_top25_until_2024.py
        ↓
performance_analysis_and_plots.py
```

### Pipeline Steps

1. **Quadrant construction**  
   `run_quadrants.py` applies the post-earnings quadrant classification to each stock in the dataset.  
   The classification logic is implemented internally in `earnings_stock_analyzer/quadrants.py`.

2. **Stock selection (ex-ante)**  
   `top_25_quadrants_until2017.py` ranks stocks by post-earnings momentum bias using only pre-2017 data and selects the Top-25 universe.

3. **Out-of-sample trading strategy**  
   `momentum_portfolio_top25_until_2024.py` executes the earnings-driven momentum strategy on the fixed stock universe from 2017 to 2024.

4. **Performance analysis & visualization**  
   `performance_analysis_and_plots.py` computes equity curves, rolling-start CAGRs, monthly and yearly returns, and benchmark comparisons.

---

##  Project Structure

```
earnings-stock-analyzer/
├── data/
│   └── sp500_and_nasdaq_tickers.csv
│
├── earnings_stock_analyzer/
│   ├── __init__.py
│   ├── fetch.py
│   ├── quadrants.py
│   ├── analyzer.py
│   ├── momentum.py
│   ├── plot.py
│   └── cli.py
│
├── scripts/
│   ├── run_quadrants.py
│   ├── top_25_quadrants_until2017.py
│   ├── momentum_portfolio_top25_until_2024.py
│   ├── performance_analysis_and_plots.py
│   └── market_wide_quadrant_analysis.py
│
├── output/
│   └── quadrants/
│
├── report/
│   └── Momentum project.pdf
│
├── README.md
├── pyproject.toml
└── poetry.lock
```

---

##  How to Run

### Install dependencies
```bash
poetry install
```

### Activate environment (optional)
```bash
poetry shell
```

### Execute the pipeline
```bash
poetry run python scripts/run_quadrants.py
```
```bash
poetry run python scripts/top_25_quadrants_until2017.py
```
```bash
poetry run python scripts/momentum_portfolio_top25_until_2024.py
```
```bash
poetry run python scripts/performance_analysis_and_plots.py
```

---

##  Outputs

All results are saved in the `output/` directory, including:
- Per-stock quadrant classifications
- Top-25 universe selection
- Trade-level and portfolio-level returns
- Equity curves
- Monthly and yearly performance tables
- Rolling forward CAGR comparisons against the S&P 500

---

##  Data Sources

Earnings dates and price reactions are obtained using the custom Python library  
**`stocks-earnings-dates`**, developed by me and based on SEC EDGAR filings.

---

## Author

Developed by **Albert Pérez**  
as an applied project in **quantitative finance, event-driven strategies, and systematic backtesting**.
