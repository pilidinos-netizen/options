# engines/position_sizer.py

from config.settings import RISK_PROFILES


def position_size(intent, risk_profile):
    """
    Determines allocation based on intent strength and risk profile.
    """

    base_allocation = RISK_PROFILES.get(risk_profile, 0.10)

    # Increase allocation for strong signals
    if intent == "STRONG BUY":
        multiplier = 1.5
    elif intent == "BUY":
        multiplier = 1.2
    elif intent == "HOLD":
        multiplier = 1.0
    elif intent == "REDUCE":
        multiplier = 0.5
    else:  # SELL
        multiplier = 0.0

    return round(base_allocation * multiplier, 3)