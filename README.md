# 📊 Earnings Stock Analyzer

This Python project analyzes how a stock has historically reacted in the market after publishing its earnings. It supports **two data sources** (library or API), multiple execution modes, and outputs both CSVs and plots for further analysis.

The **main purpose** of the project is to find a **statistical edge** that repeats historically around earnings announcements, in order to identify potential investment opportunities.

---

## 🎯 Purpose

The project has **two main types of analysis**:

1. **Earnings Reaction Analysis**

   * Calculates the **absolute price change average** around earnings announcements, the average in positive earnings, and the average in negative earnings:

     * **Previous Close → Next Open**
     * **Previous Close → Next Close**
     * **Next Open → Next Close**
2. **Momentum Analysis**

   * Focuses on **whether momentum continued the next day** after earnings:

     * Calculates the % of cases where earnings with a positive reaction continued upward the day after.
     * Calculates the % of cases where earnings with a negative reaction continued downward the day after.
     * Provides overall momentum success rate, % of positives with momentum, and % of negatives with momentum.
   * The purpose is to measure the **persistence of trends** following earnings.

Together, these two analyses provide a picture of both:

* The **magnitude of changes** caused by earnings (reaction analysis).
* The **likelihood of continuation** after earnings (momentum analysis).
* And ultimately, whether a **statistical edge** exists that can be exploited for investing strategies.

---

## 🗂 Project Structure

```
earnings-stock-analyzer/
├── earnings_stock_analyzer/
│   ├── __init__.py              # Package initializer
│   ├── analyzer.py              # Core analysis logic
│   ├── fetch.py                 # Unified data fetching (library or API)
│   ├── plot.py                  # Plotting and visualization
│   └── cli.py                   # CLI configuration
├── scripts/
│   ├── run_analysis.py          # Main script for earnings reaction analysis
│   ├── run_momentum.py          # Main script for momentum analysis
│   ├── complete_run.py          # (legacy) Old unified script
│   ├── api.py                   # (legacy) API-only analysis
├── data/                        # Input datasets (CSV)
├── output/                      # Generated results (CSVs, plots)
├── README.md
├── pyproject.toml
├── poetry.lock
```

---

## 🚀 How to Run

1. **Install dependencies:**

   ```bash
   poetry install
   ```

2. **Activate shell (optional):**

   ```bash
   poetry shell
   ```

### 🔹 Earnings Reaction Analysis

Run the analysis script:

```bash
poetry run python scripts/run_analysis.py <ticker> --source [library|api] [--api-key API_KEY]
```

Examples:

```bash
# Analyze NVDA with library data (default source if not specified)
poetry run python scripts/run_analysis.py NVDA

# Analyze NVDA with API (using default project key)
poetry run python scripts/run_analysis.py NVDA --source api

# Analyze NVDA with API and your own API key (optional, for higher limits)
poetry run python scripts/run_analysis.py NVDA --source api --api-key YOUR_KEY

# Analyze all tickers in S&P 500 + Nasdaq (no ticker specified)
poetry run python scripts/run_analysis.py
```

### 🔹 Momentum Analysis

Run the momentum script:

```bash
poetry run python scripts/run_momentum.py <ticker> --source [library|api] [--api-key API_KEY]
```

Examples:

```bash
# Momentum analysis for NVDA with library data
poetry run python scripts/run_momentum.py NVDA

# Momentum analysis for NVDA with API
poetry run python scripts/run_momentum.py NVDA --source api

# Momentum analysis for all tickers (S&P 500 + Nasdaq)
poetry run python scripts/run_momentum.py
```

---

## 📂 Output

All outputs are saved in the **`output/`** directory.

Depending on how you run the program, different CSVs are created:

### **Single Ticker (Analysis or Momentum)**

* Detailed CSV showing all historical earnings dates for the ticker.
* Includes Close→Open, Close→Close, and Open→Close changes.
* Momentum files also show continuation statistics (overall, positives, negatives).

### **All Tickers (S\&P 500 + Nasdaq)**

If no ticker is provided, the project analyzes all tickers in the dataset and creates **rankings**:

1. **Analysis Mode**:

   * CSV with the **Top 20 stocks** ranked by the highest average absolute change in **Close→Open** on earnings days.

2. **Momentum Mode**:

   * CSV with the **Top 30 overall stocks** with the highest % of momentum continuation.
   * CSV with the **Top 30 stocks on positive earnings days** with the highest % of continued momentum.
   * CSV with the **Top 30 stocks on negative earnings days** with the highest % of continued momentum.

This allows you to quickly identify which stocks historically have the largest reactions and which ones show the strongest continuation patterns.

---

## 🔑 Requirements

* Python ≥ 3.13
* Packages (auto-installed with Poetry):

  * `requests`, `pandas`, `yfinance`, `matplotlib`, `seaborn`
  * `stocks-earnings-dates` (my own library that you will see here is the one used in this project to recollect the earnings dates and % changes for each date): [GitHub link](https://github.com/AlbertPerez7/stocks-earnings-dates))

---

## ✍️ Author

Developed by [AlbertPerez7](mailto:albertperez2004@gmail.com) as a personal project to explore **API usage, data analysis, quantitative finance, and systematic investing strategies**.
