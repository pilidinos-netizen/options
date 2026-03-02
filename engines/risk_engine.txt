# engines/risk_engine.py

def risk_management(volatility, allocation):
    """
    Adjust position size based on volatility.
    Returns adjusted allocation and risk flag.
    """

    if volatility > 0.6:
        allocation *= 0.5
        risk_flag = "High Volatility - Reduced Position"

    elif volatility > 0.4:
        allocation *= 0.75
        risk_flag = "Moderate Volatility"

    else:
        risk_flag = "Normal Risk"

    return round(allocation, 3), risk_flag