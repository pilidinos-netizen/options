
# main.py


import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# main.py

from data.fundamentals import get_fundamentals
from data.market_data import get_price_history

from engines.factor_engine import compute_scores
from engines.intent_classifier import classify_intent
from engines.regime_engine import detect_regime
from engines.options_selector import select_options_strategy
from engines.position_sizer import position_size
from engines.timing_engine import timing_plan
from engines.volatility_engine import calculate_volatility
from engines.risk_engine import risk_management

from models.monte_carlo import simulate_price


def run_quant_model(ticker, risk_profile):

    # --------------------------------------
    # 1️⃣ Fundamentals
    # --------------------------------------
    info = get_fundamentals(ticker)

    # --------------------------------------
    # 2️⃣ Multi-factor scoring
    # --------------------------------------
    scores = compute_scores(info)
    weighted_score = float(scores["total"])

    # --------------------------------------
    # 3️⃣ Volatility
    # --------------------------------------
    volatility = float(calculate_volatility(ticker))

    # --------------------------------------
    # 4️⃣ Intent classification
    # --------------------------------------
    intent, confidence = classify_intent(weighted_score, volatility)

    # --------------------------------------
    # 5️⃣ Regime
    # --------------------------------------
    regime = detect_regime(weighted_score)

    # --------------------------------------
    # 6️⃣ Options strategy
    # --------------------------------------
    options_strategy = select_options_strategy(intent, risk_profile)

    # --------------------------------------
    # 7️⃣ Position sizing
    # --------------------------------------
    allocation = position_size(intent, risk_profile)

    # --------------------------------------
    # 8️⃣ Risk adjustment
    # --------------------------------------
    allocation, risk_flag = risk_management(volatility, allocation)

    # --------------------------------------
    # 9️⃣ Current Price (Hardened Extraction)
    # --------------------------------------
    price_data = get_price_history(ticker)

    if price_data.empty:
        raise ValueError("No price data available.")

    current_price = float(price_data["Close"].dropna().iloc[-1])

    # --------------------------------------
    # 🔟 Monte Carlo Projection
    # --------------------------------------
    mc_projection = simulate_price(
        S0=current_price,
        mu=0.10,
        sigma=volatility,
        T=1,
        sims=1000
    )

    # --------------------------------------
    # 1️⃣1️⃣ Timing Plan
    # --------------------------------------
    timing = timing_plan()

    return {
        "Ticker": ticker.upper(),
        "Intent": intent,
        "Confidence": confidence,
        "Regime": regime,
        "Volatility": round(volatility, 3),
        "Options Strategy": options_strategy,
        "Position Size (%)": round(allocation * 100, 2),
        "Risk Flag": risk_flag,
        "Monte Carlo Projection (1Y)": round(mc_projection, 2),
        "Timing Plan": timing,
        "Factor Scores": scores
    }


if __name__ == "__main__":
    print(run_quant_model("NVDA", "Balanced"))