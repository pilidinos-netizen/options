# engines/factor_engine.py

from config.settings import FACTOR_WEIGHTS


def compute_scores(info):
    """
    Score each fundamental factor and return a weighted composite.

    Factor score ranges:
      growth:        -2 to  5
      profitability: -1 to  4
      efficiency:    -1 to  3
      leverage:      -2 to  2
      roe:           -1 to  3
      valuation:     -3 to  2

    Max composite ≈ 3.45  |  STRONG BUY threshold: 3.0
    Min composite ≈ -1.60 |  SELL threshold: < 0.0
    """

    revenue_growth   = info.get("revenueGrowth",    0) or 0
    gross_margin     = info.get("grossMargins",      0) or 0
    operating_margin = info.get("operatingMargins",  0) or 0
    debt_to_equity   = info.get("debtToEquity",      0) or 0
    return_on_equity = info.get("returnOnEquity",    0) or 0
    forward_pe       = info.get("forwardPE",      None)

    # --- Growth ---
    if revenue_growth > 0.30:
        growth = 5
    elif revenue_growth > 0.15:
        growth = 3
    elif revenue_growth > 0:
        growth = 1
    else:
        growth = -2

    # --- Profitability ---
    if gross_margin > 0.60:
        profitability = 4
    elif gross_margin > 0.50:
        profitability = 2
    else:
        profitability = -1

    # --- Efficiency ---
    if operating_margin > 0.30:
        efficiency = 3
    elif operating_margin > 0.15:
        efficiency = 1
    else:
        efficiency = -1

    # --- Leverage ---
    if debt_to_equity < 50:
        leverage = 2
    elif debt_to_equity < 100:
        leverage = 0
    else:
        leverage = -2

    # --- Capital Efficiency ---
    if return_on_equity > 0.25:
        roe_score = 3
    elif return_on_equity > 0.15:
        roe_score = 1
    else:
        roe_score = -1

    # --- Valuation (forward P/E penalty for expensive stocks) ---
    if forward_pe is None:
        valuation = -1          # unknown = small penalty
    elif forward_pe < 15:
        valuation = 2           # cheap
    elif forward_pe < 22:
        valuation = 1           # fair
    elif forward_pe < 30:
        valuation = 0           # moderately expensive
    elif forward_pe < 45:
        valuation = -1          # expensive
    else:
        valuation = -3          # very expensive / speculative multiple

    w = FACTOR_WEIGHTS
    weighted_total = (
        growth        * w["growth"]        +
        profitability * w["profitability"] +
        efficiency    * w["efficiency"]    +
        leverage      * w["leverage"]      +
        roe_score     * w["roe"]           +
        valuation     * w["valuation"]
    )

    return {
        "growth":        growth,
        "profitability": profitability,
        "efficiency":    efficiency,
        "leverage":      leverage,
        "roe":           roe_score,
        "valuation":     valuation,
        "total":         weighted_total,
    }


def build_reasoning(ticker, info, scores, intent, volatility, confidence):
    """
    Generate detailed qualitative and quantitative reasoning for a signal.
    Returns a multi-line string suitable for display or logging.
    """
    rev_growth   = info.get("revenueGrowth",   0) or 0
    gross_margin = info.get("grossMargins",     0) or 0
    op_margin    = info.get("operatingMargins", 0) or 0
    d_e          = info.get("debtToEquity",     0) or 0
    roe          = info.get("returnOnEquity",   0) or 0
    fwd_pe       = info.get("forwardPE",     None)
    name         = info.get("shortName",   ticker)
    sector       = info.get("sector",    "Unknown")

    lines = []

    # ── Header ───────────────────────────────────────────────────────────────
    lines.append(f"{name} ({ticker.upper()})  |  {intent}  |  Confidence: {confidence}%  |  Sector: {sector}")
    lines.append("─" * 72)

    # ── Quantitative snapshot ─────────────────────────────────────────────
    lines.append("QUANTITATIVE METRICS")
    lines.append(f"  Revenue Growth     : {rev_growth * 100:+.1f}%   (factor score: {scores['growth']:+d})")
    lines.append(f"  Gross Margin       : {gross_margin * 100:.1f}%    (factor score: {scores['profitability']:+d})")
    lines.append(f"  Operating Margin   : {op_margin * 100:.1f}%    (factor score: {scores['efficiency']:+d})")
    lines.append(f"  Debt / Equity      : {d_e:.1f}     (factor score: {scores['leverage']:+d})")
    lines.append(f"  Return on Equity   : {roe * 100:.1f}%    (factor score: {scores['roe']:+d})")
    pe_str = f"{fwd_pe:.1f}x" if fwd_pe else "N/A"
    lines.append(f"  Forward P/E        : {pe_str:>6}   (factor score: {scores['valuation']:+d})")
    lines.append(f"  Annualised Vol     : {volatility * 100:.1f}%")
    lines.append(f"  Composite Score    : {scores['total']:.2f}  (STRONG BUY ≥ 3.0 | BUY ≥ 1.8 | HOLD ≥ 0.8)")
    lines.append("")

    # ── Factor-by-factor qualitative commentary ───────────────────────────
    lines.append("FACTOR ANALYSIS")

    # Growth
    g = scores["growth"]
    if g == 5:
        lines.append(f"  [GROWTH — EXCEPTIONAL +{g}]  Revenue expanding at {rev_growth*100:.1f}% — well above market "
                     f"average. Strong demand momentum suggests market share gains or a structural tailwind.")
    elif g == 3:
        lines.append(f"  [GROWTH — SOLID +{g}]  Revenue growth of {rev_growth*100:.1f}% is healthy and consistent. "
                     f"Business is expanding but acceleration would be needed to reach top-tier scoring.")
    elif g == 1:
        lines.append(f"  [GROWTH — MODEST +{g}]  Revenue growing at {rev_growth*100:.1f}%. Positive direction but "
                     f"not a differentiating factor at this rate. Watch for acceleration or deceleration.")
    else:
        lines.append(f"  [GROWTH — NEGATIVE {g}]  Revenue contraction of {rev_growth*100:.1f}% is a red flag. "
                     f"Business may be losing pricing power, market share, or facing structural headwinds.")

    # Profitability
    p = scores["profitability"]
    if p == 4:
        lines.append(f"  [PROFITABILITY — EXCEPTIONAL +{p}]  Gross margin of {gross_margin*100:.1f}% reflects a "
                     f"premium-quality business with strong pricing power and durable competitive advantage.")
    elif p == 2:
        lines.append(f"  [PROFITABILITY — GOOD +{p}]  Gross margin of {gross_margin*100:.1f}% is above average. "
                     f"Good product economics, though room exists to reach top-tier efficiency.")
    else:
        lines.append(f"  [PROFITABILITY — WEAK {p}]  Gross margin of {gross_margin*100:.1f}% is below benchmark "
                     f"thresholds. Low margin businesses are highly sensitive to cost shocks and competition.")

    # Efficiency
    e = scores["efficiency"]
    if e == 3:
        lines.append(f"  [EFFICIENCY — STRONG +{e}]  Operating margin of {op_margin*100:.1f}% signals excellent cost "
                     f"control and scalable operations. Every dollar of revenue generates meaningful profit.")
    elif e == 1:
        lines.append(f"  [EFFICIENCY — AVERAGE +{e}]  Operating margin of {op_margin*100:.1f}% is acceptable. "
                     f"Adequate but not best-in-class. Watch for margin expansion or compression trends.")
    else:
        lines.append(f"  [EFFICIENCY — WEAK {e}]  Operating margin of {op_margin*100:.1f}% suggests a high cost "
                     f"structure, heavy investment phase, or pricing pressure squeezing the bottom line.")

    # Leverage
    lev = scores["leverage"]
    if lev == 2:
        lines.append(f"  [BALANCE SHEET — STRONG +{lev}]  D/E of {d_e:.1f} — minimal leverage preserves financial "
                     f"flexibility, reduces bankruptcy risk, and enables opportunistic capital deployment.")
    elif lev == 0:
        lines.append(f"  [BALANCE SHEET — MODERATE {lev}]  D/E of {d_e:.1f} is manageable but warrants monitoring, "
                     f"especially in a rising rate environment where debt servicing costs increase.")
    else:
        lines.append(f"  [BALANCE SHEET — ELEVATED {lev}]  D/E of {d_e:.1f} is high. Elevated leverage amplifies "
                     f"downside risk and constrains the company's ability to weather a downturn.")

    # ROE
    r = scores["roe"]
    if r == 3:
        lines.append(f"  [CAPITAL EFFICIENCY — HIGH +{r}]  ROE of {roe*100:.1f}% demonstrates exceptional ability "
                     f"to generate returns for shareholders. Indicative of a wide-moat business model.")
    elif r == 1:
        lines.append(f"  [CAPITAL EFFICIENCY — MODERATE +{r}]  ROE of {roe*100:.1f}% is adequate. The business "
                     f"earns reasonable returns but is not in the top tier of capital efficiency.")
    else:
        lines.append(f"  [CAPITAL EFFICIENCY — LOW {r}]  ROE of {roe*100:.1f}% suggests the business is not "
                     f"generating sufficient returns on the capital base. Management execution or reinvestment quality is questionable.")

    # Valuation
    v = scores["valuation"]
    if fwd_pe is None:
        lines.append(f"  [VALUATION — UNAVAILABLE {v}]  Forward P/E not available. Valuation risk cannot be "
                     f"assessed — apply a margin-of-safety discount to the overall signal.")
    elif v == 2:
        lines.append(f"  [VALUATION — ATTRACTIVE +{v}]  Forward P/E of {fwd_pe:.1f}x is below 15x — stock appears "
                     f"undervalued relative to earnings. Provides a meaningful margin of safety.")
    elif v == 1:
        lines.append(f"  [VALUATION — FAIR +{v}]  Forward P/E of {fwd_pe:.1f}x — reasonably priced given the "
                     f"growth and quality profile. Not cheap, but not demanding either.")
    elif v == 0:
        lines.append(f"  [VALUATION — STRETCHED {v}]  Forward P/E of {fwd_pe:.1f}x prices in continued execution. "
                     f"Limited margin of safety — any earnings miss could trigger a sharp re-rating.")
    elif v == -1:
        lines.append(f"  [VALUATION — EXPENSIVE {v}]  Forward P/E of {fwd_pe:.1f}x is elevated. The multiple "
                     f"demands flawless growth delivery. Significant downside if guidance disappoints.")
    else:
        lines.append(f"  [VALUATION — VERY EXPENSIVE {v}]  Forward P/E of {fwd_pe:.1f}x is speculative. "
                     f"Stock is priced beyond fundamental justification — high risk of multiple compression.")

    lines.append("")

    # ── Volatility & risk ─────────────────────────────────────────────────
    lines.append("VOLATILITY & RISK CONTEXT")
    vol_pct = volatility * 100
    if volatility < 0.20:
        vol_qual = (f"LOW ({vol_pct:.1f}%). Stable price behaviour — well-suited to income strategies "
                    f"such as covered calls and cash-secured puts.")
    elif volatility < 0.30:
        vol_qual = (f"MODERATE-LOW ({vol_pct:.1f}%). Controlled movement — supports directional "
                    f"options plays with manageable risk.")
    elif volatility < 0.45:
        vol_qual = (f"MODERATE-HIGH ({vol_pct:.1f}%). Meaningful price swings — options premiums "
                    f"are rich but position sizing must account for wider drawdown risk.")
    else:
        vol_qual = (f"HIGH ({vol_pct:.1f}%). Speculative territory — large swings make options "
                    f"expensive and losses can accumulate quickly. Reduce position size accordingly.")
    lines.append(f"  Volatility is {vol_qual}")
    lines.append("")

    # ── Overall verdict ───────────────────────────────────────────────────
    lines.append("SIGNAL VERDICT")
    score = scores["total"]
    if intent == "STRONG BUY":
        lines.append(f"  All major factors align positively (composite: {score:.2f}). {name} demonstrates "
                     f"exceptional fundamentals with controlled volatility — a high-conviction long setup. "
                     f"Options strategy should reflect directional bullish exposure.")
    elif intent == "BUY":
        lines.append(f"  Majority of factors are constructive (composite: {score:.2f}). One or more areas "
                     f"fall short of top-tier thresholds — treat as a quality long with standard position sizing. "
                     f"Valuation or growth rate may be the limiting factor.")
    elif intent == "HOLD":
        lines.append(f"  Mixed signals (composite: {score:.2f}). Fundamentals are adequate but not compelling "
                     f"enough to initiate or add exposure. Suitable for existing holders; new entry requires "
                     f"a catalyst or better valuation entry point.")
    elif intent == "REDUCE":
        lines.append(f"  Weakening fundamentals (composite: {score:.2f}). Consider trimming position size "
                     f"and deploying defensive options strategies such as protective puts or collars.")
    else:
        lines.append(f"  Negative composite score ({score:.2f}) across multiple factors. Avoid new long "
                     f"exposure. Protective puts or an outright exit may be warranted depending on "
                     f"existing position size and tax considerations.")

    return "\n".join(lines)
