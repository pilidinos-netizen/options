import re
import feedparser
from collections import Counter, defaultdict
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ---------------------------------------
# Initialize Sentiment Model
# ---------------------------------------

analyzer = SentimentIntensityAnalyzer()


# ---------------------------------------
# RSS Sources
# ---------------------------------------

RSS_FEEDS = {
    "stocks": "https://www.reddit.com/r/stocks/.rss",
    "investing": "https://www.reddit.com/r/investing/.rss",
    "wallstreetbets": "https://www.reddit.com/r/wallstreetbets/.rss",
    "finance": "https://www.reddit.com/r/finance/.rss",
    "economy": "https://www.reddit.com/r/economy/.rss",
}


# ---------------------------------------
# Market Terms (relevance filter)
# ---------------------------------------

MARKET_TERMS = {
    "stock","stocks","market","markets","share","shares",
    "earnings","revenue","profit","valuation",
    "bull","bear","bullish","bearish",
    "buy","sell","short","long",
    "options","calls","puts",
    "etf","portfolio","investing","trade","trading",
    "nasdaq","sp500","dow",
    "inflation","interest rate","fed","recession","economy"
}


# ---------------------------------------
# Keywords (themes)
# ---------------------------------------

KEYWORDS = {
    "ai","semiconductor","chip","gpu",
    "inflation","interest","recession",
    "oil","gas","energy","electricity",
    "earnings","guidance","revenue"
}


# ---------------------------------------
# Ticker detection
# ---------------------------------------

TICKER_PATTERN = re.compile(r"\b[A-Z]{2,5}\b")

TICKER_STOPWORDS = {
    "THE","AND","FOR","ARE","BUT","NOT",
    "YOU","ALL","CAN","HAS","HAVE",
    "USA","CEO","GDP","AI"
}


def extract_tickers(text):

    tickers = TICKER_PATTERN.findall(text)

    return [
        t for t in set(tickers)
        if t not in TICKER_STOPWORDS
    ]


# ---------------------------------------
# Keyword extraction
# ---------------------------------------

def extract_keywords(text):

    text_lower = text.lower()

    return [
        kw for kw in KEYWORDS
        if kw in text_lower
    ]


# ---------------------------------------
# Market relevance filter
# ---------------------------------------

def is_market_relevant(text):

    text_lower = text.lower()

    for term in MARKET_TERMS:
        if term in text_lower:
            return True

    return False


# ---------------------------------------
# Clean RSS text
# ---------------------------------------

def extract_text(entry):

    title = entry.get("title", "")

    body_html = ""

    content = entry.get("content")

    if isinstance(content, list) and len(content) > 0:
        body_html = content[0].get("value", "")

    elif "summary" in entry:
        body_html = entry.get("summary", "")

    soup = BeautifulSoup(body_html or "", "html.parser")

    body_text = soup.get_text(" ")

    body_text = re.sub(r"\s+", " ", body_text).strip()

    return f"{title} {body_text}"


# ---------------------------------------
# Sentiment classification
# ---------------------------------------

def classify_sentiment(score):

    if score >= 0.05:
        return "bullish"
    elif score <= -0.05:
        return "bearish"
    return "neutral"


# ---------------------------------------
# Main Engine
# ---------------------------------------

def run_market_sentiment_engine(limit_per_feed=50):

    ticker_counter = Counter()
    keyword_counter = Counter()

    ticker_sentiment_scores = defaultdict(list)

    sentiment_scores = []

    market_posts = []

    for source, url in RSS_FEEDS.items():

        feed = feedparser.parse(url)

        entries = feed.entries[:limit_per_feed]

        print(f"{source}: {len(entries)} articles")

        for entry in entries:

            raw_text = extract_text(entry)

            if not raw_text:
                continue

            # Filter non-market posts
            if not is_market_relevant(raw_text):
                continue

            sentiment = analyzer.polarity_scores(raw_text)

            score = sentiment["compound"]

            sentiment_scores.append(score)

            tickers = extract_tickers(raw_text)

            keywords = extract_keywords(raw_text)

            for t in tickers:
                ticker_counter[t] += 1
                ticker_sentiment_scores[t].append(score)

            for k in keywords:
                keyword_counter[k] += 1

            market_posts.append({
                "title": entry.get("title",""),
                "tickers": tickers,
                "keywords": keywords,
                "sentiment": score,
                "label": classify_sentiment(score)
            })


    # ---------------------------------------
    # Overall Market Sentiment
    # ---------------------------------------

    avg_sentiment = 0

    if sentiment_scores:
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)


    # ---------------------------------------
    # Ticker Sentiment Table
    # ---------------------------------------

    ticker_sentiment_table = []

    for ticker, scores in ticker_sentiment_scores.items():

        avg_score = sum(scores) / len(scores)

        ticker_sentiment_table.append({
            "ticker": ticker,
            "mentions": len(scores),
            "sentiment": round(avg_score,3),
            "label": classify_sentiment(avg_score)
        })


    ticker_sentiment_table = sorted(
        ticker_sentiment_table,
        key=lambda x: x["mentions"],
        reverse=True
    )


    # ---------------------------------------
    # Top Tickers
    # ---------------------------------------

    top_tickers = ticker_counter.most_common(10)


    # ---------------------------------------
    # Top Keywords
    # ---------------------------------------

    top_keywords = keyword_counter.most_common(10)


    # ---------------------------------------
    # Spike Detection
    # ---------------------------------------

    spikes = []

    if ticker_counter:

        avg_mentions = sum(ticker_counter.values()) / len(ticker_counter)

        for ticker, count in ticker_counter.items():

            if count > avg_mentions * 2:

                spikes.append({
                    "ticker": ticker,
                    "mentions": count,
                    "spike_multiple": round(count / avg_mentions,2)
                })


    return {

        "Market Posts": len(market_posts),

        "Market Sentiment Score": round(avg_sentiment,3),

        "Top Tickers": top_tickers,

        "Top Keywords": top_keywords,

        "Ticker Sentiment Table": ticker_sentiment_table,

        "Ticker Spikes": spikes,

        "Sample Posts": market_posts[:5]
    }


# ---------------------------------------
# Run Engine
# ---------------------------------------

# if __name__ == "__main__":

#     result = run_market_sentiment_engine()

#     import json

#     print(json.dumps(result, indent=2))
