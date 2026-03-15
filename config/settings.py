RISK_PROFILES = {
    "Conservative": 0.05,
    "Balanced": 0.10,
    "Aggressive": 0.20,
    "Speculator": 0.30
}

# Weights must sum to 1.0 — all six factors are now explicit
FACTOR_WEIGHTS = {
    "growth":        0.25,
    "profitability": 0.20,
    "efficiency":    0.20,
    "leverage":      0.15,
    "roe":           0.10,
    "valuation":     0.10,
}
