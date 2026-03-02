# engines/performance_engine.py

import numpy as np
from data.market_data import get_price_history


def compute_performance_metrics(ticker):
    """
    Computes long-term performance statistics safely.
    """

    data = get_price_history(ticker, period="5y")

    if data is None or data.empty:
        raise ValueError("No historical data available.")

    # Handle possible multi-index column issue
    close_data = data["Close"]

    # If multi-column (rare yfinance behavior), take first column
    if hasattr(close_data, "columns"):
        close = close_data.iloc[:, 0].dropna()
    else:
        close = close_data.dropna()

    if close.empty:
        raise ValueError("No valid close price data.")

    returns = close.pct_change().dropna()

    # Ensure scalar outputs
    total_return = float((close.iloc[-1] / close.iloc[0]) - 1)
    annual_return = float(np.mean(returns.values) * 252)
    annual_volatility = float(np.std(returns.values) * np.sqrt(252))

    if annual_volatility > 0:
        sharpe = annual_return / annual_volatility
    else:
        sharpe = 0.0

    drawdown_series = close / close.cummax() - 1
    max_drawdown = float(drawdown_series.min())

    return {
        "Total Return (%)": round(total_return * 100, 2),
        "Annual Return (%)": round(annual_return * 100, 2),
        "Annual Volatility (%)": round(annual_volatility * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Max Drawdown (%)": round(max_drawdown * 100, 2)
    }