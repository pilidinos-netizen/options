# data/fundamentals.py
"""
Fundamental data with two-source fallback:
  1. yfinance  — primary (free, broad coverage)
  2. Polygon.io — fallback via /vX/reference/financials and /v3/reference/tickers
"""

import requests
import yfinance as yf

from config.api_keys import POLYGON_API_KEY

_POLYGON_BASE = "https://api.polygon.io"


# ---------------------------------------------------------------------------
# Polygon helpers
# ---------------------------------------------------------------------------

def _polygon_ticker_details(ticker: str) -> dict:
    """Fetch company metadata from Polygon /v3/reference/tickers/{ticker}."""
    if not POLYGON_API_KEY:
        return {}
    try:
        url = f"{_POLYGON_BASE}/v3/reference/tickers/{ticker.upper()}"
        r = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8)
        if r.status_code != 200:
            return {}
        data = r.json().get("results", {})
        return data or {}
    except Exception:
        return {}


def _polygon_financials(ticker: str) -> dict:
    """
    Fetch latest annual financials from Polygon /vX/reference/financials.
    Maps Polygon fields to the same keys yfinance .info uses so the rest of
    the codebase needs zero changes.
    """
    if not POLYGON_API_KEY:
        return {}
    try:
        url = f"{_POLYGON_BASE}/vX/reference/financials"
        params = {
            "ticker":    ticker.upper(),
            "timeframe": "annual",
            "limit":     2,
            "apiKey":    POLYGON_API_KEY,
        }
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return {}
        results = r.json().get("results", [])
        if not results:
            return {}

        fin = results[0].get("financials", {})
        inc = fin.get("income_statement", {})
        bal = fin.get("balance_sheet", {})
        cf  = fin.get("cash_flow_statement", {})

        def _v(section, key):
            return section.get(key, {}).get("value", None)

        revenue      = _v(inc, "revenues")
        net_income   = _v(inc, "net_income_loss")
        gross_profit = _v(inc, "gross_profit")
        op_income    = _v(inc, "operating_income_loss")
        total_assets = _v(bal, "assets")
        total_equity = _v(bal, "equity")
        total_debt   = _v(bal, "long_term_debt")

        # Prior-year revenue for growth calc
        rev_growth = None
        if len(results) > 1:
            prev_rev = results[1].get("financials", {}).get(
                "income_statement", {}
            ).get("revenues", {}).get("value", None)
            if prev_rev and prev_rev != 0 and revenue:
                rev_growth = (revenue - prev_rev) / abs(prev_rev)

        out = {}
        if rev_growth   is not None:             out["revenueGrowth"]     = rev_growth
        if revenue and gross_profit:             out["grossMargins"]      = gross_profit / revenue
        if revenue and op_income:               out["operatingMargins"]  = op_income / revenue
        if total_assets and net_income:         out["returnOnAssets"]    = net_income / total_assets
        if total_equity and net_income:         out["returnOnEquity"]    = net_income / total_equity
        if total_equity and total_debt:
            out["debtToEquity"] = (total_debt / total_equity) * 100
        return out

    except Exception:
        return {}


def _polygon_snapshot(ticker: str) -> dict:
    """Market cap + price from Polygon snapshot."""
    if not POLYGON_API_KEY:
        return {}
    try:
        url = f"{_POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}"
        r = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8)
        if r.status_code != 200:
            return {}
        snap = r.json().get("ticker", {})
        out = {}
        mc = snap.get("day", {}).get("v", None)   # volume not market cap
        # Market cap not in snapshot — use ticker details
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_fundamentals(ticker: str) -> dict:
    """
    Return fundamental data dict for ticker.
    Tries yfinance first; falls back to Polygon.io if yfinance returns
    an empty or minimal result.
    """
    # ── Primary: yfinance ─────────────────────────────────────────────────
    try:
        info = yf.Ticker(ticker).info
        # yfinance returns a minimal dict (just {}) when the ticker is bad
        # or rate-limited. Consider it failed if fewer than 10 keys returned.
        if info and len(info) >= 10:
            info["_source"] = "yfinance"
            return info
    except Exception:
        pass

    # ── Fallback: Polygon.io ──────────────────────────────────────────────
    out = {}

    details = _polygon_ticker_details(ticker)
    if details:
        out["shortName"]   = details.get("name", ticker)
        out["sector"]      = details.get("sic_description", "N/A")
        out["industry"]    = details.get("sic_description", "N/A")
        out["marketCap"]   = details.get("market_cap", None)
        out["description"] = details.get("description", "")
        out["exchange"]    = details.get("primary_exchange", "")

    financials = _polygon_financials(ticker)
    out.update(financials)

    out["_source"] = "polygon" if out else "none"
    return out
