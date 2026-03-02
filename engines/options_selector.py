# engines/options_selector.py

def select_options_strategy(intent, risk_profile):
    """
    Selects options strategy based on intent and risk profile.
    """

    if intent in ["STRONG BUY", "BUY"]:
        if risk_profile in ["Aggressive", "Speculator"]:
            return "Buy 12M ATM LEAPS"
        else:
            return "Sell Cash Secured Puts"

    elif intent == "HOLD":
        return "Covered Calls"

    else:
        return "Buy Protective Puts"