def classify_intent(weighted_score, volatility, risk_profile="Balanced"):
    """
    Map composite factor score + volatility to an intent signal.

    Risk profile controls two things:
      1. Score threshold — Conservative requires a stronger signal to commit;
         Speculator can act on weaker signals.
      2. Volatility ceiling — Conservative avoids high-vol names for top signals;
         Speculator tolerates much more movement.

    Thresholds (score / vol ceiling) by profile:
    ┌──────────────┬────────────────────────────────┬─────────────────────────────┐
    │ Profile      │ STRONG BUY (score / vol <)     │ BUY (score / vol <)         │
    ├──────────────┼────────────────────────────────┼─────────────────────────────┤
    │ Conservative │ 3.2 / 0.20                     │ 2.2 / 0.30                  │
    │ Balanced     │ 3.0 / 0.30                     │ 1.8 / 0.50                  │
    │ Aggressive   │ 2.5 / 0.45                     │ 1.5 / 0.65                  │
    │ Speculator   │ 2.0 / 0.60                     │ 1.2 / 0.80                  │
    └──────────────┴────────────────────────────────┴─────────────────────────────┘

    HOLD / REDUCE / SELL thresholds are profile-agnostic (score bands only).
    """

    thresholds = {
        "Conservative": {"sb_score": 3.2, "sb_vol": 0.20, "b_score": 2.2, "b_vol": 0.30},
        "Balanced":     {"sb_score": 3.0, "sb_vol": 0.30, "b_score": 1.8, "b_vol": 0.50},
        "Aggressive":   {"sb_score": 2.5, "sb_vol": 0.45, "b_score": 1.5, "b_vol": 0.65},
        "Speculator":   {"sb_score": 2.0, "sb_vol": 0.60, "b_score": 1.2, "b_vol": 0.80},
    }

    t = thresholds.get(risk_profile, thresholds["Balanced"])

    if weighted_score >= t["sb_score"] and volatility < t["sb_vol"]:
        return "STRONG BUY", 90
    elif weighted_score >= t["b_score"] and volatility < t["b_vol"]:
        return "BUY", 75
    elif weighted_score >= 0.8:
        return "HOLD", 60
    elif weighted_score >= 0.0:
        return "REDUCE", 45
    else:
        return "SELL", 25
