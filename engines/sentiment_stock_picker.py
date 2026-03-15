# engines/sentiment_stock_picker.py
"""
Identifies top stock/options candidates from market news sentiment data.

Logic:
  1. Score macro themes by (sentiment_strength × mention_frequency)
  2. Map bullish themes to associated tickers via THEME_TICKERS
  3. Run the full quant model in parallel on candidate tickers
  4. Rank by a combined score = quant_composite + sentiment_alignment_bonus
  5. Return top N with full model output, theme context, and options thesis
"""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---------------------------------------------------------------------------
# Theme → Ticker mapping
# ---------------------------------------------------------------------------

THEME_TICKERS = {
    "AI / Technology": [
        "NVDA", "MSFT", "GOOGL", "META", "AMD", "AVGO", "PLTR", "CRWD",
        "NET", "PANW", "ARM", "MRVL", "SMCI", "TSM", "AMAT",
    ],
    "Fed / Rates": [
        "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "SCHW",
        "V", "MA", "AXP",
    ],
    "Inflation": [
        "XOM", "CVX", "COP", "OXY", "SLB", "EOG", "GLD", "FCX",
        "NEM", "MPC", "VLO",
    ],
    "Earnings Season": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
        "TSLA", "JPM", "V", "MA", "HD",
    ],
    "Recession / Growth": [
        "JNJ", "PG", "KO", "WMT", "PEP", "MCD", "COST", "CL", "MO", "VZ",
    ],
    "Geopolitics": [
        "LMT", "RTX", "GD", "NOC", "BA", "HII", "TDG", "L3T",
    ],
    "Energy": [
        "XOM", "CVX", "COP", "OXY", "SLB", "EOG", "MPC", "VLO", "PSX", "HAL",
    ],
    "Crypto / Digital Assets": [
        "COIN", "MSTR", "RIOT", "MARA", "CLSK",
    ],
    "Labor Market": [
        "ADP", "PAYX", "MAN", "RHI", "NSP",
    ],
    "Housing / Real Estate": [
        "DHI", "LEN", "TOL", "PHM", "NVR", "LOW", "HD",
    ],
}


# ---------------------------------------------------------------------------
# Sentiment bonus logic
# ---------------------------------------------------------------------------

def _sentiment_bonus(overall_label: str, overall_score: float, intent: str) -> float:
    """
    Reward models whose direction aligns with the macro news backdrop.
    Penalise if the quant signal contradicts a strongly bearish market.
    """
    if overall_label == "Bullish" and intent in ("STRONG BUY", "BUY"):
        return round(overall_score * 0.4, 3)
    elif overall_label == "Bullish" and intent == "HOLD":
        return round(overall_score * 0.1, 3)
    elif overall_label == "Bearish" and intent in ("REDUCE", "SELL"):
        return round(abs(overall_score) * 0.2, 3)
    elif overall_label == "Bearish" and intent in ("STRONG BUY", "BUY"):
        return round(-abs(overall_score) * 0.2, 3)   # penalise contrarian buys in bear news
    return 0.0


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def identify_top_stocks(
    sentiment_data: dict,
    run_model,
    risk_profile: str = "Balanced",
    top_n: int = 5,
    max_candidates: int = 25,
    max_workers: int = 8,
) -> dict:
    """
    Parameters
    ----------
    sentiment_data  : output dict from get_market_news_sentiment()
    run_model       : callable(ticker, risk_profile) -> result dict
    risk_profile    : user-selected risk profile
    top_n           : number of final picks to return
    max_candidates  : how many tickers to run the full model on
    max_workers     : parallel workers for quant model calls

    Returns
    -------
    {
      "picks"            : list of pick dicts (top_n),
      "bullish_themes"   : list of (theme, weight, sentiment) tuples,
      "overall_label"    : str,
      "overall_score"    : float,
      "candidates_run"   : int,
    }
    """
    overall_label   = sentiment_data.get("overall_label", "Neutral")
    overall_score   = sentiment_data.get("overall_score", 0.0)
    theme_breakdown = sentiment_data.get("theme_breakdown", [])

    # ── Step 1: Score themes ──────────────────────────────────────────────
    bullish_themes = []
    for t in theme_breakdown:
        if t["avg_sentiment"] > 0.02:                        # slight bullish tilt required
            weight = t["avg_sentiment"] * (1 + 0.05 * t["mentions"])
            bullish_themes.append((t["theme"], round(weight, 4), t["avg_sentiment"]))
    bullish_themes.sort(key=lambda x: x[1], reverse=True)

    # ── Step 2: Build candidate pool from top bullish themes ─────────────
    candidate_weight = defaultdict(float)
    candidate_themes = defaultdict(list)

    for theme_name, weight, sentiment in bullish_themes[:6]:
        for ticker in THEME_TICKERS.get(theme_name, []):
            candidate_weight[ticker] += weight
            candidate_themes[ticker].append({
                "theme":     theme_name,
                "sentiment": round(sentiment, 3),
                "weight":    round(weight, 4),
            })

    if not candidate_weight:
        return {
            "picks":          [],
            "bullish_themes": bullish_themes,
            "overall_label":  overall_label,
            "overall_score":  overall_score,
            "candidates_run": 0,
            "message":        "No bullish themes detected in current news. Market sentiment may be bearish or neutral.",
        }

    ranked = sorted(candidate_weight.items(), key=lambda x: x[1], reverse=True)
    candidates = [t for t, _ in ranked[:max_candidates]]

    # ── Step 3: Run quant model in parallel ───────────────────────────────
    raw_results = []

    def _run(ticker):
        try:
            return ticker, run_model(ticker, risk_profile)
        except Exception:
            return ticker, None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run, t): t for t in candidates}
        for future in as_completed(futures):
            ticker, model = future.result()
            if model is None:
                continue

            quant_score  = float(model.get("Factor Scores", {}).get("total", 0))
            intent       = model.get("Intent", "HOLD")
            bonus        = _sentiment_bonus(overall_label, overall_score, intent)
            combined     = round(quant_score + bonus, 3)

            raw_results.append({
                "ticker":           ticker,
                "intent":           intent,
                "confidence":       model.get("Confidence", 0),
                "regime":           model.get("Regime", "N/A"),
                "quant_score":      round(quant_score, 3),
                "sentiment_bonus":  bonus,
                "combined_score":   combined,
                "volatility":       model.get("Volatility", 0),
                "risk_flag":        model.get("Risk Flag", ""),
                "position_size":    model.get("Position Size (%)", 0),
                "options_strategy": model.get("Options Strategy", ""),
                "mc_projection":    model.get("Monte Carlo Projection (1Y)", 0),
                "factor_scores":    model.get("Factor Scores", {}),
                "reasoning":        model.get("Reasoning", ""),
                "timing":           model.get("Timing Plan", ""),
                "theme_alignment":  candidate_themes[ticker],
                "theme_weight":     round(candidate_weight[ticker], 4),
            })

    # ── Step 4: Rank and return top N ─────────────────────────────────────
    # Prefer BUY/STRONG BUY signals; among those, rank by combined_score
    intent_rank = {"STRONG BUY": 0, "BUY": 1, "HOLD": 2, "REDUCE": 3, "SELL": 4}
    raw_results.sort(
        key=lambda x: (intent_rank.get(x["intent"], 5), -x["combined_score"])
    )

    return {
        "picks":          raw_results[:top_n],
        "bullish_themes": bullish_themes,
        "overall_label":  overall_label,
        "overall_score":  overall_score,
        "candidates_run": len(raw_results),
    }
