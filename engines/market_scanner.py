# engines/market_scanner.py

import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from data.market_data import get_price_history
from data.fundamentals import get_fundamentals


def _price_momentum(ticker):
    """Return 1M, 3M, 6M price returns and 52-week range position (0–100%)."""
    try:
        df = get_price_history(ticker, period="1y")
        closes = df["Close"].dropna()
        if len(closes) < 20:
            return None

        latest = float(closes.iloc[-1])
        lo52   = float(closes.min())
        hi52   = float(closes.max())

        def _ret(days):
            idx = min(days, len(closes) - 1)
            past = float(closes.iloc[-idx])
            return round((latest - past) / past * 100, 2) if past else None

        range_pos = round((latest - lo52) / (hi52 - lo52) * 100, 1) if hi52 != lo52 else 50.0

        return {
            "1M Return (%)":  _ret(21),
            "3M Return (%)":  _ret(63),
            "6M Return (%)":  _ret(126),
            "52W Range Pos (%)": range_pos,
        }
    except Exception:
        return None


def _rsi(ticker, period=14):
    """Calculate 14-day RSI."""
    try:
        df = get_price_history(ticker, period="3mo")
        closes = df["Close"].dropna()
        delta  = closes.diff()
        gain   = delta.clip(lower=0).rolling(period).mean()
        loss   = (-delta.clip(upper=0)).rolling(period).mean()
        rs     = gain / loss.replace(0, np.nan)
        rsi    = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 1)
    except Exception:
        return None


def _scan_single(ticker, run_model, profile):
    """Run the full model + supplementary data for one ticker. Returns row dict or None."""
    try:
        model   = run_model(ticker, profile)
        info    = get_fundamentals(ticker)
        mom     = _price_momentum(ticker)
        rsi_val = _rsi(ticker)

        scores     = model.get("Factor Scores", {})
        market_cap = info.get("marketCap", None)
        mcap_str   = (
            f"${market_cap/1e12:.2f}T" if market_cap and market_cap >= 1e12
            else f"${market_cap/1e9:.1f}B" if market_cap and market_cap >= 1e9
            else "N/A"
        )
        fwd_pe = info.get("forwardPE", None)

        return {
            "Ticker":           ticker.upper(),
            "Name":             info.get("shortName", ticker),
            "Sector":           info.get("sector", "N/A"),
            "Intent":           model["Intent"],
            "Confidence":       model["Confidence"],
            "Composite Score":  round(float(scores.get("total", 0)), 2),
            "Regime":           model["Regime"],
            "Rev Growth (%)":   round((info.get("revenueGrowth",   0) or 0) * 100, 1),
            "Gross Margin (%)": round((info.get("grossMargins",     0) or 0) * 100, 1),
            "Op Margin (%)":    round((info.get("operatingMargins", 0) or 0) * 100, 1),
            "Fwd P/E":          round(fwd_pe, 1) if fwd_pe else "N/A",
            "ROE (%)":          round((info.get("returnOnEquity",   0) or 0) * 100, 1),
            "Market Cap":       mcap_str,
            "Ann. Vol (%)":     round(model["Volatility"] * 100, 1),
            "Risk Flag":        model["Risk Flag"],
            "Position Size (%)": model["Position Size (%)"],
            "1M Ret (%)":       mom["1M Return (%)"]     if mom else "N/A",
            "3M Ret (%)":       mom["3M Return (%)"]     if mom else "N/A",
            "6M Ret (%)":       mom["6M Return (%)"]     if mom else "N/A",
            "52W Range (%)":    mom["52W Range Pos (%)"] if mom else "N/A",
            "RSI-14":           rsi_val if rsi_val else "N/A",
            "Options Strategy": model["Options Strategy"],
            "F:Growth":         scores.get("growth",        0),
            "F:Profitability":  scores.get("profitability", 0),
            "F:Efficiency":     scores.get("efficiency",    0),
            "F:Leverage":       scores.get("leverage",      0),
            "F:ROE":            scores.get("roe",           0),
            "F:Valuation":      scores.get("valuation",     0),
        }
    except Exception:
        return None


def scan_market(tickers, run_model, profile, max_workers=8, progress_cb=None):
    """
    Run the full quant model across a list of tickers in parallel.

    Args:
        tickers      : list of ticker strings
        run_model    : callable(ticker, profile) -> result dict
        profile      : risk profile string
        max_workers  : ThreadPoolExecutor concurrency (default 8)
        progress_cb  : optional callable(completed, total) for UI progress updates

    Returns list of row dicts sorted by Composite Score descending.
    """
    results = []
    total   = len(tickers)
    done    = 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_scan_single, t, run_model, profile): t for t in tickers}
        for future in as_completed(futures):
            row = future.result()
            if row:
                results.append(row)
            done += 1
            if progress_cb:
                progress_cb(done, total)

    return sorted(results, key=lambda x: x["Composite Score"], reverse=True)
