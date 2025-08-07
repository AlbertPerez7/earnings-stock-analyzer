# 📊 Earnings Stock Analyzer

This Python project analyzes how a stock has historically reacted in the market after publishing its earnings. It calculates the absolute average percentage changes from one trading session to the next, as well as the averages for days when the stock reacted negatively and positively to the earnings release.


##  Purpose

For any given stock ticker, the project:

- Retrieves the historical earnings release dates from the Alpha Vantage API.
- Fetches the daily stock price data surrounding those earnings dates from Yahoo Finance.
- Calculates the percentage change from:
  - **Previous Close → Next Open**
  - **Previous Close → Next Close**
  - **Next Open → Next Close**
- *“Previous Close” refers to the stock’s closing price just before the earnings release (typically after hours). “Next Open” is the price at market open the following day, and “Next Close” is the closing price on that same day.*
- Computes success rates for strong movements and trend continuation.
- Visualizes the changes with a clear line plot.


##  Project Structure

```
earnings-stock-analyzer/
├── earnings_stock_analyzer/
│   ├── __init__.py              # Package initializer
│   ├── analyzer.py              # Earnings analysis logic
│   ├── cli.py                   # Ticker input
│   ├── fetch.py                 # Stock and earnings data fetching
│   └── plot.py                  # Result visualization
├── scripts/
│   └── run_single_analysis.py   # Script to run the full pipeline
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

2. **Activate shell (optional, but recommended):**

   ```bash
   poetry shell
   ```

3. **Run the analysis script:**

   ```bash
   poetry run python scripts/run_single_analysis.py
   ```

4. **When prompted**, enter a valid stock ticker (e.g., `NVDA`, `AAPL`, `MSFT`).

---

## Output

- Console output with:
  - Average absolute % change
  - Breakdown of positive and negative day performance
  - Strategy success rate
  - Trend continuation statistics
- Interactive Matplotlib plot showing:
  - Close→Open
  - Close→Close
  - Open→Close
  for each earnings event.

---

##  Example

```
Enter the stock ticker symbol: NVDA

📊 AVERAGE ABSOLUTE PERCENTAGE CHANGE AFTER EARNINGS:
• Close → Next Open: 4.23%
• Close → Next Close: 6.12%
• Next Open → Next Close: 1.89%
...
```

---

## Requirements

- Python ≥ 3.13
- Packages (auto-installed with Poetry):
  - `requests`, `pandas`, `yfinance`, `matplotlib`, `seaborn`

---

## ✍️ Author

Developed by [AlbertPerez7](mailto:albertperez2004@gmail.com) as a personal project to explore real-world API usage, data analysis, and packaging best practices.
