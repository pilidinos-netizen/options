# engines/social_sentiment_engine.py

import praw
from textblob import TextBlob


# 🔐 Replace with your Reddit app credentials
REDDIT_CLIENT_ID = "YOUR_CLIENT_ID"
REDDIT_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDDIT_USER_AGENT = "quant_platform_app"


def get_reddit_sentiment(ticker, limit=30):
    """
    Analyze Reddit posts for ticker sentiment.
    """

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )

        subreddit = reddit.subreddit("wallstreetbets+stocks+investing")

        posts = subreddit.search(ticker, limit=limit)

        sentiments = []
        mentions = 0
        sample_posts = []

        for post in posts:
            text = f"{post.title} {post.selftext}"

            if text.strip():
                blob = TextBlob(text)
                sentiments.append(blob.sentiment.polarity)
                mentions += 1
                sample_posts.append(post.title)

        if mentions == 0:
            return {
                "Mentions": 0,
                "Average Sentiment": 0,
                "Sample Posts": []
            }

        avg_sentiment = sum(sentiments) / len(sentiments)

        return {
            "Mentions": mentions,
            "Average Sentiment": round(avg_sentiment, 3),
            "Sample Posts": sample_posts[:5]
        }

    except Exception as e:
        return {
            "Mentions": 0,
            "Average Sentiment": 0,
            "Error": str(e)
        }