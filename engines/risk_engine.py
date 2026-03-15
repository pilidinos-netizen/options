# engines/risk_engine.py

def risk_management(volatility, allocation, risk_profile="Balanced"):
    """
    Adjust position size based on volatility, calibrated to the risk profile.

    Conservative investors are flagged and cut earlier (lower vol tolerance).
    Speculators tolerate significantly more volatility before a position cut.

    Vol thresholds by profile:
    ┌──────────────┬──────────────────┬──────────────────┐
    │ Profile      │ Flag (moderate)  │ Flag (high)      │
    ├──────────────┼──────────────────┼──────────────────┤
    │ Conservative │ vol > 0.25       │ vol > 0.40       │
    │ Balanced     │ vol > 0.40       │ vol > 0.60       │
    │ Aggressive   │ vol > 0.55       │ vol > 0.75       │
    │ Speculator   │ vol > 0.70       │ vol > 0.90       │
    └──────────────┴──────────────────┴──────────────────┘
    """

    vol_thresholds = {
        "Conservative": {"moderate": 0.25, "high": 0.40},
        "Balanced":     {"moderate": 0.40, "high": 0.60},
        "Aggressive":   {"moderate": 0.55, "high": 0.75},
        "Speculator":   {"moderate": 0.70, "high": 0.90},
    }

    t = vol_thresholds.get(risk_profile, vol_thresholds["Balanced"])

    if volatility > t["high"]:
        allocation *= 0.5
        risk_flag = f"High Volatility ({volatility*100:.0f}%) — Position halved [{risk_profile}]"
    elif volatility > t["moderate"]:
        allocation *= 0.75
        risk_flag = f"Elevated Volatility ({volatility*100:.0f}%) — Position reduced [{risk_profile}]"
    else:
        risk_flag = f"Normal Risk ({volatility*100:.0f}% vol within {risk_profile} tolerance)"

    return round(allocation, 3), risk_flag
