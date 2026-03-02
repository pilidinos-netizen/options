def classify_intent(weighted_score, volatility):

    if weighted_score >= 5 and volatility < 0.4:
        return "STRONG BUY", 90
    elif weighted_score >= 3:
        return "BUY", 75
    elif weighted_score >= 1:
        return "HOLD", 60
    elif weighted_score >= -1:
        return "REDUCE", 45
    else:
        return "SELL", 25