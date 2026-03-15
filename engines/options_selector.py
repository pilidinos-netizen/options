# engines/options_selector.py

def select_options_strategy(intent, risk_profile):
    """
    Select an options strategy based on intent AND risk profile.

    Each profile has its own strategy set reflecting its risk/reward preference:

    Conservative  — income-first, capital-preservation, defined-risk structures
    Balanced      — directional with defined risk, spread-based
    Aggressive    — outright directional, higher leverage, LEAPS
    Speculator    — maximum leverage, OTM structures, short-dated plays
    """

    strategies = {
        "Conservative": {
            "STRONG BUY": "Sell Cash-Secured Put (ATM, 30–45 DTE)",
            "BUY":        "Bull Put Spread (defined risk, 30–45 DTE)",
            "HOLD":       "Covered Call (OTM, 30 DTE) for income",
            "REDUCE":     "Buy Protective Put (ATM hedge)",
            "SELL":       "Sell Covered Call (deep ITM) / Exit position",
        },
        "Balanced": {
            "STRONG BUY": "Bull Call Spread (ATM/OTM, 45–60 DTE)",
            "BUY":        "Buy ATM Call (45–60 DTE) or Bull Call Spread",
            "HOLD":       "Covered Call (slight OTM, 30–45 DTE)",
            "REDUCE":     "Bear Put Spread (defined downside hedge)",
            "SELL":       "Buy Protective Put or close long position",
        },
        "Aggressive": {
            "STRONG BUY": "Buy 12M ATM LEAPS Call",
            "BUY":        "Buy ATM Call (30–60 DTE), 2–3% OTM strike",
            "HOLD":       "Sell ATM Straddle (IV-rich environment) or Covered Call",
            "REDUCE":     "Buy OTM Put (30 DTE) or Bear Call Spread",
            "SELL":       "Buy ATM Put / Ratio Put Spread",
        },
        "Speculator": {
            "STRONG BUY": "Buy OTM Call (5–10% OTM, 30–60 DTE) + LEAPS kicker",
            "BUY":        "Buy OTM Call (2–5% OTM, 21–45 DTE)",
            "HOLD":       "Short Strangle (collect premium, manage actively)",
            "REDUCE":     "Buy OTM Put (5–10% OTM) / Debit Put Spread",
            "SELL":       "Buy Deep OTM Put / Bear Put Spread (high leverage)",
        },
    }

    profile_strategies = strategies.get(risk_profile, strategies["Balanced"])
    return profile_strategies.get(intent, "No strategy available")
