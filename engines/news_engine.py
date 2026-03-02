# engines/news_engine.py

import feedparser
import yfinance as yf
from datetime import datetime, timedelta
from textblob import TextBlob


# ------------------------------------------------
# Utility: Sentiment Classification
# ------------------------------------------------
def classify_sentiment(score):
    if score > 0.15:
        return "Positive"
    elif score < -0.15:
        return "Negative"
    return "Neutral"


# ------------------------------------------------
# Ecosystem Mapping (Basic Industry Logic)
# ------------------------------------------------
def get_ecosystem_entities(ticker):
    """
    Basic rule-based ecosystem detection.
    Can be expanded with database mapping later.
    """

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        company = info.get("shortName", ticker)
        industry = info.get("industry", "")
    except Exception:
        company = ticker
        industry = ""

    competitors = []
    suppliers = []

    if "Semiconductor" in industry:
        competitors = ["AMD", "INTC", "TSM"]
        suppliers = ["TSMC", "ASML", "Applied Materials"]

    elif "Software" in industry:
        competitors = ["ORCL", "SAP", "CRM"]
        suppliers = ["Microsoft Azure", "AWS"]

    elif "Automobile" in industry:
        competitors = ["GM", "Ford", "Toyota"]
        suppliers = ["Magna", "Bosch"]

    return {
        "company": company,
        "industry": industry,
        "competitors": competitors,
        "suppliers": suppliers
    }


# ------------------------------------------------
# Financial Announcement Detection
# ------------------------------------------------
def detect_financial_announcements(text):

    text_upper = text.upper()

    keywords = {
        "Earnings Release": ["EARNINGS", "QUARTERLY RESULTS", "EPS"],
        "Guidance Update": ["GUIDANCE", "FORECAST", "OUTLOOK"],
        "Dividend Announcement": ["DIVIDEND"],
        "Stock Split": ["STOCK SPLIT"],
        "Mergers & Acquisitions": ["ACQUIRE", "MERGER", "BUYOUT"],
        "SEC Filing": ["SEC", "10-K", "10-Q"],
        "Pre-Market News": ["PRE-MARKET"],
        "After-Hours News": ["AFTER HOURS"]
    }

    detected = []

    for category, words in keywords.items():
        if any(word in text_upper for word in words):
            detected.append(category)

    return detected


# ------------------------------------------------
# Impact Interpretation
# ------------------------------------------------
def analyze_impact(sentiment_label, announcements):

    base = {}

    if sentiment_label == "Positive":
        base["Company"] = "Positive developments may support stock price."
    elif sentiment_label == "Negative":
        base["Company"] = "Negative developments may pressure stock."
    else:
        base["Company"] = "Limited short-term impact expected."

    if announcements:
        base["Financial Announcement Detected"] = ", ".join(announcements)

    return base


# ------------------------------------------------
# Main News Engine
# ------------------------------------------------
def get_market_news(ticker, days_back=15, max_items=25):

    ticker = ticker.upper()
    ecosystem = get_ecosystem_entities(ticker)

    keywords = [ticker, ecosystem["company"]]
    keywords += ecosystem["competitors"]
    keywords += ecosystem["suppliers"]

    cutoff_date = datetime.now() - timedelta(days=days_back)

    query = " OR ".join(keywords)
    google_rss = f"https://news.google.com/rss/search?q={query}"

    rss_feeds = [
        google_rss,
        "https://finance.yahoo.com/rss/",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"
    ]

    articles = []
    sentiment_scores = []
    detected_announcements = []

    for rss_url in rss_feeds:

        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries:

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                if published and published < cutoff_date:
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", "")
                combined_text = f"{title} {summary}"

                if any(keyword.upper() in combined_text.upper() for keyword in keywords):

                    polarity = TextBlob(combined_text).sentiment.polarity
                    sentiment_scores.append(polarity)

                    announcements = detect_financial_announcements(combined_text)
                    detected_announcements.extend(announcements)

                    articles.append({
                        "Title": title,
                        "Source": feed.feed.get("title", "Unknown Source"),
                        "Link": entry.get("link", ""),
                        "Published": published.strftime("%Y-%m-%d") if published else "N/A",
                        "Announcements": announcements
                    })

        except Exception:
            continue

    if not articles:
        return {
            "Error": f"No significant news found in last {days_back} days.",
            "Articles": [],
            "Sentiment Score": 0,
            "Sentiment Label": "Neutral",
            "Summary": "Limited recent coverage detected.",
            "Impact Analysis": {},
            "Ecosystem": ecosystem
        }

    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
    sentiment_label = classify_sentiment(avg_sentiment)

    summary = (
        f"{len(articles)} relevant articles found in the last {days_back} days. "
        f"Overall sentiment appears {sentiment_label}."
    )

    impact = analyze_impact(sentiment_label, list(set(detected_announcements)))

    return {
        "Articles": articles[:max_items],
        "Sentiment Score": round(avg_sentiment, 3),
        "Sentiment Label": sentiment_label,
        "Summary": summary,
        "Impact Analysis": impact,
        "Ecosystem": ecosystem
    }