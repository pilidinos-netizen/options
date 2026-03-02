# engines/options_contract_engine.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


def select_leaps_contract(ticker, min_months=10, target_delta=None):
    """
    Automatically selects a long-dated ATM call (LEAPS).
    """

    stock = yf.Ticker(ticker)

    expirations = stock.options

    if not expirations:
        raise ValueError("No options data available.")

    # Select expiration at least min_months out
    selected_exp = None
    today = datetime.today()

    for exp in expirations:
        exp_date = datetime.strptime(exp, "%Y-%m-%d")
        months_out = (exp_date - today).days / 30

        if months_out >= min_months:
            selected_exp = exp
            break

    if selected_exp is None:
        selected_exp = expirations[-1]

    chain = stock.option_chain(selected_exp)
    calls = chain.calls

    current_price = stock.history(period="1d")["Close"].iloc[-1]

    # Find closest ATM strike
    calls["distance"] = abs(calls["strike"] - current_price)
    atm_call = calls.sort_values("distance").iloc[0]

    return {
        "Expiration": selected_exp,
        "Strike": float(atm_call["strike"]),
        "Premium": float(atm_call["lastPrice"]),
        "Contract Symbol": atm_call["contractSymbol"]
    }