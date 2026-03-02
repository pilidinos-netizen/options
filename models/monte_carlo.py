# models/monte_carlo.py

import numpy as np


def simulate_price(S0, mu=0.10, sigma=0.30, T=1, sims=1000):
    """
    Monte Carlo simulation using Geometric Brownian Motion.
    """

    S0 = float(S0)
    sigma = float(sigma)

    if S0 <= 0:
        raise ValueError("Initial price must be positive")

    results = []

    for _ in range(sims):
        ST = S0 * np.exp(
            (mu - 0.5 * sigma**2) * T
            + sigma * np.random.normal()
        )
        results.append(ST)

    return float(np.mean(results))