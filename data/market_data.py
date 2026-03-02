# data/market_data.py

import yfinance as yf
import pandas as pd


def get_price_history(ticker, period="1y"):
    """
    Downloads historical price data using yfinance.
    Returns pandas DataFrame.
    """

    data = yf.download(ticker, period=period, progress=False)

    if data is None or data.empty:
        raise ValueError(f"No market data returned for {ticker}")

    return data