import requests
import pandas as pd
import yfinance as yf

from config.api_keys import POLYGON_API_KEY
from storage.cache import save_options_cache, load_options_cache

_POLYGON_BASE = "https://api.polygon.io/v3/snapshot/options"


# ---------------------------------------------------------------------------
# Polygon helpers
# ---------------------------------------------------------------------------

def _fetch_polygon_raw(ticker, expiry=None):
    """Fetch all option contracts from Polygon; optionally filter by expiry."""
    params = {"limit": 250, "apiKey": POLYGON_API_KEY}
    if expiry:
        params["expiration_date"] = expiry
    resp = requests.get(f"{_POLYGON_BASE}/{ticker.upper()}", params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError("Polygon returned no options data.")
    rows = []
    for r in results:
        details = r.get("details", {})
        greeks  = r.get("greeks", {})
        quote   = r.get("last_quote", {})
        day     = r.get("day", {})
        rows.append({
            "contractSymbol": details.get("ticker", ""),
            "strike":         details.get("strike_price"),
            "expiration":     details.get("expiration_date"),
            "contractType":   details.get("contract_type"),
            "bid":            quote.get("bid"),
            "ask":            quote.get("ask"),
            "lastPrice":      quote.get("midpoint"),
            "volume":         day.get("volume"),
            "openInterest":   r.get("open_interest"),
            "impliedVolatility": r.get("implied_volatility"),
            "delta": greeks.get("delta"),
            "gamma": greeks.get("gamma"),
            "theta": greeks.get("theta"),
            "vega":  greeks.get("vega"),
        })
    return pd.DataFrame(rows)


def _split_calls_puts(df, expiry=None):
    """Filter df to an expiry (or nearest) and split into (calls, puts)."""
    target = expiry if expiry else df["expiration"].dropna().min()
    df = df[df["expiration"] == target]
    calls = df[df["contractType"] == "call"].reset_index(drop=True)
    puts  = df[df["contractType"] == "put"].reset_index(drop=True)
    return calls, puts


# ---------------------------------------------------------------------------
# yfinance helpers
# ---------------------------------------------------------------------------

def _fetch_yfinance_chain(ticker, expiry=None):
    """Fetch yfinance chain for a specific expiry or nearest if None."""
    stock = yf.Ticker(ticker)
    expirations = stock.options
    if not expirations:
        raise ValueError("yfinance returned no expirations.")
    target = expiry if (expiry and expiry in expirations) else expirations[0]
    chain = stock.option_chain(target)
    return chain.calls, chain.puts


# ---------------------------------------------------------------------------
# Public: get_expirations
# ---------------------------------------------------------------------------

def get_expirations(ticker):
    """
    Return a sorted list of available expiration date strings (YYYY-MM-DD).
    Fallback order: Polygon → yfinance → cache.
    """
    if POLYGON_API_KEY:
        try:
            df = _fetch_polygon_raw(ticker)
            return sorted(df["expiration"].dropna().unique().tolist())
        except Exception as e:
            print(f"[options_chain] Polygon expirations failed ({e}), trying yfinance...")

    try:
        expirations = yf.Ticker(ticker).options
        if expirations:
            return list(expirations)
    except Exception as e:
        print(f"[options_chain] yfinance expirations failed ({e}), trying cache...")

    # Last resort: pull dates out of any cached nearest-expiry data
    calls, _ = load_options_cache(ticker)
    if calls is not None and "expiration" in calls.columns:
        dates = calls["expiration"].dropna().unique().tolist()
        if dates:
            return sorted(dates)

    return []


# ---------------------------------------------------------------------------
# Public: get_options_chain  (nearest expiry)
# ---------------------------------------------------------------------------

def get_options_chain(ticker):
    """
    Fetch options chain for the nearest available expiry.
    Fallback order: Polygon → yfinance → local cache.
    Returns (calls_df, puts_df) or (None, None).
    """
    return _get_chain_with_fallback(ticker, expiry=None)


# ---------------------------------------------------------------------------
# Public: get_options_by_expiry  (specific expiry)
# ---------------------------------------------------------------------------

def get_options_by_expiry(ticker, expiry):
    """
    Fetch options chain for a specific expiration date (YYYY-MM-DD).
    Fallback order: Polygon → yfinance → local cache.
    Returns (calls_df, puts_df) or (None, None).
    """
    return _get_chain_with_fallback(ticker, expiry=expiry)


# ---------------------------------------------------------------------------
# Internal fallback engine
# ---------------------------------------------------------------------------

def _get_chain_with_fallback(ticker, expiry=None):
    calls, puts, source = None, None, None
    label = expiry or "nearest"

    # 1 — Polygon
    if POLYGON_API_KEY:
        try:
            df = _fetch_polygon_raw(ticker, expiry=expiry)
            calls, puts = _split_calls_puts(df, expiry=expiry)
            source = "Polygon"
        except Exception as e:
            print(f"[options_chain] Polygon failed ({e}), trying yfinance...")

    # 2 — yfinance
    if calls is None:
        try:
            calls, puts = _fetch_yfinance_chain(ticker, expiry=expiry)
            source = "yfinance"
        except Exception as e:
            print(f"[options_chain] yfinance failed ({e}), trying cache...")

    # 3 — Local cache
    if calls is None:
        calls, puts = load_options_cache(ticker, expiry=expiry)
        if calls is not None:
            source = "cache"
            print(f"[options_chain] {ticker} ({label}) loaded from local cache.")

    if calls is None:
        print(f"[options_chain] All sources failed for {ticker} ({label}).")
        return None, None

    # Keep cache warm whenever we got live data
    if source in ("Polygon", "yfinance"):
        save_options_cache(ticker, calls, puts, expiry=expiry)

    print(f"[options_chain] {ticker} ({label}) loaded from {source}.")
    return calls, puts
