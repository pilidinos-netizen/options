# engines/volatility_engine.py

import numpy as np
from data.market_data import get_price_history


def calculate_volatility(ticker):
    """
    Returns annualized volatility as float.
    """

    data = get_price_history(ticker)

    if data.empty:
        raise ValueError("No market data for volatility calculation.")

    close_prices = data["Close"].dropna()

    returns = close_prices.pct_change().dropna()

    annual_vol = np.std(returns.values) * np.sqrt(252)

    return float(annual_vol)