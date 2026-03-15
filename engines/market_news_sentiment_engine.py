# engines/market_news_sentiment_engine.py
"""
Broad financial-news sentiment engine.

Fetches from multiple financial news RSS feeds, scores each article with
VADER, detects macro themes, and returns per-source + aggregate market
sentiment suitable for a quant sentiment dashboard.
"""

import feedparser
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# ---------------------------------------------------------------------------
# News sources
# ---------------------------------------------------------------------------

NEWS_SOURCES = {
    "CNBC":             "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "MarketWatch":      "https://feeds.marketwatch.com/marketwatch/topstories/",
    "Yahoo Finance":    "https://finance.yahoo.com/news/rssindex",
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "Bloomberg":        "https://feeds.bloomberg.com/markets/news.rss",
    "CNN Business":     "http://rss.cnn.com/rss/money_markets.rss",
    "Google Finance":   "https://news.google.com/rss/search?q=stock+market+finance&hl=en-US&gl=US&ceid=US:en",
    "Barron's":         "https://www.barrons.com/xml/rss/3_7014.xml",
    "Seeking Alpha":    "https://seekingalpha.com/market_currents.xml",
    "Morningstar":      "https://www.morningstar.com/rss/rss.aspx?categoryId=102",
    "Investopedia":     "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_articles",
    "FT Markets":       "https://www.ft.com/rss/home/europe",
}

# ---------------------------------------------------------------------------
# Macro theme detection
# ---------------------------------------------------------------------------

MACRO_THEMES = {
    "Fed / Rates": [
        "fed", "federal reserve", "fomc", "interest rate", "rate cut",
        "rate hike", "powell", "central bank", "basis points", "yield", "treasury",
    ],
    "Inflation": [
        "inflation", "cpi", "pce", "deflation", "price pressure",
        "consumer prices", "producer prices", "stagflation",
    ],
    "Earnings Season": [
        "earnings", "eps", "revenue", "quarterly results", "beats estimates",
        "misses estimates", "guidance", "profit margin", "analyst estimate",
    ],
    "Recession / Growth": [
        "recession", "gdp", "economic growth", "slowdown", "contraction",
        "expansion", "soft landing", "hard landing",
    ],
    "Geopolitics": [
        "war", "sanctions", "trade war", "tariff", "china", "russia",
        "ukraine", "middle east", "taiwan", "geopolitical", "conflict",
    ],
    "AI / Technology": [
        "artificial intelligence", " ai ", "chip", "semiconductor",
        "nvidia", "chatgpt", "llm", "generative", "machine learning",
    ],
    "Energy": [
        "oil", "crude", "natural gas", "energy", "opec", "petroleum",
        "brent", "wti", "gasoline", "refinery",
    ],
    "Crypto / Digital Assets": [
        "bitcoin", "crypto", "cryptocurrency", "blockchain",
        "ethereum", "btc", "defi", "stablecoin",
    ],
    "Labor Market": [
        "jobs", "unemployment", "payrolls", "labor market",
        "nonfarm", "wage growth", "hiring", "layoffs", "jobless claims",
    ],
    "Housing / Real Estate": [
        "housing", "mortgage", "real estate", "home prices",
        "home sales", "hpi", "existing home", "new home",
    ],
}

# Sentiment signal words to boost headline readability
_BULLISH_WORDS = {
    "rally", "surge", "soar", "gain", "bull", "record high", "breakout",
    "upside", "optimism", "recovery", "rebound", "beats", "outperform",
}
_BEARISH_WORDS = {
    "sell-off", "plunge", "crash", "bear", "decline", "drop", "tumble",
    "fear", "downturn", "recession", "panic", "collapse", "miss", "underperform",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify(score: float) -> str:
    if score >= 0.05:
        return "Bullish"
    elif score <= -0.05:
        return "Bearish"
    return "Neutral"


def _score_text(text: str) -> float:
    return _analyzer.polarity_scores(text)["compound"]


def _detect_themes(text: str) -> list:
    t = text.lower()
    return [theme for theme, kws in MACRO_THEMES.items() if any(k in t for k in kws)]


def _market_bias(text: str) -> str:
    t = text.lower()
    bull = sum(1 for w in _BULLISH_WORDS if w in t)
    bear = sum(1 for w in _BEARISH_WORDS if w in t)
    if bull > bear:
        return "Bullish"
    elif bear > bull:
        return "Bearish"
    return "Neutral"


def _fetch_source(name: str, url: str, days_back: int, max_per_source: int):
    """Fetch and parse one RSS feed. Returns list of article dicts."""
    articles = []
    cutoff = datetime.now() - timedelta(days=days_back)
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        for entry in feed.entries[:max_per_source * 2]:
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            link    = entry.get("link", "")
            text    = f"{title} {summary}"

            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception:
                    pass
            if published and published < cutoff:
                continue

            score  = _score_text(text)
            themes = _detect_themes(text)
            bias   = _market_bias(text)

            articles.append({
                "source":    name,
                "title":     title,
                "link":      link,
                "published": published.strftime("%Y-%m-%d %H:%M") if published else "N/A",
                "sentiment_score": round(score, 3),
                "sentiment_label": _classify(score),
                "market_bias":     bias,
                "themes":          themes,
            })
            if len(articles) >= max_per_source:
                break
    except Exception:
        pass
    return articles


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_market_news_sentiment(
    days_back: int = 3,
    max_per_source: int = 15,
    max_workers: int = 10,
) -> dict:
    """
    Fetch financial news from all configured sources in parallel and
    return a comprehensive market sentiment report.

    Returns
    -------
    dict with keys:
      overall_score         : float  — aggregate VADER compound score
      overall_label         : str    — "Bullish" / "Neutral" / "Bearish"
      overall_bias          : str    — word-frequency based market bias
      articles_analysed     : int
      sources_reached       : list[str]
      sources_failed        : list[str]
      per_source            : dict   — source -> {score, label, article_count, top_headlines}
      theme_breakdown       : list   — [{theme, mentions, avg_sentiment, label}]
      top_bullish_headlines : list   — top 5 most positive headlines
      top_bearish_headlines : list   — top 5 most negative headlines
      all_articles          : list   — full article list (sorted by score desc)
    """
    all_articles   = []
    sources_reached = []
    sources_failed  = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_source, name, url, days_back, max_per_source): name
            for name, url in NEWS_SOURCES.items()
        }
        for future in as_completed(futures):
            name     = futures[future]
            articles = future.result()
            if articles:
                all_articles.extend(articles)
                sources_reached.append(name)
            else:
                sources_failed.append(name)

    if not all_articles:
        return {
            "overall_score":  0.0,
            "overall_label":  "Neutral",
            "overall_bias":   "Neutral",
            "articles_analysed": 0,
            "sources_reached": [],
            "sources_failed":  list(NEWS_SOURCES.keys()),
            "per_source":      {},
            "theme_breakdown": [],
            "top_bullish_headlines": [],
            "top_bearish_headlines": [],
            "all_articles": [],
        }

    # ── Aggregate sentiment ───────────────────────────────────────────────
    scores        = [a["sentiment_score"] for a in all_articles]
    overall_score = round(sum(scores) / len(scores), 3)
    overall_label = _classify(overall_score)

    bias_counts  = Counter(a["market_bias"] for a in all_articles)
    overall_bias = bias_counts.most_common(1)[0][0]

    # ── Per-source breakdown ──────────────────────────────────────────────
    source_groups = defaultdict(list)
    for a in all_articles:
        source_groups[a["source"]].append(a)

    per_source = {}
    for src, arts in source_groups.items():
        src_scores = [a["sentiment_score"] for a in arts]
        avg        = round(sum(src_scores) / len(src_scores), 3)
        per_source[src] = {
            "score":         avg,
            "label":         _classify(avg),
            "article_count": len(arts),
            "top_headlines": [
                {"title": a["title"], "link": a["link"],
                 "published": a["published"], "score": a["sentiment_score"]}
                for a in sorted(arts, key=lambda x: x["published"], reverse=True)[:5]
            ],
        }

    # ── Theme breakdown ───────────────────────────────────────────────────
    theme_scores = defaultdict(list)
    for a in all_articles:
        for t in a["themes"]:
            theme_scores[t].append(a["sentiment_score"])

    theme_breakdown = sorted(
        [
            {
                "theme":         t,
                "mentions":      len(s),
                "avg_sentiment": round(sum(s) / len(s), 3),
                "label":         _classify(sum(s) / len(s)),
            }
            for t, s in theme_scores.items()
        ],
        key=lambda x: x["mentions"],
        reverse=True,
    )

    # ── Top headlines ─────────────────────────────────────────────────────
    sorted_asc  = sorted(all_articles, key=lambda x: x["sentiment_score"])
    sorted_desc = sorted(all_articles, key=lambda x: x["sentiment_score"], reverse=True)

    top_bearish  = [{"title": a["title"], "source": a["source"], "score": a["sentiment_score"], "link": a["link"]} for a in sorted_asc[:5]]
    top_bullish  = [{"title": a["title"], "source": a["source"], "score": a["sentiment_score"], "link": a["link"]} for a in sorted_desc[:5]]

    return {
        "overall_score":         overall_score,
        "overall_label":         overall_label,
        "overall_bias":          overall_bias,
        "articles_analysed":     len(all_articles),
        "sources_reached":       sorted(sources_reached),
        "sources_failed":        sorted(sources_failed),
        "per_source":            per_source,
        "theme_breakdown":       theme_breakdown,
        "top_bullish_headlines": top_bullish,
        "top_bearish_headlines": top_bearish,
        "all_articles":          sorted(all_articles, key=lambda x: x["published"], reverse=True),
    }
