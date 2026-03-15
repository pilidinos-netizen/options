# engines/market_screener.py
"""
Lightweight pre-screener that runs in parallel across a large ticker universe.
Fetches only basic yfinance .info (one network call per ticker) and applies
simple quantitative filters before the expensive full model is invoked.
"""

import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed


def _fetch_basic_info(ticker):
    """Fetch minimal info needed for pre-screening. Returns (ticker, info) or None."""
    try:
        info = yf.Ticker(ticker).info
        return ticker, info
    except Exception:
        return ticker, None


def pre_screen(
    tickers,
    min_market_cap_b=1.0,
    min_avg_volume=500_000,
    sectors=None,
    max_workers=12,
):
    """
    Quickly filter a large universe down to investable candidates.

    Filters applied:
      - Market cap >= min_market_cap_b billion dollars
      - Average daily volume >= min_avg_volume shares
      - Sector inclusion list (None = all sectors)

    Returns a list of dicts with basic stats, sorted by market cap descending.
    Also returns the full count so the UI can show "X of Y passed screen".
    """
    results = []
    failed  = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_basic_info, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, info = future.result()
            if not info:
                failed.append(ticker)
                continue

            market_cap  = info.get("marketCap",     0) or 0
            avg_volume  = info.get("averageVolume",  0) or 0
            sector      = info.get("sector",        "Unknown")
            name        = info.get("shortName",     ticker)
            fwd_pe      = info.get("forwardPE",     None)
            rev_growth  = (info.get("revenueGrowth", 0) or 0) * 100
            gross_margin= (info.get("grossMargins",  0) or 0) * 100

            # Apply filters
            if market_cap < min_market_cap_b * 1e9:
                continue
            if avg_volume < min_avg_volume:
                continue
            if sectors and sector not in sectors:
                continue

            mcap_str = (
                f"${market_cap/1e12:.2f}T" if market_cap >= 1e12
                else f"${market_cap/1e9:.1f}B"
            )

            results.append({
                "Ticker":          ticker,
                "Name":            name,
                "Sector":          sector,
                "Market Cap":      mcap_str,
                "Market Cap (raw)": market_cap,
                "Avg Volume":      avg_volume,
                "Fwd P/E":         round(fwd_pe, 1) if fwd_pe else "N/A",
                "Rev Growth (%)":  round(rev_growth, 1),
                "Gross Margin (%)":round(gross_margin, 1),
            })

    # Sort by market cap descending (largest first as default)
    results.sort(key=lambda x: x["Market Cap (raw)"], reverse=True)
    return results, failed
