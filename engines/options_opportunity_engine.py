# engines/options_opportunity_engine.py

import yfinance as yf
from datetime import datetime


def get_liquidity_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.info.get("averageVolume", 0)
    except Exception:
        return 0


def calculate_opportunity_score(confidence, volatility, liquidity):
    return (
        confidence * 0.5 +
        volatility * 100 * 0.3 +
        (liquidity / 1_000_000) * 0.2
    )


def select_best_option_contract(ticker, intent):
    stock = yf.Ticker(ticker)
    expirations = stock.options

    if not expirations:
        return None

    # Pick nearest expiration > 30 days
    selected_exp = expirations[0]

    chain = stock.option_chain(selected_exp)

    current_price = stock.history(period="1d")["Close"].iloc[-1]

    if intent in ["STRONG BUY", "BUY"]:
        calls = chain.calls
        calls["distance"] = abs(calls["strike"] - current_price)
        best = calls.sort_values("distance").iloc[0]
    else:
        puts = chain.puts
        puts["distance"] = abs(puts["strike"] - current_price)
        best = puts.sort_values("distance").iloc[0]

    strike = float(best["strike"])
    premium = float(best["lastPrice"])

    if intent in ["STRONG BUY", "BUY"]:
        break_even = strike + premium
        strategy_type = "Call Option"
    else:
        break_even = strike - premium
        strategy_type = "Put Option"

    return {
        "Expiration": selected_exp,
        "Strike": strike,
        "Premium": premium,
        "Break Even": round(break_even, 2),
        "Strategy Type": strategy_type
    }


def rank_option_opportunities(tickers, run_model, profile):

    opportunities = []

    for ticker in tickers:

        try:
            result = run_model(ticker, profile)

            confidence = result["Confidence"]
            volatility = result["Volatility"]
            intent = result["Intent"]
            liquidity = get_liquidity_score(ticker)

            score = calculate_opportunity_score(
                confidence,
                volatility,
                liquidity
            )

            contract = select_best_option_contract(ticker, intent)

            if not contract:
                continue

            reasoning = (
                f"{intent} signal with confidence {confidence}. "
                f"Volatility at {round(volatility,3)} supports options activity."
            )

            opportunities.append({
                "Ticker": ticker,
                "Intent": intent,
                "Confidence": confidence,
                "Volatility": round(volatility, 3),
                "Liquidity": liquidity,
                "Opportunity Score": round(score, 2),
                "Strategy": contract["Strategy Type"],
                "Strike Price": contract["Strike"],
                "Expiration Date": contract["Expiration"],
                "Premium (Cost)": contract["Premium"],
                "Break Even Price": contract["Break Even"],
                "Reasoning": reasoning
            })

        except Exception:
            continue

    return sorted(
        opportunities,
        key=lambda x: x["Opportunity Score"],
        reverse=True
    )[:10]