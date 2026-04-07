import logging
import os
import sqlite3
import tempfile
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
import yfinance as yf

SUPPORTED_SOURCES = {"library", "api"}
DEFAULT_TIMEOUT_SECONDS = 20
YFINANCE_CACHE_DIR = Path(tempfile.gettempdir()) / "earnings_stock_analyzer_yfinance_cache"

logger = logging.getLogger(__name__)


def get_earnings_data(
    ticker: str,
    source: str = "library",
    api_key: str | None = None,
    require_api: bool = False,
) -> List[Dict]:
    """
    Return normalized earnings reaction records for a ticker.

    Output schema:
        {
            "date": "YYYY-MM-DD",
            "close_to_open_pct": float,
            "close_to_close_pct": float,
            "open_to_close_pct": float,
        }

    Sources:
    - library: uses the local custom library that already returns reaction metrics
    - api: uses Alpha Vantage earnings dates and derives reaction metrics from Yahoo Finance prices
    """
    normalized_ticker = ticker.strip().upper()
    normalized_source = source.strip().lower()

    if not normalized_ticker:
        raise ValueError("Ticker must be a non-empty string.")

    if normalized_source not in SUPPORTED_SOURCES:
        raise ValueError(
            f"Unknown source: {source}. Supported sources: {sorted(SUPPORTED_SOURCES)}"
        )

    if normalized_source == "library":
        return _get_from_library(normalized_ticker)

    return _get_from_api(
        ticker=normalized_ticker,
        api_key=api_key,
        require_api=require_api,
    )


def _get_from_library(ticker: str) -> List[Dict]:
    """Fetch precomputed earnings reactions from the local packaged library."""
    try:
        from stocks_earnings_dates import get_earnings_price_reactions

        raw_reactions = get_earnings_price_reactions(ticker)
    except Exception as exc:
        logger.debug(
            "Library helper failed for %s; falling back to packaged earnings database: %s",
            ticker,
            exc,
        )
        return _get_from_packaged_database(ticker)

    return _normalize_reactions(raw_reactions)


def _get_from_packaged_database(ticker: str) -> List[Dict]:
    """
    Compute earnings reactions from stocks-earnings-dates' bundled SQLite DB.

    This keeps the project working even if the dependency's convenience helper
    is not importable, while still using the same bundled earnings-date source.
    """
    earnings_dates = _fetch_packaged_earnings_dates(ticker)
    if not earnings_dates:
        return []

    price_data = _fetch_price_history_for_earnings_window(ticker, earnings_dates)
    if price_data.empty:
        return []

    return _build_reactions_from_prices(earnings_dates, price_data)


def _fetch_packaged_earnings_dates(ticker: str) -> List[pd.Timestamp]:
    """Return earnings dates from the installed stocks-earnings-dates database."""
    try:
        dist = metadata.distribution("stocks-earnings-dates")
        db_path = dist.locate_file("stocks_earnings_dates/data/earnings.db")
    except metadata.PackageNotFoundError:
        logger.exception("stocks-earnings-dates is not installed.")
        return []

    if not db_path.exists():
        logger.warning("Packaged earnings database not found at %s.", db_path)
        return []

    query = """
        SELECT Earnings_Date
        FROM earnings
        WHERE UPPER(Ticker) = ?
        ORDER BY Earnings_Date ASC
    """

    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(query, (ticker.upper(),)).fetchall()
    except sqlite3.Error as exc:
        logger.exception("Packaged earnings database query failed for %s: %s", ticker, exc)
        return []

    today = datetime.now().date()
    earnings_dates: List[pd.Timestamp] = []

    for (date_value,) in rows:
        ts = pd.to_datetime(date_value, errors="coerce")
        if pd.isna(ts):
            continue

        normalized = ts.normalize()
        if (today - normalized.date()).days >= 1:
            earnings_dates.append(normalized)

    return sorted(set(earnings_dates))


def _get_from_api(
    ticker: str,
    api_key: str | None,
    require_api: bool,
) -> List[Dict]:
    """
    Fetch earnings dates from Alpha Vantage, then compute reaction metrics
    using Yahoo Finance daily OHLC data.

    Note:
    Alpha Vantage's earnings endpoint provides dates but not the exact release
    timing (before open vs after close). Therefore this path is a daily approximation.
    """
    resolved_api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")

    if not resolved_api_key:
        message = (
            "Alpha Vantage API key not found. "
            "Pass --api-key or set ALPHAVANTAGE_API_KEY in your environment."
        )
        if require_api:
            raise RuntimeError(message)
        logger.warning(message)
        return []

    earnings_dates = _fetch_alpha_vantage_earnings_dates(
        ticker=ticker,
        api_key=resolved_api_key,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
    if not earnings_dates:
        return []

    price_data = _fetch_price_history_for_earnings_window(ticker, earnings_dates)
    if price_data.empty:
        return []

    return _build_reactions_from_prices(earnings_dates, price_data)


def _fetch_alpha_vantage_earnings_dates(
    ticker: str,
    api_key: str,
    timeout_seconds: int,
) -> List[pd.Timestamp]:
    """Return normalized historical earnings dates from Alpha Vantage."""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "EARNINGS",
        "symbol": ticker,
        "apikey": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=timeout_seconds)
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
    except requests.RequestException as exc:
        logger.exception("Alpha Vantage request failed for %s: %s", ticker, exc)
        return []
    except ValueError as exc:
        logger.exception("Invalid JSON response from Alpha Vantage for %s: %s", ticker, exc)
        return []

    if "Error Message" in payload:
        logger.warning("Alpha Vantage error for %s: %s", ticker, payload['Error Message'])
        return []

    if "Note" in payload:
        logger.warning("Alpha Vantage note for %s: %s", ticker, payload["Note"])
        return []

    quarterly_earnings = payload.get("quarterlyEarnings")
    if not isinstance(quarterly_earnings, list):
        logger.warning("No quarterlyEarnings field returned for %s.", ticker)
        return []

    today = datetime.now().date()
    valid_dates: List[pd.Timestamp] = []

    for item in quarterly_earnings:
        reported_date = item.get("reportedDate")
        if not reported_date:
            continue

        ts = pd.to_datetime(reported_date, errors="coerce")
        if pd.isna(ts):
            continue

        normalized = ts.normalize()

        # Exclude same-day/future dates to avoid incomplete next-session data
        if (today - normalized.date()).days >= 1:
            valid_dates.append(normalized)

    valid_dates = sorted(set(valid_dates))
    logger.info(
        "Fetched %d valid earnings dates for %s from Alpha Vantage.",
        len(valid_dates),
        ticker,
    )
    return valid_dates


def _fetch_price_history_for_earnings_window(
    ticker: str,
    earnings_dates: List[pd.Timestamp],
) -> pd.DataFrame:
    """Fetch daily price history covering all earnings dates plus a buffer window."""
    if not earnings_dates:
        return pd.DataFrame()

    start_date = min(earnings_dates) - pd.Timedelta(days=5)
    end_date = max(earnings_dates) + pd.Timedelta(days=5)

    try:
        YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))
        price_data = yf.Ticker(ticker).history(start=start_date, end=end_date)
    except Exception as exc:
        logger.warning("Yahoo Finance download failed for %s: %s", ticker, exc)
        return pd.DataFrame()

    if price_data.empty:
        logger.warning("No Yahoo Finance price history found for %s.", ticker)
        return pd.DataFrame()

    price_data = price_data.copy()

    if getattr(price_data.index, "tz", None) is not None:
        price_data.index = price_data.index.tz_localize(None)

    price_data["Next_Open"] = price_data["Open"].shift(-1)
    price_data["Next_Close"] = price_data["Close"].shift(-1)
    price_data.reset_index(inplace=True)
    price_data["Date"] = pd.to_datetime(price_data["Date"]).dt.normalize()

    return price_data


def _build_reactions_from_prices(
    earnings_dates: List[pd.Timestamp],
    price_data: pd.DataFrame,
) -> List[Dict]:
    """Compute normalized reaction metrics from earnings dates and daily price data."""
    results: List[Dict] = []

    for earnings_date in earnings_dates:
        row = price_data.loc[price_data["Date"] == earnings_date]
        if row.empty:
            continue

        close_price = row["Close"].iloc[0]
        next_open = row["Next_Open"].iloc[0]
        next_close = row["Next_Close"].iloc[0]

        if pd.isna(close_price) or pd.isna(next_open) or pd.isna(next_close):
            continue
        if close_price == 0 or next_open == 0:
            continue

        results.append(
            {
                "date": earnings_date.date().isoformat(),
                "close_to_open_pct": round((next_open - close_price) / close_price * 100, 2),
                "close_to_close_pct": round((next_close - close_price) / close_price * 100, 2),
                "open_to_close_pct": round((next_close - next_open) / next_open * 100, 2),
            }
        )

    return results


def _normalize_reactions(raw_reactions: List[Dict[str, Any]]) -> List[Dict]:
    """Normalize provider output to the package's internal canonical schema."""
    normalized: List[Dict] = []

    for item in raw_reactions:
        try:
            date_value = str(item["date"])
            c2o = float(item["close_to_open_pct"])
            c2c = float(item["close_to_close_pct"])
            o2c = float(item["open_to_close_pct"])
        except (KeyError, TypeError, ValueError):
            continue

        normalized.append(
            {
                "date": date_value,
                "close_to_open_pct": round(c2o, 2),
                "close_to_close_pct": round(c2c, 2),
                "open_to_close_pct": round(o2c, 2),
            }
        )

    return normalized
