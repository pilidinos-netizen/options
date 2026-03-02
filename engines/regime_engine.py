def detect_regime(score):
    if score > 3:
        return "Expansion"
    elif score > 1:
        return "Late Cycle"
    elif score > -1:
        return "Neutral"
    else:
        return "Contraction"