# engines/options_payoff_engine.py

import numpy as np


def calculate_call_payoff(strike, premium, price_range):

    payoff = []

    for price in price_range:
        intrinsic = max(price - strike, 0)
        profit = intrinsic - premium
        payoff.append(profit)

    return payoff