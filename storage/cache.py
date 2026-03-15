import sqlite3
import os
import pickle
import time

# --- Signals DB ---

def init_db():
    conn = sqlite3.connect("quant.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        ticker TEXT,
        intent TEXT,
        confidence REAL
    )
    """)
    conn.commit()
    return conn


# --- Options chain file cache ---

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "options_cache")


def _ensure_cache_dir():
    os.makedirs(_CACHE_DIR, exist_ok=True)


def _cache_path(ticker, expiry=None):
    suffix = f"_{expiry}" if expiry else "_nearest"
    return os.path.join(_CACHE_DIR, f"{ticker.upper()}_options{suffix}.pkl")


def save_options_cache(ticker, calls, puts, expiry=None):
    """Persist calls and puts DataFrames to disk with a timestamp.
    expiry=None means nearest-expiry cache."""
    _ensure_cache_dir()
    payload = {"calls": calls, "puts": puts, "timestamp": time.time()}
    with open(_cache_path(ticker, expiry), "wb") as f:
        pickle.dump(payload, f)


def load_options_cache(ticker, expiry=None, max_age_hours=4):
    """
    Load cached options data for ticker.
    expiry=None loads the nearest-expiry cache.
    Returns (calls, puts) if cache exists and is fresh, else (None, None).
    """
    path = _cache_path(ticker, expiry)
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        age_hours = (time.time() - payload["timestamp"]) / 3600
        if age_hours > max_age_hours:
            return None, None
        return payload["calls"], payload["puts"]
    except Exception:
        return None, None
