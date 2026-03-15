# data/market_data.py
"""
Historical price data with two-source fallback:
  1. yfinance       — primary (free, OHLCV via Yahoo Finance)
  2. Polygon.io     — fallback via /v2/aggs/ticker/{ticker}/range/...
"""

import requests
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config.api_keys import POLYGON_API_KEY

_POLYGON_BASE = "https://api.polygon.io"

# Map yfinance period strings to approximate calendar days
_PERIOD_DAYS = {
    "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
    "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 3650,
}


# ---------------------------------------------------------------------------
# Polygon fallback
# ---------------------------------------------------------------------------

def _polygon_price_history(ticker: str, period: str) -> pd.DataFrame:
    """
    Fetch daily OHLCV bars from Polygon /v2/aggs.
    Returns a DataFrame with the same column structure as yfinance download.
    """
    if not POLYGON_API_KEY:
        return pd.DataFrame()
    try:
        days = _PERIOD_DAYS.get(period, 365)
        end_dt   = datetime.today()
        start_dt = end_dt - timedelta(days=days)

        url = (
            f"{_POLYGON_BASE}/v2/aggs/ticker/{ticker.upper()}/range/1/day/"
            f"{start_dt.strftime('%Y-%m-%d')}/{end_dt.strftime('%Y-%m-%d')}"
        )
        r = requests.get(url, params={
            "adjusted": "true",
            "sort":     "asc",
            "limit":    50000,
            "apiKey":   POLYGON_API_KEY,
        }, timeout=10)

        if r.status_code != 200:
            return pd.DataFrame()

        results = r.json().get("results", [])
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df["Date"] = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_localize(None)
        df = df.rename(columns={
            "o": "Open", "h": "High", "l": "Low",
            "c": "Close", "v": "Volume",
        })
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].set_index("Date")
        return df

    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Return OHLCV price history DataFrame for ticker.
    Tries yfinance first; falls back to Polygon.io if yfinance returns
    empty data or raises an exception.
    """
    # ── Primary: yfinance ─────────────────────────────────────────────────
    try:
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if data is not None and not data.empty:
            # yfinance multi-level columns when downloading single ticker
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data
    except Exception:
        pass

    # ── Fallback: Polygon.io ──────────────────────────────────────────────
    data = _polygon_price_history(ticker, period)
    if not data.empty:
        return data

    raise ValueError(f"No market data available for {ticker} from any source.")
