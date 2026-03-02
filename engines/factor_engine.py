# engines/factor_engine.py

from config.settings import FACTOR_WEIGHTS


def compute_scores(info):

    revenue_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    operating_margin = info.get("operatingMargins", 0) or 0
    debt_to_equity = info.get("debtToEquity", 0) or 0
    return_on_equity = info.get("returnOnEquity", 0) or 0

    # Growth
    if revenue_growth > 0.30:
        growth = 5
    elif revenue_growth > 0.15:
        growth = 3
    elif revenue_growth > 0:
        growth = 1
    else:
        growth = -2

    # Profitability
    if gross_margin > 0.60:
        profitability = 4
    elif gross_margin > 0.50:
        profitability = 2
    else:
        profitability = -1

    # Efficiency
    if operating_margin > 0.30:
        efficiency = 3
    elif operating_margin > 0.15:
        efficiency = 1
    else:
        efficiency = -1

    # Balance Sheet Risk
    if debt_to_equity < 50:
        leverage = 2
    elif debt_to_equity < 100:
        leverage = 0
    else:
        leverage = -2

    # Capital Efficiency
    if return_on_equity > 0.25:
        roe_score = 3
    elif return_on_equity > 0.15:
        roe_score = 1
    else:
        roe_score = -1

    weighted_total = (
        growth * FACTOR_WEIGHTS["growth"] +
        profitability * FACTOR_WEIGHTS["profitability"] +
        efficiency * 0.4 +
        leverage * 0.3 +
        roe_score * 0.5
    )

    return {
        "growth": growth,
        "profitability": profitability,
        "efficiency": efficiency,
        "leverage": leverage,
        "roe": roe_score,
        "total": weighted_total
    }