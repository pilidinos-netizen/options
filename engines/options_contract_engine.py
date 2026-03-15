# engines/options_contract_engine.py

import pandas as pd
from datetime import datetime

from data.options_chain import get_expirations, get_options_by_expiry
from data.market_data import get_price_history


def select_leaps_contract(ticker, min_months=10, target_delta=None):
    """
    Automatically selects a long-dated ATM call (LEAPS).
    Uses Polygon → yfinance → cache fallback via get_expirations / get_options_by_expiry.
    """
    expirations = get_expirations(ticker)

    if not expirations:
        raise ValueError("No options expirations available.")

    # Select expiration at least min_months out
    today = datetime.today()
    selected_exp = None

    for exp in expirations:
        exp_date = datetime.strptime(exp, "%Y-%m-%d")
        months_out = (exp_date - today).days / 30
        if months_out >= min_months:
            selected_exp = exp
            break

    if selected_exp is None:
        selected_exp = expirations[-1]

    calls, _ = get_options_by_expiry(ticker, selected_exp)

    if calls is None or calls.empty:
        raise ValueError(f"No calls data available for {ticker} expiry {selected_exp}.")

    price_data = get_price_history(ticker, period="1d")
    current_price = float(price_data["Close"].dropna().iloc[-1])

    calls["distance"] = abs(calls["strike"] - current_price)
    atm_call = calls.sort_values("distance").iloc[0]

    return {
        "Expiration":       selected_exp,
        "Strike":           float(atm_call["strike"]),
        "Premium":          float(atm_call["lastPrice"]),
        "Contract Symbol":  atm_call["contractSymbol"],
    }
